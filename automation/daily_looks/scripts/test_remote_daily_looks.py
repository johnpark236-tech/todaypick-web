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
    CANONICAL_V3_MAX_SEPARATOR_PX,
    FileSystemPublisher,
    GcsPublisher,
    SourceImage,
    atomic_publish_segments,
    build_index_manifest,
    build_leaf_catalog,
    build_manifest,
    canonical_v3_cell_box,
    canonical_v3_column_boundaries,
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
    col_bounds = [0, 263, 525, 788, 1050, 1313]
    row_bounds = [0, 599, 1198]
    for row in range(2):
        for col in range(5):
            color = (220, 30 + col * 20, 30) if row == 0 else (30, 60 + col * 20, 220)
            x0 = col_bounds[col]
            x1 = col_bounds[col + 1]
            y0 = row_bounds[row]
            y1 = row_bounds[row + 1]
            for x in range(x0, x1):
                for y in range(y0, y1):
                    image.putpixel((x, y), (
                        (color[0] + x + y) % 255,
                        (color[1] + x * 2 + y // 2) % 255,
                        (color[2] + x // 3 + y * 3) % 255,
                    ))
    image.save(path)
    return path


def make_separator_sheet(path, separator_px):
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (CANONICAL_V3_WIDTH, CANONICAL_V3_HEIGHT), (220, 230, 238))
    col_bounds = [0, 263, 525, 788, 1050, 1313]
    row_bounds = [0, 599, 1198]
    for row in range(2):
        for col in range(5):
            color = (80 + col * 20, 120 + row * 30, 150 + col * 8)
            x0 = col_bounds[col]
            x1 = col_bounds[col + 1]
            y0 = row_bounds[row]
            y1 = row_bounds[row + 1]
            Image.new("RGB", (x1 - x0, y1 - y0), color).save(path.with_suffix(f".{row}{col}.tmp.png"))
            patch = Image.open(path.with_suffix(f".{row}{col}.tmp.png"))
            image.paste(patch, (x0, y0))
            path.with_suffix(f".{row}{col}.tmp.png").unlink()
    half = separator_px // 2
    for x in (263, 525, 788, 1050):
        for dx in range(separator_px):
            px = x - half + dx
            if 0 <= px < CANONICAL_V3_WIDTH:
                for y in range(CANONICAL_V3_HEIGHT):
                    image.putpixel((px, y), (255, 255, 255))
    y = 599
    for dy in range(separator_px):
        py = y - half + dy
        if 0 <= py < CANONICAL_V3_HEIGHT:
            for x in range(CANONICAL_V3_WIDTH):
                image.putpixel((x, py), (255, 255, 255))
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
        # New: Korean season prefix + YYMMDD suffix
        ("겨울_여성10대_260912.png", "winter", "female_10"),
        ("여성10대_260912.png", None, "female_10"),
        ("여성10대.png", None, "female_10"),
        ("가을_남성30대_260912.png", "autumn", "male_30"),
        ("winter_female_10_260912.png", "winter", "female_10"),
        ("봄_여성20대_260601.png", "spring", "female_20"),
        ("여름_남성20대.png", "summer", "male_20"),
    ):
        match = FILENAME_RE.match(filename)
        assert match, filename
        assert season_from_match(match) == expected_season, f"{filename}: expected season={expected_season!r}, got {season_from_match(match)!r}"
        assert segment_from_match(match)[2] == expected_segment, f"{filename}: expected segment={expected_segment!r}"

    # Date extraction tests using FILENAME_RE directly

    result = FILENAME_RE.match("겨울_여성10대_260912.png")
    assert result is not None
    assert result.group("date") == "260912"
    assert season_from_match(result) == "winter"
    assert segment_from_match(result)[2] == "female_10"
    # No date suffix should yield None for date group
    result2 = FILENAME_RE.match("여성10대.png")
    assert result2 is not None
    assert result2.group("date") is None

    # Unsupported filenames must return None from FILENAME_RE
    for bad in ("불명확_파일.png", "look_01.webp", "sheet.jpg", "random.png"):
        assert FILENAME_RE.match(bad) is None, f"Expected no match for {bad!r}"


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
        assert "1313x1198" in reason

        thin_separator = make_separator_sheet(root / "thin_separator.png", CANONICAL_V3_MAX_SEPARATOR_PX)
        ok, reason, _ = validate_source(thin_separator, cfg, crop_profile=CANONICAL_V3_PROFILE)
        assert ok, reason

        wide_separator = make_separator_sheet(root / "wide_separator.png", CANONICAL_V3_MAX_SEPARATOR_PX + 3)
        ok, reason, _ = validate_source(wide_separator, cfg, crop_profile=CANONICAL_V3_PROFILE)
        assert not ok
        assert "separator too wide" in reason

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

        # === CANONICAL SIZE TESTS (section 13) ===
        # 1313x1198 MUST pass
        assert (CANONICAL_V3_WIDTH, CANONICAL_V3_HEIGHT) == (1313, 1198)
        # 1280x1168 MUST fail canonical_v3 validation
        old_size_img = root / "old_size_sheet.png"
        Image.new("RGB", (1280, 1168), (200, 200, 200)).save(old_size_img)
        ok_old, reason_old, _ = validate_source(old_size_img, cfg, crop_profile=CANONICAL_V3_PROFILE)
        assert not ok_old, "1280x1168 must fail canonical_v3 validation"
        assert "1313x1198" in reason_old

        # === GRID BOUNDARY TESTS (section 14) ===
        # Verify raw column boundaries match MASTER spec exactly
        assert canonical_v3_column_boundaries() == [0, 263, 525, 788, 1050, 1313], (
            f"Column boundaries mismatch: {canonical_v3_column_boundaries()}"
        )
        # Verify raw cell coordinates (before separator trim) for all 10 cells
        INNER = 2  # CANONICAL_V3_INNER_SEPARATOR_TRIM_PX
        expected_cells_raw = [
            (0, 0, 263, 599),
            (263, 0, 525, 599),
            (525, 0, 788, 599),
            (788, 0, 1050, 599),
            (1050, 0, 1313, 599),
            (0, 599, 263, 1198),
            (263, 599, 525, 1198),
            (525, 599, 788, 1198),
            (788, 599, 1050, 1198),
            (1050, 599, 1313, 1198),
        ]
        col_b = [0, 263, 525, 788, 1050, 1313]
        row_b = [0, 599, 1198]
        for row in range(2):
            for col in range(5):
                idx = row * 5 + col
                ex = expected_cells_raw[idx]
                # Raw boundaries (before trim) must match MASTER
                assert (col_b[col], row_b[row], col_b[col + 1], row_b[row + 1]) == ex, (
                    f"raw cell ({row},{col}) expected {ex}"
                )
                # cell_box applies inner separator trim
                x0, y0, x1, y1 = canonical_v3_cell_box(row, col)
                assert x0 == (ex[0] + INNER if col > 0 else ex[0])
                assert x1 == (ex[2] - INNER if col < 4 else ex[2])
                assert y0 == (ex[1] + INNER if row > 0 else ex[1])
                assert y1 == (ex[3] - INNER if row < 1 else ex[3])

        # === CUT COUNT AND SIZE TESTS (section 15) ===
        assert len(cut_files) == 10, f"Expected 10 cuts, got {len(cut_files)}"
        for item in cut_files:
            cut_im = Image.open(item["path"])
            assert cut_im.size == (648, 1152), (
                f"Cut {item['path']} expected 648x1152, got {cut_im.size}"
            )

        # === CROSS-ROW PIXEL ACCESS TEST (section 16) ===
        # Create a sheet where row1=reddish, row2=bluish.
        # Directly verify that cell_box for row2 cells does NOT include any row1 pixels.
        # This is a direct boundary unit test — no validate_cut file-size requirement.
        from PIL import ImageDraw as _ImageDraw
        cr_img = Image.new("RGB", (CANONICAL_V3_WIDTH, CANONICAL_V3_HEIGHT))
        cr_draw = _ImageDraw.Draw(cr_img)
        # Row1 (y=0..598): reddish
        cr_draw.rectangle([0, 0, CANONICAL_V3_WIDTH - 1, 598], fill=(220, 20, 10))
        # Row2 (y=599..1197): bluish
        cr_draw.rectangle([0, 599, CANONICAL_V3_WIDTH - 1, CANONICAL_V3_HEIGHT - 1], fill=(10, 20, 220))

        # Verify that row2 cell crops have zero row1 pixels
        CROSS_ROW_PIXEL_ACCESS = False
        for col in range(5):
            x0, y0, x1, y1 = canonical_v3_cell_box(1, col)  # row=1
            assert y0 >= 599, f"Row2 cell_box y0={y0} must be >= 599 (row2 start)"
            cell_crop = cr_img.crop((x0, y0, x1, y1))
            stat = cell_crop.getpixel((cell_crop.width // 2, cell_crop.height // 2))
            r, g, b = stat
            # Row2 is bluish: R should be low
            if r > 100 and b < 50:
                CROSS_ROW_PIXEL_ACCESS = True
                break
        assert not CROSS_ROW_PIXEL_ACCESS, "Row2 cell_box must not sample row1 (reddish) pixels"

        # === BLUR BACKGROUND TESTS (section 17) ===
        # Verify output is not pure white or pure black padding, and size is 648x1152.
        # Use ImageStat for efficiency instead of per-pixel loop.
        from PIL import ImageStat as _ImageStat
        for item in cut_files:
            cut_im = Image.open(item["path"]).convert("RGB")
            assert cut_im.size == (648, 1152)
            stat = _ImageStat.Stat(cut_im)
            # min extrema per channel: if all channels have minimum ≥ 254 → all-white
            all_white = all(stat.extrema[c][0] >= 254 for c in range(3))
            # max extrema per channel: if all channels have maximum ≤ 1 → all-black
            all_black = all(stat.extrema[c][1] <= 1 for c in range(3))
            assert not all_white, f"Cut {item['path']} must not be all-white (solid padding)"
            assert not all_black, f"Cut {item['path']} must not be all-black"

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
