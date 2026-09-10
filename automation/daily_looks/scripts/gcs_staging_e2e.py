import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))

from remote_daily_looks import (  # noqa: E402
    GcsPublisher,
    build_manifest,
    build_review_sheet,
    crop_source_image,
    discover_sources,
    load_config,
    resolve_project_path,
    validate_complete_manifest,
    validate_source,
    write_json,
)


KST = timezone(timedelta(hours=9))
GCLOUD_BIN = shutil.which("gcloud") or shutil.which("gcloud.cmd") or "gcloud"


def run_gcloud(args, project):
    result = subprocess.run([GCLOUD_BIN, *args, "--project", project, "--quiet"], text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gcloud command failed")
    return result.stdout


def fetch(url, method="GET", data=None):
    try:
        request = Request(url, method=method, data=data)
        with urlopen(request, timeout=20) as response:
            return {
                "status": response.status,
                "content_type": response.headers.get("Content-Type", "").split(";")[0].lower(),
                "cache_control": response.headers.get("Cache-Control", ""),
                "size_probe": len(response.read(1)),
            }
    except HTTPError as exc:
        return {"status": exc.code, "content_type": "", "cache_control": "", "size_probe": 0}
    except (URLError, TimeoutError) as exc:
        return {"status": 0, "error": str(exc), "content_type": "", "cache_control": "", "size_probe": 0}


def read_url_json(url):
    request = Request(url, method="GET")
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def get_object_metadata(bucket, object_name, project):
    raw = run_gcloud(
        ["storage", "objects", "describe", f"gs://{bucket}/{object_name}", "--format=json"],
        project,
    )
    return json.loads(raw)


def process_sources(date_folder, source_root, cfg):
    staging_root = resolve_project_path(cfg["staging_root"])
    review_root = resolve_project_path(cfg["review_root"])
    folder, discovered, discovery_status = discover_sources(source_root, date_folder, cfg)
    processed = []
    review_sheets = []
    failures = []
    for source in discovered:
        ok, reason, image = validate_source(source.path, cfg)
        if not ok:
            failures.append({"source_file": source.filename, "segment": source.segment, "reason": reason})
            continue
        out_dir = staging_root / date_folder / source.gender / str(source.age)
        crop_ok, cut_files, validations = crop_source_image(image, out_dir, source, date_folder, cfg)
        if not crop_ok:
            failures.append({"source_file": source.filename, "segment": source.segment, "validations": validations})
            continue
        review_sheets.append(str(build_review_sheet(source.segment, date_folder, cut_files, review_root, cfg)))
        processed.append((source, cut_files))
    return {
        "folder": str(folder),
        "discovery_status": discovery_status,
        "discovered": discovered,
        "processed": processed,
        "review_sheets": review_sheets,
        "failures": failures,
    }


def publish_segments(processed, publisher, date_folder, content_version):
    base_manifest = publisher.read_current_latest()
    uploaded = []
    for source, cut_files in processed:
        segment_uploads = []
        for item in cut_files:
            upload = publisher.upload_asset(item["path"], date_folder, source, item)
            if not publisher.validate_asset_url(upload["url"]):
                raise RuntimeError(f"URL validation failed: {upload['url']}")
            segment_uploads.append({**item, "url": upload["url"]})
        uploaded.append((source, segment_uploads))

    manifest = build_manifest(base_manifest, uploaded, date_folder, publisher.public_base_url, dry_run=False)
    manifest["content_version"] = content_version
    manifest["published_at"] = datetime.now(KST).isoformat(timespec="seconds")
    ok, reason = validate_complete_manifest(manifest, require_public_urls=True)
    if not ok:
        raise RuntimeError(reason)
    manifest_path = publisher.write_versioned_manifest(content_version, manifest)
    publisher.switch_latest(manifest_path)
    return manifest, manifest_path


def assert_failure_before_switch(processed, publisher, date_folder, content_version):
    before = publisher.read_current_latest()
    try:
        uploaded = []
        for source, cut_files in processed:
            segment_uploads = []
            for item in cut_files:
                upload = publisher.upload_asset(item["path"], date_folder, source, item)
                segment_uploads.append({**item, "url": upload["url"]})
            uploaded.append((source, segment_uploads))
        manifest = build_manifest(before, uploaded, date_folder, publisher.public_base_url, dry_run=False)
        manifest["content_version"] = content_version
        raise RuntimeError("intentional validation failure before latest switch")
    except RuntimeError:
        after = publisher.read_current_latest()
        return before == after


def main():
    parser = argparse.ArgumentParser(description="Run TodayPick GCS staging E2E publish checks.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--source-root", default=None)
    parser.add_argument("--prefix", default="staging")
    args = parser.parse_args()

    cfg = load_config()
    source_root = Path(args.source_root or cfg["source_root"])
    run_data = process_sources(args.date, source_root, cfg)
    if run_data["failures"]:
        raise RuntimeError(json.dumps(run_data["failures"], ensure_ascii=False))
    if len(run_data["processed"]) != 3:
        raise RuntimeError(f"expected 3 processed sources, got {len(run_data['processed'])}")
    expected_assets = sum(len(cuts) for _, cuts in run_data["processed"])
    if expected_assets != 30:
        raise RuntimeError(f"expected 30 assets, got {expected_assets}")

    publisher = GcsPublisher(args.bucket, args.project, args.prefix)
    version_a = f"{args.date}_001"
    version_b = f"{args.date}_002"
    failure_version = f"{args.date}_fail_{int(time.time())}"

    before_assets = [
        f"{publisher.prefix}/assets/{source.gender}/{source.age}/{args.date}/{Path(item['filename']).name}"
        for source, cuts in run_data["processed"]
        for item in cuts
    ]
    existed_before = sum(1 for object_name in before_assets if publisher._object_exists(object_name))

    manifest_a, manifest_a_path = publish_segments(run_data["processed"], publisher, args.date, version_a)
    latest_a = read_url_json(f"https://storage.googleapis.com/{args.bucket}/{publisher.latest_object}")
    failure_kept_latest = assert_failure_before_switch(run_data["processed"], publisher, args.date, failure_version)
    latest_after_failure = read_url_json(f"https://storage.googleapis.com/{args.bucket}/{publisher.latest_object}")
    manifest_b, manifest_b_path = publish_segments(run_data["processed"], publisher, args.date, version_b)
    latest_b = read_url_json(f"https://storage.googleapis.com/{args.bucket}/{publisher.latest_object}")
    rollback_ok = publisher.rollback_latest()
    latest_after_rollback = read_url_json(f"https://storage.googleapis.com/{args.bucket}/{publisher.latest_object}")

    asset_urls = [
        look["url"]
        for segment in ("female_10", "female_20", "female_30")
        for look in manifest_b["segments"][segment]["looks"]
    ]
    asset_fetches = [fetch(url) for url in asset_urls]
    anonymous_put = fetch(asset_urls[0], method="PUT", data=b"anonymous write test")
    anonymous_delete = fetch(asset_urls[0], method="DELETE")
    latest_url = f"https://storage.googleapis.com/{args.bucket}/{publisher.latest_object}"
    manifest_url = f"https://storage.googleapis.com/{args.bucket}/{manifest_b_path}"
    latest_fetch = fetch(latest_url)
    manifest_fetch = fetch(manifest_url)

    metadata = {
        "asset": get_object_metadata(args.bucket, before_assets[0], args.project),
        "latest": get_object_metadata(args.bucket, publisher.latest_object, args.project),
        "manifest": get_object_metadata(args.bucket, manifest_b_path, args.project),
    }

    report = {
        "SOURCE_FILES": len(run_data["processed"]),
        "ASSETS_EXPECTED": 30,
        "ASSETS_UPLOADED": expected_assets,
        "ASSETS_EXISTED_BEFORE_UPLOAD": existed_before,
        "HTTPS_URL_VALIDATION": sum(1 for item in asset_fetches if item["status"] == 200),
        "WEBP_CONTENT_TYPE_VALIDATION": sum(1 for item in asset_fetches if item["content_type"] == "image/webp"),
        "STAGING_MANIFEST_CREATED": True,
        "STAGING_MANIFEST_URL": manifest_url,
        "STAGING_LATEST_URL": latest_url,
        "PARTIAL_SEGMENT_PRESERVATION": "INITIAL_MANIFEST_ONLY_3_SEGMENTS" if not manifest_a.get("previous_manifest") else "PRESERVED",
        "ATOMIC_STAGING_PUBLISH": latest_a.get("content_version") == version_a and latest_b.get("content_version") == version_b,
        "FAILURE_BEFORE_SWITCH_TEST": failure_kept_latest,
        "PARTIAL_CONTENT_VISIBLE_THROUGH_LATEST": latest_after_failure.get("content_version") != failure_version,
        "ROLLBACK_STAGING_E2E": rollback_ok and latest_after_rollback.get("content_version") == version_a,
        "IDEMPOTENCY_GCS": "HASHED_ASSET_PATH_REUSE" if existed_before == expected_assets else "FIRST_UPLOAD_CREATED_HASHED_ASSETS",
        "ANONYMOUS_GET": all(item["status"] == 200 for item in asset_fetches),
        "ANONYMOUS_PUT": anonymous_put["status"],
        "ANONYMOUS_DELETE": anonymous_delete["status"],
        "CACHE_HEADERS": {
            "asset": metadata["asset"].get("metadata", {}).get("cacheControl") or metadata["asset"].get("cacheControl"),
            "manifest": metadata["manifest"].get("metadata", {}).get("cacheControl") or metadata["manifest"].get("cacheControl"),
            "latest": metadata["latest"].get("metadata", {}).get("cacheControl") or metadata["latest"].get("cacheControl"),
            "latest_fetch": latest_fetch.get("cache_control"),
            "manifest_fetch": manifest_fetch.get("cache_control"),
        },
        "CONTENT_VERSIONS": {"A": version_a, "B": version_b, "after_rollback": latest_after_rollback.get("content_version")},
        "REVIEW_SHEETS": run_data["review_sheets"],
    }

    out = resolve_project_path(cfg["manifest_root"]) / f"{args.date}_gcs_staging_e2e_report.json"
    write_json(out, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
