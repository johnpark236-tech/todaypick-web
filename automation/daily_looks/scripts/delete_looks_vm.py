#!/usr/bin/env python3
"""One-shot VM delete executor. Called exclusively by GitHub Actions (todaypick-drive-delete-sync).
Wraps admin_delete_look.delete_look() for each look_id in the request JSON.
"""
import argparse
import json
import pathlib
import sys

_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from admin_delete_look import AdminDeleteRequest, delete_look, STATE_DB_PATH


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=pathlib.Path)
    args = parser.parse_args()

    payload = json.loads(args.request.read_text(encoding="utf-8"))
    look_ids = payload["look_ids"]
    season = payload["season"]
    segment = payload["segment"]
    dry_run = bool(payload.get("dry_run", False))
    skip_drive_backup = bool(payload.get("skip_drive_backup", False))

    _ALREADY_DONE = ("look_id not found in catalog:", "look already tombstoned")

    results = []
    failed = []
    for look_id in look_ids:
        req = AdminDeleteRequest(
            season=season,
            segment=segment,
            look_id=look_id,
            deleted_by="gas_auto",
            dry_run=dry_run,
            skip_drive_backup=skip_drive_backup,
        )
        result = delete_look(req, state_db_path=STATE_DB_PATH)
        d = result.to_dict()
        already_done = not result.success and any(
            result.error and result.error.startswith(pfx) for pfx in _ALREADY_DONE
        )
        if already_done:
            d["success"] = True
            d["already_done"] = True
        results.append(d)
        print(json.dumps(d, ensure_ascii=False))
        if not d["success"]:
            failed.append(look_id)

    print(f"\nDELETE_SUMMARY: {len(look_ids)} requested, "
          f"{len(look_ids) - len(failed)} succeeded, {len(failed)} failed")
    if failed:
        print("FAILED_IDS:", failed, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("DELETE_FAILED:", type(error).__name__, str(error)[:1000], file=sys.stderr)
        sys.exit(1)
