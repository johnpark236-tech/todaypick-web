#!/usr/bin/env python3
"""
Cloud Single-First Watcher — v1.0 (2026-09-22)

GCP VM용 Google Drive 기반 SINGLE-FIRST v3.2 자동 인제스트 워처.

동작:
  1. Drive API로 TodayPick_user_config/YYMMDD/f_10…m_60 세그먼트 폴더를 스캔
  2. 세그먼트 폴더에 정확히 10장 이미지가 있으면 업로드 안정성 검사 (2회 연속)
  3. 통과 시 SINGLE-FIRST v3.2 파이프라인 실행
     normalize → technical QA → sheet → roundtrip → GCS 게시 → 카탈로그/인덱스 갱신
  4. SQLite로 안정성 및 중복 처리 방지

사용:
  python cloud_single_first_watcher.py [--once] [--dry-run] [--date YYMMDD]
  python cloud_single_first_watcher.py --poll-interval 300

보안:
  - 실제 API 키를 코드/로그에 출력하지 않는다
  - 기존 production 데이터를 삭제하거나 덮어쓰지 않는다
  - git commit/push는 수동 승인 후 수행한다
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import sqlite3
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# ── sys.path ────────────────────────────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from remote_daily_looks import (
    SINGLE_CUT_HEIGHT,
    SINGLE_CUT_WIDTH,
    compose_single_cuts_to_canonical_sheet,
    roundtrip_canonical_sheet,
    season_for_date_folder,
    sha256_file,
    technical_validate_cut,
    today_yymmdd,
)
from append_seasonal_catalog_from_staging import (
    public_url,
    publish_index,
    publish_segment,
)
from providers.base_provider import fit_and_save

# ── paths ───────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = _SCRIPT_DIR.parents[2]
RUNTIME_ROOT = _PROJECT_ROOT / "automation" / "daily_looks" / "runtime" / "cloud_single_first"
LOG_ROOT = _PROJECT_ROOT / "automation" / "daily_looks" / "logs"
STATE_DB = RUNTIME_ROOT / "state.sqlite3"
LOCK_PATH = RUNTIME_ROOT / "worker.lock"

# ── constants ───────────────────────────────────────────────────────────────────
DEFAULT_ROOT_FOLDER_ID = "1WvKlV8B3xM9X21vl_47Oh6dTfBDFVUPd"  # TodayPick_user_config
DEFAULT_POLL_INTERVAL = 300  # 5 minutes
STABILITY_SCANS_REQUIRED = 2
REQUIRED_IMAGE_COUNT = 10
SEGMENT_FOLDER_RE = re.compile(r"^(f|m)_(10|20|30|40|50|60)$", re.IGNORECASE)
SOURCE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
IMAGE_EXTS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
TECH_QA_CFG = {"cut_width": SINGLE_CUT_WIDTH, "cut_height": SINGLE_CUT_HEIGHT}
KST = ZoneInfo("Asia/Seoul")


# ═══════════════════════════════════════════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════════════════════════════════════════

def log(message: str, **fields):
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": datetime.now(timezone.utc).isoformat(), "message": message, **fields}
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    with (LOG_ROOT / "cloud_single_first_watcher.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Lock
# ═══════════════════════════════════════════════════════════════════════════════

def _pid_alive(pid: int) -> bool:
    try:
        import os
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_lock() -> bool:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    import os
    try:
        fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        pid = int(data.get("pid") or 0)
        if pid and not _pid_alive(pid):
            LOCK_PATH.unlink(missing_ok=True)
            fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump({"pid": os.getpid(), "created_at": datetime.now(timezone.utc).isoformat()}, fh)
            return True
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"pid": os.getpid(), "created_at": datetime.now(timezone.utc).isoformat()}, fh)
    return True


def release_lock():
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# Drive API
# ═══════════════════════════════════════════════════════════════════════════════

class DriveClient:
    def __init__(self):
        from googleapiclient.discovery import build
        import google.auth
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/drive"])
        self.svc = build("drive", "v3", credentials=creds, cache_discovery=False)
        from googleapiclient.http import MediaIoBaseDownload
        self._MediaIoBaseDownload = MediaIoBaseDownload

    def find_folder(self, parent_id: str, name: str) -> str | None:
        q = (
            f"'{parent_id}' in parents and trashed = false "
            f"and mimeType = 'application/vnd.google-apps.folder' and name = '{name}'"
        )
        r = self.svc.files().list(
            q=q, fields="files(id,name)", pageSize=5,
            supportsAllDrives=True, includeItemsFromAllDrives=True,
        ).execute()
        files = r.get("files", [])
        return files[0]["id"] if files else None

    def list_segment_folders(self, date_folder_id: str) -> list[dict]:
        """List all f_10…m_60 subfolders inside the date folder."""
        q = (
            f"'{date_folder_id}' in parents and trashed = false "
            f"and mimeType = 'application/vnd.google-apps.folder'"
        )
        r = self.svc.files().list(
            q=q, fields="files(id,name)", pageSize=20,
            supportsAllDrives=True, includeItemsFromAllDrives=True, orderBy="name",
        ).execute()
        return [
            f for f in r.get("files", [])
            if SEGMENT_FOLDER_RE.match(f["name"])
        ]

    def list_image_files(self, folder_id: str) -> list[dict]:
        """List image files directly in folder_id."""
        q = f"'{folder_id}' in parents and trashed = false"
        r = self.svc.files().list(
            q=q,
            fields="files(id,name,mimeType,size,md5Checksum,modifiedTime)",
            pageSize=30,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            orderBy="name",
        ).execute()
        files = []
        for item in r.get("files", []):
            mime = item.get("mimeType", "")
            if mime == "application/vnd.google-apps.folder":
                continue
            suffix = Path(item["name"]).suffix.lower()
            if mime not in SOURCE_MIME_TYPES and suffix not in IMAGE_EXTS:
                continue
            files.append(item)
        return files

    def download(self, file_id: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = self.svc.files().get_media(fileId=file_id, supportsAllDrives=True)
        buf = io.BytesIO()
        downloader = self._MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        dest.write_bytes(buf.getvalue())


# ═══════════════════════════════════════════════════════════════════════════════
# Segment classification
# ═══════════════════════════════════════════════════════════════════════════════

def classify_segment(folder_name: str) -> str | None:
    m = SEGMENT_FOLDER_RE.match(folder_name.strip())
    if not m:
        return None
    gender = "female" if m.group(1).lower() == "f" else "male"
    return f"{gender}_{m.group(2)}"


# ═══════════════════════════════════════════════════════════════════════════════
# State DB
# ═══════════════════════════════════════════════════════════════════════════════

def open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.execute("""
        CREATE TABLE IF NOT EXISTS processed_sets (
            input_set_hash TEXT PRIMARY KEY,
            date_folder    TEXT NOT NULL,
            segment        TEXT NOT NULL,
            season         TEXT NOT NULL,
            processed_at   TEXT NOT NULL,
            gcs_catalog_url TEXT,
            status         TEXT NOT NULL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS stability_checks (
            input_set_hash TEXT PRIMARY KEY,
            date_folder    TEXT NOT NULL,
            segment        TEXT NOT NULL,
            season         TEXT NOT NULL,
            scan_count     INTEGER NOT NULL DEFAULT 1,
            first_seen_at  TEXT NOT NULL,
            last_seen_at   TEXT NOT NULL
        )
    """)
    con.commit()
    return con


def is_processed(con: sqlite3.Connection, h: str) -> bool:
    row = con.execute("SELECT status FROM processed_sets WHERE input_set_hash=?", (h,)).fetchone()
    return row is not None and row[0] == "COMPLETE"


def upsert_stability(con: sqlite3.Connection, h: str, date_folder: str, segment: str, season: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    row = con.execute("SELECT scan_count FROM stability_checks WHERE input_set_hash=?", (h,)).fetchone()
    if row is None:
        con.execute(
            "INSERT INTO stability_checks (input_set_hash, date_folder, segment, season, scan_count, first_seen_at, last_seen_at) VALUES (?,?,?,?,1,?,?)",
            (h, date_folder, segment, season, now, now),
        )
        count = 1
    else:
        count = row[0] + 1
        con.execute("UPDATE stability_checks SET scan_count=?, last_seen_at=? WHERE input_set_hash=?", (count, now, h))
    con.commit()
    return count


def clear_stability(con: sqlite3.Connection, h: str):
    con.execute("DELETE FROM stability_checks WHERE input_set_hash=?", (h,))
    con.commit()


def prune_stale_stability(con: sqlite3.Connection, current: set[str]):
    rows = con.execute("SELECT input_set_hash FROM stability_checks").fetchall()
    stale = [r[0] for r in rows if r[0] not in current]
    for h in stale:
        con.execute("DELETE FROM stability_checks WHERE input_set_hash=?", (h,))
    if stale:
        con.commit()


def record_complete(con: sqlite3.Connection, h: str, date_folder: str, segment: str, season: str, catalog_url: str):
    con.execute(
        "INSERT OR REPLACE INTO processed_sets (input_set_hash, date_folder, segment, season, processed_at, gcs_catalog_url, status) VALUES (?,?,?,?,?,?,?)",
        (h, date_folder, segment, season, datetime.now(timezone.utc).isoformat(), catalog_url, "COMPLETE"),
    )
    con.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# Pending input (Drive-based)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DriveSegmentPending:
    date_folder: str
    seg_folder_name: str
    seg_folder_id: str
    segment: str
    season: str
    drive_files: list[dict]    # [{id, name, md5Checksum, ...}]
    input_set_hash: str        # SHA-256 of sorted md5 checksums


def compute_drive_set_hash(files: list[dict]) -> str:
    """SHA-256 of sorted md5 checksums (proxy for file content fingerprint)."""
    checksums = sorted(f.get("md5Checksum", f["id"]) for f in files)
    return hashlib.sha256("".join(checksums).encode()).hexdigest()


def scan_drive_pending(
    drive: DriveClient,
    root_folder_id: str,
    date_folder: str,
    con: sqlite3.Connection,
) -> list[DriveSegmentPending]:
    result: list[DriveSegmentPending] = []

    try:
        season = season_for_date_folder(date_folder)
    except ValueError:
        log("bad date folder", date_folder=date_folder)
        return result

    date_folder_id = drive.find_folder(root_folder_id, date_folder)
    if not date_folder_id:
        log("date folder not found in drive", date_folder=date_folder, root=root_folder_id)
        return result

    seg_folders = drive.list_segment_folders(date_folder_id)
    log("scan drive", date_folder=date_folder, segment_folders=len(seg_folders))

    for sf in seg_folders:
        segment = classify_segment(sf["name"])
        if not segment:
            continue
        try:
            images = drive.list_image_files(sf["id"])
        except Exception as exc:
            log("list images failed", segment=sf["name"], error=str(exc))
            continue

        if len(images) != REQUIRED_IMAGE_COUNT:
            if images:
                log("waiting upload", segment=sf["name"], count=len(images), needed=REQUIRED_IMAGE_COUNT)
            continue

        h = compute_drive_set_hash(images)
        if is_processed(con, h):
            continue

        result.append(DriveSegmentPending(
            date_folder=date_folder,
            seg_folder_name=sf["name"],
            seg_folder_id=sf["id"],
            segment=segment,
            season=season,
            drive_files=images,
            input_set_hash=h,
        ))

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Download + pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def _download_segment(drive: DriveClient, pending: DriveSegmentPending, dl_dir: Path) -> list[Path]:
    """Download 10 images to dl_dir/look_01..look_10.ext (preserve names for hash stability)."""
    dl_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for f in sorted(pending.drive_files, key=lambda x: x["name"]):
        dest = dl_dir / f["name"]
        if not dest.exists():
            drive.download(f["id"], dest)
        paths.append(dest)
    return sorted(paths, key=lambda p: p.name)


def process_pending(
    pending: DriveSegmentPending,
    drive: DriveClient,
    con: sqlite3.Connection,
    work_root: Path,
    dry_run: bool = False,
) -> dict:
    """
    Full SINGLE-FIRST v3.2 pipeline for one Drive segment.
    Returns the result dict from publish_segment.
    """
    date_folder = pending.date_folder
    segment = pending.segment
    season = pending.season
    gender, age_s = segment.split("_")
    age = int(age_s)

    work_dir = work_root / date_folder / "single_first" / season / segment
    work_dir.mkdir(parents=True, exist_ok=True)

    dl_dir = work_root / date_folder / "downloads" / pending.seg_folder_name
    log("step 0: downloading", segment=segment, date=date_folder)
    src_files = _download_segment(drive, pending, dl_dir)

    # 1. Normalize → 648×1152 WebP
    log("step 1: normalize", segment=segment)
    singles_dir = work_dir / "singles"
    singles_dir.mkdir(parents=True, exist_ok=True)
    normalized: list[Path] = []
    for i, src in enumerate(src_files, 1):
        out = singles_dir / f"look_{i:02d}.webp"
        fit_and_save(src.read_bytes(), out, SINGLE_CUT_WIDTH, SINGLE_CUT_HEIGHT)
        normalized.append(out)

    # 2. Technical QA
    log("step 2: technical QA", segment=segment)
    for i, path in enumerate(normalized, 1):
        ok, reason = technical_validate_cut(path, TECH_QA_CFG)
        if not ok:
            raise RuntimeError(f"look_{i:02d}.webp: technical QA failed: {reason}")

    look_shas = [sha256_file(p) for p in normalized]

    # 3. Canonical sheet
    log("step 3: compose sheet", segment=segment)
    sheet_path = work_dir / "sheet.png"
    compose_single_cuts_to_canonical_sheet(normalized, sheet_path)

    # 4. Roundtrip
    log("step 4: roundtrip", segment=segment)
    roundtrip_dir = work_dir / "roundtrip"
    roundtrip = roundtrip_canonical_sheet(sheet_path, roundtrip_dir)
    if len(roundtrip) != REQUIRED_IMAGE_COUNT:
        raise RuntimeError(f"roundtrip: expected {REQUIRED_IMAGE_COUNT}, got {len(roundtrip)}")

    # 5. Build GCS items
    log("step 5: build items", segment=segment)
    items: list[dict] = []
    for i, (path, sha) in enumerate(zip(normalized, look_shas), 1):
        obj = f"production/assets/{season}/{date_folder}/{gender}/{age}/look_{i:02d}_{sha[:12]}.webp"
        items.append({
            "id": f"{season}_{segment}_{date_folder}_{i:02d}",
            "url": public_url(obj),
            "sha256": sha,
            "width": SINGLE_CUT_WIDTH,
            "height": SINGLE_CUT_HEIGHT,
            "source_date": date_folder,
            "index": i,
            "path": str(path),
            "object_name": obj,
            "generation_method": "manual_upload",
            "pipeline_version": "v3.2",
            "single_first": True,
            "user_approved_input": True,
        })

    # 6. GCS publish
    log("step 6: GCS publish", segment=segment, dry_run=dry_run)
    seg_result = publish_segment(season, date_folder, segment, items, dry_run)
    index_url = publish_index(season, [seg_result], dry_run)

    # Checkpoint
    checkpoint = {
        "segment": f"{season}_{segment}",
        "input_set_hash": pending.input_set_hash,
        "date_folder": date_folder,
        "season": season,
        "pipeline_version": "v3.2",
        "generation_method": "manual_upload",
        "user_approved_input": True,
        "technical_qa": f"{REQUIRED_IMAGE_COUNT}/{REQUIRED_IMAGE_COUNT} PASS",
        "ai_visual_qa": "NOT_PERFORMED",
        "single_count": REQUIRED_IMAGE_COUNT,
        "catalog_publish": "DRY_RUN" if dry_run else "PASS",
        "catalog_url": seg_result["url"],
        "index_url": index_url,
        "dry_run": dry_run,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    cp_path = work_dir / f"{season}_{segment}_COMPLETE.json"
    cp_path.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")

    record_complete(con, pending.input_set_hash, date_folder, segment, season, seg_result["url"])

    log(
        "SEGMENT_COMPLETE",
        segment=segment,
        date_folder=date_folder,
        season=season,
        catalog_url=seg_result["url"],
        index_url=index_url,
        dry_run=dry_run,
    )
    return seg_result


# ═══════════════════════════════════════════════════════════════════════════════
# Main loop
# ═══════════════════════════════════════════════════════════════════════════════

def run_watcher(args) -> int:
    con = open_db(STATE_DB)
    drive = DriveClient()
    work_root = RUNTIME_ROOT / "work"

    log("watcher_start", poll_interval=args.poll_interval, dry_run=args.dry_run)

    while True:
        date_folder = today_yymmdd(args.date)
        try:
            pending_list = scan_drive_pending(drive, args.root_folder_id, date_folder, con)
            current_hashes = {p.input_set_hash for p in pending_list}
            prune_stale_stability(con, current_hashes)

            for pending in pending_list:
                count = upsert_stability(con, pending.input_set_hash, pending.date_folder, pending.segment, pending.season)
                if count < STABILITY_SCANS_REQUIRED:
                    log("waiting_stability", segment=pending.seg_folder_name, count=count, required=STABILITY_SCANS_REQUIRED)
                    continue

                log("processing", segment=pending.segment, date=pending.date_folder, season=pending.season)
                try:
                    process_pending(pending, drive, con, work_root, dry_run=args.dry_run)
                    clear_stability(con, pending.input_set_hash)
                except Exception as exc:
                    log("process_error", segment=pending.segment, error=str(exc))

        except Exception as exc:
            log("scan_error", error=str(exc))

        if args.once:
            return 0
        time.sleep(args.poll_interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="TodayPick cloud single-first Drive watcher")
    parser.add_argument("--root-folder-id", default=DEFAULT_ROOT_FOLDER_ID)
    parser.add_argument("--date", default=None, help="YYMMDD override")
    parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not acquire_lock():
        log("already_running", lock=str(LOCK_PATH))
        return 0
    try:
        return run_watcher(args)
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
