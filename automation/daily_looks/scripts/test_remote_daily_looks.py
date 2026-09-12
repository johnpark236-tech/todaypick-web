import json
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from remote_daily_looks import (  # noqa: E402
    CANONICAL_V3_CELL_HEIGHT,
    CANONICAL_V3_PROFILE,
    CANONICAL_V3_WIDTH,
    CANONICAL_V3_HEIGHT,
    FileSystemPublisher,
    GcsPublisher,
    SourceImage,
    atomic_publish_segments,
    build_index_manifest,
    build_leaf_catalog,
    build_manifest,
    canonical_v3_crop_box,
    crop_source_image,
    load_config,
    season_for_date_folder,
    season_for_month,
    season_from_match,
    segment_from_match,
    FILENAME_RE,
    validate_leaf_catalog,
    validate_complete_manifest,
    validate_index_manifest,
    validate_public_asset_url,
    validate_source,
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


def make_canonical_sheet(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (CANONICAL_V3_WIDTH, CANONICAL_V3_HEIGHT), (245, 245, 245))
    for row in range(2):
        for col in range(5):
            color = (220, 30 + col * 20, 30) if row == 0 else (30, 60 + col * 20, 220)
            x0 = col * 256
            x1 = (col + 1) * 256
            y0 = row * 584
            y1 = (row + 1) * 584
            for x in range(x0, x1):
                for y in range(y0, y1):
                    image.putpixel((
                        x,
                        y,
                    ), (
                        (color[0] + x + y) % 255,
                        (color[1] + x * 2 + y // 2) % 255,
                        (color[2] + x // 3 + y * 3) % 255,
                    ))
    image.save(path)
    return path


def assert_latest_unchanged(root, before):
    current = json.loads((root / "latest.json").read_text(encoding="utf-8"))
    assert current == before


def run():
    assert season_for_month(1) == "winter"
    assert season_for_month(2) == "winter"
    assert season_for_month(3) == "spring"
    assert season_for_month(5) == "spring"
    assert season_for_month(6) == "summer"
    assert season_for_month(8) == "summer"
    assert season_for_month(9) == "autumn"
    assert season_for_month(11) == "autumn"
    assert season_for_month(12) == "winter"
    assert season_for_date_folder("260911") == "autumn"
    for filename, expected_season, expected_segment in (
        ("autumn_여성10대.png", "autumn", "female_10"),
        ("winter_female_10.webp", "winter", "female_10"),
        ("여성20대.jpg", None, "female_20"),
        ("male_60.jpeg", None, "male_60"),
    ):
        match = FILENAME_RE.match(filename)
        assert match, filename
        assert season_from_match(match) == expected_season
        assert segment_from_match(match)[2] == expected_segment

    assert not validate_public_asset_url("C:/c/todaypick-web/a.webp")
    assert not validate_public_asset_url("G:/내 드라이브/a.webp")
    assert not validate_public_asset_url("file:///C:/a.webp")
    assert not validate_public_asset_url("../a.webp")
    assert not validate_public_asset_url("http://localhost/a.webp")
    assert validate_public_asset_url("https://valid-public-host.example/a.webp")

    cfg = load_config()
    assert cfg["cut_width"] == 648
    assert cfg["cut_height"] == 1152
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        canonical_path = make_canonical_sheet(root / "여성20대.png")
        ok, reason, image = validate_source(canonical_path, cfg, crop_profile=CANONICAL_V3_PROFILE)
        assert ok, reason
        source = SourceImage(
            path=canonical_path,
            gender="female",
            age=20,
            segment="female_20",
            filename="여성20대.png",
            size=canonical_path.stat().st_size,
            mtime=canonical_path.stat().st_mtime,
            sha256="a" * 64,
        )
        crop_ok, cut_files, validations = crop_source_image(
            image,
            root / "cuts",
            source,
            "260912",
            cfg,
            crop_profile=CANONICAL_V3_PROFILE,
        )
        assert crop_ok
        assert len(cut_files) == 10
        assert sum(1 for item in validations if item["status"] == "PASS") == 10

        portrait = root / "portrait.png"
        Image.new("RGB", (1024, 1536), (255, 255, 255)).save(portrait)
        ok, reason, _ = validate_source(portrait, cfg, crop_profile=CANONICAL_V3_PROFILE)
        assert not ok
        assert "1280x1168" in reason

        _, row2_y0, _, _ = canonical_v3_crop_box(1, 0, cfg["cut_width"] / float(cfg["cut_height"]))
        assert row2_y0 >= CANONICAL_V3_CELL_HEIGHT

        crop_ok2, cut_files2, _ = crop_source_image(
            image,
            root / "cuts_again",
            source,
            "260912",
            cfg,
            crop_profile=CANONICAL_V3_PROFILE,
        )
        assert crop_ok2
        assert [Path(item["path"]).name for item in cut_files] == [Path(item["path"]).name for item in cut_files2]

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
        assert len(dry_manifest["segments"]["female_10"]["looks"]) == 20
        newest_dry_look = dry_manifest["segments"]["female_10"]["looks"][-1]
        assert newest_dry_look["url"] is None
        assert newest_dry_look["staging_path"].endswith(".webp")
        ok, reason = validate_complete_manifest(dry_manifest, require_public_urls=False)
        assert ok, reason

        publisher = FileSystemPublisher(root / "publisher", "https://valid-public-host.example")
        write_json(publisher.root / "latest.json", latest)
        published = atomic_publish_segments(processed, "260910", publisher)
        latest_after = json.loads((publisher.root / "latest.json").read_text(encoding="utf-8"))
        assert latest_after == published
        assert len(latest_after["segments"]["female_10"]["looks"]) == 20
        assert len(latest_after["segments"]["female_20"]["looks"]) == 20
        assert len(latest_after["segments"]["female_30"]["looks"]) == 20
        assert latest_after["segments"]["female_10"]["source_date"] == "260910"
        assert latest_after["segments"]["female_20"]["source_date"] == "260910"
        assert latest_after["segments"]["female_30"]["source_date"] == "260910"
        for segment in SEGMENTS[3:]:
            assert latest_after["segments"][segment] == latest["segments"][segment]

        published_again = atomic_publish_segments(processed, "260910", publisher)
        assert len(published_again["segments"]["female_10"]["looks"]) == 20
        assert len(published_again["segments"]["female_20"]["looks"]) == 20
        assert len(published_again["segments"]["female_30"]["looks"]) == 20

        next_processed = [make_source("female_10", "260911", cut_root)]
        published_next = atomic_publish_segments(next_processed, "260911", publisher)
        assert len(published_next["segments"]["female_10"]["looks"]) == 30
        assert len(published_next["segments"]["female_20"]["looks"]) == 20
        assert len(published_next["segments"]["male_10"]["looks"]) == 10
        ok, reason = validate_complete_manifest(published_next, require_public_urls=True)
        assert ok, reason

        base_source, base_cuts = make_source("female_20", "260910", cut_root)
        base_looks = [
            {
                "id": item["id"],
                "url": f"https://valid-public-host.example/autumn/female_20/{item['filename']}",
                "sha256": item["sha256"],
                "width": 648,
                "height": 1152,
            }
            for item in base_cuts
        ]
        leaf = build_leaf_catalog({}, base_source, base_looks, "autumn", "260910")
        assert leaf["count"] == 10
        ok, reason = validate_leaf_catalog(leaf, require_public_urls=True)
        assert ok, reason

        next_source, next_cuts = make_source("female_20", "260911", cut_root)
        next_looks = [
            {
                "id": item["id"],
                "url": f"https://valid-public-host.example/autumn/female_20/{item['filename']}",
                "sha256": item["sha256"],
                "width": 648,
                "height": 1152,
            }
            for item in next_cuts
        ]
        leaf = build_leaf_catalog(leaf, next_source, next_looks, "autumn", "260911")
        assert leaf["count"] == 20
        leaf = build_leaf_catalog(leaf, next_source, next_looks, "autumn", "260911")
        assert leaf["count"] == 20

        for size in (1, 10, 20, 100, 500):
            sized = dict(leaf)
            sized["looks"] = [
                {
                    "id": f"autumn_female_20_sized_{index:03d}",
                    "url": f"https://valid-public-host.example/autumn/female_20/sized_{index:03d}.webp",
                    "sha256": f"{index + 1:064x}"[-64:],
                    "width": 648,
                    "height": 1152,
                }
                for index in range(size)
            ]
            sized["count"] = size
            ok, reason = validate_leaf_catalog(sized, require_public_urls=True)
            assert ok, reason

        summer_leaf = build_leaf_catalog({}, base_source, base_looks, "summer", "260610")
        male_source, male_cuts = make_source("male_20", "260911", cut_root)
        male_looks = [
            {
                "id": item["id"],
                "url": f"https://valid-public-host.example/autumn/male_20/{item['filename']}",
                "sha256": item["sha256"],
                "width": 648,
                "height": 1152,
            }
            for item in male_cuts
        ]
        male_leaf = build_leaf_catalog({}, male_source, male_looks, "autumn", "260911")
        assert leaf["count"] == 20
        assert summer_leaf["season"] == "summer"
        assert summer_leaf["count"] == 10
        assert male_leaf["segment"] == "male_20"
        assert male_leaf["count"] == 10
        index = build_index_manifest({}, [
            ("autumn", "female_20", "https://valid-public-host.example/production/autumn/female_20.json"),
            ("summer", "female_20", "https://valid-public-host.example/production/summer/female_20.json"),
            ("autumn", "male_20", "https://valid-public-host.example/production/autumn/male_20.json"),
        ])
        ok, reason = validate_index_manifest(index)
        assert ok, reason

        assert publisher.rollback_latest()
        rolled_back = json.loads((publisher.root / "latest.json").read_text(encoding="utf-8"))
        assert rolled_back == published_again

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
