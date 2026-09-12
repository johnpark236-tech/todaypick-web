import argparse
import base64
import json
import re
import subprocess
import tempfile
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

from remote_daily_looks import GCLOUD_BIN, load_config, write_json


KST = timezone(timedelta(hours=9))
CODE_PREFIX = "TPDEL1."
VALID_SEASONS = {"spring", "summer", "autumn", "winter"}
VALID_MODE_RE = re.compile(r"^(female|male)_(10|20|30|40|50|60)s$")
VALID_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def now_kst():
    return datetime.now(KST).isoformat(timespec="seconds")


def decode_delete_code(code):
    if not isinstance(code, str) or not code.startswith(CODE_PREFIX):
        raise ValueError("delete code must start with TPDEL1.")
    raw = code[len(CODE_PREFIX):].strip()
    padded = raw + ("=" * (-len(raw) % 4))
    try:
        payload = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        data = json.loads(payload)
    except Exception as exc:
        raise ValueError(f"invalid delete code payload: {exc}") from exc
    if data.get("schema") != "todaypick.delete_request" or data.get("version") != 1:
        raise ValueError("unsupported delete request schema")
    if not isinstance(data.get("deletedLooks"), list) or not data["deletedLooks"]:
        raise ValueError("delete request has no looks")
    return data


def normalize_requests(payload):
    grouped = defaultdict(dict)
    skipped = []
    for item in payload["deletedLooks"]:
        look_id = str(item.get("id") or "").strip()
        mode = str(item.get("mode") or "").strip()
        season = item.get("remoteSeason")
        if not season and "_" in look_id:
            candidate = look_id.split("_", 1)[0]
            if candidate in VALID_SEASONS:
                season = candidate
        if season not in VALID_SEASONS:
            skipped.append({"id": look_id, "mode": mode, "reason": "missing remote season"})
            continue
        match = VALID_MODE_RE.match(mode)
        if not match:
            skipped.append({"id": look_id, "mode": mode, "season": season, "reason": "invalid mode"})
            continue
        if not look_id or not VALID_ID_RE.match(look_id):
            skipped.append({"id": look_id, "mode": mode, "season": season, "reason": "invalid look id"})
            continue
        segment = f"{match.group(1)}_{match.group(2)}"
        grouped[(season, segment)][look_id] = item
    return grouped, skipped


def run_gcloud(args, project):
    cmd = [GCLOUD_BIN, *args, "--project", project, "--quiet"]
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gcloud command failed")
    return result.stdout


def storage_url(bucket, object_name):
    return f"gs://{bucket}/{object_name}"


def object_exists(bucket, project, object_name):
    result = subprocess.run(
        [GCLOUD_BIN, "storage", "objects", "describe", storage_url(bucket, object_name), "--project", project, "--format=json", "--quiet"],
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def validate_catalog_after_delete(catalog):
    looks = catalog.get("looks")
    if not isinstance(looks, list):
        return False, "looks must be a list"
    if int(catalog.get("count", -1)) != len(looks):
        return False, "count mismatch"
    if len(looks) < 1:
        return False, "catalog would become empty"
    ids = set()
    for look in looks:
        look_id = look.get("id")
        if not look_id or look_id in ids:
            return False, "invalid or duplicate look id"
        ids.add(look_id)
        if not look.get("url") or not look.get("sha256"):
            return False, "look is missing url or sha256"
    return True, "PASS"


def apply_delete_request(code, bucket, project, dry_run=False):
    payload = decode_delete_code(code)
    grouped, skipped = normalize_requests(payload)
    if not grouped:
        raise ValueError("delete request has no production remote looks")

    run_id = datetime.now(KST).strftime("%Y%m%d-%H%M%S")
    report = {
        "schema": "todaypick.delete_apply_report",
        "version": 1,
        "runId": run_id,
        "appliedAt": now_kst(),
        "dryRun": dry_run,
        "assetsDeleted": False,
        "catalogs": [],
        "skipped": skipped,
    }

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for (season, segment), requests in sorted(grouped.items()):
            object_name = f"production/{season}/{segment}.json"
            if not object_exists(bucket, project, object_name):
                report["catalogs"].append({
                    "season": season,
                    "segment": segment,
                    "status": "SKIP_MISSING_CATALOG",
                    "requested": sorted(requests),
                    "removed": [],
                })
                continue

            catalog_path = root / f"{season}_{segment}.json"
            run_gcloud(["storage", "cp", storage_url(bucket, object_name), str(catalog_path)], project)
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            before = len(catalog.get("looks") or [])
            remove_ids = set(requests)
            kept = [look for look in catalog.get("looks", []) if look.get("id") not in remove_ids]
            removed = [look for look in catalog.get("looks", []) if look.get("id") in remove_ids]

            if not removed:
                report["catalogs"].append({
                    "season": season,
                    "segment": segment,
                    "status": "NO_MATCH",
                    "before": before,
                    "after": before,
                    "requested": sorted(requests),
                    "removed": [],
                })
                continue

            next_catalog = dict(catalog)
            next_catalog["looks"] = kept
            next_catalog["count"] = len(kept)
            next_catalog["updated_at"] = now_kst()
            next_catalog["last_admin_delete_request"] = {
                "runId": run_id,
                "removedIds": [look["id"] for look in removed],
            }
            ok, reason = validate_catalog_after_delete(next_catalog)
            if not ok:
                raise RuntimeError(f"{season}/{segment} delete validation failed: {reason}")

            report["catalogs"].append({
                "season": season,
                "segment": segment,
                "status": "DRY_RUN" if dry_run else "UPDATED",
                "before": before,
                "after": len(kept),
                "requested": sorted(requests),
                "removed": [look["id"] for look in removed],
            })

            if dry_run:
                continue

            backup_object = f"production/deletion_backups/{run_id}/{season}/{segment}.json"
            run_gcloud(["storage", "cp", storage_url(bucket, object_name), storage_url(bucket, backup_object)], project)
            out_path = root / f"{season}_{segment}.updated.json"
            write_json(out_path, next_catalog)
            run_gcloud([
                "storage",
                "cp",
                "--content-type=application/json",
                "--cache-control=no-cache",
                str(out_path),
                storage_url(bucket, object_name),
            ], project)

        if not dry_run:
            report_path = root / "delete_apply_report.json"
            write_json(report_path, report)
            run_gcloud([
                "storage",
                "cp",
                "--content-type=application/json",
                "--cache-control=private, max-age=0",
                str(report_path),
                storage_url(bucket, f"production/deletion_audit/{run_id}.json"),
            ], project)

    return report


def main():
    parser = argparse.ArgumentParser(description="Apply a TodayPick admin delete code to production seasonal catalogs.")
    parser.add_argument("--code", required=True, help="TPDEL1 delete code copied from the app admin panel.")
    parser.add_argument("--bucket", default=None)
    parser.add_argument("--project", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    bucket = args.bucket or "todaypick-daily-looks-363284724091"
    project = args.project or cfg.get("gcp_project") or "my-youtube-automation-497504"
    report = apply_delete_request(args.code, bucket, project, dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
