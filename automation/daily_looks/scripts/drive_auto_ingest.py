import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from append_seasonal_catalog_from_staging import (  # noqa: E402
    get_segment_count,
    publish_segments_from_staging,
)
from remote_daily_looks import (  # noqa: E402
    CANONICAL_V3_PROFILE,
    crop_source_image,
    discover_sources,
    build_review_sheet,
    load_config,
    now_iso,
    season_for_date_folder,
    today_yymmdd,
    validate_source,
    write_json,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = PROJECT_ROOT / "automation" / "daily_looks" / "runtime"
LOG_ROOT = PROJECT_ROOT / "automation" / "daily_looks" / "logs"
LOCK_PATH = RUNTIME_ROOT / "drive_auto_ingest.lock"
LEDGER_PATH = RUNTIME_ROOT / "drive_ingest_ledger.json"
DEFAULT_DRIVE_ROOT = Path(r"G:\내 드라이브\TodayPick_user_config")
DEFAULT_POLL_INTERVAL = 30
MASTER_GUIDE_NAME = "TodayPick_2x5_10컷_이미지생성_커팅_지침서_MASTER_v3"
MASTER_GUIDE_VERSION = "v3"


def log_event(message, **fields):
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": now_iso(), "message": message, **fields}
    with (LOG_ROOT / "drive_auto_ingest.log").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def load_ledger():
    if not LEDGER_PATH.exists():
        return {"sources": {}}
    try:
        return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"sources": {}}


def save_ledger(ledger):
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_json(LEDGER_PATH, ledger)


def pid_is_running(pid):
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        text=True,
        capture_output=True,
    )
    return result.returncode == 0 and str(pid) in result.stdout


def acquire_lock():
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists():
        try:
            data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
            existing_pid = int(data.get("pid", 0))
        except Exception:
            existing_pid = 0
        if pid_is_running(existing_pid):
            log_event("single instance already running", pid=existing_pid, lock=str(LOCK_PATH))
            return False
        LOCK_PATH.unlink(missing_ok=True)
    fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"pid": os.getpid(), "created_at": now_iso()}, fh)
    return True


def release_lock():
    try:
        if LOCK_PATH.exists():
            LOCK_PATH.unlink()
    except OSError:
        pass


def process_source(source, date_folder, cfg, ledger, dry_run=False):
    season = season_for_date_folder(date_folder)
    ledger_key = f"{date_folder}/{source.segment}/{source.sha256}"
    prior = ledger["sources"].get(ledger_key)
    if prior and prior.get("result") == "PUBLISHED":
        log_event(
            "source skipped duplicate",
            date_folder=date_folder,
            filename=source.filename,
            segment=source.segment,
            sha256=source.sha256,
            catalog_count_after=prior.get("catalog_count_after"),
        )
        return {"status": "SKIP_DUPLICATE", "segment": source.segment}

    log_event("source detected", date_folder=date_folder, filename=source.filename, segment=source.segment, sha256=source.sha256)
    ok, reason, image = validate_source(source.path, cfg, crop_profile=CANONICAL_V3_PROFILE)
    if not ok:
        ledger["sources"][ledger_key] = {
            "date_folder": date_folder,
            "filename": source.filename,
            "segment": source.segment,
            "sha256": source.sha256,
            "processed_at": now_iso(),
            "result": "FAILED_SOURCE_VALIDATION",
            "reason": reason,
        }
        save_ledger(ledger)
        log_event("source validation failed", date_folder=date_folder, filename=source.filename, segment=source.segment, reason=reason)
        return {"status": "FAILED", "segment": source.segment, "reason": reason}

    staging_root = RUNTIME_ROOT / "auto_staging" / f"{date_folder}_{source.segment}_{source.sha256[:12]}"
    review_root = RUNTIME_ROOT / "auto_review"
    cut_dir = staging_root / date_folder / source.gender / str(source.age)
    crop_ok, cut_files, validations = crop_source_image(
        image,
        cut_dir,
        source,
        date_folder,
        cfg,
        crop_profile=CANONICAL_V3_PROFILE,
    )
    valid_count = sum(1 for item in validations if item.get("status") == "PASS")
    if not crop_ok or len(cut_files) != 10:
        ledger["sources"][ledger_key] = {
            "date_folder": date_folder,
            "filename": source.filename,
            "segment": source.segment,
            "sha256": source.sha256,
            "processed_at": now_iso(),
            "result": "FAILED_CROP_VALIDATION",
            "crop_validated": valid_count,
        }
        save_ledger(ledger)
        log_event("crop validation failed", date_folder=date_folder, filename=source.filename, segment=source.segment, crops=len(cut_files), validated=valid_count)
        return {"status": "FAILED", "segment": source.segment, "reason": "crop validation failed"}

    review_sheet = build_review_sheet(source.segment, date_folder, cut_files, review_root, cfg)
    before_count = get_segment_count(season, source.segment)
    publish_report = publish_segments_from_staging(
        date_folder,
        season,
        staging_root,
        segments=[source.segment],
        dry_run=dry_run,
    )
    result = publish_report["segments"][0] if publish_report["segments"] else {
        "before": before_count,
        "after": before_count,
        "appended": 0,
        "skipped_duplicates": 0,
    }
    ledger["sources"][ledger_key] = {
        "date_folder": date_folder,
        "filename": source.filename,
        "segment": source.segment,
        "sha256": source.sha256,
        "processed_at": now_iso(),
        "result": "DRY_RUN" if dry_run else "PUBLISHED",
        "catalog_count_before": result["before"],
        "catalog_count_after": result["after"],
        "appended": result["appended"],
        "skipped_duplicates": result["skipped_duplicates"],
        "review_root": str(review_root),
        "review_sheet": str(review_sheet),
        "staging_root": str(staging_root),
    }
    save_ledger(ledger)
    log_event(
        "source processed",
        date_folder=date_folder,
        filename=source.filename,
        segment=source.segment,
        sha256=source.sha256,
        crop_result="PASS",
        crop_validated=valid_count,
        upload_result="DRY_RUN" if dry_run else "PASS",
        catalog_before=result["before"],
        catalog_after=result["after"],
        appended=result["appended"],
        skipped_duplicates=result["skipped_duplicates"],
    )
    return {"status": "OK", "segment": source.segment, **result}


def scan_once(source_root, date_folder, cfg, dry_run=False):
    folder, sources, discovery_status = discover_sources(source_root, date_folder, cfg)
    ledger = load_ledger()
    log_event("scan", date_folder=date_folder, folder=str(folder), discovery_status=discovery_status, discovered=len(sources))
    results = []
    for source in sources:
        results.append(process_source(source, date_folder, cfg, ledger, dry_run=dry_run))
    return {
        "date_folder": date_folder,
        "source_folder": str(folder),
        "discovery_status": discovery_status,
        "discovered": len(sources),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="TodayPick Google Drive auto ingest watcher.")
    parser.add_argument("--source-root", default=str(DEFAULT_DRIVE_ROOT))
    parser.add_argument("--date", default=None, help="YYMMDD folder. Defaults to KST today each scan.")
    parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL)
    parser.add_argument("--once", action="store_true", help="Run one reconciliation scan and exit.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.poll_interval < 30 or args.poll_interval > 60:
        raise SystemExit("poll interval must be between 30 and 60 seconds")
    if not acquire_lock():
        return 0

    cfg = load_config()
    source_root = Path(args.source_root)
    log_event(
        "master guide preflight",
        master_guide_referenced="YES",
        master_guide_name=MASTER_GUIDE_NAME,
        master_guide_version=MASTER_GUIDE_VERSION,
        crop_profile=CANONICAL_V3_PROFILE,
        canonical_source_size="1280x1168",
        target_output_size=f"{cfg['cut_width']}x{cfg['cut_height']}",
    )
    try:
        while True:
            date_folder = today_yymmdd(args.date)
            scan_once(source_root, date_folder, cfg, dry_run=args.dry_run)
            if args.once:
                return 0
            time.sleep(args.poll_interval)
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
