#!/usr/bin/env python3
"""One-shot VM reassign executor. Called exclusively by GitHub Actions (todaypick-reassign-look)."""
import argparse
import json
import pathlib
import sys

_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from admin_reassign_look import batch_reassign_looks_for_segment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=pathlib.Path)
    args = parser.parse_args()

    payload = json.loads(args.request.read_text(encoding="utf-8"))
    look_ids = payload["look_ids"]
    source_season = payload["source_season"]
    target_season = payload["target_season"]
    segment = payload["segment"]
    dry_run = bool(payload.get("dry_run", False))

    results = batch_reassign_looks_for_segment(
        source_season=source_season,
        target_season=target_season,
        segment=segment,
        look_ids=look_ids,
        dry_run=dry_run,
    )

    failed = []
    for d in results:
        print(json.dumps(d, ensure_ascii=False))
        if not d.get("success"):
            failed.append(d.get("look_id"))

    print(f"\nREASSIGN_SUMMARY: {len(look_ids)} requested, "
          f"{len(look_ids) - len(failed)} succeeded, {len(failed)} failed")
    if failed:
        print("FAILED_IDS:", failed, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("REASSIGN_FAILED:", type(error).__name__, str(error)[:1000], file=sys.stderr)
        sys.exit(1)
