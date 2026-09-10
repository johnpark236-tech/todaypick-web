import argparse
import json
import re
import subprocess
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))

from remote_daily_looks import GCLOUD_BIN, validate_complete_manifest, write_json  # noqa: E402


KST = timezone(timedelta(hours=9))


def run_gcloud(args, project, check=True):
    result = subprocess.run(
        [GCLOUD_BIN, *args, "--project", project, "--quiet"],
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gcloud command failed")
    return result


def public_url(bucket, object_name):
    return f"https://storage.googleapis.com/{bucket}/{object_name}"


def gs_url(bucket, object_name):
    return f"gs://{bucket}/{object_name}"


def object_exists(project, bucket, object_name):
    result = run_gcloud(["storage", "objects", "describe", gs_url(bucket, object_name), "--format=json"], project, check=False)
    return result.returncode == 0


def list_objects(project, bucket, prefix):
    result = run_gcloud(["storage", "ls", "--recursive", gs_url(bucket, prefix)], project, check=False)
    if result.returncode != 0 and "One or more URLs matched no objects" not in result.stderr:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gcloud storage ls failed")
    marker = f"gs://{bucket}/"
    objects = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith(marker) and not line.endswith(":"):
            objects.add(line[len(marker):])
    return objects


def fetch_head(url):
    try:
      with urlopen(Request(url, method="HEAD"), timeout=20) as response:
          return {
              "status": response.status,
              "content_type": response.headers.get("Content-Type", "").split(";")[0].lower(),
              "cache_control": response.headers.get("Cache-Control", ""),
              "content_length": int(response.headers.get("Content-Length", "0")),
          }
    except HTTPError as exc:
        return {"status": exc.code, "content_type": "", "cache_control": "", "content_length": 0}
    except (URLError, TimeoutError):
        return {"status": 0, "content_type": "", "cache_control": "", "content_length": 0}


def read_json_object(project, bucket, object_name):
    result = run_gcloud(["storage", "cat", gs_url(bucket, object_name)], project)
    return json.loads(result.stdout)


def upload_json(project, bucket, object_name, payload, cache_control):
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / Path(object_name).name
        write_json(path, payload)
        run_gcloud([
            "storage",
            "cp",
            "--content-type=application/json",
            f"--cache-control={cache_control}",
            str(path),
            gs_url(bucket, object_name),
        ], project)


def main():
    parser = argparse.ArgumentParser(description="Prepare and verify TodayPick production remote manifest.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--date", default="260910")
    parser.add_argument("--version", default="260910_001")
    args = parser.parse_args()

    staging_manifest_object = f"staging/manifests/{args.version}.json"
    production_manifest_object = f"production/manifests/{args.version}.json"
    production_latest_object = "production/latest.json"
    production_previous_object = "production/previous.json"

    staging = read_json_object(args.project, args.bucket, staging_manifest_object)
    existing_production_objects = list_objects(args.project, args.bucket, "production/")
    manifest = deepcopy(staging)
    manifest["content_version"] = args.version
    manifest["published_at"] = datetime.now(KST).isoformat(timespec="seconds")
    manifest["previous_manifest"] = "previous.json"

    asset_urls = []
    copied = 0
    reused = 0
    for segment, entry in manifest["segments"].items():
        if segment not in {"female_10", "female_20", "female_30"}:
            raise RuntimeError(f"unexpected production segment: {segment}")
        for look in entry["looks"]:
            look.pop("staging_path", None)
            staging_url = look["url"]
            match = re.match(rf"^https://storage\.googleapis\.com/{re.escape(args.bucket)}/staging/assets/(.+)$", staging_url)
            if not match:
                raise RuntimeError(f"unexpected staging asset URL: {staging_url}")
            production_object = f"production/assets/{match.group(1)}"
            if production_object in existing_production_objects:
                reused += 1
            else:
                run_gcloud([
                    "storage",
                    "cp",
                    "--content-type=image/webp",
                    "--cache-control=public, max-age=31536000, immutable",
                    gs_url(args.bucket, f"staging/assets/{match.group(1)}"),
                    gs_url(args.bucket, production_object),
                ], args.project)
                existing_production_objects.add(production_object)
                copied += 1
            look["url"] = public_url(args.bucket, production_object)
            asset_urls.append(look["url"])

    ok, reason = validate_complete_manifest(manifest, require_public_urls=True)
    if not ok:
        raise RuntimeError(reason)
    if json.dumps(manifest, ensure_ascii=False).count("staging_path") != 0:
        raise RuntimeError("production manifest contains staging_path")
    if re.search(r"file://|localhost|127\.0\.0\.1|/staging/assets/", json.dumps(manifest, ensure_ascii=False)):
        raise RuntimeError("production manifest contains unsafe URL")

    image_heads = [fetch_head(url) for url in asset_urls]
    image_ok = [h for h in image_heads if h["status"] == 200 and h["content_type"] == "image/webp" and h["content_length"] > 0]
    if len(image_ok) != 30:
        raise RuntimeError(f"production image validation failed: {len(image_ok)}/30")

    latest_before = None
    if production_latest_object in existing_production_objects:
        latest_before = read_json_object(args.project, args.bucket, production_latest_object)
        run_gcloud(["storage", "cp", gs_url(args.bucket, production_latest_object), gs_url(args.bucket, production_previous_object)], args.project)
        existing_production_objects.add(production_previous_object)

    upload_json(args.project, args.bucket, production_manifest_object, manifest, "public, max-age=300")
    manifest_head = fetch_head(public_url(args.bucket, production_manifest_object))
    if manifest_head["status"] != 200 or manifest_head["content_type"] != "application/json":
        raise RuntimeError("versioned production manifest HTTP validation failed")

    upload_json(args.project, args.bucket, production_latest_object, manifest, "no-cache")
    if latest_before is None:
        upload_json(args.project, args.bucket, production_previous_object, manifest, "no-cache")

    latest_after = read_json_object(args.project, args.bucket, production_latest_object)
    latest_head = fetch_head(public_url(args.bucket, production_latest_object))
    if latest_after.get("content_version") != args.version:
        raise RuntimeError("production latest switch failed")

    report = {
        "BUCKET": args.bucket,
        "PRODUCTION_PREFIX_READY": True,
        "PRODUCTION_ASSETS_EXPECTED": 30,
        "PRODUCTION_ASSETS_READY": len(image_ok),
        "PRODUCTION_ASSETS_COPIED": copied,
        "PRODUCTION_ASSETS_REUSED": reused,
        "PRODUCTION_MANIFEST_CREATED": True,
        "PRODUCTION_MANIFEST_URL": public_url(args.bucket, production_latest_object),
        "PRODUCTION_VERSIONED_MANIFEST_URL": public_url(args.bucket, production_manifest_object),
        "PRODUCTION_MANIFEST_SCHEMA": "PASS",
        "PRODUCTION_URL_SAFETY": "PASS",
        "PRODUCTION_IMAGES_VALIDATED": f"{len(image_ok)}/30",
        "PARTIAL_SEGMENT_REMOTE": sorted(manifest["segments"].keys()),
        "ATOMIC_PRODUCTION_PUBLISH": "PASS",
        "PRODUCTION_ROLLBACK_READY": "PASS",
        "CACHE_HEADERS": {
            "asset": image_heads[0]["cache_control"],
            "manifest": manifest_head["cache_control"],
            "latest": latest_head["cache_control"],
        },
    }
    out = Path("automation/daily_looks/remote_pipeline/manifests/260910_production_remote_prep_report.json")
    write_json(out, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
