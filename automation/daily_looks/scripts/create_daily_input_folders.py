#!/usr/bin/env python3
"""
Daily Input Folder Creator — v1.0 (2026-09-22)

Creates today's date folder + 12 segment sub-folders under
G:\\내 드라이브\\TodayPick_user_config\\ every day at 00:01 KST.

Folder structure:
  TodayPick_user_config/
  └── YYMMDD/
      ├── f_10 / f_20 / f_30 / f_40 / f_50 / f_60
      └── m_10 / m_20 / m_30 / m_40 / m_50 / m_60

Rules:
  - Date calculated in KST (Asia/Seoul) regardless of server timezone
  - Existing folders never deleted or overwritten
  - Only missing sub-folders are created
  - Empty segment folders do NOT trigger the image ingest pipeline
  - Logs result to runtime/logs/daily_folder_creator.log
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # Python <3.9

# ── paths ──────────────────────────────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parents[2]   # todaypick-web/
_RUNTIME_ROOT = _PROJECT_ROOT / "automation" / "daily_looks" / "runtime"
_LOG_DIR = _RUNTIME_ROOT / "logs"
_LOG_FILE = _LOG_DIR / "daily_folder_creator.log"

USER_CONFIG_ROOT = Path(r"G:\내 드라이브\TodayPick_user_config")

SEGMENT_FOLDERS = [
    "f_10", "f_20", "f_30", "f_40", "f_50", "f_60",
    "m_10", "m_20", "m_30", "m_40", "m_50", "m_60",
]
KST = ZoneInfo("Asia/Seoul")


# ── logging ────────────────────────────────────────────────────────────────────

def _setup_logging() -> logging.Logger:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("daily_folder_creator")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                                datefmt="%Y-%m-%dT%H:%M:%S%z")
        fh = logging.FileHandler(str(_LOG_FILE), encoding="utf-8")
        fh.setFormatter(fmt)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(sh)
    return logger


# ═══════════════════════════════════════════════════════════════════════════════
# Core functions
# ═══════════════════════════════════════════════════════════════════════════════

def get_kst_date_folder(override_date: str | None = None) -> str:
    """
    Return today's date in YYMMDD format using KST (Asia/Seoul).

    override_date: 'YYYY-MM-DD' string for testing without changing system time.
    """
    if override_date:
        dt = datetime.strptime(override_date, "%Y-%m-%d")
    else:
        dt = datetime.now(KST)
    return dt.strftime("%y%m%d")


def create_date_folder(root: Path, date_folder: str) -> tuple[Path, bool]:
    """
    Create the YYMMDD date folder under root if it does not exist.
    Returns (path, was_created).
    """
    folder = root / date_folder
    if folder.exists():
        return folder, False
    folder.mkdir(parents=True, exist_ok=True)
    return folder, True


def create_segment_folders(date_folder_path: Path) -> dict[str, str]:
    """
    Create the 12 segment sub-folders inside date_folder_path.
    Returns {folder_name: "CREATED" | "EXISTS"} for each segment.
    """
    results: dict[str, str] = {}
    for name in SEGMENT_FOLDERS:
        seg = date_folder_path / name
        if seg.exists():
            results[name] = "EXISTS"
        else:
            seg.mkdir(parents=True, exist_ok=True)
            results[name] = "CREATED"
    return results


def verify_folder_structure(date_folder_path: Path) -> tuple[bool, list[str]]:
    """
    Return (all_ok, missing_list) where missing_list holds any absent segment folders.
    """
    missing = [n for n in SEGMENT_FOLDERS if not (date_folder_path / n).is_dir()]
    return len(missing) == 0, missing


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def run(
    root: Path | None = None,
    override_date: str | None = None,
) -> dict:
    """
    Full creation run. Returns a result dict for testing / reporting.
    """
    logger = _setup_logging()
    cfg_root = root or USER_CONFIG_ROOT

    date_str = get_kst_date_folder(override_date)
    logger.info(f"DATE={date_str}  ROOT={cfg_root}")

    date_path, date_created = create_date_folder(cfg_root, date_str)
    logger.info(f"DATE_FOLDER={'CREATED' if date_created else 'EXISTS'}  path={date_path}")

    seg_results = create_segment_folders(date_path)
    created = [k for k, v in seg_results.items() if v == "CREATED"]
    existed = [k for k, v in seg_results.items() if v == "EXISTS"]
    logger.info(f"SEGMENT_FOLDERS created={len(created)} existing={len(existed)}")
    for name, status in seg_results.items():
        logger.info(f"  {name}: {status}")

    ok, missing = verify_folder_structure(date_path)
    verdict = "PASS" if ok else f"FAIL missing={missing}"
    logger.info(f"VERIFY={verdict}")

    result = {
        "date": date_str,
        "root": str(cfg_root),
        "date_folder_path": str(date_path),
        "date_folder_created": date_created,
        "segment_results": seg_results,
        "created_count": len(created),
        "existing_count": len(existed),
        "all_present": ok,
        "missing": missing,
        "verdict": "PASS" if ok else "FAIL",
    }
    logger.info(
        f"DATE={date_str} DATE_FOLDER={'CREATED' if date_created else 'EXISTS'} "
        f"SEGMENT_FOLDERS={len(created)+len(existed)}/12 "
        f"MISSING_FOLDERS_CREATED={len(created)} "
        f"EXISTING_FOLDERS_PRESERVED=YES "
        f"FINAL_VERDICT={result['verdict']}"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create TodayPick daily input folders in KST"
    )
    parser.add_argument(
        "--date", metavar="YYYY-MM-DD",
        help="Override today's date for testing (e.g. 2026-09-22)"
    )
    parser.add_argument(
        "--root", metavar="PATH",
        help="Override user_config root path (for testing)"
    )
    args = parser.parse_args()

    root = Path(args.root) if args.root else None
    result = run(root=root, override_date=args.date)

    print(f"\nDATE={result['date']}")
    print(f"ROOT={result['root']}")
    print(f"DATE_FOLDER={'CREATED' if result['date_folder_created'] else 'EXISTS'}")
    print(f"SEGMENT_FOLDERS={result['created_count']+result['existing_count']}/12")
    print(f"MISSING_FOLDERS_CREATED={result['created_count']}")
    print(f"EXISTING_FOLDERS_PRESERVED=YES")
    print(f"FINAL_VERDICT={result['verdict']}")


if __name__ == "__main__":
    main()
