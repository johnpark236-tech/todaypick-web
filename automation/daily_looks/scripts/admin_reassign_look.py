"""
TodayPick Admin Look Reassigner
Moves looks between seasons in the GCS catalog (catalog-only, no image file moves).
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


def batch_reassign_looks_for_segment(
    source_season: str,
    target_season: str,
    segment: str,
    look_ids: list[str],
    dry_run: bool = False,
) -> list[dict]:
    """Move look_ids from source_season/segment → target_season/segment in GCS catalog."""
    if source_season not in VALID_SEASONS:
        raise ValueError(f"invalid source_season: {source_season}")
    if target_season not in VALID_SEASONS:
        raise ValueError(f"invalid target_season: {target_season}")
    if segment not in VALID_SEGMENTS:
        raise ValueError(f"invalid segment: {segment}")
    if source_season == target_season:
        raise ValueError("source and target season are the same")

    look_id_set = set(look_ids)
    src_obj = f"production/{source_season}/{segment}.json"
    tgt_obj = f"production/{target_season}/{segment}.json"

    print(f"Reading {src_obj} ...", flush=True)
    src_data = _read_gcs_json(src_obj)
    print(f"Reading {tgt_obj} ...", flush=True)
    tgt_data = _read_gcs_json(tgt_obj)

    src_looks: list[dict] = src_data.get("looks", [])
    tgt_looks: list[dict] = tgt_data.get("looks", [])

    moved, remaining = [], []
    for look in src_looks:
        (moved if look["id"] in look_id_set else remaining).append(look)

    moved_ids = {l["id"] for l in moved}
    not_found = [lid for lid in look_ids if lid not in moved_ids]

    if not dry_run:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        src_data["looks"] = remaining
        src_data["count"] = len(remaining)
        src_data["updated_at"] = now

        existing_tgt_ids = {l["id"] for l in tgt_looks}
        for look in moved:
            if look["id"] not in existing_tgt_ids:
                tgt_looks.append(look)
        tgt_data["looks"] = tgt_looks
        tgt_data["count"] = len(tgt_looks)
        tgt_data["updated_at"] = now

        print(f"Uploading {src_obj} ({len(remaining)} looks) ...", flush=True)
        _upload_gcs_json(src_data, src_obj)
        print(f"Uploading {tgt_obj} ({len(tgt_looks)} looks) ...", flush=True)
        _upload_gcs_json(tgt_data, tgt_obj)

    results = []
    for look in moved:
        results.append({
            "look_id": look["id"], "success": True, "action": "reassigned",
            "source": source_season, "target": target_season,
            "segment": segment, "dry_run": dry_run,
        })
    for lid in not_found:
        results.append({
            "look_id": lid, "success": False, "action": "not_found",
            "source": source_season, "target": target_season,
            "segment": segment, "dry_run": dry_run,
        })

    print(f"REASSIGN_SUMMARY: {len(moved)} moved, {len(not_found)} not_found", flush=True)
    return results
