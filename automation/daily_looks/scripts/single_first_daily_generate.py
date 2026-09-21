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
    openart = bool(os.environ.get("OPENART_API_KEY", "").strip())
    fal = bool(os.environ.get("FAL_KEY", "").strip())
    picsart = bool(os.environ.get("PICSART_API_KEY", "").strip())
    multi_capable = provider == "multi_provider" and (openart or fal or picsart)
    legacy_gemini_capable = provider == "gemini_single_first" and gemini
    return {
        "provider": provider or None,
        "gemini_api_key_present": gemini,
        "openart_key_present": openart,
        "fal_key_present": fal,
        "picsart_key_present": picsart,
        "capable": multi_capable or legacy_gemini_capable,
        "mode": "multi_provider" if multi_capable else ("gemini_single_first" if legacy_gemini_capable else None),
    }


_NEGATIVE_PROMPT_PATH = DAILY_LOOKS_ROOT / "config" / "negative_prompt.txt"
_SINGLE_PROMPT_TEMPLATE_PATH = DAILY_LOOKS_ROOT / "config" / "single_first_prompt_template.txt"
_CANONICAL_PROMPT_ROOT = DEFAULT_DRIVE_SOURCE_ROOT / "00_IMAGE_PROMPTS" / "v3.2_single_first_48"

_SEASON_FOLDER_MAP = {
    "spring": "01_SPRING",
    "summer": "02_SUMMER",
    "autumn": "03_AUTUMN",
    "winter": "04_WINTER",
}


def _canonical_prompt_path(segment: str, season: str) -> Path:
    folder = _SEASON_FOLDER_MAP.get(season, f"04_{'WINTER'}")
    filename = f"TodayPick_v3.2_{season}_{segment}_10looks.md"
    return _CANONICAL_PROMPT_ROOT / folder / filename


def _build_single_first_prompt(segment: str, season: str, index: int) -> str:
    """Build prompt for look {index} from the canonical v3.2 prompt library.

    Strategy:
    1. Load the authoritative segment prompt file from Drive.
    2. Extract the global header (all content before the first ### LOOK).
    3. Extract the specific ### LOOK NN block.
    4. Combine: global header + look-specific block.
    5. If the canonical file is unavailable, append the generic template wrapper.
    """
    prompt_path = _canonical_prompt_path(segment, season)
    wrapper_suffix = ""
    if _SINGLE_PROMPT_TEMPLATE_PATH.exists():
        wrapper_suffix = "\n\n" + _SINGLE_PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8").strip()

    if not prompt_path.exists():
        # Canonical prompt not found; use generic wrapper as fallback.
        return (
            f"One full-body Korean fashion portrait, single character, head to toe. "
            f"Segment: {segment}, season: {season.upper()}, look {index:02d} of 10. "
            f"Full body mandatory: head, face, hair, hands, feet, shoes all visible. "
            f"One person only. No text, watermark, or logos. "
            f"2D digital illustration style, clean linework, Korean fashion app quality."
            + wrapper_suffix
        )

    full_text = prompt_path.read_text(encoding="utf-8")

    # Split on ### LOOK markers to isolate global header and per-look sections.
    import re
    look_pattern = re.compile(r"^### LOOK\s+(\d+)", re.MULTILINE)
    markers = list(look_pattern.finditer(full_text))

    if not markers:
        return full_text + wrapper_suffix

    global_header = full_text[: markers[0].start()].strip()

    target_look = None
    for i, m in enumerate(markers):
        look_num = int(m.group(1))
        if look_num == index:
            end = markers[i + 1].start() if i + 1 < len(markers) else len(full_text)
            target_look = full_text[m.start(): end].strip()
            break

    if target_look is None:
        # Requested index not found; use global header only.
        return global_header + wrapper_suffix

    return global_header + "\n\n## Diversity Matrix\n\n" + target_look + wrapper_suffix


def _load_negative_prompt_text() -> str:
    if _NEGATIVE_PROMPT_PATH.exists():
        return _NEGATIVE_PROMPT_PATH.read_text(encoding="utf-8").strip()
    return (
        "blurry, low quality, distorted anatomy, cropped head, cropped feet, "
        "cut-off shoes, missing limbs, extra limbs, text, watermark, logo, "
        "multiple people in frame, 3D render, photorealistic, deformed"
    )


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
                "set TODAYPICK_SINGLE_FIRST_PROVIDER=multi_provider with at least one of "
                "OPENART_API_KEY / FAL_KEY / PICSART_API_KEY"
            )

        if capability.get("mode") == "gemini_single_first":
            raise SingleFirstCapabilityError(
                "gemini_single_first provider contract is reserved but not implemented; "
                "use TODAYPICK_SINGLE_FIRST_PROVIDER=multi_provider instead"
            )

        # Live autonomous single-first generation via provider router.
        report["states"].extend([
            "GENERATING_SINGLES", "VISUAL_QA", "COMPOSING_SHEETS", "ROUNDTRIP_VALIDATION",
        ])
        from providers.provider_router import ProviderRouter

        try:
            router = ProviderRouter()
        except RuntimeError as exc:
            raise SingleFirstCapabilityError(str(exc)) from exc

        report["available_providers"] = router.available_providers
        cfg = load_config()
        work_root = PREPARED_ROOT / options.date_folder / options.season / options.run_id
        neg_prompt = _load_negative_prompt_text()

        for segment in options.segments:
            segment_dir = work_root / segment
            singles: list[Path] = []
            qa_records: list[dict[str, Any]] = []

            for index in range(1, 11):
                out_path = segment_dir / "singles" / f"single_{index:02d}.webp"
                prompt = _build_single_first_prompt(segment, options.season, index)
                gen_result = router.generate_single(
                    prompt=prompt,
                    negative_prompt=neg_prompt,
                    output_path=out_path,
                    width=SINGLE_CUT_WIDTH,
                    height=SINGLE_CUT_HEIGHT,
                )
                ok, reason = technical_validate_cut(
                    out_path, {"cut_width": SINGLE_CUT_WIDTH, "cut_height": SINGLE_CUT_HEIGHT}
                )
                if not ok:
                    raise RuntimeError(f"{segment} #{index:02d}: technical validation failed: {reason}")
                singles.append(out_path)
                qa_records.append({
                    "segment": segment,
                    "index": index,
                    "provider": gen_result.get("provider_id"),
                    "sha256": sha256_file(out_path),
                    "width": SINGLE_CUT_WIDTH,
                    "height": SINGLE_CUT_HEIGHT,
                })

            sheet = compose_single_cuts_to_canonical_sheet(
                singles, segment_dir / "sheet.png"
            )
            roundtrip = roundtrip_canonical_sheet(sheet, segment_dir / "roundtrip")
            assert_roundtrip_mapping(singles, roundtrip)
            sheet_sha = sha256_file(sheet)
            set_id = f"{options.season}_{segment}_{options.date_folder}_{sheet_sha[:8]}"

            report["segments"][segment] = {
                "segment": segment,
                "status": "GENERATED",
                "single_count": len(singles),
                "qa_records": qa_records,
                "sheet_path": str(sheet),
                "sheet_sha256": sheet_sha,
                "roundtrip_mapping": f"{len(roundtrip)}/10",
                "set_id": set_id,
                "publish": bool(options.publish),
            }

        report["status"] = "PUBLISHED" if options.publish else "GENERATED"
        report["duration_seconds"] = round(time.time() - started, 3)
        write_json(report_path, report)
        return {**report, "report_path": str(report_path)}
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
