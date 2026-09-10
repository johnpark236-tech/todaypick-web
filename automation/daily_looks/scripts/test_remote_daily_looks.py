import json
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from remote_daily_looks import (  # noqa: E402
    FileSystemPublisher,
    GcsPublisher,
    SourceImage,
    atomic_publish_segments,
    build_manifest,
    validate_complete_manifest,
    validate_public_asset_url,
)


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


def old_segment(segment):
    return {
        "source_date": "260909",
        "count": 10,
        "looks": [
            {
                "id": f"{segment}_old_{index:02d}",
                "url": f"https://cdn.example/old/{segment}/look_{index:02d}.webp",
                "sha256": "0" * 64,
                "width": 648,
                "height": 1152,
            }
            for index in range(1, 11)
        ],
    }


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def make_cut(path, color):
    Image.new("RGB", (648, 1152), color).save(path, "WEBP", quality=80)


def make_source(segment, date_folder, cut_root):
    gender, age = segment.split("_")
    age_num = int(age)
    cut_dir = cut_root / gender / str(age_num)
    cut_dir.mkdir(parents=True, exist_ok=True)
    cuts = []
    for index in range(1, 11):
        path = cut_dir / f"look_{index:02d}_{segment}.webp"
        make_cut(path, (index * 12 % 255, age_num * 3 % 255, 80))
        cuts.append({
            "index": index,
            "path": str(path),
            "filename": path.name,
            "sha256": f"{index:064x}"[-64:],
            "id": f"{segment}_{date_folder}_{index:02d}",
        })
    source = SourceImage(
        path=cut_root / f"{segment}.png",
        gender=gender,
        age=age_num,
        segment=segment,
        filename=f"{segment}.png",
        size=1234,
        mtime=1.0,
        sha256=("f" if gender == "female" else "e") * 64,
    )
    return source, cuts


def assert_latest_unchanged(root, before):
    current = json.loads((root / "latest.json").read_text(encoding="utf-8"))
    assert current == before


def run():
    assert not validate_public_asset_url("C:/c/todaypick-web/a.webp")
    assert not validate_public_asset_url("G:/내 드라이브/a.webp")
    assert not validate_public_asset_url("file:///C:/a.webp")
    assert not validate_public_asset_url("../a.webp")
    assert not validate_public_asset_url("http://localhost/a.webp")
    assert validate_public_asset_url("https://valid-public-host.example/a.webp")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        latest = {
            "schema_version": 1,
            "published_at": "2026-09-09T05:00:00+09:00",
            "content_version": "260909_001",
            "segments": {segment: old_segment(segment) for segment in SEGMENTS},
        }
        write_json(root / "latest.json", latest)

        cut_root = root / "cuts"
        processed = [make_source(segment, "260910", cut_root) for segment in ("female_10", "female_20", "female_30")]
        dry_manifest = build_manifest(latest, processed, "260910", "", dry_run=True)
        first_look = dry_manifest["segments"]["female_10"]["looks"][0]
        assert first_look["url"] is None
        assert first_look["staging_path"].endswith(".webp")
        ok, reason = validate_complete_manifest(dry_manifest, require_public_urls=False)
        assert ok, reason

        publisher = FileSystemPublisher(root / "publisher", "https://valid-public-host.example")
        write_json(publisher.root / "latest.json", latest)
        published = atomic_publish_segments(processed, "260910", publisher)
        latest_after = json.loads((publisher.root / "latest.json").read_text(encoding="utf-8"))
        assert latest_after == published
        assert latest_after["segments"]["female_10"]["source_date"] == "260910"
        assert latest_after["segments"]["female_20"]["source_date"] == "260910"
        assert latest_after["segments"]["female_30"]["source_date"] == "260910"
        for segment in SEGMENTS[3:]:
            assert latest_after["segments"][segment] == latest["segments"][segment]

        assert publisher.rollback_latest()
        rolled_back = json.loads((publisher.root / "latest.json").read_text(encoding="utf-8"))
        assert rolled_back == latest

        for kwargs in (
            {"fail_upload": True},
            {"fail_url_validation": True},
            {"fail_manifest_validation": True},
            {"fail_switch": True},
        ):
            fail_root = root / ("fail_" + "_".join(kwargs.keys()))
            failing = FileSystemPublisher(fail_root, "https://valid-public-host.example", **kwargs)
            write_json(failing.root / "latest.json", latest)
            before = json.loads((failing.root / "latest.json").read_text(encoding="utf-8"))
            try:
                atomic_publish_segments(processed, "260910", failing)
                raise AssertionError(f"expected failure for {kwargs}")
            except RuntimeError:
                assert_latest_unchanged(failing.root, before)

        source, cuts = make_source("female_10", "260910", cut_root)
        gcs = GcsPublisher("todaypick-test-bucket", "test-project")
        gcs._object_exists = lambda _object_name: False
        calls = []
        gcs._run_gcloud = lambda args: calls.append(args) or ""
        uploaded = gcs.upload_asset(cuts[0]["path"], "260910", source, cuts[0])
        assert uploaded["path"].startswith("gs://todaypick-test-bucket/staging/assets/female/10/260910/look_01_")
        assert uploaded["url"].startswith("https://storage.googleapis.com/todaypick-test-bucket/staging/assets/female/10/260910/look_01_")
        assert "--content-type=image/webp" in calls[0]
        assert "--cache-control=public, max-age=31536000, immutable" in calls[0]

    print("remote daily look tests passed")


if __name__ == "__main__":
    run()
