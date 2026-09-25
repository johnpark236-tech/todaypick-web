#!/usr/bin/env python3
"""One-shot VM transform updater. Called exclusively by GitHub Actions (todaypick-update-transform)."""
import argparse
import json
import pathlib
import sys

_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from admin_update_transform import batch_update_transforms_for_segment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=pathlib.Path)
    args = parser.parse_args()

    payload = json.loads(args.request.read_text(encoding="utf-8"))
    season = payload["season"]
    segment = payload["segment"]
    updates = payload["updates"]  # [{look_id, display_transform}]
    dry_run = bool(payload.get("dry_run", False))

    results = batch_update_transforms_for_segment(
        season=season,
        segment=segment,
        updates=updates,
        dry_run=dry_run,
    )

    failed = []
    for d in results:
        print(json.dumps(d, ensure_ascii=False))
        if not d.get("success"):
            failed.append(d.get("look_id"))

    if failed:
        print("FAILED_IDS:", failed, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("UPDATE_FAILED:", type(error).__name__, str(error)[:1000], file=sys.stderr)
        sys.exit(1)
