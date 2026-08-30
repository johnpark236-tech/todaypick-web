import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

def build_group_prompt(group_key, group_meta, group_plan, prompt_template, season_rules, date_str):
    season_name = group_plan["season"]
    season_rule = season_rules["rules"].get(season_name, {})
    anchor = group_meta["anchor"]

    # Assemble outfit plans text
    plans_lines = []
    for idx, look in enumerate(group_plan.get("looks", [])):
        look_num = idx + 1
        if look.get("type") == "onepiece":
            desc = f"Cell {look_num:02d}: wearing {look['onepiece']}, with {look['shoes']}"
        else:
            desc = f"Cell {look_num:02d}: wearing {look['top']} and {look['bottom']}, with {look['shoes']}"
        plans_lines.append(f"- {desc}")
    outfit_plans_text = "\n".join(plans_lines)

    forbidden_summary = ", ".join(season_rule.get("forbidden_clothing", [])[:10])

    prompt = prompt_template.format(
        group_label=group_meta["label"],
        character_identity=anchor["identity"],
        character_face=anchor["face"],
        character_hair=anchor["hair"],
        character_body=anchor["body"],
        character_aesthetic=anchor["aesthetic"],
        season_name=season_name.upper(),
        current_date_kst=date_str,
        season_directive=season_rule.get("prompt_directive", ""),
        forbidden_items_summary=forbidden_summary,
        outfit_plans_text=outfit_plans_text
    )
    return prompt

def build_and_save_all_prompts(daily_plan, output_base_dir=None):
    base_dir = Path(__file__).resolve().parent.parent
    if not output_base_dir:
        output_base_dir = base_dir / "output"

    groups_cfg = json.loads((base_dir / "config" / "groups.json").read_text(encoding="utf-8"))["groups"]
    seasons_cfg = json.loads((base_dir / "config" / "season_rules.json").read_text(encoding="utf-8"))
    prompt_template = (base_dir / "config" / "prompt_template.txt").read_text(encoding="utf-8")

    date_compact = daily_plan["date"].replace("-", "")
    prompts_dir = output_base_dir / date_compact / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    generated_prompts = {}

    for g_key, g_plan in daily_plan["groups"].items():
        if g_key in groups_cfg:
            p_text = build_group_prompt(
                g_key, groups_cfg[g_key], g_plan, prompt_template, seasons_cfg, daily_plan["date"]
            )
            p_file = prompts_dir / f"{g_key}.txt"
            p_file.write_text(p_text, encoding="utf-8")
            generated_prompts[g_key] = {
                "prompt_path": str(p_file),
                "prompt_text": p_text
            }

    return generated_prompts

if __name__ == "__main__":
    from generate_plan import generate_daily_plan
    plan = generate_daily_plan()
    prompts = build_and_save_all_prompts(plan)
    print(f"Generated and saved {len(prompts)} prompt files in output history.")
