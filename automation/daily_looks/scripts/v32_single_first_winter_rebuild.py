import argparse
import json
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parent))

from append_seasonal_catalog_from_staging import (  # noqa: E402
    CACHE_ASSET,
    CACHE_NO_CACHE,
    CACHE_VERSIONED_JSON,
    public_url,
    read_json_object,
    run_gcloud,
    storage_url,
    upload_json,
)
from remote_daily_looks import (  # noqa: E402
    SINGLE_CUT_HEIGHT,
    SINGLE_CUT_WIDTH,
    SourceImage,
    compose_single_cuts_to_canonical_sheet,
    load_config,
    now_iso,
    roundtrip_canonical_sheet,
    sha256_file,
    technical_validate_cut,
    validate_leaf_catalog,
    write_json,
)
from prompt_rotation import accumulate_new_set_first  # noqa: E402


SEGMENTS = [
    "female_10", "female_20", "female_30", "female_40", "female_50", "female_60",
    "male_10", "male_20", "male_30", "male_40", "male_50", "male_60",
]

VISUAL_QA_FIELDS = [
    "HEAD_VISIBLE",
    "HAIR_NOT_CROPPED",
    "FEET_VISIBLE",
    "SHOES_VISIBLE",
    "ONE_PERSON_ONLY",
    "NO_ADJACENT_PERSON",
    "NO_TEXT",
    "NO_LOGO",
    "NO_WATERMARK",
    "NO_MAJOR_FACE_ARTIFACT",
    "NO_MAJOR_HAND_ARTIFACT",
    "AGE_MATCH",
    "GENDER_MATCH",
    "WINTER_STYLE",
]


@dataclass
class ApprovedSingle:
    index: int
    path: Path
    sha256: str


def upload_file_force(path, object_name, content_type, cache_control):
    run_gcloud([
        "storage",
        "cp",
        f"--content-type={content_type}",
        f"--cache-control={cache_control}",
        str(path),
        storage_url(object_name),
    ])


def find_single(segment_dir, index):
    candidates = [
        segment_dir / f"{index:02d}.png",
        segment_dir / f"{index:02d}.webp",
        segment_dir / f"single_{index:02d}.png",
        segment_dir / f"single_{index:02d}.webp",
        segment_dir / f"look_{index:02d}.png",
        segment_dir / f"look_{index:02d}.webp",
    ]
    for path in candidates:
        if path.exists():
            return path
    matches = sorted(segment_dir.glob(f"*{index:02d}*"))
    matches = [path for path in matches if path.suffix.lower() in {".png", ".webp", ".jpg", ".jpeg"}]
    return matches[0] if matches else None


def load_visual_qa(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "cuts" in data:
        data = data["cuts"]
    if not isinstance(data, list):
        raise RuntimeError("visual QA file must be a list or an object with a cuts list")
    qa = {}
    for item in data:
        segment = item.get("segment")
        index = int(item.get("index", item.get("cut_index", 0)))
        if segment and index:
            qa[(segment, index)] = item
    return qa


def assert_visual_qa_pass(visual_qa, segment, index):
    item = visual_qa.get((segment, index))
    if not item:
        raise RuntimeError(f"{segment} #{index:02d}: missing visual QA record")
    failed = [field for field in VISUAL_QA_FIELDS if item.get(field) is not True]
    if failed:
        raise RuntimeError(f"{segment} #{index:02d}: visual QA not PASS: {failed}")
    if int(item.get("QA_SCORE", 0)) < 90:
        raise RuntimeError(f"{segment} #{index:02d}: QA_SCORE below 90: {item.get('QA_SCORE')}")


def prepare_single(path, out_path, cfg):
    with Image.open(path) as im:
        image = im.convert("RGB")
    if image.size != (SINGLE_CUT_WIDTH, SINGLE_CUT_HEIGHT):
        raise RuntimeError(f"{path}: expected {SINGLE_CUT_WIDTH}x{SINGLE_CUT_HEIGHT}, got {image.size}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, "WEBP", quality=int(cfg.get("webp_quality", 90)))
    ok, reason = technical_validate_cut(out_path, cfg)
    if not ok:
        raise RuntimeError(f"{path}: technical validation failed: {reason}")
    return ApprovedSingle(index=0, path=out_path, sha256=sha256_file(out_path))


def mean_abs_delta(a, b):
    a_img = Image.open(a).convert("RGB").resize((64, 114), Image.Resampling.LANCZOS)
    b_img = Image.open(b).convert("RGB").resize((64, 114), Image.Resampling.LANCZOS)
    diff = ImageChops.difference(a_img, b_img)
    pixels = diff.tobytes()
    return sum(pixels) / max(1, len(pixels))


def assert_roundtrip_mapping(singles, roundtrip):
    if len(roundtrip) != 10:
        raise RuntimeError(f"ROUNDTRIP_CUT_COUNT expected 10, got {len(roundtrip)}")
    for idx, cut_path in enumerate(roundtrip):
        own = mean_abs_delta(cut_path, singles[idx].path)
        nearest = min(mean_abs_delta(cut_path, other.path) for pos, other in enumerate(singles) if pos != idx)
        if own >= nearest:
            raise RuntimeError(f"roundtrip mapping mismatch at cut {idx + 1}: own={own:.3f}, nearest_other={nearest:.3f}")


def load_index():
    try:
        return read_json_object("production/index.json")
    except Exception:
        return {"schema_version": 2, "seasons": {}}


def upload_index_with_winter_segments(index):
    index.setdefault("schema_version", 2)
    index.setdefault("seasons", {})
    winter = index["seasons"].setdefault("winter", {})
    for segment in SEGMENTS:
        winter[segment] = public_url(f"production/winter/{segment}.json")
    index["updated_at"] = now_iso()
    upload_json(index, "production/index.json", CACHE_NO_CACHE)


def process_segment(args, cfg, visual_qa, segment, work_root):
    gender, age_s = segment.split("_")
    age = int(age_s)
    segment_dir = Path(args.base_dir) / segment
    if not segment_dir.exists():
        raise RuntimeError(f"{segment}: missing input directory: {segment_dir}")

    singles = []
    for index in range(1, 11):
        source_path = find_single(segment_dir, index)
        if not source_path:
            raise RuntimeError(f"{segment}: missing single cut #{index:02d}")
        assert_visual_qa_pass(visual_qa, segment, index)
        out_path = work_root / segment / "singles_webp" / f"look_{index:02d}.webp"
        single = prepare_single(source_path, out_path, cfg)
        single.index = index
        singles.append(single)

    sheet_path = work_root / segment / "sheet.png"
    compose_single_cuts_to_canonical_sheet([single.path for single in singles], sheet_path)
    roundtrip = roundtrip_canonical_sheet(sheet_path, work_root / segment / "roundtrip")
    assert_roundtrip_mapping(singles, roundtrip)

    sheet_sha = sha256_file(sheet_path)
    set_id = f"winter_{gender}_{age}_{args.date}_{sheet_sha[:8]}"
    sheet_object = f"production/sheets/winter/{args.date}/{gender}/{age}/sheet_{sheet_sha[:12]}.png"
    sheet_url = public_url(sheet_object)

    looks = []
    for single in singles:
        object_name = f"production/assets/winter/{args.date}/{gender}/{age}/look_{single.index:02d}_{single.sha256[:12]}.webp"
        looks.append({
            "id": f"winter_{segment}_{args.date}_{single.index:02d}",
            "url": public_url(object_name),
            "sha256": single.sha256,
            "width": SINGLE_CUT_WIDTH,
            "height": SINGLE_CUT_HEIGHT,
            "source_date": args.date,
            "set_id": set_id,
            "sheet_url": sheet_url,
            "cut_index": single.index,
            "generation_method": "single_first",
            "pipeline_version": "v3.2",
            "single_first": True,
            "_local_path": str(single.path),
            "_object_name": object_name,
        })

    source = SourceImage(
        path=sheet_path,
        gender=gender,
        age=age,
        segment=segment,
        filename=sheet_path.name,
        size=sheet_path.stat().st_size,
        mtime=sheet_path.stat().st_mtime,
        sha256=sheet_sha,
        season="winter",
    )
    active_object = f"production/winter/{segment}.json"
    previous_object = f"production/winter/previous/{segment}.json"
    try:
        old_catalog = read_json_object(active_object)
    except Exception:
        old_catalog = {
            "schema_version": 2,
            "season": "winter",
            "gender": gender,
            "age_group": age,
            "segment": segment,
            "count": 0,
            "looks": [],
        }

    accumulation = accumulate_new_set_first(
        old_catalog.get("looks", []),
        [{k: v for k, v in look.items() if not k.startswith("_")} for look in looks],
        existing_catalog=old_catalog,
    )
    catalog = {
        **old_catalog,
        "schema_version": 2,
        "season": "winter",
        "gender": gender,
        "age_group": age,
        "segment": segment,
        "count": len(accumulation["looks"]),
        "updated_at": now_iso(),
        "last_source_date": args.date,
        "last_10cut_set_id": set_id,
        "last_10cut_sheet_url": sheet_url,
        "single_first": True,
        "visual_qa_required": True,
        "source_file": source.filename,
        "source_sha256": source.sha256,
        "catalog_policy": "new_single_first_set_first_preserve_single_first_history_exclude_sheet_first_legacy",
        "legacy_sheet_first_removed": accumulation["legacy_removed"],
        "preserved_single_first_history": accumulation["preserved_single_first"],
        "looks": accumulation["looks"],
    }
    valid, valid_reason = validate_leaf_catalog(catalog, require_public_urls=True)
    if not valid:
        raise RuntimeError(f"{segment}: catalog validation failed: {valid_reason}")

    if args.publish:
        upload_file_force(sheet_path, sheet_object, "image/png", CACHE_ASSET)
        for look in looks:
            upload_file_force(Path(look["_local_path"]), look["_object_name"], "image/webp", CACHE_ASSET)
        upload_json(catalog, f"production/winter/manifests/{segment}_{args.date}_v32_single_first_{int(time.time())}.json", CACHE_VERSIONED_JSON)
        try:
            run_gcloud(["storage", "cp", storage_url(active_object), storage_url(previous_object)])
        except Exception:
            pass
        upload_json(catalog, active_object, CACHE_NO_CACHE)

    return {
        "segment": segment,
        "status": "READY" if not args.publish else "PUBLISHED",
        "single_count": len(singles),
        "roundtrip_cut_count": len(roundtrip),
        "roundtrip_mapping_1_to_1": True,
        "set_id": set_id,
        "sheet_url": sheet_url,
        "old_url_reused": False,
        "catalog_url": public_url(active_object),
    }


def main():
    parser = argparse.ArgumentParser(description="Build winter production catalogs from approved single-first v3.2 assets.")
    parser.add_argument("--base-dir", required=True, help="Directory containing one folder per segment, each with 10 approved singles.")
    parser.add_argument("--visual-qa", required=True, help="JSON list with explicit visual PASS fields for every cut.")
    parser.add_argument("--date", default="260915")
    parser.add_argument("--segments", default=",".join(SEGMENTS))
    parser.add_argument("--report", required=True)
    parser.add_argument("--publish", action="store_true", help="Upload and activate catalogs. Without this, only validates locally.")
    args = parser.parse_args()

    cfg = load_config()
    visual_qa = load_visual_qa(args.visual_qa)
    selected_segments = [item.strip() for item in args.segments.split(",") if item.strip()]
    unknown = [segment for segment in selected_segments if segment not in SEGMENTS]
    if unknown:
        raise RuntimeError(f"unknown segments: {unknown}")
    with tempfile.TemporaryDirectory() as td:
        work_root = Path(td)
        results = {}
        for segment in selected_segments:
            results[segment] = process_segment(args, cfg, visual_qa, segment, work_root)
        if args.publish:
            upload_index_with_winter_segments(load_index())

    report = {
        "MASTER_GUIDE_VERSION": "v3.2",
        "PIPELINE": "single-first",
        "PUBLISH_MODE": bool(args.publish),
        "SEGMENTS": results,
        "READY_FOR_UI": bool(args.publish and len(results) == 12),
    }
    write_json(Path(args.report), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
