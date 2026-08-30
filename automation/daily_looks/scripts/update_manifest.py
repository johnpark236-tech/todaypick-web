import json
import shutil
from pathlib import Path

def get_manifest_paths():
    base_dir = Path(__file__).resolve().parent.parent
    reg_dir = base_dir / "registry"
    return {
        "latest": reg_dir / "manifest_latest.json",
        "staging": reg_dir / "manifest_staging.json",
        "archive": reg_dir / "manifest_archive.json"
    }

def update_staging_manifest(date_str, season_name, group_results):
    paths = get_manifest_paths()
    latest_manifest = {}
    if paths["latest"].exists():
        try:
            latest_manifest = json.loads(paths["latest"].read_text(encoding="utf-8"))
        except:
            pass

    staging = {
        "manifest_version": "1.0.0",
        "status": "STAGING",
        "generated_at": date_str,
        "season": season_name,
        "groups": {}
    }

    # Populate with previous active state as fallback baseline
    if "groups" in latest_manifest:
        staging["groups"] = dict(latest_manifest["groups"])

    # Update groups that passed QA
    for g_key, g_res in group_results.items():
        if g_res.get("status") == "PASS":
            staging["groups"][g_key] = {
                "status": "ACTIVE",
                "approved_date": date_str,
                "asset_dir": f"/assets/looks/{g_key}",
                "look_count": len(g_res.get("cropped_files", [])),
                "qa_status": "PASS"
            }
        else:
            # Retain previous active baseline on failure
            if g_key in staging["groups"]:
                staging["groups"][g_key]["fallback_retained"] = True
                staging["groups"][g_key]["qa_status"] = "FAIL_FALLBACK"

    paths["staging"].write_text(json.dumps(staging, ensure_ascii=False, indent=2), encoding="utf-8")
    return staging

def promote_staging_to_latest():
    paths = get_manifest_paths()
    if not paths["staging"].exists():
        return False, "No staging manifest found."

    staging_data = json.loads(paths["staging"].read_text(encoding="utf-8"))
    # Validate staging schema
    if not staging_data.get("groups") or len(staging_data["groups"]) != 12:
        return False, "Staging validation failed: 12 groups required."

    # Archive previous latest if exists
    if paths["latest"].exists():
        prev_data = json.loads(paths["latest"].read_text(encoding="utf-8"))
        # append to archive
        archive_history = []
        if paths["archive"].exists():
            try:
                archive_history = json.loads(paths["archive"].read_text(encoding="utf-8"))
            except:
                pass
        archive_history.append(prev_data)
        paths["archive"].write_text(json.dumps(archive_history, ensure_ascii=False, indent=2), encoding="utf-8")

    # Promote staging
    staging_data["status"] = "ACTIVE"
    paths["latest"].write_text(json.dumps(staging_data, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["staging"].unlink()
    return True, "Staging successfully promoted to manifest_latest.json"
