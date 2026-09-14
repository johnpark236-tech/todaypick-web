import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT_DIR = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent

BASE_DIR = Path(r"G:\내 드라이브\TodayPick_user_config\260913")
PROC_DIR = BASE_DIR / "_Processed"

TARGET_SOURCES = {
    "female_10": PROC_DIR / "가을_여성10대_260913.png",
    "female_30": PROC_DIR / "가을_여성30대_260913.png",
    "female_40": PROC_DIR / "가을_여성40대_260913.png",
    "female_50": PROC_DIR / "가을_여성50대_260913.png",
    "female_60": PROC_DIR / "가을_여성60대_260913.png",
    "male_10": PROC_DIR / "가을_남성10대_260913.png",
    "male_20": PROC_DIR / "가을_남성20대_260913.png",
    "male_30": PROC_DIR / "가을_남성30대_260913.png",
    "male_40": PROC_DIR / "가을_남성40대_260913.png",
    "male_50": BASE_DIR / "가을_남성50대_260913.png",
    "male_60": PROC_DIR / "가을_남성60대_260913.png",
}

# ABSOLUTE SAFETY RULE: female_20 must never be re-processed
assert "female_20" not in TARGET_SOURCES, "FATAL: female_20 must be excluded from expansion targets!"
assert len(TARGET_SOURCES) == 11, f"Expected 11 targets, got {len(TARGET_SOURCES)}"


def run_segment_ingest(segment: str, source_path: Path, date: str = "260914", dry_run: bool = False):
    if "female_20" in segment:
        raise RuntimeError("FATAL: Attempted to process female_20!")
    gender, age = segment.split("_")
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "one_set_10cut_ingest.py"),
        "--source", str(source_path),
        "--date", date,
        "--season", "autumn",
        "--gender", gender,
        "--age", str(age),
    ]
    if dry_run:
        cmd.append("--dry-run")

    print(f"[{'DRY-RUN' if dry_run else 'INGEST'}] Running {segment}...")
    res = subprocess.run(cmd, text=True, capture_output=True)
    if res.returncode != 0:
        print(f"FAILED {segment}:")
        print(res.stderr or res.stdout)
        raise RuntimeError(f"Ingest failed for {segment}: {res.stderr}")

    try:
        report = json.loads(res.stdout)
    except Exception as e:
        print(f"Invalid JSON output for {segment}: {res.stdout}")
        raise RuntimeError(f"Failed to parse report for {segment}: {e}")

    # Validate report contents
    assert report.get("status") == "OK", f"Expected status OK, got {report.get('status')}"
    assert report.get("catalog_count_delta") == 10, f"Expected delta 10, got {report.get('catalog_count_delta')}"
    assert report.get("new_images_appended") == 10, f"Expected 10 new images, got {report.get('new_images_appended')}"
    assert len(report.get("cuts", [])) == 10, f"Expected 10 cuts, got {len(report.get('cuts', []))}"
    set_id = report.get("set_id")
    sheet_url = report.get("sheet_url")
    assert set_id and set_id.startswith(f"autumn_{segment}_{date}_"), f"Bad set_id: {set_id}"
    assert sheet_url and "sheet.png" in sheet_url, f"Bad sheet_url: {sheet_url}"

    print(f"SUCCESS {segment}: before={report['before_count']} after={report['after_count']} delta={report['catalog_count_delta']} setId={set_id}")
    return report


def main():
    dry_run = "--live" not in sys.argv
    print(f"=== Starting Batch 10-Cut Expansion (dry_run={dry_run}) ===")
    reports = {}
    for segment, source_path in TARGET_SOURCES.items():
        if not source_path.exists():
            raise FileNotFoundError(f"Source sheet for {segment} not found: {source_path}")
        report = run_segment_ingest(segment, source_path, date="260914", dry_run=dry_run)
        reports[segment] = report

    print(f"\nAll 11 segments completed successfully in {'DRY-RUN' if dry_run else 'LIVE'} mode!")
    out_file = SCRIPT_DIR / f"batch_expansion_report_{'dryrun' if dry_run else 'live'}.json"
    out_file.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report written to {out_file}")


if __name__ == "__main__":
    main()
