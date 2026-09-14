"""TodayPick Winter Full 12-Segment 10-Cut Batch Expansion Pipeline

Processes all 12 winter segments:
  female_10, female_20, female_30, female_40, female_50, female_60
  male_10, male_20, male_30, male_40, male_50, male_60

Strict Safety Rules:
- Canonical source size: 1313x1198 (5 cols x 2 rows, 10 cuts)
- Real AI source sheets only (no placeholders)
- Fail closed on any missing source, invalid size, upload or cut error
- Append-only to GCS winter catalogs
- Existing legacy images preserved (e.g. female_10 10 legacy items)
- Autumn data never touched
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
ROOT_DIR = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent

ALL_WINTER_SEGMENTS = [
    "female_10", "female_20", "female_30", "female_40", "female_50", "female_60",
    "male_10", "male_20", "male_30", "male_40", "male_50", "male_60",
]

SEGMENT_TO_KR = {
    "female_10": "여성10대", "female_20": "여성20대", "female_30": "여성30대",
    "female_40": "여성40대", "female_50": "여성50대", "female_60": "여성60대",
    "male_10": "남성10대", "male_20": "남성20대", "male_30": "남성30대",
    "male_40": "남성40대", "male_50": "남성50대", "male_60": "남성60대",
}

CANONICAL_WIDTH = 1313
CANONICAL_HEIGHT = 1198


def discover_source_sheet(base_dir: Path, segment: str, date: str) -> Path | None:
    """Find source sheet for a given segment in base_dir or base_dir/_Processed."""
    kr_name = SEGMENT_TO_KR[segment]
    proc_dir = base_dir / "_Processed" if (base_dir / "_Processed").is_dir() else base_dir
    candidates = [
        proc_dir / f"겨울_{kr_name}_{date}.png",
        base_dir / f"겨울_{kr_name}_{date}.png",
        proc_dir / f"겨울_{kr_name}.png",
        base_dir / f"겨울_{kr_name}.png",
        proc_dir / f"winter_{segment}_{date}.png",
        base_dir / f"winter_{segment}_{date}.png",
        proc_dir / f"winter_{kr_name}.png",
        base_dir / f"winter_{kr_name}.png",
        proc_dir / f"winter_{segment}.png",
        base_dir / f"winter_{segment}.png",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def validate_source_sheet(source_path: Path) -> tuple[bool, str, dict]:
    """Strictly validates source sheet against canonical requirements."""
    if not source_path.exists():
        return False, f"File does not exist: {source_path}", {}
    try:
        with Image.open(source_path) as im:
            width, height = im.size
            if width != CANONICAL_WIDTH or height != CANONICAL_HEIGHT:
                return False, f"Non-canonical dimension: {width}x{height} (expected {CANONICAL_WIDTH}x{CANONICAL_HEIGHT})", {}
        data = source_path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        meta = {
            "path": str(source_path),
            "size": len(data),
            "sha256": sha,
            "width": width,
            "height": height,
        }
        return True, "OK", meta
    except Exception as e:
        return False, f"Error validating source sheet: {e}", {}


def run_segment_ingest(segment: str, source_path: Path, date: str, dry_run: bool = False):
    """Executes one_set_10cut_ingest.py for a single winter segment."""
    gender, age = segment.split("_")
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "one_set_10cut_ingest.py"),
        "--source", str(source_path),
        "--date", date,
        "--season", "winter",
        "--gender", gender,
        "--age", str(age),
    ]
    if dry_run:
        cmd.append("--dry-run")

    print(f"[{'DRY-RUN' if dry_run else 'INGEST'}] Running winter {segment} from {source_path.name}...")
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

    assert report.get("status") == "OK", f"Expected status OK, got {report.get('status')}"
    assert report.get("catalog_count_delta") == 10, f"Expected delta 10, got {report.get('catalog_count_delta')}"
    assert report.get("new_images_appended") == 10, f"Expected 10 new images, got {report.get('new_images_appended')}"
    assert len(report.get("cuts", [])) == 10, f"Expected 10 cuts, got {len(report.get('cuts', []))}"
    set_id = report.get("set_id")
    sheet_url = report.get("sheet_url")
    assert set_id and set_id.startswith(f"winter_{segment}_{date}_"), f"Bad set_id: {set_id}"
    assert sheet_url and "sheet.png" in sheet_url, f"Bad sheet_url: {sheet_url}"

    print(f"SUCCESS {segment}: before={report['before_count']} after={report['after_count']} delta={report['catalog_count_delta']} setId={set_id}")
    return report


def main():
    parser = argparse.ArgumentParser(description="TodayPick Winter Full 12-Segment 10-Cut Expansion")
    parser.add_argument("--base-dir", default=r"G:\내 드라이브\TodayPick_user_config\260914", help="Base directory containing winter sheets")
    parser.add_argument("--date", default="260914", help="Source date YYMMDD")
    parser.add_argument("--live", action="store_true", help="Execute live ingest against GCS (default is dry-run)")
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    dry_run = not args.live
    print(f"=== TodayPick Winter 12-Segment Batch Ingest (dry_run={dry_run}, base_dir={base_dir}, date={args.date}) ===")

    manifest = {}
    missing_sources = []
    invalid_sources = []

    for seg in ALL_WINTER_SEGMENTS:
        src = discover_source_sheet(base_dir, seg, args.date)
        if not src:
            missing_sources.append(seg)
            continue
        valid, reason, meta = validate_source_sheet(src)
        if not valid:
            invalid_sources.append((seg, str(src), reason))
        else:
            manifest[seg] = meta

    if missing_sources or invalid_sources:
        print("\nFATAL: Source verification failed closed!")
        if missing_sources:
            print(f"Missing source sheets for {len(missing_sources)} segments: {', '.join(missing_sources)}")
        if invalid_sources:
            for seg, path, reason in invalid_sources:
                print(f"Invalid source sheet for {seg} ({path}): {reason}")
        print(f"\nDiscovered valid: {len(manifest)}/12 segments.")
        sys.exit(1)

    print(f"All 12 winter source sheets verified: CANONICAL 1313x1198. Proceeding with {'DRY-RUN' if dry_run else 'LIVE'} ingest...")

    reports = {}
    for seg in ALL_WINTER_SEGMENTS:
        src_path = Path(manifest[seg]["path"])
        report = run_segment_ingest(seg, src_path, date=args.date, dry_run=dry_run)
        reports[seg] = report

    out_file = SCRIPT_DIR / f"batch_winter_report_{'dryrun' if dry_run else 'live'}.json"
    out_file.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nAll 12 winter segments successfully processed! Report written to {out_file}")


if __name__ == "__main__":
    main()
