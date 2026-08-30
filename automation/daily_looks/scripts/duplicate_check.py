import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

def normalize_text(text):
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r"[^a-zA-Z0-9가-힣\s]", "", t)
    return " ".join(t.split())

def tokenize(text):
    return set(normalize_text(text).split())

def check_look_duplicate(candidate_look, registry_records, window_days=30):
    norm_kw = normalize_text(candidate_look.get("keyword", ""))
    cand_tokens = tokenize(candidate_look.get("keyword", ""))

    for rec in registry_records:
        rec_norm = normalize_text(rec.get("keyword", ""))
        # Level 1: Exact match
        if norm_kw and norm_kw == rec_norm:
            return False, f"LEVEL 1 Duplicate: exact keyword match with {rec.get('id', 'existing')}"

        # Level 2: Token similarity > 0.75
        rec_tokens = tokenize(rec.get("keyword", ""))
        if cand_tokens and rec_tokens:
            intersection = cand_tokens.intersection(rec_tokens)
            union = cand_tokens.union(rec_tokens)
            jaccard = len(intersection) / float(len(union))
            if jaccard >= 0.75:
                return False, f"LEVEL 2 Duplicate: high token similarity ({jaccard:.2f}) with {rec.get('id', 'existing')}"

    return True, "OK"

def check_group_plan_duplicates(group_plan, registry_path=None):
    if not registry_path:
        base_dir = Path(__file__).resolve().parent.parent
        registry_path = base_dir / "registry" / "look_registry.json"

    registry_records = []
    if registry_path.exists():
        try:
            reg_data = json.loads(registry_path.read_text(encoding="utf-8"))
            registry_records = reg_data.get("records", [])
        except:
            pass

    results = []
    all_pass = True

    seen_in_plan = []
    for look in group_plan.get("looks", []):
        # 1. Intra-plan diversity check
        intra_pass, intra_msg = check_look_duplicate(look, seen_in_plan)
        if not intra_pass:
            all_pass = False
            results.append({"look_index": look["index"], "status": "FAIL", "reason": f"Intra-batch: {intra_msg}"})
            continue

        # 2. Historical registry check
        hist_pass, hist_msg = check_look_duplicate(look, registry_records)
        if not hist_pass:
            all_pass = False
            results.append({"look_index": look["index"], "status": "FAIL", "reason": f"History: {hist_msg}"})
            continue

        seen_in_plan.append(look)
        results.append({"look_index": look["index"], "status": "PASS", "reason": "Unique"})

    return all_pass, results

if __name__ == "__main__":
    from generate_plan import generate_daily_plan
    plan = generate_daily_plan()
    g1 = list(plan["groups"].keys())[0]
    ok, res = check_group_plan_duplicates(plan["groups"][g1])
    print(f"Group {g1} duplicate check: {ok} ({len(res)} items)")
