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
    roundtrip_canonical_sheet,
    technical_validate_cut,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DAILY_LOOKS_ROOT = PROJECT_ROOT / "automation" / "daily_looks"
REPORT_ROOT = DAILY_LOOKS_ROOT / "remote_pipeline" / "manifests"
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
