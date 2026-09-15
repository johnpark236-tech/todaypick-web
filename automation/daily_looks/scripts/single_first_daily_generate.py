"""TodayPick MASTER v3.2 single-first daily generation orchestration.

Production direction is intentionally:
approved independent singles -> deterministic 5x2 sheets -> roundtrip QA.

The old direction, AI sheet -> crop -> production singles, is not allowed from
scheduled or Run Now production entrypoints.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw

from remote_daily_looks import (
    SINGLE_CUT_HEIGHT,
    SINGLE_CUT_WIDTH,
    compose_single_cuts_to_canonical_sheet,
    load_config,
    roundtrip_canonical_sheet,
    sha256_file,
    technical_validate_cut,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DAILY_LOOKS_ROOT = PROJECT_ROOT / "automation" / "daily_looks"
REPORT_ROOT = DAILY_LOOKS_ROOT / "remote_pipeline" / "manifests"
PREPARED_ROOT = DAILY_LOOKS_ROOT / "remote_pipeline" / "single_first_prepared"
DEFAULT_DRIVE_SOURCE_ROOT = Path(os.environ.get("TODAYPICK_USER_CONFIG_ROOT", r"G:\내 드라이브\TodayPick_user_config"))
KST = timezone(timedelta(hours=9), name="KST")

SEGMENTS = [
    "female_10", "female_20", "female_30", "female_40", "female_50", "female_60",
    "male_10", "male_20", "male_30", "male_40", "male_50", "male_60",
]

VISUAL_QA_FIELDS = [
    "HEAD_VISIBLE",
    "HAIR_VISIBLE",
    "FEET_VISIBLE",
    "ONE_PERSON_ONLY",
    "NO_ADJACENT_PERSON",
    "AGE_MATCH",
    "GENDER_MATCH",
    "SEASON_MATCH",
]


class SingleFirstCapabilityError(RuntimeError):
    """Raised when autonomous v3.2 generation is not configured."""


@dataclass
class SingleFirstOptions:
    date_folder: str
    date_iso: str
    season: str
    segments: list[str]
    trigger_source: str
    scheduled_time: str | None
    schedule_revision: int | None
    run_id: str
    mode: str = "live"
    manual_input_base: Path | None = None
    prepare_only: bool = False
    verify_only: bool = False
    publish: bool = False
    smoke: bool = False


def now_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def report_path_for(date_folder: str, run_id: str) -> Path:
    safe_run_id = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in run_id)
    return REPORT_ROOT / f"{date_folder}_single_first_auto_run_report_{safe_run_id}.json"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def assert_visual_qa_pass(record: dict[str, Any], segment: str, index: int) -> None:
    failed = [field for field in VISUAL_QA_FIELDS if record.get(field) is not True]
    if failed:
        raise RuntimeError(f"{segment} #{index:02d}: visual QA failed: {failed}")
    if int(record.get("QA_SCORE", 0)) < 90:
        raise RuntimeError(f"{segment} #{index:02d}: QA_SCORE below 90")


def find_manual_single(segment_dir: Path, index: int) -> Path | None:
    candidates = [
        segment_dir / f"{index:02d}.png",
        segment_dir / f"{index:02d}.webp",
        segment_dir / f"{index:02d}.jpg",
        segment_dir / f"{index:02d}.jpeg",
        segment_dir / f"single_{index:02d}.png",
        segment_dir / f"single_{index:02d}.webp",
        segment_dir / f"look_{index:02d}.png",
        segment_dir / f"look_{index:02d}.webp",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def load_visual_qa_manifest(segment_dir: Path) -> dict[tuple[str, int], dict[str, Any]]:
    path = segment_dir / "visual_qa.json"
    if not path.exists():
        raise RuntimeError(f"{segment_dir}: visual_qa.json is required")
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "cuts" in data:
        rows = data["cuts"]
    elif isinstance(data, list):
        rows = data
    else:
        raise RuntimeError(f"{path}: visual QA file must be a list or an object with cuts")
    if not isinstance(rows, list):
        raise RuntimeError(f"{path}: cuts must be a list")
    qa: dict[tuple[str, int], dict[str, Any]] = {}
    for item in rows:
        if not isinstance(item, dict):
            raise RuntimeError(f"{path}: each QA row must be an object")
        item_segment = str(item.get("segment") or "")
        index = int(item.get("index", item.get("cut_index", 0)) or 0)
        if not item_segment or not index:
            raise RuntimeError(f"{path}: each QA row requires segment and index")
        qa[(item_segment, index)] = item
    return qa


def manual_base_for(options: SingleFirstOptions) -> Path:
    if options.manual_input_base:
        return Path(options.manual_input_base)
    return DEFAULT_DRIVE_SOURCE_ROOT / options.date_folder / "single_first" / options.season


def segment_input_dir(base: Path, season: str, segment: str) -> Path:
    direct = base / segment
    if direct.exists():
        return direct
    nested = base / season / segment
    if nested.exists():
        return nested
    return direct


def prepare_manual_single(path: Path, out_path: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    with Image.open(path) as im:
        image = im.convert("RGB")
    if image.size != (SINGLE_CUT_WIDTH, SINGLE_CUT_HEIGHT):
        raise RuntimeError(f"{path}: expected {SINGLE_CUT_WIDTH}x{SINGLE_CUT_HEIGHT}, got {image.size}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, "WEBP", quality=int(cfg.get("webp_quality", 90)))
    ok, reason = technical_validate_cut(out_path, {"cut_width": SINGLE_CUT_WIDTH, "cut_height": SINGLE_CUT_HEIGHT})
    if not ok:
        raise RuntimeError(f"{path}: technical validation failed: {reason}")
    return {
        "path": out_path,
        "sha256": sha256_file(out_path),
    }


def mean_abs_delta(a: Path, b: Path) -> float:
    a_img = Image.open(a).convert("RGB").resize((64, 114), Image.Resampling.LANCZOS)
    b_img = Image.open(b).convert("RGB").resize((64, 114), Image.Resampling.LANCZOS)
    diff = ImageChops.difference(a_img, b_img)
    data = diff.tobytes()
    return sum(data) / max(1, len(data))


def assert_roundtrip_mapping(singles: list[Path], roundtrip: list[Path]) -> None:
    if len(roundtrip) != 10:
        raise RuntimeError(f"ROUNDTRIP_CUT_COUNT expected 10, got {len(roundtrip)}")
    for idx, cut_path in enumerate(roundtrip):
        own = mean_abs_delta(cut_path, singles[idx])
        nearest_other = min(mean_abs_delta(cut_path, other) for pos, other in enumerate(singles) if pos != idx)
        if own >= nearest_other:
            raise RuntimeError(f"roundtrip mapping mismatch at cut {idx + 1}")


def create_smoke_single(path: Path, segment: str, index: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    base = ((index * 31) % 220, 80 + (index * 11) % 120, 130 + (index * 17) % 100)
    im = Image.new("RGB", (SINGLE_CUT_WIDTH, SINGLE_CUT_HEIGHT), base)
    draw = ImageDraw.Draw(im)
    draw.rectangle([0, 0, SINGLE_CUT_WIDTH, SINGLE_CUT_HEIGHT], fill=base)
    # Non-text marker blocks keep smoke tests deterministic without creating
    # any production-looking placeholder output.
    marker = (255 - base[0], 255 - base[1], 255 - base[2])
    for x in range(0, SINGLE_CUT_WIDTH, 5):
        for y in range(0, SINGLE_CUT_HEIGHT, 7):
            draw.point((x, y), fill=((base[0] + x) % 255, (base[1] + y) % 255, (base[2] + x + y) % 255))
    draw.rectangle([40 + index * 9, 90, 120 + index * 9, 190], fill=marker)
    draw.ellipse([260, 160, 388, 288], fill=(230, 196, 172))
    draw.rectangle([244, 320, 404, 650], fill=marker)
    draw.rectangle([260, 650, 318, 980], fill=(35, 45, 55))
    draw.rectangle([330, 650, 388, 980], fill=(35, 45, 55))
    draw.rectangle([245, 990, 320, 1035], fill=(240, 240, 240))
    draw.rectangle([325, 990, 400, 1035], fill=(240, 240, 240))
    im.save(path, "WEBP", quality=92)
    return path


def smoke_visual_qa_record(segment: str, index: int) -> dict[str, Any]:
    gender, age = segment.split("_", 1)
    return {
        "segment": segment,
        "index": index,
        "HEAD_VISIBLE": True,
        "HAIR_VISIBLE": True,
        "FEET_VISIBLE": True,
        "ONE_PERSON_ONLY": True,
        "NO_ADJACENT_PERSON": True,
        "AGE_MATCH": True,
        "GENDER_MATCH": True,
        "SEASON_MATCH": True,
        "QA_SCORE": 95,
        "gender": gender,
        "age_group": int(age),
    }


def provider_capability() -> dict[str, Any]:
    provider = os.environ.get("TODAYPICK_SINGLE_FIRST_PROVIDER", "").strip()
    gemini = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    return {
        "provider": provider or None,
        "gemini_api_key_present": gemini,
        "capable": provider == "gemini_single_first" and gemini,
    }


def process_segment_smoke(options: SingleFirstOptions, segment: str, work_root: Path) -> dict[str, Any]:
    segment_dir = work_root / segment
    singles: list[Path] = []
    qa_records = []
    for index in range(1, 11):
        single = create_smoke_single(segment_dir / "singles" / f"single_{index:02d}.webp", segment, index)
        ok, reason = technical_validate_cut(single, {"cut_width": SINGLE_CUT_WIDTH, "cut_height": SINGLE_CUT_HEIGHT})
        if not ok:
            raise RuntimeError(f"{segment} #{index:02d}: technical validation failed: {reason}")
        record = smoke_visual_qa_record(segment, index)
        assert_visual_qa_pass(record, segment, index)
        qa_records.append(record)
        singles.append(single)

    sheet = compose_single_cuts_to_canonical_sheet(singles, segment_dir / "sheet.png")
    roundtrip = roundtrip_canonical_sheet(sheet, segment_dir / "roundtrip")
    assert_roundtrip_mapping(singles, roundtrip)
    return {
        "segment": segment,
        "status": "SMOKE_PASS",
        "single_target": 10,
        "single_generation_count": len(singles),
        "visual_qa_count": len(qa_records),
        "sheet_count": 1,
        "roundtrip_mapping": f"{len(roundtrip)}/10",
        "publish": False,
    }


def process_segment_manual(options: SingleFirstOptions, segment: str, input_base: Path, prepared_root: Path) -> dict[str, Any]:
    segment_dir = segment_input_dir(input_base, options.season, segment)
    if not segment_dir.exists():
        raise RuntimeError(f"{segment}: missing input directory: {segment_dir}")
    visual_qa = load_visual_qa_manifest(segment_dir)
    cfg = load_config()
    prepared_segment = prepared_root / segment
    singles: list[Path] = []
    look_records = []
    for index in range(1, 11):
        source = find_manual_single(segment_dir, index)
        if not source:
            raise RuntimeError(f"{segment}: missing approved single image #{index:02d}")
        qa_record = visual_qa.get((segment, index))
        if not qa_record:
            raise RuntimeError(f"{segment} #{index:02d}: missing visual QA record")
        assert_visual_qa_pass(qa_record, segment, index)
        prepared = prepare_manual_single(source, prepared_segment / "singles_webp" / f"look_{index:02d}.webp", cfg)
        singles.append(prepared["path"])
        look_records.append({
            "index": index,
            "sha256": prepared["sha256"],
            "width": SINGLE_CUT_WIDTH,
            "height": SINGLE_CUT_HEIGHT,
            "source_file": source.name,
            "cut_index": index,
        })

    sheet = compose_single_cuts_to_canonical_sheet(singles, prepared_segment / "sheet.png")
    roundtrip = roundtrip_canonical_sheet(sheet, prepared_segment / "roundtrip")
    assert_roundtrip_mapping(singles, roundtrip)
    sheet_sha = sha256_file(sheet)
    set_id = f"{options.season}_{segment}_{options.date_folder}_{sheet_sha[:8]}"
    for record in look_records:
        record["set_id"] = set_id
        record["sheet_sha256"] = sheet_sha

    backup_path = None
    if options.publish:
        if options.verify_only or options.prepare_only:
            raise RuntimeError("publish cannot be combined with prepare-only or verify-only")
        if options.segments != SEGMENTS:
            raise RuntimeError("publish mode requires all 12 segments to avoid partial production writes")
        backup_path = f"production/{options.season}/previous/{segment}_{options.date_folder}_{int(time.time())}.json"

    return {
        "segment": segment,
        "status": "PUBLISH_READY" if options.publish else "VERIFIED",
        "input_dir": str(segment_dir),
        "single_count": len(singles),
        "visual_qa_count": 10,
        "sheet_count": 1,
        "sheet_path": str(sheet),
        "sheet_sha256": sheet_sha,
        "roundtrip_mapping": f"{len(roundtrip)}/10",
        "roundtrip_mapping_1_to_1": True,
        "set_id": set_id,
        "backup_path": backup_path,
        "publish_gate": "PASS",
    }


def run_single_first_daily_generation(options: SingleFirstOptions) -> dict[str, Any]:
    started = time.time()
    report_path = report_path_for(options.date_folder, options.run_id)
    report: dict[str, Any] = {
        "MASTER_GUIDE_VERSION": "v3.2",
        "PIPELINE": "v3.2_SINGLE_FIRST",
        "trigger_source": options.trigger_source,
        "scheduled_time": options.scheduled_time,
        "schedule_revision": options.schedule_revision,
        "run_id": options.run_id,
        "date_folder": options.date_folder,
        "date_iso": options.date_iso,
        "season": options.season,
        "segment_target": len(options.segments),
        "single_target": len(options.segments) * 10,
        "sheet_target": len(options.segments),
        "states": ["STARTED"],
        "segments": {},
        "failures": [],
        "publish": bool(options.publish),
        "authoritative_single_source": True,
        "old_sheet_crop_ingest_bypassed": True,
        "status": "STARTED",
    }
    write_json(report_path, report)

    try:
        if options.smoke:
            if len(options.segments) != 1:
                raise RuntimeError("smoke mode requires exactly one segment")
            report["states"].extend(["GENERATING_SINGLES", "VISUAL_QA", "COMPOSING_SHEETS", "ROUNDTRIP_VALIDATION"])
            with tempfile.TemporaryDirectory() as td:
                result = process_segment_smoke(options, options.segments[0], Path(td))
            report["segments"][options.segments[0]] = result
            report["status"] = "SMOKE_PASS"
            report["duration_seconds"] = round(time.time() - started, 3)
            write_json(report_path, report)
            return {**report, "report_path": str(report_path)}

        if options.mode == "manual":
            report["states"].extend(["LOADING_APPROVED_SINGLES", "VISUAL_QA", "COMPOSING_SHEETS", "ROUNDTRIP_VALIDATION"])
            input_base = manual_base_for(options)
            prepared_root = PREPARED_ROOT / options.date_folder / options.season / options.run_id
            for segment in options.segments:
                report["segments"][segment] = process_segment_manual(options, segment, input_base, prepared_root)
            report["manual_input_base"] = str(input_base)
            report["prepared_root"] = str(prepared_root)
            report["prepare_only"] = bool(options.prepare_only)
            report["verify_only"] = bool(options.verify_only)
            report["backup_before_publish"] = bool(options.publish)
            report["status"] = "PUBLISH_READY" if options.publish else "VERIFIED"
            report["duration_seconds"] = round(time.time() - started, 3)
            write_json(report_path, report)
            return {**report, "report_path": str(report_path)}

        capability = provider_capability()
        report["provider_capability"] = capability
        if not capability["capable"]:
            raise SingleFirstCapabilityError(
                "v3.2 single-first autonomous image generation provider is not configured; "
                "set TODAYPICK_SINGLE_FIRST_PROVIDER=gemini_single_first with GEMINI_API_KEY/GOOGLE_API_KEY"
            )

        raise SingleFirstCapabilityError(
            "gemini_single_first provider contract is reserved but not implemented; production fails closed"
        )
    except Exception as exc:
        report["status"] = "FAILED"
        report["failures"].append({"error": str(exc), "type": type(exc).__name__})
        report["duration_seconds"] = round(time.time() - started, 3)
        write_json(report_path, report)
        raise


__all__ = [
    "SEGMENTS",
    "SingleFirstCapabilityError",
    "SingleFirstOptions",
    "provider_capability",
    "run_single_first_daily_generation",
]
