import json
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))

def get_kst_now():
    return datetime.now(KST)

def get_current_season(kst_dt, season_rules):
    month_str = str(kst_dt.month)
    return season_rules["month_mapping"].get(month_str, "summer")

SUMMER_PALETTES = ["아이보리", "화이트", "스카이블루", "민트", "베이지", "연청", "네이비", "라벤더", "레몬", "올리브"]
SUMMER_TOPS = [
    "린넨 오픈카라 반팔 셔츠", "오버핏 코튼 그래픽 반팔티", "슬림 골지 하이넥 반팔 니트",
    "퍼프소매 린넨 스모크 블라우스", "시어서커 스트라이프 반팔 셔츠", "루즈핏 코튼 크루넥 반팔티",
    "보트넥 슬리브리스 탑", "카라형 반팔 피케 니트", "루즈핏 썸머 카디건", "린넨 스트라이프 셔츠"
]
SUMMER_BOTTOMS = [
    "린넨 와이드 이지 슬랙스", "라이트 데님 숏팬츠", "플리츠 A라인 미니스커트",
    "스트레이트 핏 코튼 치노", "하이웨스트 와이드 핀턱 팬츠", "린넨 랩 미디스커트",
    "크롭 일자 연청 데님", "버뮤다 핀턱 숏팬츠", "쿨링 밴딩 조거팬츠", "티어드 롱 플레어 스커트"
]
SUMMER_ONEPIECES = [
    "린넨 벨티드 셔츠 롱원피스", "스퀘어넥 플로럴 미니원피스", "슬리브리스 핀턱 플레어 원피스",
    "시어서커 스트라이프 랩 원피스", "티어드 코튼 롱 나시 원피스", "퍼프소매 카라 버튼 롱원피스"
]
SUMMER_SHOES = [
    "스트랩 가죽 플랫 샌들", "캔버스 클래식 로우탑 스니커즈", "소가죽 썸머 페니 로퍼",
    "스퀘어토 슬링백 샌들", "미니멀 화이트 코트화", "컴포트 에어 메쉬 샌들"
]

def generate_group_plan(group_key, group_meta, season_name, season_rule, date_str):
    looks = []
    gender = group_meta["gender"]
    label = group_meta["label"]

    for i in range(1, 11):
        is_onepiece = (gender == "female" and i in [3, 7])
        color = SUMMER_PALETTES[(i - 1) % len(SUMMER_PALETTES)]
        shoes = SUMMER_SHOES[(i - 1) % len(SUMMER_SHOES)]

        if is_onepiece:
            op_name = f"{color} {SUMMER_ONEPIECES[(i - 1) % len(SUMMER_ONEPIECES)]}"
            look_obj = {
                "index": i,
                "type": "onepiece",
                "onepiece": op_name,
                "shoes": shoes,
                "keyword": f"{label} 여름 {op_name}",
                "items": [
                    {"slot": "원피스", "name": op_name, "searchKeyword": f"{label} {op_name}"},
                    {"slot": "신발", "name": shoes, "searchKeyword": f"{label} {shoes}"}
                ]
            }
        else:
            top_name = f"{color} {SUMMER_TOPS[(i - 1) % len(SUMMER_TOPS)]}"
            btm_color = "아이보리" if color in ["네이비", "스카이블루", "올리브"] else "네이비"
            btm_name = f"{btm_color} {SUMMER_BOTTOMS[(i - 1) % len(SUMMER_BOTTOMS)]}"
            look_obj = {
                "index": i,
                "type": "top_bottom",
                "top": top_name,
                "bottom": btm_name,
                "shoes": shoes,
                "keyword": f"{label} 여름 {top_name} 및 {btm_name}",
                "items": [
                    {"slot": "상의", "name": top_name, "searchKeyword": f"{label} {top_name}"},
                    {"slot": "하의", "name": btm_name, "searchKeyword": f"{label} {btm_name}"},
                    {"slot": "신발", "name": shoes, "searchKeyword": f"{label} {shoes}"}
                ]
            }
        looks.append(look_obj)

    return {
        "group": group_key,
        "label": label,
        "date": date_str,
        "season": season_name,
        "looks": looks
    }

def generate_daily_plan(date_str=None, target_group=None):
    base_dir = Path(__file__).resolve().parent.parent
    groups_cfg = json.loads((base_dir / "config" / "groups.json").read_text(encoding="utf-8"))["groups"]
    seasons_cfg = json.loads((base_dir / "config" / "season_rules.json").read_text(encoding="utf-8"))

    kst_now = get_kst_now()
    if not date_str:
        date_str = kst_now.strftime("%Y-%m-%d")
    season_name = get_current_season(kst_now, seasons_cfg)
    season_rule = seasons_cfg["rules"][season_name]

    daily_plan = {
        "plan_version": "1.0.0",
        "generated_at_kst": kst_now.isoformat(),
        "date": date_str,
        "season": season_name,
        "groups": {}
    }

    groups_to_process = [target_group] if target_group and target_group != "all" else groups_cfg.keys()

    for g_key in groups_to_process:
        if g_key in groups_cfg:
            daily_plan["groups"][g_key] = generate_group_plan(
                g_key, groups_cfg[g_key], season_name, season_rule, date_str
            )

    return daily_plan

if __name__ == "__main__":
    p = generate_daily_plan()
    print(f"Generated plan for {len(p['groups'])} groups in season: {p['season']}")
