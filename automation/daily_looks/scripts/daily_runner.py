import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

from generate_plan import generate_daily_plan, get_kst_now
from duplicate_check import check_group_plan_duplicates
from build_prompts import build_and_save_all_prompts
from image_generator import get_image_generator
from validate_sheet import validate_sheet_image
from crop_sheet import crop_sheet_to_looks
from update_manifest import update_staging_manifest, promote_staging_to_latest

def run_daily_automation(dry_run=True, target_group=None, auto_publish=False):
    base_dir = Path(__file__).resolve().parent.parent
    kst_now = get_kst_now()
    date_str = kst_now.strftime("%Y-%m-%d")
    date_compact = date_str.replace("-", "")

    print(f"==================================================")
    print(f"TodayPick Daily Look Automation Run")
    print(f"Date (KST): {date_str} {kst_now.strftime('%H:%M:%S')}")
    print(f"Mode: {'DRY_RUN' if dry_run else 'LIVE_GENERATION'}")
    print(f"Target: {target_group or 'ALL (12 Groups)'}")
    print(f"Auto Publish: {auto_publish}")
    print(f"==================================================")

    # Step 1: Generate Daily Look Plans
    daily_plan = generate_daily_plan(date_str=date_str, target_group=target_group)
    season = daily_plan["season"]
    print(f"[Step 1] Season: {season.upper()} | Groups planned: {len(daily_plan['groups'])}")

    # Step 2: Duplicate Check
    print(f"[Step 2] Running Duplicate Check against registry...")
    clean_plans = {}
    dup_failures = 0
    for g_key, g_plan in daily_plan["groups"].items():
        is_dup_ok, dup_details = check_group_plan_duplicates(g_plan)
        if is_dup_ok:
            clean_plans[g_key] = g_plan
        else:
            dup_failures += 1
            print(f"  [DUP_FAIL] {g_key}: Duplicate detected in plan!")
    print(f"  Passed duplicate check: {len(clean_plans)} / {len(daily_plan['groups'])}")

    # Step 3: Build Prompts & Save History
    print(f"[Step 3] Building 4-tier Prompts and saving to history...")
    built_prompts = build_and_save_all_prompts(daily_plan)
    print(f"  Prompt files saved: {len(built_prompts)} in output/{date_compact}/prompts/")

    # Step 4: Image Generation Adapter
    generator = get_image_generator(dry_run=dry_run)
    print(f"[Step 4] Generator Backend: {generator.backend_name}")

    raw_dir = base_dir / "output" / date_compact / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    cropped_dir = base_dir / "output" / date_compact / "cropped"

    group_results = {}
    total_retries = 0

    negative_prompt = (base_dir / "config" / "negative_prompt.txt").read_text(encoding="utf-8")

    # Step 5: Generate, QA & Crop per group with Retry loop (max 3)
    print(f"[Step 5] Processing groups with QA & Crop pipeline...")
    for g_key, g_plan in clean_plans.items():
        prompt_info = built_prompts.get(g_key, {})
        prompt_text = prompt_info.get("prompt_text", "")
        sheet_path = raw_dir / f"{g_key}_sheet.jpg"

        group_pass = False
        attempts = 0
        crop_files = []

        while attempts < 3 and not group_pass:
            attempts += 1
            if attempts > 1:
                total_retries += 1
                prompt_text += "\n[RETRY AUGMENTATION] Ensure strict 5x2 grid, exactly 10 full body cells, feet visible, pure summer wear."

            # Generate Sheet
            gen_ok, gen_msg = generator.generate(prompt_text, negative_prompt, sheet_path)
            if not gen_ok:
                print(f"  [{g_key}] Attempt {attempts} Gen Failed: {gen_msg}")
                continue

            # Validate QA
            qa_rep = validate_sheet_image(sheet_path, g_plan)
            if qa_rep["overall_status"] == "PASS":
                # Crop Sheet
                crop_ok, crop_files = crop_sheet_to_looks(sheet_path, cropped_dir / g_key, f"{g_key}_{date_compact}")
                if crop_ok:
                    group_pass = True
                    print(f"  [{g_key}] PASS on Attempt {attempts} (10 looks cropped)")
                else:
                    print(f"  [{g_key}] Crop QA failed on Attempt {attempts}")
            else:
                print(f"  [{g_key}] QA failed on Attempt {attempts}: {qa_rep['reasons']}")

        group_results[g_key] = {
            "status": "PASS" if group_pass else "FAIL",
            "attempts": attempts,
            "cropped_files": crop_files if group_pass else []
        }

    # Step 6: Manifest Management
    print(f"[Step 6] Updating Manifest Staging...")
    staging = update_staging_manifest(date_str, season, group_results)

    if auto_publish:
        ok, msg = promote_staging_to_latest()
        print(f"  [AUTO_PUBLISH=TRUE] {msg}")
    else:
        print(f"  [AUTO_PUBLISH=FALSE] Staging prepared. Retaining current active manifest pending human approval.")

    # Step 7: Summary Report
    pass_cnt = sum(1 for r in group_results.values() if r["status"] == "PASS")
    fail_cnt = len(group_results) - pass_cnt

    report_lines = [
        f"# TodayPick Daily Look Generation Report — {date_str}",
        f"",
        f"- **Date (KST)**: {date_str} {kst_now.strftime('%H:%M:%S')}",
        f"- **Season**: {season.upper()}",
        f"- **Mode**: {'DRY_RUN' if dry_run else 'LIVE_GENERATION'}",
        f"- **Backend**: {generator.backend_name}",
        f"- **Total Groups**: {len(daily_plan['groups'])}",
        f"- **PASS**: {pass_cnt}",
        f"- **FAIL / Fallback Retained**: {fail_cnt}",
        f"- **Retry Count**: {total_retries}",
        f"- **Auto Publish**: {'ENABLED' if auto_publish else 'DISABLED (Default Safe)'}",
        f"",
        f"## Group Results Matrix",
        f"| Group | Label | Status | Attempts | Cropped Looks | Final Action |",
        f"| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    groups_cfg = json.loads((base_dir / "config" / "groups.json").read_text(encoding="utf-8"))["groups"]
    for g_key in daily_plan["groups"].keys():
        res = group_results.get(g_key, {"status": "FAIL", "attempts": 0, "cropped_files": []})
        lbl = groups_cfg.get(g_key, {}).get("label", g_key)
        action = "Active Updated" if res["status"] == "PASS" else "Previous Active Retained"
        report_lines.append(
            f"| {g_key} | {lbl} | {'✅ PASS' if res['status'] == 'PASS' else '❌ FAIL'} | {res['attempts']} | {len(res['cropped_files'])} | {action} |"
        )

    report_content = "\n".join(report_lines)
    rep_file = base_dir / "reports" / f"{date_compact}_daily_look_report.md"
    rep_file.write_text(report_content, encoding="utf-8")
    print(f"[Step 7] Report written to {rep_file}")

    print(f"==================================================")
    print(f"Telegram Summary Preview:")
    print(f"TodayPick Daily Look Generation\nDate: {date_str}\nSeason: {season.capitalize()}\nGroups: {len(daily_plan['groups'])}\nPASS: {pass_cnt}\nFAIL/Fallback: {fail_cnt}\nSheets: {len(group_results)}\nRetry Count: {total_retries}\nActive Updated: {pass_cnt if auto_publish else 0}\nPrevious Retained: {fail_cnt if auto_publish else len(daily_plan['groups'])}")
    print(f"==================================================")

    return {
        "status": "PASS",
        "date": date_str,
        "season": season,
        "pass_count": pass_cnt,
        "fail_count": fail_cnt,
        "retries": total_retries
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True, help="Dry-run simulation mode")
    parser.add_argument("--live", action="store_true", help="Live generation mode")
    parser.add_argument("--group", type=str, default="all", help="Target group (all or group_key)")
    parser.add_argument("--auto-publish", action="store_true", default=False, help="Auto publish pass groups to latest")
    args = parser.parse_args()

    is_dry_run = not args.live
    run_daily_automation(dry_run=is_dry_run, target_group=args.group, auto_publish=args.auto_publish)
