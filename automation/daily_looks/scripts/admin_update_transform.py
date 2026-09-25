"""
TodayPick Admin Display Transform Updater
Updates display_transform field on individual looks in GCS segment JSON files.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import shutil

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

BUCKET = "todaypick-daily-looks-363284724091"
GCS_PROJECT = "my-youtube-automation-497504"
GCLOUD_BIN = shutil.which("gcloud") or shutil.which("gcloud.cmd") or "gcloud"
CACHE_NO_CACHE = "no-cache"

VALID_SEASONS = frozenset({"spring", "summer", "autumn", "winter"})
VALID_SEGMENTS = frozenset({
    "female_10", "female_20", "female_30", "female_40", "female_50", "female_60",
    "male_10", "male_20", "male_30", "male_40", "male_50", "male_60",
})


def _gs(obj: str) -> str:
    return f"gs://{BUCKET}/{obj}"


def _run(args: list[str]) -> str:
    r = subprocess.run(
        [GCLOUD_BIN, *args, "--project", GCS_PROJECT, "--quiet"],
        text=True, capture_output=True,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip() or "gcloud error")
    return r.stdout


def _read_gcs_json(obj: str) -> dict:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "f.json"
        _run(["storage", "cp", _gs(obj), str(out)])
        return json.loads(out.read_text(encoding="utf-8"))


def _upload_gcs_json(data: dict, obj: str) -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "f.json"
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        _run([
            "storage", "cp",
            "--content-type=application/json",
            f"--cache-control={CACHE_NO_CACHE}",
            str(p), _gs(obj),
        ])


def _validate_transform(t: dict) -> dict:
    """Clamp and validate display_transform values."""
    return {
        "x": max(-200.0, min(200.0, float(t.get("x", 0)))),
        "y": max(-200.0, min(200.0, float(t.get("y", 0)))),
        "scale": max(0.3, min(3.0, float(t.get("scale", 1.0)))),
    }


def batch_update_transforms_for_segment(
    season: str,
    segment: str,
    updates: list[dict],  # [{look_id, display_transform}]
    dry_run: bool = False,
) -> list[dict]:
    """
    Apply display_transform overrides to looks in a segment JSON.
    updates: list of {look_id: str, display_transform: {x, y, scale} | null}
    Passing display_transform=null removes the transform.
    """
    if season not in VALID_SEASONS:
        raise ValueError(f"invalid season: {season}")
    if segment not in VALID_SEGMENTS:
        raise ValueError(f"invalid segment: {segment}")
    if not updates:
        return []

    obj = f"production/{season}/{segment}.json"
    print(f"Reading {obj} ...", flush=True)
    data = _read_gcs_json(obj)
    looks: list[dict] = data.get("looks", [])

    update_map = {u["look_id"]: u.get("display_transform") for u in updates}
    results = []
    changed = 0

    for look in looks:
        lid = look["id"]
        if lid not in update_map:
            continue
        transform = update_map[lid]
        if transform is None:
            look.pop("display_transform", None)
            action = "removed"
        else:
            look["display_transform"] = _validate_transform(transform)
            action = "updated"
        changed += 1
        results.append({"look_id": lid, "success": True, "action": action,
                        "transform": look.get("display_transform"), "dry_run": dry_run})

    not_found = [uid for uid in update_map if uid not in {l["id"] for l in looks}]
    for lid in not_found:
        results.append({"look_id": lid, "success": False, "action": "not_found", "dry_run": dry_run})

    if not dry_run and changed:
        data["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"Uploading {obj} ({changed} transforms updated) ...", flush=True)
        _upload_gcs_json(data, obj)
    else:
        print(f"DRY_RUN or no changes — skipping upload (changed={changed})", flush=True)

    print(f"TRANSFORM_SUMMARY: {changed} updated, {len(not_found)} not_found", flush=True)
    return results
