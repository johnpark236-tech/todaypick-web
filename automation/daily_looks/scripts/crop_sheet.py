import json
from pathlib import Path
from PIL import Image

TARGET_WIDTH = 442
TARGET_HEIGHT = 973

def crop_sheet_to_looks(sheet_image_path, output_dir, file_prefix):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(sheet_image_path).convert("RGB")
    W, H = img.size

    col_w = W / 5.0
    row_h = H / 2.0

    cropped_files = []

    for idx in range(10):
        row = idx // 5
        col = idx % 5

        left = int(col * col_w)
        right = int((col + 1) * col_w)
        top = int(row * row_h)
        bottom = int((row + 1) * row_h)

        cell = img.crop((left, top, right, bottom))
        cw, ch = cell.size

        bg_color = cell.getpixel((5, 5))
        canvas = Image.new("RGB", (TARGET_WIDTH, TARGET_HEIGHT), bg_color)

        scale = min(TARGET_WIDTH / float(cw), TARGET_HEIGHT / float(ch))
        new_w = int(cw * scale)
        new_h = int(ch * scale)
        resized_cell = cell.resize((new_w, new_h), Image.Resampling.LANCZOS)

        offset_x = (TARGET_WIDTH - new_w) // 2
        offset_y = (TARGET_HEIGHT - new_h) // 2
        canvas.paste(resized_cell, (offset_x, offset_y))

        out_name = f"{file_prefix}_{idx+1:02d}.webp"
        out_file = output_dir / out_name
        canvas.save(out_file, "WEBP", quality=90)
        cropped_files.append(str(out_file))

    # CROP QA: Verify 10 files, non-zero, decodable
    crop_qa_pass = True
    if len(cropped_files) != 10:
        crop_qa_pass = False
    for cf in cropped_files:
        cfp = Path(cf)
        if not cfp.exists() or cfp.stat().st_size == 0:
            crop_qa_pass = False
        try:
            im = Image.open(cfp)
            im.verify()
        except:
            crop_qa_pass = False

    return crop_qa_pass, cropped_files
