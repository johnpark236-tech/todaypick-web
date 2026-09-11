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
    build_index_manifest,
    merge_cumulative_looks,
    now_iso,
    validate_index_manifest,
    validate_leaf_catalog,
    write_json,
)


BUCKET = "todaypick-daily-looks-363284724091"
PROJECT = "my-youtube-automation-497504"
CACHE_NO_CACHE = "no-cache"
CACHE_VERSIONED = "public, max-age=300"


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


def upload_json(path, object_name, cache_control):
    run_gcloud([
        "storage",
        "cp",
        "--content-type=application/json",
        f"--cache-control={cache_control}",
        str(path),
        storage_url(object_name),
    ])


def convert_look_id(look, season, segment):
    parts = str(look.get("id", "")).split("_")
    if len(parts) >= 4 and parts[-2].isdigit() and parts[-1].isdigit():
      return f"{season}_{segment}_{parts[-2]}_{parts[-1]}"
    return f"{season}_{look.get('id')}"


def normalize_looks(entry, season, segment):
    out = []
    for look in entry.get("looks", []):
        item = dict(look)
        item["id"] = convert_look_id(item, season, segment)
        out.append(item)
    return out


def build_catalogs(previous, current, season):
    catalogs = {}
    segments = sorted(set(previous.get("segments", {})) | set(current.get("segments", {})))
    for segment in segments:
        prev_entry = previous.get("segments", {}).get(segment, {})
        cur_entry = current.get("segments", {}).get(segment, {})
        merged = merge_cumulative_looks(
            normalize_looks(prev_entry, season, segment),
            normalize_looks(cur_entry, season, segment),
        )
        gender, age = segment.split("_")
        catalog = {
            "schema_version": 2,
            "season": season,
            "gender": gender,
            "age_group": int(age),
            "segment": segment,
            "count": len(merged),
            "updated_at": now_iso(),
            "looks": merged,
            "paging": {
                "mode": "single_leaf",
                "future_page_size": 1000
            },
        }
        ok, reason = validate_leaf_catalog(catalog, require_public_urls=True)
        if not ok:
            raise RuntimeError(f"{segment}: {reason}")
        catalogs[segment] = catalog
    return catalogs


def publish_catalogs(catalogs, season):
    leaf_urls = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for segment, catalog in catalogs.items():
            version = f"{int(time.time())}"
            versioned_object = f"production/{season}/manifests/{segment}_{version}.json"
            active_object = f"production/{season}/{segment}.json"
            previous_object = f"production/{season}/previous/{segment}.json"
            path = root / f"{segment}.json"
            write_json(path, catalog)
            upload_json(path, versioned_object, CACHE_VERSIONED)
            if object_exists(active_object):
                run_gcloud(["storage", "cp", storage_url(active_object), storage_url(previous_object)])
            upload_json(path, active_object, CACHE_NO_CACHE)
            leaf_urls.append((season, segment, public_url(active_object)))

        index_object = "production/index.json"
        existing_index = read_json_object(index_object) if object_exists(index_object) else {}
        index = build_index_manifest(existing_index, leaf_urls)
        ok, reason = validate_index_manifest(index)
        if not ok:
            raise RuntimeError(reason)
        index_path = root / "index.json"
        write_json(index_path, index)
        if object_exists(index_object):
            run_gcloud(["storage", "cp", storage_url(index_object), storage_url("production/index.previous.json")])
        upload_json(index_path, index_object, CACHE_NO_CACHE)
    return leaf_urls


def main():
    parser = argparse.ArgumentParser(description="Publish TodayPick seasonal schema v2 catalogs.")
    parser.add_argument("--season", default="autumn")
    parser.add_argument("--previous-object", default="production/previous.json")
    parser.add_argument("--current-object", default="production/latest.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    previous = read_json_object(args.previous_object)
    current = read_json_object(args.current_object)
    catalogs = build_catalogs(previous, current, args.season)
    if args.dry_run:
        print(json.dumps({segment: catalog["count"] for segment, catalog in catalogs.items()}, indent=2))
        return 0

    leaf_urls = publish_catalogs(catalogs, args.season)
    print(json.dumps({
        "season": args.season,
        "catalogs": {segment: catalog["count"] for segment, catalog in catalogs.items()},
        "leaf_urls": leaf_urls,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
