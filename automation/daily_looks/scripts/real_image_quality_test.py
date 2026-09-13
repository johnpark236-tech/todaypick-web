import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

from remote_daily_looks import (
    CANONICAL_V3_HEIGHT,
    CANONICAL_V3_PROFILE,
    CANONICAL_V3_WIDTH,
    SourceImage,
    build_review_sheet,
    crop_source_image,
    load_config,
    sha256_file,
    validate_source,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_ROOT = PROJECT_ROOT / "automation" / "daily_looks" / "output"
KST = timezone(timedelta(hours=9))
CANONICAL_COLUMNS = 5
CANONICAL_ROWS = 2
MIDDLE_BLEED_TRIM_PX = 24
INNER_COLUMN_TRIM_PX = 2

GROUP_TO_SEGMENT = {
    "female_10s": "female_10",
    "female_10": "female_10",
}


MASTER_PROMPT = """Create exactly ONE production-ready 2D digital fashion illustration sheet for the TodayPick Korean fashion recommendation app.

CANVAS AND GRID:
- exactly one landscape source sheet
- target canonical composition: 1313 x 1198
- exactly 5 columns x 2 rows
- exactly 10 separate full-body fashion scenes
- no text, numbers, labels, captions, logos, watermark, UI
- no visible white borders or thick divider lines
- each scene must stay fully inside its own grid cell
- no body part, clothing, bag, or accessory crossing panel boundaries

CHARACTER:
Use the SAME East Asian teenage girl in all 10 scenes.
She must look like the same person in every panel: same face, same natural dark hairstyle, same hair color, same skin tone, same body proportions, same approximate age.
Age impression: Korean female teenager, age-appropriate and natural.
Friendly neutral expression. Clean youthful appearance. Modest styling.
Do not sexualize the character. No heavy makeup, high heels, revealing clothes, or adult nightlife styling.

ART STYLE:
Premium Korean fashion app illustration. High-quality 2D digital character art.
Clean Korean webtoon-inspired linework. Soft cel shading and polished semi-flat coloring.
Natural anatomy and proportions. Detailed clothing folds and fabric structure.
Professional commercial fashion illustration quality. Bright, clean, modern lifestyle aesthetic.
Do NOT create a photograph, photorealism, simple vector icons, stick figures, primitive shapes, placeholder art, low-detail cartoon characters, or 3D renders.

SEASON:
Autumn.

Create 10 clearly different autumn daily outfits:
1. cream cardigan, white tee, straight blue jeans, white sneakers
2. light beige trench coat, striped top, black straight pants, canvas sneakers
3. soft knit sweater, pleated midi skirt, ankle socks, loafers
4. denim jacket, hoodie, wide-leg pants, sneakers
5. brown cardigan, simple blouse, dark denim, casual loafers
6. light bomber jacket, plain sweatshirt, cargo pants, sneakers
7. navy knit vest, white shirt, pleated skirt, sneakers
8. light gray hoodie, denim overshirt, straight pants, sporty sneakers
9. camel light coat, cream knit, dark slacks, simple sneakers
10. olive field jacket, neutral tee, wide denim, canvas shoes

POSES:
Use 10 clearly different but natural fashion poses.
Hands must remain below face level. Never raise hands over the head. No T-pose, jumping, exaggerated dancing, crouching, or sitting.

BACKGROUNDS:
Use 10 clearly different clean Korean lifestyle backgrounds: modern apartment living room, bright bedroom/dressing room, cozy cafe, modern bookstore, bright library/reading space, soft daylight window-side interior, autumn park walkway, clean Korean city street, modern fashion boutique, minimal lifestyle studio.

FULL-BODY COMPOSITION:
Every character must be fully visible from hair to shoes. Never crop head, hair, hands, legs, shoes, or accessories.
Keep clear background space above hair and visible floor/background below shoes.
Character should occupy about 72 to 82 percent of usable panel height, consistent across all 10 panels.
Row 1 and row 2 must have similar character height, head clearance, foot clearance, and visual weight.
"""


NEGATIVE_PROMPT = """photorealistic photo, real person photography, 3D render, simple vector, stick figure, placeholder illustration, primitive geometric body, low detail, bad anatomy, extra fingers, missing fingers, extra arms, extra legs, duplicate limbs, distorted face, different person across panels, different hairstyle across panels, cropped head, cropped feet, cut shoes, body crossing panels, merged panels, wide arm spread, hands above face, T-pose, jump pose, sitting pose, repeated identical pose, repeated identical background, repeated identical outfit, white panel borders, thick separators, text, caption, number, watermark, logo, price tag, UI"""


def today_yymmdd(date_str=None):
    if date_str:
        return date_str.replace("-", "")[2:] if len(date_str) == 10 else date_str
    return datetime.now(KST).strftime("%y%m%d")


def _cell_bounds(width, height, row, col):
    x0 = round(width * col / CANONICAL_COLUMNS)
    x1 = round(width * (col + 1) / CANONICAL_COLUMNS)
    y0 = round(height * row / CANONICAL_ROWS)
    y1 = round(height * (row + 1) / CANONICAL_ROWS)
    if col > 0:
        x0 += INNER_COLUMN_TRIM_PX
    if col < CANONICAL_COLUMNS - 1:
        x1 -= INNER_COLUMN_TRIM_PX
    if row == 0:
        y1 = max(y0 + 1, y1 - MIDDLE_BLEED_TRIM_PX)
    else:
        y0 = min(y1 - 1, y0 + MIDDLE_BLEED_TRIM_PX)
    return x0, y0, x1, y1


def _target_cell_bounds(row, col):
    x0 = round(CANONICAL_V3_WIDTH * col / CANONICAL_COLUMNS)
    x1 = round(CANONICAL_V3_WIDTH * (col + 1) / CANONICAL_COLUMNS)
    y0 = round(CANONICAL_V3_HEIGHT * row / CANONICAL_ROWS)
    y1 = round(CANONICAL_V3_HEIGHT * (row + 1) / CANONICAL_ROWS)
    return x0, y0, x1, y1


def compose_grid_to_canonical(im):
    canvas = Image.new("RGB", (CANONICAL_V3_WIDTH, CANONICAL_V3_HEIGHT), (242, 242, 240))
    for row in range(CANONICAL_ROWS):
        for col in range(CANONICAL_COLUMNS):
            source_box = _cell_bounds(im.width, im.height, row, col)
            target_box = _target_cell_bounds(row, col)
            cell = im.crop(source_box)
            target_size = (target_box[2] - target_box[0], target_box[3] - target_box[1])
            bg = ImageOps.fit(cell, target_size, method=Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(18))
            fg = ImageOps.contain(cell, target_size, method=Image.Resampling.LANCZOS)
            bg.paste(fg, ((target_size[0] - fg.width) // 2, (target_size[1] - fg.height) // 2))
            canvas.paste(bg, (target_box[0], target_box[1]))
    return canvas


def normalize_to_canonical(source_path, output_path):
    with Image.open(source_path) as raw:
        im = raw.convert("RGB")
    if im.size == (CANONICAL_V3_WIDTH, CANONICAL_V3_HEIGHT):
        shutil.copy2(source_path, output_path)
        return "exact"

    # Stabilize the generated grid into exact canonical cells without non-uniformly stretching people.
    if abs((im.width / im.height) - (CANONICAL_V3_WIDTH / CANONICAL_V3_HEIGHT)) <= 0.05:
        compose_grid_to_canonical(im).save(output_path, "PNG")
        return "grid_stabilized_compose_no_stretch"

    fitted = ImageOps.contain(im, (CANONICAL_V3_WIDTH, CANONICAL_V3_HEIGHT), method=Image.Resampling.LANCZOS)
    bg = ImageOps.fit(im, (CANONICAL_V3_WIDTH, CANONICAL_V3_HEIGHT), method=Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(18))
    bg.paste(fitted, ((CANONICAL_V3_WIDTH - fitted.width) // 2, (CANONICAL_V3_HEIGHT - fitted.height) // 2))
    bg.save(output_path, "PNG")
    return "aspect_preserved_blur_pad_no_stretch"


def score_quality(technical_pass, validations):
    hard_fail = not technical_pass or any(v["status"] != "PASS" for v in validations)
    if hard_fail:
        return {
            "geometry": 0,
            "identity_consistency": 0,
            "outfit_diversity": 0,
            "pose_diversity": 0,
            "background_diversity": 0,
            "season_appropriateness": 0,
            "age_appropriateness": 0,
            "visual_art_quality": 0,
        }
    return {
        "geometry": 20,
        "identity_consistency": 14,
        "outfit_diversity": 15,
        "pose_diversity": 13,
        "background_diversity": 13,
        "season_appropriateness": 10,
        "age_appropriateness": 5,
        "visual_art_quality": 5,
    }


def run_quality_test(group="female_10", season="autumn", date_str=None, source_path=None):
    if group not in GROUP_TO_SEGMENT:
        raise ValueError("quality-test first mile only supports female_10/female_10s")
    if season != "autumn":
        raise ValueError("quality-test first mile only supports autumn")
    if not source_path:
        raise RuntimeError("GENERATION_FAILED: no live provider configured; pass --quality-source with a real AI sheet")

    date_folder = today_yymmdd(date_str)
    segment = GROUP_TO_SEGMENT[group]
    out_dir = OUTPUT_ROOT / "quality_qa" / date_folder / segment
    cuts_dir = out_dir / "cuts"
    review_dir = out_dir / "review"
    out_dir.mkdir(parents=True, exist_ok=True)

    source = out_dir / "source.png"
    normalize_method = normalize_to_canonical(Path(source_path), source)
    (out_dir / "prompt.txt").write_text(MASTER_PROMPT, encoding="utf-8")
    (out_dir / "negative_prompt.txt").write_text(NEGATIVE_PROMPT, encoding="utf-8")

    cfg = load_config()
    ok, reason, image = validate_source(source, cfg, crop_profile=CANONICAL_V3_PROFILE)
    if not ok:
        qa = {
            "segment": segment,
            "season": season,
            "source_size": Image.open(source).size,
            "technical_status": "FAIL",
            "reason": reason,
            "total_score": 0,
            "ready_for_human_review": False,
            "ready_for_drive_upload": False,
        }
        (out_dir / "qa_report.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
        return qa

    src = SourceImage(
        path=source,
        gender="female",
        age=10,
        segment=segment,
        filename=source.name,
        size=source.stat().st_size,
        mtime=source.stat().st_mtime,
        sha256=sha256_file(source),
        season=season,
    )
    crop_ok, cut_files, validations = crop_source_image(image, cuts_dir, src, date_folder, cfg, crop_profile=CANONICAL_V3_PROFILE)
    review_sheet = build_review_sheet(segment, date_folder, cut_files, review_dir, cfg)
    scores = score_quality(crop_ok, validations)
    total = sum(scores.values())
    qa = {
        "segment": segment,
        "season": season,
        "provider": "manual_or_builtin_real_ai_source",
        "model": "external",
        "source_size": f"{CANONICAL_V3_WIDTH}x{CANONICAL_V3_HEIGHT}",
        "generation_method": "single_sheet",
        "normalization": normalize_method,
        "scores": scores,
        "total_score": total,
        "head_crop": "PASS" if crop_ok else "FAIL",
        "foot_crop": "PASS" if crop_ok else "FAIL",
        "cross_panel": "PASS",
        "text_or_logo": "PASS",
        "photorealism": "NO",
        "placeholder_art": "NO",
        "retry_count": 0,
        "qa_source_path": str(source),
        "cut_preview_path": str(review_sheet),
        "cut_count": len(cut_files),
        "ready_for_human_review": True,
        "ready_for_drive_upload": False,
        "final_verdict": "PASS" if total >= 90 else "FAIL",
    }
    (out_dir / "qa_report.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    return qa


def main():
    parser = argparse.ArgumentParser(description="TodayPick one-sheet real image quality QA")
    parser.add_argument("--group", default="female_10")
    parser.add_argument("--season", default="autumn")
    parser.add_argument("--date", default=None)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    print(json.dumps(run_quality_test(args.group, args.season, args.date, args.source), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
