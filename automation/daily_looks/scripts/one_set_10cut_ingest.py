import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from append_seasonal_catalog_from_staging import (  # noqa: E402
    BUCKET,
    CACHE_ASSET,
    CACHE_NO_CACHE,
    CACHE_VERSIONED_JSON,
    PROJECT,
    object_exists,
    public_url,
    read_json_object,
    run_gcloud,
    storage_url,
    upload_json,
)
from remote_daily_looks import (  # noqa: E402
    CANONICAL_V3_PROFILE,
    SourceImage,
    build_set_id,
    crop_source_image,
    load_config,
    now_iso,
    season_for_date_folder,
    sha256_file,
    validate_leaf_catalog,
    validate_source,
    write_json,
)


def upload_file(path, object_name, content_type, cache_control):
    if object_exists(object_name):
        return
    run_gcloud([
        "storage",
        "cp",
        f"--content-type={content_type}",
        f"--cache-control={cache_control}",
        str(path),
        storage_url(object_name),
    ])


def content_type_for(path):
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "application/octet-stream")


def http_status(url):
    import urllib.request

    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read(1)
        return {
            "status": response.status,
            "content_type": response.headers.get("Content-Type", "").split(";")[0],
            "has_body": bool(body),
        }


def main():
    parser = argparse.ArgumentParser(description="Append exactly one canonical 2x5 TodayPick source sheet as a 10-cut production set.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--date", required=True, help="YYMMDD date folder for the new set.")
    parser.add_argument("--season", default=None)
    parser.add_argument("--gender", default="female", choices=["female", "male"])
    parser.add_argument("--age", type=int, default=20, choices=[10, 20, 30, 40, 50, 60])
    parser.add_argument("--report", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    source_path = Path(args.source)
    season = args.season or season_for_date_folder(args.date)
    segment = f"{args.gender}_{args.age}"
    sha = sha256_file(source_path)
    source = SourceImage(
        path=source_path,
        gender=args.gender,
        age=args.age,
        segment=segment,
        filename=source_path.name,
        size=source_path.stat().st_size,
        mtime=source_path.stat().st_mtime,
        sha256=sha,
        season=season,
    )

    ok, reason, image = validate_source(source_path, cfg, crop_profile=CANONICAL_V3_PROFILE)
    if not ok:
        raise RuntimeError(f"source validation failed: {reason}")

    active_object = f"production/{season}/{segment}.json"
    previous_object = f"production/{season}/previous/{segment}.json"
    base = read_json_object(active_object) if object_exists(active_object) else {
        "schema_version": 2,
        "season": season,
        "gender": args.gender,
        "age_group": args.age,
        "segment": segment,
        "count": 0,
        "looks": [],
    }
    before_count = int(base.get("count", len(base.get("looks", []))))

    with tempfile.TemporaryDirectory() as td:
        staging_root = Path(td) / "staging"
        cut_dir = staging_root / args.date / args.gender / str(args.age)
        crop_ok, cut_files, validations = crop_source_image(
            image,
            cut_dir,
            source,
            args.date,
            cfg,
            crop_profile=CANONICAL_V3_PROFILE,
        )
        if not crop_ok or len(cut_files) != 10:
            raise RuntimeError(f"crop failed: {validations}")

        set_id = build_set_id(source, args.date, sha)
        sheet_object = f"production/sheets/{season}/{args.date}/{args.gender}/{args.age}/sheet{source_path.suffix.lower()}"
        sheet_url = public_url(sheet_object)
        new_looks = []
        for item in sorted(cut_files, key=lambda row: row["index"]):
            object_name = f"production/assets/{season}/{args.date}/{args.gender}/{args.age}/{Path(item['filename']).name}"
            url = public_url(object_name)
            new_looks.append({
                "id": f"{season}_{segment}_{args.date}_{item['index']:02d}",
                "url": url,
                "sha256": item["sha256"],
                "width": int(cfg["cut_width"]),
                "height": int(cfg["cut_height"]),
                "source_date": args.date,
                "set_id": set_id,
                "sheet_url": sheet_url,
                "cut_index": int(item["index"]),
                "_local_path": item["path"],
                "_object_name": object_name,
            })

        existing = list(base.get("looks", []))
        seen_ids = {look.get("id") for look in existing}
        seen_sha = {look.get("sha256") for look in existing}
        appended = []
        skipped = []
        for look in new_looks:
            if look["id"] in seen_ids or look["sha256"] in seen_sha:
                skipped.append(look["id"])
                continue
            appended.append(look)
            seen_ids.add(look["id"])
            seen_sha.add(look["sha256"])

        merged = existing + [{k: v for k, v in look.items() if not k.startswith("_")} for look in appended]
        catalog = {
            **base,
            "schema_version": 2,
            "season": season,
            "gender": args.gender,
            "age_group": args.age,
            "segment": segment,
            "count": len(merged),
            "updated_at": now_iso(),
            "last_source_date": args.date,
            "last_10cut_set_id": set_id,
            "last_10cut_sheet_url": sheet_url,
            "looks": merged,
        }
        valid, valid_reason = validate_leaf_catalog(catalog, require_public_urls=True)
        if not valid:
            raise RuntimeError(valid_reason)

        if not args.dry_run:
            upload_file(source_path, sheet_object, content_type_for(source_path), CACHE_ASSET)
            for look in appended:
                upload_file(Path(look["_local_path"]), look["_object_name"], "image/webp", CACHE_ASSET)
            versioned_object = f"production/{season}/manifests/{segment}_{args.date}_{int(time.time())}.json"
            upload_json(catalog, versioned_object, CACHE_VERSIONED_JSON)
            if object_exists(active_object):
                run_gcloud(["storage", "cp", storage_url(active_object), storage_url(previous_object)])
            upload_json(catalog, active_object, CACHE_NO_CACHE)

        report = {
            "status": "OK",
            "dry_run": args.dry_run,
            "date": args.date,
            "season": season,
            "segment": segment,
            "source_path": str(source_path),
            "source_filename": source_path.name,
            "source_size": list(image.size),
            "source_bytes": source_path.stat().st_size,
            "source_sha256": sha,
            "before_count": before_count,
            "after_count": len(merged),
            "catalog_count_delta": len(merged) - before_count,
            "new_images_appended": len(appended),
            "skipped_duplicates": skipped,
            "set_id": set_id,
            "sheet_url": sheet_url,
            "source_object_path": storage_url(sheet_object),
            "catalog_url": public_url(active_object),
            "cuts": [{k: v for k, v in look.items() if not k.startswith("_")} for look in appended],
            "source_validation": reason,
            "crop_validations": validations,
        }
        if not args.dry_run:
            report["sheet_http"] = http_status(sheet_url)
            for look in report["cuts"]:
                look["http"] = http_status(look["url"])
        if args.report:
            write_json(Path(args.report), report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
