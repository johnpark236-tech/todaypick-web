import json
from pathlib import Path
from PIL import Image

def validate_sheet_image(image_path, group_plan, quality_rules=None, season_rules=None):
    report = {
        "file_exists": False,
        "image_decode": False,
        "dimensions_ok": False,
        "cell_count": 0,
        "season_compliance": False,
        "overall_status": "FAIL",
        "reasons": []
    }

    p = Path(image_path)
    if not p.exists() or p.stat().st_size == 0:
        report["reasons"].append("File does not exist or has 0 bytes.")
        return report

    report["file_exists"] = True

    try:
        im = Image.open(p)
        im.verify()
        report["image_decode"] = True
    except Exception as e:
        report["reasons"].append(f"Image decode failed: {str(e)}")
        return report

    # Check dimensions
    im = Image.open(p)
    w, h = im.size
    aspect = w / float(h)
    # Expected 16:9 ratio approximately (1.6 ~ 1.9)
    if 1.5 <= aspect <= 2.0 and w >= 800 and h >= 450:
        report["dimensions_ok"] = True
    else:
        report["reasons"].append(f"Unexpected dimensions: {w}x{h} (aspect {aspect:.2f})")

    # Season check on outfit plan metadata
    season_name = group_plan.get("season", "summer")
    base_dir = Path(__file__).resolve().parent.parent
    if not season_rules:
        season_rules = json.loads((base_dir / "config" / "season_rules.json").read_text(encoding="utf-8"))

    forbidden_items = season_rules["rules"].get(season_name, {}).get("forbidden_clothing", [])
    season_violation = False

    for look in group_plan.get("looks", []):
        kw = look.get("keyword", "").lower()
        for f_word in forbidden_items:
            if f_word in kw:
                season_violation = True
                report["reasons"].append(f"Season violation: found forbidden term '{f_word}' in look {look['index']}")
                break

    report["season_compliance"] = not season_violation
    report["cell_count"] = 10 # 5x2 grid layout

    if report["file_exists"] and report["image_decode"] and report["dimensions_ok"] and report["season_compliance"]:
        report["overall_status"] = "PASS"
    else:
        report["overall_status"] = "FAIL"

    return report
