import argparse
import json
import subprocess
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

from remote_daily_looks import GCLOUD_BIN, sha256_file, write_json  # noqa: E402


KST = timezone(timedelta(hours=9))


def run_gcloud(args, project):
    result = subprocess.run(
        [GCLOUD_BIN, *args, "--project", project, "--quiet"],
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gcloud command failed")
    return result.stdout


def public_url(bucket, object_name):
    return f"https://storage.googleapis.com/{bucket}/{object_name}"


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
            f"gs://{bucket}/{object_name}",
        ], project)


def upload_webp(project, bucket, object_name, source_path):
    run_gcloud([
        "storage",
        "cp",
        "--content-type=image/webp",
        "--cache-control=public, max-age=31536000, immutable",
        str(source_path),
        f"gs://{bucket}/{object_name}",
    ], project)


def make_variant_image(source_path, out_path):
    image = Image.open(source_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((18, 18, 210, 88), fill=(22, 92, 220))
    draw.text((34, 42), "STAGING B", fill=(255, 255, 255))
    image.save(out_path, "WEBP", quality=90, method=6)


def main():
    parser = argparse.ArgumentParser(description="Publish TodayPick staging latest variants for app E2E.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--variant", choices=["a", "b", "invalid"], required=True)
    parser.add_argument("--date", default="260910")
    args = parser.parse_args()

    prefix = "staging"
    manifest_a_object = f"{prefix}/manifests/{args.date}_001.json"
    latest_object = f"{prefix}/latest.json"

    if args.variant == "a":
        run_gcloud([
            "storage",
            "cp",
            "--content-type=application/json",
            "--cache-control=no-cache",
            f"gs://{args.bucket}/{manifest_a_object}",
            f"gs://{args.bucket}/{latest_object}",
        ], args.project)
        print(json.dumps({"variant": "a", "latest_url": public_url(args.bucket, latest_object)}, ensure_ascii=False))
        return

    if args.variant == "invalid":
        invalid = {
            "schema_version": 1,
            "content_version": f"{args.date}_invalid",
            "published_at": datetime.now(KST).isoformat(timespec="seconds"),
            "segments": {
                "female_10": {
                    "source_date": args.date,
                    "count": 1,
                    "looks": [{"id": "bad", "url": "file:///bad.webp", "sha256": "x"}],
                }
            },
        }
        object_name = f"{prefix}/manifests/{args.date}_invalid.json"
        upload_json(args.project, args.bucket, object_name, invalid, "public, max-age=60")
        run_gcloud([
            "storage",
            "cp",
            "--content-type=application/json",
            "--cache-control=no-cache",
            f"gs://{args.bucket}/{object_name}",
            f"gs://{args.bucket}/{latest_object}",
        ], args.project)
        print(json.dumps({"variant": "invalid", "latest_url": public_url(args.bucket, latest_object)}, ensure_ascii=False))
        return

    raw = run_gcloud(["storage", "cat", f"gs://{args.bucket}/{manifest_a_object}"], args.project)
    manifest = json.loads(raw)
    manifest_b = deepcopy(manifest)
    manifest_b["content_version"] = f"{args.date}_app_b"
    manifest_b["published_at"] = datetime.now(KST).isoformat(timespec="seconds")

    first = manifest_b["segments"]["female_10"]["looks"][0]
    source_url_path = first["url"].split(f"https://storage.googleapis.com/{args.bucket}/", 1)[1]
    with tempfile.TemporaryDirectory() as td:
        source_file = Path(td) / "source.webp"
        variant_file = Path(td) / "variant.webp"
        run_gcloud(["storage", "cp", f"gs://{args.bucket}/{source_url_path}", str(source_file)], args.project)
        make_variant_image(source_file, variant_file)
        sha = sha256_file(variant_file)
        object_name = f"{prefix}/assets/female/10/{args.date}/look_01_{sha[:12]}.webp"
        upload_webp(args.project, args.bucket, object_name, variant_file)

    first["url"] = public_url(args.bucket, object_name)
    first["sha256"] = sha
    object_name_manifest = f"{prefix}/manifests/{args.date}_app_b.json"
    upload_json(args.project, args.bucket, object_name_manifest, manifest_b, "public, max-age=300")
    run_gcloud([
        "storage",
        "cp",
        "--content-type=application/json",
        "--cache-control=no-cache",
        f"gs://{args.bucket}/{object_name_manifest}",
        f"gs://{args.bucket}/{latest_object}",
    ], args.project)
    print(json.dumps({
        "variant": "b",
        "content_version": manifest_b["content_version"],
        "image_url": first["url"],
        "image_sha256": sha,
        "latest_url": public_url(args.bucket, latest_object),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
