import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from remote_daily_looks import (  # noqa: E402
    GCLOUD_BIN,
    SEASONS,
    build_index_manifest,
    now_iso,
    season_for_date_folder,
    validate_index_manifest,
    validate_leaf_catalog,
    write_json,
)


BUCKET = "todaypick-daily-looks-363284724091"
PROJECT = "my-youtube-automation-497504"
CACHE_NO_CACHE = "no-cache"
CACHE_VERSIONED_JSON = "public, max-age=300"
CACHE_ASSET = "public, max-age=31536000, immutable"
SEGMENTS = [
    "female_10",
    "female_20",
    "female_30",
    "female_40",
    "female_50",
    "female_60",
    "male_10",
    "male_20",
    "male_30",
    "male_40",
    "male_50",
    "male_60",
]


def run_gcloud(args):
    result = subprocess.run([GCLOUD_BIN, *args, "--project", PROJECT, "--quiet"], text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gcloud command failed")
    return result.stdout


def storage_url(object_name):
    return f"gs://{BUCKET}/{object_name}"


def public_url(object_name):
    return f"https://storage.googleapis.com/{BUCKET}/{object_name}"


def object_exists(object_name):
    result = subprocess.run(
        [GCLOUD_BIN, "storage", "objects", "describe", storage_url(object_name), "--project", PROJECT, "--format=json", "--quiet"],
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def read_json_object(object_name):
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "object.json"
        run_gcloud(["storage", "cp", storage_url(object_name), str(out)])
        return json.loads(out.read_text(encoding="utf-8"))


def upload_json(data, object_name, cache_control):
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "catalog.json"
        write_json(path, data)
        run_gcloud([
            "storage",
            "cp",
            "--content-type=application/json",
            f"--cache-control={cache_control}",
            str(path),
            storage_url(object_name),
        ])


def upload_asset(path, object_name):
    if object_exists(object_name):
        return
    run_gcloud([
        "storage",
        "cp",
        "--content-type=image/webp",
        f"--cache-control={CACHE_ASSET}",
        str(path),
        storage_url(object_name),
    ])


def staging_items(staging_root, date_folder, segment, season):
    gender, age = segment.split("_")
    source_dir = Path(staging_root) / date_folder / gender / age
    if not source_dir.exists():
        return []
    items = []
    for path in sorted(source_dir.glob("look_*.webp")):
        parts = path.stem.split("_")
        if len(parts) < 3 or not parts[1].isdigit():
            continue
        index = int(parts[1])
        sha12 = parts[2]
        object_name = f"production/assets/{season}/{date_folder}/{gender}/{age}/{path.name}"
        items.append({
            "id": f"{season}_{segment}_{date_folder}_{index:02d}",
            "url": public_url(object_name),
            "sha256": sha256_from_name_or_file(path, sha12),
            "width": 648,
            "height": 1152,
            "source_date": date_folder,
            "index": index,
            "path": str(path),
            "object_name": object_name,
        })
    return sorted(items, key=lambda item: item["index"])


def sha256_from_name_or_file(path, sha12):
    import hashlib

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if not digest.startswith(sha12):
        raise RuntimeError(f"sha mismatch for {path}")
    return digest


def dedupe_append(existing_looks, new_looks):
    merged = []
    seen_ids = set()
    seen_sha = set()
    appended = 0
    skipped = 0
    for look in existing_looks:
        look_id = look.get("id")
        sha = look.get("sha256")
        if look_id:
            seen_ids.add(look_id)
        if sha:
            seen_sha.add(sha)
        merged.append(look)
    for look in new_looks:
        if look["id"] in seen_ids or look["sha256"] in seen_sha:
            skipped += 1
            continue
        seen_ids.add(look["id"])
        seen_sha.add(look["sha256"])
        merged.append({k: v for k, v in look.items() if k not in {"path", "object_name", "index"}})
        appended += 1
    return merged, appended, skipped


def get_segment_count(season, segment):
    active_object = f"production/{season}/{segment}.json"
    if not object_exists(active_object):
        return 0
    catalog = read_json_object(active_object)
    return int(catalog.get("count", 0))


def publish_segment(season, date_folder, segment, items, dry_run):
    active_object = f"production/{season}/{segment}.json"
    previous_object = f"production/{season}/previous/{segment}.json"
    gender, age = segment.split("_")
    base = read_json_object(active_object) if object_exists(active_object) else {
        "schema_version": 2,
        "season": season,
        "gender": gender,
        "age_group": int(age),
        "segment": segment,
        "count": 0,
        "looks": [],
    }
    merged, appended, skipped = dedupe_append(base.get("looks", []), items)
    catalog = {
        **base,
        "schema_version": 2,
        "season": season,
        "gender": gender,
        "age_group": int(age),
        "segment": segment,
        "count": len(merged),
        "updated_at": now_iso(),
        "last_source_date": date_folder,
        "looks": merged,
        "paging": {
            "mode": "single_leaf",
            "future_page_size": 1000,
        },
    }
    ok, reason = validate_leaf_catalog(catalog, require_public_urls=True)
    if not ok:
        raise RuntimeError(f"{segment}: {reason}")
    if not dry_run:
        for item in items:
            upload_asset(Path(item["path"]), item["object_name"])
        versioned_object = f"production/{season}/manifests/{segment}_{date_folder}_{int(time.time())}.json"
        upload_json(catalog, versioned_object, CACHE_VERSIONED_JSON)
        if object_exists(active_object):
            run_gcloud(["storage", "cp", storage_url(active_object), storage_url(previous_object)])
        upload_json(catalog, active_object, CACHE_NO_CACHE)
    return {
        "segment": segment,
        "before": len(base.get("looks", [])),
        "appended": appended,
        "skipped_duplicates": skipped,
        "after": len(merged),
        "url": public_url(active_object),
    }


def publish_index(season, segment_results, dry_run):
    index_object = "production/index.json"
    existing_index = read_json_object(index_object) if object_exists(index_object) else {}
    leaf_urls = [(season, result["segment"], result["url"]) for result in segment_results]
    index = build_index_manifest(existing_index, leaf_urls)
    ok, reason = validate_index_manifest(index)
    if not ok:
        raise RuntimeError(reason)
    if not dry_run:
        if object_exists(index_object):
            run_gcloud(["storage", "cp", storage_url(index_object), storage_url("production/index.previous.json")])
        upload_json(index, index_object, CACHE_NO_CACHE)
    return public_url(index_object)


def publish_segments_from_staging(date_folder, season, staging_root, segments=None, dry_run=False):
    segment_list = segments or SEGMENTS
    results = []
    for segment in segment_list:
        items = staging_items(staging_root, date_folder, segment, season)
        if not items:
            continue
        if len(items) != 10:
            raise RuntimeError(f"{segment}: expected 10 staged WEBP files, found {len(items)}")
        results.append(publish_segment(season, date_folder, segment, items, dry_run))
    index_url = publish_index(season, results, dry_run) if results else public_url("production/index.json")
    return {
        "date": date_folder,
        "season": season,
        "dry_run": dry_run,
        "index_url": index_url,
        "total_appended": sum(result["appended"] for result in results),
        "total_skipped_duplicates": sum(result["skipped_duplicates"] for result in results),
        "segments": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Append staged TodayPick cuts to schema v2 seasonal production catalogs.")
    parser.add_argument("--date", required=True, help="YYMMDD source date folder.")
    parser.add_argument("--season", default=None, choices=SEASONS)
    parser.add_argument("--staging-root", default="automation/daily_looks/remote_pipeline/staging")
    parser.add_argument("--segments", nargs="*", choices=SEGMENTS, help="Optional subset for partial ingest.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    season = args.season or season_for_date_folder(args.date)
    report = publish_segments_from_staging(args.date, season, args.staging_root, args.segments, args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
