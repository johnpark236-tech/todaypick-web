#!/usr/bin/env python3
"""
Simple Manual Upload Ingest Pipeline  —  v1.0  (2026-09-21)

Input contract (Work Order 260921):
  G:\\내 드라이브\\TodayPick_user_config\\<YYMMDD>\\<f_10|m_60|…>\\ — 10 approved images

Processing:
  classify → normalize to 648×1152 WebP → technical QA → sheet+roundtrip →
  GCS publish → catalog+index update → TodayPick_Fashion patch file

Rules:
  - No single_first subfolder, no season folder required from user
  - Date → Season from YYMMDD month (3-5=spring, 6-8=summer, 9-11=autumn, 12/1/2=winter)
  - Segment from folder name: f_10→female_10, m_60→male_60
  - Originals preserved; normalized copies in YYMMDD/single_first/<season>/<segment>/singles/
  - input_set_hash idempotency: skip if already COMPLETE
  - Stability window: 2 consecutive scans (≥5-minute interval)
  - USER_APPROVED_INPUT: user placement = approval; technical QA still required
  - git commit/push 금지 until explicitly authorized
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

# ── sys.path: allow importing sibling scripts ──────────────────────────────────
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
)
from append_seasonal_catalog_from_staging import (
    CACHE_NO_CACHE,
    public_url,
    publish_index,
    publish_segment,
)
from providers.base_provider import fit_and_save

# ── paths ──────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = _SCRIPT_DIR.parents[2]  # scripts/ → daily_looks/ → automation/ → todaypick-web/
TODAYPICK_FASHION_ROOT = _PROJECT_ROOT.parent / "TodayPick_Fashion"
USER_CONFIG_ROOT = Path(r"G:\내 드라이브\TodayPick_user_config")
RUNTIME_ROOT = _PROJECT_ROOT / "automation" / "daily_looks" / "runtime"
STATE_DB_PATH = RUNTIME_ROOT / "manual_upload_watcher.sqlite3"

# ── constants ──────────────────────────────────────────────────────────────────
SEGMENT_FOLDER_RE = re.compile(r"^(f|m)_(10|20|30|40|50|60)$", re.IGNORECASE)
IMAGE_EXTS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
REQUIRED_IMAGE_COUNT = 10
SCAN_INTERVAL_SECONDS = 300       # 5-minute detection interval
STABILITY_SCANS_REQUIRED = 2      # 2 consecutive stable scans
TECH_QA_CFG = {"cut_width": SINGLE_CUT_WIDTH, "cut_height": SINGLE_CUT_HEIGHT}


# ═══════════════════════════════════════════════════════════════════════════════
# Classification
# ═══════════════════════════════════════════════════════════════════════════════

def classify_segment_folder(folder_name: str) -> str | None:
    """f_10 → female_10,  m_60 → male_60.  Returns None for any unrecognised name."""
    m = SEGMENT_FOLDER_RE.match(folder_name.strip())
    if not m:
        return None
    gender = "female" if m.group(1).lower() == "f" else "male"
    return f"{gender}_{m.group(2)}"


# ═══════════════════════════════════════════════════════════════════════════════
# Image helpers
# ═══════════════════════════════════════════════════════════════════════════════

def scan_image_files(folder: Path) -> list[Path]:
    """Sorted list of image files directly inside folder (non-recursive)."""
    return sorted(
        [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS],
        key=lambda p: p.name,
    )


def compute_input_set_hash(files: list[Path]) -> str:
    """SHA-256 of the concatenation of per-file SHA-256s, sorted by filename."""
    combined = "".join(sha256_file(f) for f in sorted(files, key=lambda p: p.name))
    return hashlib.sha256(combined.encode()).hexdigest()


def normalize_inputs(src_files: list[Path], work_dir: Path) -> list[Path]:
    """
    Contain-fit each source image to 648×1152, save as look_01.webp … look_10.webp
    in work_dir/singles/.  Originals are NOT moved or deleted.
    """
    singles_dir = work_dir / "singles"
    singles_dir.mkdir(parents=True, exist_ok=True)
    output_paths: list[Path] = []
    for i, src in enumerate(src_files, 1):
        out_path = singles_dir / f"look_{i:02d}.webp"
        fit_and_save(src.read_bytes(), out_path, SINGLE_CUT_WIDTH, SINGLE_CUT_HEIGHT)
        output_paths.append(out_path)
    return output_paths


# ═══════════════════════════════════════════════════════════════════════════════
# State DB  (idempotency)
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
    # Persistent stability tracker — survives process restarts between one-shot runs
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


def is_already_processed(con: sqlite3.Connection, input_set_hash: str) -> bool:
    row = con.execute(
        "SELECT status FROM processed_sets WHERE input_set_hash=?",
        (input_set_hash,),
    ).fetchone()
    return row is not None and row[0] == "COMPLETE"


def _upsert_stability(con: sqlite3.Connection, pending: "PendingInput") -> int:
    """Increment scan_count for this hash; returns the new count."""
    now = datetime.now(timezone.utc).isoformat()
    row = con.execute(
        "SELECT scan_count FROM stability_checks WHERE input_set_hash=?",
        (pending.input_set_hash,),
    ).fetchone()
    if row is None:
        con.execute(
            """INSERT INTO stability_checks
                   (input_set_hash, date_folder, segment, season,
                    scan_count, first_seen_at, last_seen_at)
               VALUES (?, ?, ?, ?, 1, ?, ?)""",
            (pending.input_set_hash, pending.date_folder, pending.segment,
             pending.season, now, now),
        )
        count = 1
    else:
        count = row[0] + 1
        con.execute(
            "UPDATE stability_checks SET scan_count=?, last_seen_at=? WHERE input_set_hash=?",
            (count, now, pending.input_set_hash),
        )
    con.commit()
    return count


def _clear_stability(con: sqlite3.Connection, input_set_hash: str) -> None:
    con.execute("DELETE FROM stability_checks WHERE input_set_hash=?", (input_set_hash,))
    con.commit()


def _prune_stale_stability(con: sqlite3.Connection, current_hashes: set[str]) -> None:
    """Remove stability entries whose hash is no longer detected in the input folder."""
    rows = con.execute("SELECT input_set_hash FROM stability_checks").fetchall()
    stale = [r[0] for r in rows if r[0] not in current_hashes]
    for h in stale:
        con.execute("DELETE FROM stability_checks WHERE input_set_hash=?", (h,))
    if stale:
        con.commit()


def record_processing(
    con: sqlite3.Connection,
    input_set_hash: str,
    date_folder: str,
    segment: str,
    season: str,
    gcs_catalog_url: str,
    status: str,
) -> None:
    con.execute(
        """INSERT OR REPLACE INTO processed_sets
               (input_set_hash, date_folder, segment, season,
                processed_at, gcs_catalog_url, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            input_set_hash,
            date_folder,
            segment,
            season,
            datetime.now(timezone.utc).isoformat(),
            gcs_catalog_url,
            status,
        ),
    )
    con.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# Scan
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PendingInput:
    date_folder: str
    seg_folder_name: str
    segment: str
    season: str
    input_set_hash: str
    images: list[Path]


def scan_for_pending_inputs(user_config_root: Path, con: sqlite3.Connection) -> list[PendingInput]:
    """Return PendingInput entries for every valid YYMMDD/f_XX folder with exactly 10 images."""
    result: list[PendingInput] = []
    if not user_config_root.exists():
        return result
    for date_dir in sorted(user_config_root.iterdir()):
        if not (date_dir.is_dir() and re.match(r"^\d{6}$", date_dir.name)):
            continue
        try:
            season = season_for_date_folder(date_dir.name)
        except ValueError:
            continue
        for seg_dir in sorted(date_dir.iterdir()):
            if not seg_dir.is_dir():
                continue
            segment = classify_segment_folder(seg_dir.name)
            if segment is None:
                continue
            images = scan_image_files(seg_dir)
            if len(images) != REQUIRED_IMAGE_COUNT:
                continue
            input_set_hash = compute_input_set_hash(images)
            if is_already_processed(con, input_set_hash):
                continue
            result.append(PendingInput(
                date_folder=date_dir.name,
                seg_folder_name=seg_dir.name,
                segment=segment,
                season=season,
                input_set_hash=input_set_hash,
                images=images,
            ))
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def process_upload(pending: PendingInput, con: sqlite3.Connection, dry_run: bool = False) -> dict:
    """
    Full pipeline for one PendingInput.

    Returns the result dict from publish_segment.
    Raises RuntimeError on any failure.
    """
    date_folder = pending.date_folder
    segment = pending.segment
    season = pending.season
    gender, age_s = segment.split("_")
    age = int(age_s)

    work_dir = USER_CONFIG_ROOT / date_folder / "single_first" / season / segment
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"    [1/6] normalizing {len(pending.images)} images → {work_dir}")
    normalized = normalize_inputs(pending.images, work_dir)

    print("    [2/6] technical QA")
    for i, path in enumerate(normalized, 1):
        ok, reason = technical_validate_cut(path, TECH_QA_CFG)
        if not ok:
            raise RuntimeError(f"look_{i:02d}.webp: technical QA failed: {reason}")

    look_shas = [sha256_file(p) for p in normalized]

    print("    [3/6] composing canonical sheet")
    sheet_path = work_dir / "sheet.png"
    compose_single_cuts_to_canonical_sheet(normalized, sheet_path)

    print("    [4/6] roundtrip verification")
    roundtrip_dir = work_dir / "roundtrip"
    roundtrip = roundtrip_canonical_sheet(sheet_path, roundtrip_dir)
    if len(roundtrip) != REQUIRED_IMAGE_COUNT:
        raise RuntimeError(f"roundtrip produced {len(roundtrip)} cuts, expected {REQUIRED_IMAGE_COUNT}")

    print("    [5/6] building GCS items")
    items: list[dict] = []
    for i, (path, sha) in enumerate(zip(normalized, look_shas), 1):
        object_name = (
            f"production/assets/{season}/{date_folder}/{gender}/{age}"
            f"/look_{i:02d}_{sha[:12]}.webp"
        )
        items.append({
            "id": f"{season}_{segment}_{date_folder}_{i:02d}",
            "url": public_url(object_name),
            "sha256": sha,
            "width": SINGLE_CUT_WIDTH,
            "height": SINGLE_CUT_HEIGHT,
            "source_date": date_folder,
            "index": i,
            "path": str(path),
            "object_name": object_name,
            "generation_method": "manual_upload",
            "pipeline_version": "v3.2",
            "single_first": True,
            "user_approved_input": True,
        })

    print(f"    [6/6] GCS publish (dry_run={dry_run})")
    seg_result = publish_segment(season, date_folder, segment, items, dry_run)
    index_url = publish_index(season, [seg_result], dry_run)

    _write_fashion_patch(date_folder, season, segment, items, work_dir)
    _write_checkpoint(pending, seg_result, index_url, sheet_path, dry_run, work_dir)

    record_processing(
        con,
        pending.input_set_hash,
        date_folder,
        segment,
        season,
        seg_result["url"],
        "COMPLETE",
    )
    return seg_result


def _write_fashion_patch(
    date_folder: str, season: str, segment: str, items: list[dict], work_dir: Path
) -> None:
    """
    Write outfits.ts-compatible patch entries for TodayPick_Fashion.
    Manual apply required (no auto-commit).
    """
    gender, age_s = segment.split("_")
    age = int(age_s)
    entries = [
        {
            "id": f"outfit-{season}-{segment}-{item['index']:02d}",
            "season": season,
            "gender": gender,
            "age": f"{age}s",
            "imageUrl": item["url"],
            "setId": f"{season}_{segment}_{date_folder}",
            "cutIndex": item["index"],
            "source_date": date_folder,
        }
        for item in items
    ]
    patch_path = work_dir / "todaypick_fashion_patch.json"
    patch_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      TodayPick_Fashion patch: {patch_path}")


def _write_checkpoint(
    pending: PendingInput,
    seg_result: dict,
    index_url: str,
    sheet_path: Path,
    dry_run: bool,
    work_dir: Path,
) -> None:
    checkpoint = {
        "segment": f"{pending.season}_{pending.segment}",
        "input_set_hash": pending.input_set_hash,
        "date_folder": pending.date_folder,
        "season": pending.season,
        "pipeline_version": "v3.2",
        "generation_method": "manual_upload",
        "user_approved_input": True,
        "technical_qa": f"{REQUIRED_IMAGE_COUNT}/{REQUIRED_IMAGE_COUNT} PASS",
        "single_count": REQUIRED_IMAGE_COUNT,
        "catalog_publish": "DRY_RUN" if dry_run else "PASS",
        "catalog_url": seg_result["url"],
        "index_url": index_url,
        "dry_run": dry_run,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    cp_path = work_dir / f"{pending.season}_{pending.segment}_COMPLETE.json"
    cp_path.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      checkpoint: {cp_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# Watcher loop  (stability via in-memory scan-count tracking)
# ═══════════════════════════════════════════════════════════════════════════════

def run_watcher(
    dry_run: bool = False,
    one_shot: bool = False,
    user_config_root: Path | None = None,
    state_db_path: Path | None = None,
) -> None:
    """
    Scan every SCAN_INTERVAL_SECONDS.
    An input set must appear unchanged in STABILITY_SCANS_REQUIRED consecutive scans
    before it is processed.

    Stability state is persisted in the SQLite stability_checks table so that
    two separate --one-shot runs correctly accumulate the scan count across
    process restarts (fixes the in-memory-only regression).
    """
    cfg_root = user_config_root or USER_CONFIG_ROOT
    db_path = state_db_path or STATE_DB_PATH
    con = open_db(db_path)

    print(f"[watcher] started — scanning {cfg_root}")
    print(f"[watcher] stability_scans_required={STABILITY_SCANS_REQUIRED}, "
          f"interval={SCAN_INTERVAL_SECONDS}s, dry_run={dry_run}")

    while True:
        try:
            pending_list = scan_for_pending_inputs(cfg_root, con)
            current_hashes = {p.input_set_hash for p in pending_list}

            # Remove stability entries for hashes no longer detected
            _prune_stale_stability(con, current_hashes)

            for pending in pending_list:
                count = _upsert_stability(con, pending)

                if count < STABILITY_SCANS_REQUIRED:
                    print(
                        f"[watcher] {pending.date_folder}/{pending.seg_folder_name} "
                        f"detected (stable={count}/{STABILITY_SCANS_REQUIRED})"
                    )
                    continue

                print(
                    f"[watcher] PROCESSING {pending.date_folder}/{pending.seg_folder_name} "
                    f"→ {pending.season}/{pending.segment}"
                )
                try:
                    result = process_upload(pending, con, dry_run=dry_run)
                    print(
                        f"[watcher] COMPLETE  appended={result['appended']} "
                        f"catalog={result['url']}"
                    )
                    _clear_stability(con, pending.input_set_hash)
                except Exception as exc:
                    print(f"[watcher] FAILED  {pending.segment}: {exc}")
                    record_processing(con, pending.input_set_hash, pending.date_folder,
                                      pending.segment, pending.season, "", "FAILED")
                    _clear_stability(con, pending.input_set_hash)

        except Exception as exc:
            print(f"[watcher] scan error: {exc}")

        if one_shot:
            break
        print(f"[watcher] sleeping {SCAN_INTERVAL_SECONDS}s …")
        time.sleep(SCAN_INTERVAL_SECONDS)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="TodayPick simple manual upload ingest watcher")
    parser.add_argument("--dry-run", action="store_true", help="skip GCS upload")
    parser.add_argument("--one-shot", action="store_true",
                        help="scan once and exit (bypasses stability wait)")
    args = parser.parse_args()
    run_watcher(dry_run=args.dry_run, one_shot=args.one_shot)


if __name__ == "__main__":
    main()
