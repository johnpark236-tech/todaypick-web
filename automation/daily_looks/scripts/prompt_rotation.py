"""48-segment v3.2 prompt rotation and catalog set helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DAILY_LOOKS_ROOT = PROJECT_ROOT / "automation" / "daily_looks"
STATE_ROOT = DAILY_LOOKS_ROOT / "state"
CURSOR_PATH = STATE_ROOT / "single_first_rotation_cursor.json"
LOCAL_PROMPT_ROOT = Path(os.environ.get("TODAYPICK_PROMPT_LIBRARY_ROOT", r"G:\내 드라이브\TodayPick_user_config\00_IMAGE_PROMPTS\v3.2_single_first_48"))
GCS_PROMPT_PREFIX = os.environ.get("TODAYPICK_PROMPT_GCS_PREFIX", "production/prompts/v3.2_single_first_48").strip("/")
PROMPT_PUBLIC_BASE = f"https://storage.googleapis.com/todaypick-daily-looks-363284724091/{GCS_PROMPT_PREFIX}"
PROMPT_BUCKET = os.environ.get("TODAYPICK_PROMPT_GCS_BUCKET", "todaypick-daily-looks-363284724091")
GCLOUD_PROJECT = os.environ.get("TODAYPICK_GCLOUD_PROJECT", "my-youtube-automation-497504")
GCLOUD_BIN = shutil.which("gcloud") or shutil.which("gcloud.cmd") or "gcloud"
KST = timezone(timedelta(hours=9), name="KST")

SEASONS_IN_ROTATION = ["autumn", "winter", "spring", "summer"]
SEASON_FOLDERS = {
    "spring": "01_SPRING",
    "summer": "02_SUMMER",
    "autumn": "03_AUTUMN",
    "winter": "04_WINTER",
}
SEGMENTS_IN_SEASON = [
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
ROTATION = [f"{season}_{segment}" for season in SEASONS_IN_ROTATION for segment in SEGMENTS_IN_SEASON]


@dataclass(frozen=True)
class RotationTarget:
    rotation_key: str
    rotation_index: int
    cycle_number: int
    season: str
    segment: str
    gender: str
    age: int


def now_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def split_rotation_key(rotation_key: str) -> tuple[str, str, str, int]:
    match = re.fullmatch(r"(spring|summer|autumn|winter)_(female|male)_(10|20|30|40|50|60)", rotation_key)
    if not match:
        raise ValueError(f"invalid rotation key: {rotation_key}")
    season, gender, age = match.groups()
    return season, f"{gender}_{age}", gender, int(age)


def target_for_index(rotation_index: int, cycle_number: int = 1) -> RotationTarget:
    idx = int(rotation_index) % len(ROTATION)
    season, segment, gender, age = split_rotation_key(ROTATION[idx])
    return RotationTarget(
        rotation_key=ROTATION[idx],
        rotation_index=idx,
        cycle_number=int(cycle_number),
        season=season,
        segment=segment,
        gender=gender,
        age=age,
    )


def initial_cursor() -> dict[str, Any]:
    current = target_for_index(0, 1)
    nxt = target_for_index(1, 1)
    return {
        "schema_version": 1,
        "rotation_index": current.rotation_index,
        "current_segment": current.rotation_key,
        "next_segment": nxt.rotation_key,
        "last_attempt_segment": None,
        "last_success_segment": None,
        "last_success_at": None,
        "last_run_id": None,
        "cycle_number": current.cycle_number,
        "updated_at": now_iso(),
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_cursor(path: Path = CURSOR_PATH) -> dict[str, Any]:
    if not path.exists():
        cursor = initial_cursor()
        write_json_atomic(path, cursor)
        return cursor
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    if data.get("schema_version") != 1 or int(data.get("rotation_index", -1)) not in range(len(ROTATION)):
        cursor = initial_cursor()
        write_json_atomic(path, cursor)
        return cursor
    idx = int(data["rotation_index"])
    cycle = int(data.get("cycle_number") or 1)
    current = target_for_index(idx, cycle)
    nxt_idx = (idx + 1) % len(ROTATION)
    nxt_cycle = cycle + 1 if nxt_idx == 0 else cycle
    data["current_segment"] = current.rotation_key
    data["next_segment"] = target_for_index(nxt_idx, nxt_cycle).rotation_key
    data["cycle_number"] = cycle
    return data


def save_attempt(cursor: dict[str, Any], run_id: str, path: Path = CURSOR_PATH) -> dict[str, Any]:
    target = target_for_index(int(cursor["rotation_index"]), int(cursor.get("cycle_number") or 1))
    updated = {
        **cursor,
        "last_attempt_segment": target.rotation_key,
        "last_run_id": run_id,
        "updated_at": now_iso(),
    }
    write_json_atomic(path, updated)
    return updated


def advance_after_success(cursor: dict[str, Any], run_id: str, path: Path = CURSOR_PATH) -> dict[str, Any]:
    current = target_for_index(int(cursor["rotation_index"]), int(cursor.get("cycle_number") or 1))
    next_index = (current.rotation_index + 1) % len(ROTATION)
    next_cycle = current.cycle_number + 1 if next_index == 0 else current.cycle_number
    nxt = target_for_index(next_index, next_cycle)
    after_next_index = (next_index + 1) % len(ROTATION)
    after_next_cycle = next_cycle + 1 if after_next_index == 0 else next_cycle
    updated = {
        **cursor,
        "rotation_index": next_index,
        "current_segment": nxt.rotation_key,
        "next_segment": target_for_index(after_next_index, after_next_cycle).rotation_key,
        "last_attempt_segment": current.rotation_key,
        "last_success_segment": current.rotation_key,
        "last_success_at": now_iso(),
        "last_run_id": run_id,
        "cycle_number": next_cycle,
        "updated_at": now_iso(),
    }
    write_json_atomic(path, updated)
    return updated


def prompt_path_for_target(target: RotationTarget, root: Path = LOCAL_PROMPT_ROOT) -> Path:
    return root / SEASON_FOLDERS[target.season] / f"TodayPick_v3.2_{target.season}_{target.gender}_{target.age}_10looks.md"


def prompt_gcs_object_for_target(target: RotationTarget) -> str:
    return f"{GCS_PROMPT_PREFIX}/{SEASON_FOLDERS[target.season]}/TodayPick_v3.2_{target.season}_{target.gender}_{target.age}_10looks.md"


def prompt_public_url_for_target(target: RotationTarget) -> str:
    return f"{PROMPT_PUBLIC_BASE}/{SEASON_FOLDERS[target.season]}/TodayPick_v3.2_{target.season}_{target.gender}_{target.age}_10looks.md"


def load_prompt_for_target(target: RotationTarget, root: Path = LOCAL_PROMPT_ROOT) -> dict[str, Any]:
    path = prompt_path_for_target(target, root)
    if path.exists():
        text = path.read_text(encoding="utf-8")
        source = "local_mirror"
    else:
        object_name = prompt_gcs_object_for_target(target)
        result = subprocess.run(
            [GCLOUD_BIN, "storage", "cat", f"gs://{PROMPT_BUCKET}/{object_name}", "--project", GCLOUD_PROJECT, "--quiet"],
            text=True,
            capture_output=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"failed to read prompt: {object_name}")
        text = result.stdout
        source = "gcs"
    return {
        "path": str(path),
        "source": source,
        "text": text,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "gcs_object": prompt_gcs_object_for_target(target),
        "public_url": prompt_public_url_for_target(target),
    }


def validate_gcs_prompt_library() -> dict[str, Any]:
    prefix_url = f"gs://{PROMPT_BUCKET}/{GCS_PROMPT_PREFIX}/**"
    result = subprocess.run(
        [GCLOUD_BIN, "storage", "ls", "--recursive", prefix_url, "--project", GCLOUD_PROJECT, "--quiet"],
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return {"root": prefix_url, "file_count": 0, "readback": "0/48", "failures": [{"reason": result.stderr.strip() or result.stdout.strip()}], "ok": False}
    md_files = [line.strip() for line in result.stdout.splitlines() if line.strip().endswith(".md")]
    other_files = [line.strip() for line in result.stdout.splitlines() if line.strip() and not line.strip().endswith(".md") and not line.strip().endswith(":")]
    return {
        "root": prefix_url,
        "file_count": len(md_files),
        "readback": f"{len(md_files)}/48",
        "failures": [{"reason": "non-md files present", "files": other_files}] if other_files else [],
        "ok": len(md_files) == 48 and not other_files,
    }


def validate_prompt_library(root: Path = LOCAL_PROMPT_ROOT) -> dict[str, Any]:
    if not root.exists():
        return validate_gcs_prompt_library()
    files = []
    failures = []
    for idx, key in enumerate(ROTATION):
        target = target_for_index(idx, 1)
        path = prompt_path_for_target(target, root)
        if not path.exists():
            failures.append({"target": key, "reason": "missing", "path": str(path)})
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            failures.append({"target": key, "reason": str(exc), "path": str(path)})
            continue
        ok = all(needle in text for needle in ("SINGLE_FIRST_ONLY", "NO_SHEET_FIRST", "TARGET_SIZE=648x1152"))
        looks = len(re.findall(r"^### LOOK \d{2}$", text, flags=re.M))
        if not ok or looks != 10:
            failures.append({"target": key, "reason": f"invalid prompt contract looks={looks}", "path": str(path)})
            continue
        files.append(path)
    return {
        "root": str(root),
        "file_count": len(files),
        "readback": f"{len(files)}/48",
        "failures": failures,
        "ok": len(files) == 48 and not failures,
    }


def is_single_first_look(look: dict[str, Any]) -> bool:
    generation_method = str(look.get("generation_method") or "").lower()
    pipeline_version = str(look.get("pipeline_version") or "").lower()
    return bool(
        look.get("single_first") is True
        or generation_method == "single_first"
        or pipeline_version in {"v3.2", "single_first_v3.2"}
    )


def is_legacy_sheet_first_look(look: dict[str, Any]) -> bool:
    if is_single_first_look(look):
        return False
    generation_method = str(look.get("generation_method") or "").lower()
    pipeline_version = str(look.get("pipeline_version") or "").lower()
    return generation_method in {"sheet_first_legacy", "sheet_first", "legacy_crop"} or pipeline_version.startswith("legacy") or not look.get("set_id")


def catalog_is_single_first(catalog: dict[str, Any] | None) -> bool:
    if not catalog:
        return False
    generation_method = str(catalog.get("generation_method") or "").lower()
    pipeline_version = str(catalog.get("pipeline_version") or "").lower()
    catalog_policy = str(catalog.get("catalog_policy") or "").lower()
    return bool(
        catalog.get("single_first") is True
        or generation_method == "single_first"
        or pipeline_version in {"v3.2", "single_first_v3.2"}
        or "single_first" in catalog_policy
    )


def accumulate_new_set_first(
    existing_looks: list[dict[str, Any]],
    new_looks: list[dict[str, Any]],
    existing_catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return new-set-first looks, preserving historical single-first and excluding legacy."""
    seen: set[tuple[str | None, str | None]] = set()
    merged: list[dict[str, Any]] = []
    legacy_removed = 0
    preserved_single_first = 0
    duplicate_skipped = 0
    preserve_catalog = catalog_is_single_first(existing_catalog)

    def add_look(look: dict[str, Any]) -> None:
        nonlocal duplicate_skipped
        key = (look.get("id"), look.get("sha256"))
        if key in seen:
            duplicate_skipped += 1
            return
        seen.add(key)
        merged.append(look)

    for look in new_looks:
        stamped = {
            **look,
            "generation_method": "single_first",
            "pipeline_version": "v3.2",
            "single_first": True,
        }
        add_look(stamped)

    for look in existing_looks:
        if preserve_catalog or is_single_first_look(look):
            preserved_single_first += 1
            add_look(look)
        elif is_legacy_sheet_first_look(look):
            legacy_removed += 1
        else:
            legacy_removed += 1

    return {
        "looks": merged,
        "legacy_removed": legacy_removed,
        "preserved_single_first": preserved_single_first,
        "duplicate_skipped": duplicate_skipped,
    }


def build_rotation_run_id(date_iso: str, scheduled_time: str | None, schedule_revision: int | None, trigger_source: str, target: RotationTarget) -> str:
    safe_time = (scheduled_time or "manual").replace(":", "-")
    return (
        f"{date_iso}__{safe_time}__rev{int(schedule_revision or 0)}__{trigger_source}"
        f"__rot{target.rotation_index:02d}__cycle{target.cycle_number}__{target.rotation_key}"
    )
