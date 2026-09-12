import argparse
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))

from append_seasonal_catalog_from_staging import (  # noqa: E402
    BUCKET,
    PROJECT,
    get_segment_count,
    publish_segments_from_staging,
    public_url,
    run_gcloud,
    storage_url,
)
from remote_daily_looks import (  # noqa: E402
    CANONICAL_V3_PROFILE,
    FILENAME_RE,
    SourceImage,
    build_review_sheet,
    crop_source_image,
    load_config,
    now_iso,
    season_for_date_folder,
    season_from_match,
    segment_from_match,
    sha256_file,
    today_yymmdd,
    validate_source,
    write_json,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = PROJECT_ROOT / "automation" / "daily_looks" / "runtime" / "cloud_drive_ingest"
LOG_ROOT = PROJECT_ROOT / "automation" / "daily_looks" / "logs"
STATE_DB = RUNTIME_ROOT / "state.sqlite3"
LOCK_PATH = RUNTIME_ROOT / "worker.lock"
DEFAULT_ROOT_FOLDER_ID = "1WvKlV8B3xM9X21vl_47Oh6dTfBDFVUPd"
DEFAULT_POLL_INTERVAL_SECONDS = 120
MASTER_GUIDE_NAME = "TodayPick_2x5_10컷_이미지생성_커팅_지침서_MASTER_v3"
MASTER_GUIDE_VERSION = "v3"
MAX_ATTEMPTS = 3
SOURCE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
TERMINAL_FAILURES = {
    "SOURCE_DECODE_FAILED",
    "INVALID_GRID",
    "CROP_FAILED",
    "CROP_QA_FAILED",
    "WEBP_VALIDATION_FAILED",
    "CATALOG_VALIDATION_FAILED",
    "UNRECOVERABLE_DRIVE_ERROR",
}


@dataclass
class DriveFile:
    id: str
    name: str
    mime_type: str
    modified_time: str
    size: int
    md5_checksum: str
    parent_id: str


def log_event(message, **fields):
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": now_iso(), "message": message, **fields}
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    with (LOG_ROOT / "cloud_drive_auto_ingest.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


def notify_failure(title, fields):
    token = os.environ.get("TODAYPICK_TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TODAYPICK_TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log_event("failure notification skipped", reason="telegram not configured", title=title)
        return "NOT_CONFIGURED"
    text = title + "\n\n" + "\n".join(f"{key}: {value}" for key, value in fields.items())
    data = urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    try:
        req = Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data, method="POST")
        with urlopen(req, timeout=15) as resp:
            return "PASS" if 200 <= resp.status < 300 else f"HTTP_{resp.status}"
    except Exception as exc:
        log_event("failure notification failed", error=str(exc), title=title)
        return "FAILED"


def parse_source_name(filename):
    match = FILENAME_RE.match(filename)
    if not match:
        return None
    gender, age, segment = segment_from_match(match)
    return gender, age, segment, season_from_match(match)


def acquire_lock():
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        pid = int(data.get("pid") or 0)
        if pid and not pid_is_running(pid):
            log_event("stale worker lock removed", lock=str(LOCK_PATH), stale_pid=pid)
            LOCK_PATH.unlink(missing_ok=True)
            fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump({"pid": os.getpid(), "created_at": now_iso()}, fh)
            return True
        log_event("single active worker lock exists", lock=str(LOCK_PATH), holder=data)
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"pid": os.getpid(), "created_at": now_iso()}, fh)
    return True


def pid_is_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def release_lock():
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


class StateStore:
    def __init__(self, path=STATE_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path))
        self.db.row_factory = sqlite3.Row
        self.init_schema()

    def init_schema(self):
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
              drive_file_id TEXT NOT NULL,
              source_sha256 TEXT NOT NULL DEFAULT '',
              drive_parent_folder_id TEXT NOT NULL,
              date_folder TEXT NOT NULL,
              filename TEXT NOT NULL,
              mime_type TEXT NOT NULL,
              modified_time TEXT,
              size INTEGER,
              md5_checksum TEXT,
              season TEXT,
              segment TEXT,
              status TEXT NOT NULL,
              attempt_count INTEGER NOT NULL DEFAULT 0,
              discovered_at TEXT,
              processing_started_at TEXT,
              completed_at TEXT,
              error_code TEXT,
              error_message TEXT,
              catalog_before INTEGER,
              catalog_after INTEGER,
              dlq_path TEXT,
              updated_at TEXT,
              PRIMARY KEY (drive_file_id, source_sha256)
            )
            """
        )
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS heartbeats (
              id INTEGER PRIMARY KEY CHECK (id = 1),
              last_run_at TEXT,
              last_success_at TEXT,
              last_error_at TEXT,
              worker_version TEXT,
              health_status TEXT
            )
            """
        )
        self.db.commit()

    def completed_by_metadata(self, drive_file):
        rows = self.db.execute(
            """
            SELECT 1 FROM sources
            WHERE drive_file_id = ?
              AND status = 'COMPLETED'
              AND COALESCE(md5_checksum, '') = COALESCE(?, '')
              AND COALESCE(size, 0) = COALESCE(?, 0)
              AND COALESCE(modified_time, '') = COALESCE(?, '')
            LIMIT 1
            """,
            (drive_file.id, drive_file.md5_checksum, drive_file.size, drive_file.modified_time),
        ).fetchone()
        return rows is not None

    def get(self, drive_file_id, source_sha256):
        row = self.db.execute(
            "SELECT * FROM sources WHERE drive_file_id = ? AND source_sha256 = ?",
            (drive_file_id, source_sha256),
        ).fetchone()
        return dict(row) if row else None

    def upsert(self, drive_file, source_sha256, date_folder, season, segment, status, **fields):
        now = now_iso()
        existing = self.get(drive_file.id, source_sha256)
        attempt_count = fields.pop("attempt_count", None)
        if attempt_count is None:
            attempt_count = (existing or {}).get("attempt_count", 0)
        values = {
            "drive_file_id": drive_file.id,
            "source_sha256": source_sha256,
            "drive_parent_folder_id": drive_file.parent_id,
            "date_folder": date_folder,
            "filename": drive_file.name,
            "mime_type": drive_file.mime_type,
            "modified_time": drive_file.modified_time,
            "size": drive_file.size,
            "md5_checksum": drive_file.md5_checksum,
            "season": season,
            "segment": segment,
            "status": status,
            "attempt_count": attempt_count,
            "discovered_at": (existing or {}).get("discovered_at") or now,
            "processing_started_at": fields.get("processing_started_at", (existing or {}).get("processing_started_at")),
            "completed_at": fields.get("completed_at", (existing or {}).get("completed_at")),
            "error_code": fields.get("error_code"),
            "error_message": fields.get("error_message"),
            "catalog_before": fields.get("catalog_before", (existing or {}).get("catalog_before")),
            "catalog_after": fields.get("catalog_after", (existing or {}).get("catalog_after")),
            "dlq_path": fields.get("dlq_path", (existing or {}).get("dlq_path")),
            "updated_at": now,
        }
        self.db.execute(
            """
            INSERT INTO sources (
              drive_file_id, source_sha256, drive_parent_folder_id, date_folder, filename,
              mime_type, modified_time, size, md5_checksum, season, segment, status,
              attempt_count, discovered_at, processing_started_at, completed_at,
              error_code, error_message, catalog_before, catalog_after, dlq_path, updated_at
            ) VALUES (
              :drive_file_id, :source_sha256, :drive_parent_folder_id, :date_folder, :filename,
              :mime_type, :modified_time, :size, :md5_checksum, :season, :segment, :status,
              :attempt_count, :discovered_at, :processing_started_at, :completed_at,
              :error_code, :error_message, :catalog_before, :catalog_after, :dlq_path, :updated_at
            )
            ON CONFLICT(drive_file_id, source_sha256) DO UPDATE SET
              status = excluded.status,
              attempt_count = excluded.attempt_count,
              processing_started_at = excluded.processing_started_at,
              completed_at = excluded.completed_at,
              error_code = excluded.error_code,
              error_message = excluded.error_message,
              catalog_before = excluded.catalog_before,
              catalog_after = excluded.catalog_after,
              dlq_path = excluded.dlq_path,
              updated_at = excluded.updated_at
            """,
            values,
        )
        self.db.commit()

    def mark_heartbeat(self, success, error=None, worker_version="cloud-drive-auto-ingest-v2"):
        now = now_iso()
        row = self.db.execute("SELECT * FROM heartbeats WHERE id = 1").fetchone()
        last_success = now if success else (row["last_success_at"] if row else None)
        status = "HEALTHY" if success else "DEGRADED"
        self.db.execute(
            """
            INSERT INTO heartbeats (id, last_run_at, last_success_at, last_error_at, worker_version, health_status)
            VALUES (1, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              last_run_at = excluded.last_run_at,
              last_success_at = excluded.last_success_at,
              last_error_at = excluded.last_error_at,
              worker_version = excluded.worker_version,
              health_status = excluded.health_status
            """,
            (now, last_success, None if success else now, worker_version, status),
        )
        self.db.commit()
        if error:
            log_event("heartbeat error", error=str(error), health_status=status)


class DriveApiClient:
    def __init__(self):
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
        import google.auth

        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/drive"])
        self.service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        self.media_downloader = MediaIoBaseDownload

    def find_child_folder(self, parent_id, name):
        safe_name = name.replace("'", "\\'")
        q = (
            f"'{parent_id}' in parents and trashed = false "
            f"and mimeType = 'application/vnd.google-apps.folder' and name = '{safe_name}'"
        )
        result = self.service.files().list(
            q=q,
            fields="files(id,name,mimeType,modifiedTime)",
            pageSize=10,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        files = result.get("files", [])
        return files[0]["id"] if files else None

    def ensure_child_folder(self, parent_id, name):
        existing = self.find_child_folder(parent_id, name)
        if existing:
            return existing
        body = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
        folder = self.service.files().create(body=body, fields="id", supportsAllDrives=True).execute()
        return folder["id"]

    def list_source_files(self, date_folder_id):
        q = f"'{date_folder_id}' in parents and trashed = false"
        result = self.service.files().list(
            q=q,
            fields="files(id,name,mimeType,modifiedTime,size,md5Checksum,parents)",
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            orderBy="name",
        ).execute()
        sources = []
        for item in result.get("files", []):
            if item.get("mimeType") == "application/vnd.google-apps.folder":
                continue
            parsed = parse_source_name(item.get("name", ""))
            if not parsed:
                continue
            mime_type = item.get("mimeType") or ""
            if mime_type and mime_type not in SOURCE_MIME_TYPES:
                continue
            sources.append(DriveFile(
                id=item["id"],
                name=item["name"],
                mime_type=mime_type,
                modified_time=item.get("modifiedTime", ""),
                size=int(item.get("size", 0) or 0),
                md5_checksum=item.get("md5Checksum", ""),
                parent_id=(item.get("parents") or [date_folder_id])[0],
            ))
        return sources

    def download_file(self, file_id, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)
        with destination.open("wb") as fh:
            downloader = self.media_downloader(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

    def move_file(self, file_id, old_parent_id, new_parent_id):
        self.service.files().update(
            fileId=file_id,
            addParents=new_parent_id,
            removeParents=old_parent_id,
            fields="id,parents",
            supportsAllDrives=True,
        ).execute()


class GcsDlq:
    def __init__(self, bucket=BUCKET):
        self.bucket = bucket

    def write(self, source_path, metadata, error):
        date_folder = metadata["date_folder"]
        segment = metadata["segment"]
        sha = metadata.get("sha256") or "unknown"
        prefix = f"automation/dlq/{date_folder}/{segment}/{sha}"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_copy = root / ("source" + Path(metadata["filename"]).suffix.lower())
            shutil.copy2(source_path, source_copy)
            metadata_path = root / "metadata.json"
            error_path = root / "error.json"
            write_json(metadata_path, metadata)
            write_json(error_path, error)
            run_gcloud(["storage", "cp", str(source_copy), storage_url(f"{prefix}/{source_copy.name}")])
            run_gcloud(["storage", "cp", "--content-type=application/json", str(metadata_path), storage_url(f"{prefix}/metadata.json")])
            run_gcloud(["storage", "cp", "--content-type=application/json", str(error_path), storage_url(f"{prefix}/error.json")])
        return f"gs://{self.bucket}/{prefix}/"


class CloudDriveIngestWorker:
    def __init__(self, drive_client, state_store, dlq, root_folder_id, dry_run=False, drive_move=True):
        self.drive = drive_client
        self.state = state_store
        self.dlq = dlq
        self.root_folder_id = root_folder_id
        self.dry_run = dry_run
        self.drive_move = drive_move
        self.cfg = load_config()
        log_event(
            "master guide preflight",
            master_guide_referenced="YES",
            master_guide_name=MASTER_GUIDE_NAME,
            master_guide_version=MASTER_GUIDE_VERSION,
            crop_profile=CANONICAL_V3_PROFILE,
            canonical_source_size="1280x1168",
            target_output_size=f"{self.cfg['cut_width']}x{self.cfg['cut_height']}",
        )

    def scan_once(self, date_folder):
        date_folder_id = self.drive.find_child_folder(self.root_folder_id, date_folder)
        if not date_folder_id:
            log_event("date folder not found", date_folder=date_folder, root_folder_id=self.root_folder_id)
            return {"date_folder": date_folder, "status": "NO_DAILY_FOLDER", "processed": 0}
        files = self.drive.list_source_files(date_folder_id)
        log_event("cloud drive scan", date_folder=date_folder, date_folder_id=date_folder_id, discovered=len(files))
        results = []
        for drive_file in files:
            if self.state.completed_by_metadata(drive_file):
                log_event("metadata skip completed source", file_id=drive_file.id, filename=drive_file.name)
                results.append({"filename": drive_file.name, "status": "SKIP_COMPLETED_METADATA"})
                continue
            results.append(self.process_file(drive_file, date_folder, date_folder_id))
        return {"date_folder": date_folder, "status": "OK", "processed": len(results), "results": results}

    def process_file(self, drive_file, date_folder, date_folder_id):
        parsed = parse_source_name(drive_file.name)
        if not parsed:
            return {"filename": drive_file.name, "status": "SKIP_NAME"}
        gender, age, segment, season_override = parsed
        season = season_override or season_for_date_folder(date_folder)
        download_dir = RUNTIME_ROOT / "downloads" / date_folder / drive_file.id
        source_path = download_dir / drive_file.name

        self.state.upsert(drive_file, "", date_folder, season, segment, "DISCOVERED")
        self.drive.download_file(drive_file.id, source_path)
        source_sha = sha256_file(source_path)
        prior = self.state.get(drive_file.id, source_sha)
        if prior and prior.get("status") == "COMPLETED":
            log_event("source skipped completed state", file_id=drive_file.id, filename=drive_file.name, sha256=source_sha)
            return {"filename": drive_file.name, "status": "SKIP_COMPLETED_STATE"}

        attempt_count = ((prior or {}).get("attempt_count") or 0) + 1
        self.state.upsert(drive_file, source_sha, date_folder, season, segment, "DOWNLOADED", attempt_count=attempt_count)
        try:
            return self._process_downloaded(drive_file, source_path, source_sha, date_folder, date_folder_id, season, gender, age, segment, attempt_count)
        except Exception as exc:
            error_code = getattr(exc, "error_code", None) or "UNRECOVERABLE_DRIVE_ERROR"
            if attempt_count < MAX_ATTEMPTS and error_code not in TERMINAL_FAILURES:
                self.state.upsert(
                    drive_file,
                    source_sha,
                    date_folder,
                    season,
                    segment,
                    "DISCOVERED",
                    attempt_count=attempt_count,
                    error_code=error_code,
                    error_message=str(exc),
                )
                log_event("source retry scheduled", filename=drive_file.name, segment=segment, attempt_count=attempt_count, error=str(exc))
                return {"filename": drive_file.name, "status": "RETRY", "error": str(exc)}
            dlq_path = self._send_to_dlq(drive_file, source_path, source_sha, date_folder, season, segment, error_code, str(exc), attempt_count)
            self.state.upsert(
                drive_file,
                source_sha,
                date_folder,
                season,
                segment,
                "DLQ",
                attempt_count=attempt_count,
                error_code=error_code,
                error_message=str(exc),
                dlq_path=dlq_path,
            )
            self._move_source(drive_file, date_folder_id, "_Failed")
            notify_failure("TodayPick Ingest Failure", {
                "Date": date_folder,
                "Segment": segment,
                "File": drive_file.name,
                "Stage": error_code,
                "Attempts": attempt_count,
                "DLQ": dlq_path,
                "Result": "production unchanged",
            })
            return {"filename": drive_file.name, "status": "DLQ", "error": str(exc), "dlq": dlq_path}

    def _process_downloaded(self, drive_file, source_path, source_sha, date_folder, date_folder_id, season, gender, age, segment, attempt_count):
        self.state.upsert(drive_file, source_sha, date_folder, season, segment, "VALIDATING", attempt_count=attempt_count)
        ok, reason, image = validate_source(source_path, self.cfg, crop_profile=CANONICAL_V3_PROFILE)
        if not ok:
            raise IngestError("INVALID_GRID", reason)

        self.state.upsert(drive_file, source_sha, date_folder, season, segment, "PROCESSING", attempt_count=attempt_count, processing_started_at=now_iso())
        staging_root = RUNTIME_ROOT / "staging" / f"{date_folder}_{segment}_{source_sha[:12]}"
        review_root = RUNTIME_ROOT / "review"
        cut_dir = staging_root / date_folder / gender / str(age)
        source = SourceImage(
            path=source_path,
            gender=gender,
            age=age,
            segment=segment,
            filename=drive_file.name,
            size=source_path.stat().st_size,
            mtime=source_path.stat().st_mtime,
            sha256=source_sha,
        )
        crop_ok, cut_files, validations = crop_source_image(
            image,
            cut_dir,
            source,
            date_folder,
            self.cfg,
            crop_profile=CANONICAL_V3_PROFILE,
        )
        valid_count = sum(1 for item in validations if item.get("status") == "PASS")
        if not crop_ok or len(cut_files) != 10 or valid_count != 10:
            raise IngestError("CROP_QA_FAILED", f"crops={len(cut_files)} valid={valid_count}")
        build_review_sheet(segment, date_folder, cut_files, review_root, self.cfg)

        before_count = get_segment_count(season, segment)
        self.state.upsert(drive_file, source_sha, date_folder, season, segment, "QA_PASSED", attempt_count=attempt_count, catalog_before=before_count)
        self.state.upsert(drive_file, source_sha, date_folder, season, segment, "PUBLISHING", attempt_count=attempt_count, catalog_before=before_count)
        report = publish_segments_from_staging(date_folder, season, staging_root, segments=[segment], dry_run=self.dry_run)
        result = report["segments"][0]
        after_count = int(result["after"])
        if not self.dry_run and after_count < before_count:
            raise IngestError("CATALOG_VALIDATION_FAILED", f"catalog count regressed {before_count}->{after_count}")

        self.state.upsert(
            drive_file,
            source_sha,
            date_folder,
            season,
            segment,
            "COMPLETED",
            attempt_count=attempt_count,
            completed_at=now_iso(),
            catalog_before=before_count,
            catalog_after=after_count,
        )
        move_result = self._move_source(drive_file, date_folder_id, "_Processed")
        log_event(
            "cloud source completed",
            filename=drive_file.name,
            file_id=drive_file.id,
            segment=segment,
            sha256=source_sha,
            catalog_before=before_count,
            catalog_after=after_count,
            appended=result["appended"],
            skipped_duplicates=result["skipped_duplicates"],
            drive_move=move_result,
        )
        return {
            "filename": drive_file.name,
            "status": "COMPLETED",
            "segment": segment,
            "catalog_before": before_count,
            "catalog_after": after_count,
            "drive_move": move_result,
        }

    def _send_to_dlq(self, drive_file, source_path, source_sha, date_folder, season, segment, error_code, error_message, attempt_count):
        metadata = {
            "date": date_folder,
            "date_folder": date_folder,
            "drive_file_id": drive_file.id,
            "drive_parent_folder_id": drive_file.parent_id,
            "filename": drive_file.name,
            "mime_type": drive_file.mime_type,
            "modified_time": drive_file.modified_time,
            "segment": segment,
            "season": season,
            "sha256": source_sha,
            "attempt_count": attempt_count,
            "failed_stage": error_code,
            "created_at": now_iso(),
        }
        error = {
            "error_code": error_code,
            "error_message": error_message,
            "created_at": now_iso(),
        }
        try:
            return self.dlq.write(source_path, metadata, error)
        except Exception as exc:
            log_event("dlq upload failed", filename=drive_file.name, error=str(exc))
            return "DLQ_UPLOAD_FAILED"

    def _move_source(self, drive_file, date_folder_id, folder_name):
        if not self.drive_move or self.dry_run:
            return "STATE_ONLY"
        try:
            target_folder = self.drive.ensure_child_folder(date_folder_id, folder_name)
            self.drive.move_file(drive_file.id, drive_file.parent_id, target_folder)
            return f"MOVE:{folder_name}"
        except Exception as exc:
            log_event("drive move not supported", filename=drive_file.name, target=folder_name, error=str(exc))
            return "STATE_ONLY"


class IngestError(RuntimeError):
    def __init__(self, error_code, message):
        super().__init__(message)
        self.error_code = error_code


def run_worker(args):
    state = StateStore(Path(args.state_db))
    drive = DriveApiClient()
    worker = CloudDriveIngestWorker(
        drive,
        state,
        GcsDlq(),
        args.root_folder_id,
        dry_run=args.dry_run,
        drive_move=not args.no_drive_move,
    )
    while True:
        date_folder = today_yymmdd(args.date)
        try:
            report = worker.scan_once(date_folder)
            state.mark_heartbeat(success=True)
            log_event("cloud scan completed", **{k: v for k, v in report.items() if k != "results"})
        except Exception as exc:
            state.mark_heartbeat(success=False, error=exc)
            log_event("cloud scan failed", error=str(exc))
            notify_failure("TodayPick Cloud Worker Failure", {
                "Date": date_folder,
                "Stage": "SCAN",
                "Error": str(exc),
            })
        if args.once:
            return 0
        time.sleep(args.poll_interval)


def main():
    parser = argparse.ArgumentParser(description="TodayPick cloud-primary Google Drive API ingest worker.")
    parser.add_argument("--root-folder-id", default=DEFAULT_ROOT_FOLDER_ID)
    parser.add_argument("--date", default=None, help="YYMMDD folder. Defaults to current KST date.")
    parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL_SECONDS)
    parser.add_argument("--state-db", default=str(STATE_DB))
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-drive-move", action="store_true")
    args = parser.parse_args()

    if args.poll_interval < 60 or args.poll_interval > 300:
        raise SystemExit("poll interval must be between 60 and 300 seconds")
    if not acquire_lock():
        return 0
    try:
        return run_worker(args)
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
