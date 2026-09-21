#!/usr/bin/env python3
"""
Tests for create_daily_input_folders.py  — T01-T10
Run: pytest automation/daily_looks/scripts/test_create_daily_input_folders.py -v
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from create_daily_input_folders import (
    SEGMENT_FOLDERS,
    create_date_folder,
    create_segment_folders,
    get_kst_date_folder,
    run,
    verify_folder_structure,
)


# ─── T01 ──────────────────────────────────────────────────────────────────────
def test_T01_kst_date_format():
    """get_kst_date_folder() returns a 6-char YYMMDD string."""
    date_str = get_kst_date_folder("2026-09-22")
    assert date_str == "260922", f"expected '260922', got '{date_str}'"
    assert len(date_str) == 6


# ─── T02 ──────────────────────────────────────────────────────────────────────
def test_T02_kst_timezone_not_utc():
    """KST date is +9h from UTC; at UTC 15:02 the KST date is already the NEXT day."""
    from zoneinfo import ZoneInfo
    from unittest.mock import patch as _patch
    # UTC 2026-09-21 15:02 = KST 2026-09-22 00:02
    utc_dt = datetime(2026, 9, 21, 15, 2, 0, tzinfo=ZoneInfo("UTC"))
    kst = ZoneInfo("Asia/Seoul")
    kst_dt = utc_dt.astimezone(kst)
    assert kst_dt.strftime("%y%m%d") == "260922"


# ─── T03 ──────────────────────────────────────────────────────────────────────
def test_T03_segment_folder_count():
    """Exactly 12 segment folders are defined."""
    assert len(SEGMENT_FOLDERS) == 12


# ─── T04 ──────────────────────────────────────────────────────────────────────
def test_T04_segment_folder_names():
    """Segment folders follow the pattern g_NN with correct genders and ages."""
    expected = {
        "f_10", "f_20", "f_30", "f_40", "f_50", "f_60",
        "m_10", "m_20", "m_30", "m_40", "m_50", "m_60",
    }
    assert set(SEGMENT_FOLDERS) == expected


# ─── T05 ──────────────────────────────────────────────────────────────────────
def test_T05_create_date_folder_creates_new(tmp_path):
    """create_date_folder() creates the folder and returns was_created=True."""
    path, created = create_date_folder(tmp_path, "260922")
    assert path == tmp_path / "260922"
    assert path.is_dir()
    assert created is True


# ─── T06 ──────────────────────────────────────────────────────────────────────
def test_T06_create_date_folder_idempotent(tmp_path):
    """create_date_folder() returns was_created=False when folder already exists."""
    (tmp_path / "260922").mkdir()
    path, created = create_date_folder(tmp_path, "260922")
    assert path.is_dir()
    assert created is False


# ─── T07 ──────────────────────────────────────────────────────────────────────
def test_T07_create_segment_folders_all_created(tmp_path):
    """create_segment_folders() creates all 12 subfolders and reports CREATED."""
    date_path = tmp_path / "260922"
    date_path.mkdir()
    results = create_segment_folders(date_path)
    assert len(results) == 12
    for name, status in results.items():
        assert (date_path / name).is_dir(), f"{name} not created"
        assert status == "CREATED", f"{name} expected CREATED, got {status}"


# ─── T08 ──────────────────────────────────────────────────────────────────────
def test_T08_create_segment_folders_idempotent(tmp_path):
    """create_segment_folders() reports EXISTS for pre-existing folders, does not delete."""
    date_path = tmp_path / "260922"
    date_path.mkdir()
    # pre-create some
    (date_path / "f_10").mkdir()
    (date_path / "m_60").mkdir()
    results = create_segment_folders(date_path)
    assert results["f_10"] == "EXISTS"
    assert results["m_60"] == "EXISTS"
    # others were created
    assert results["f_20"] == "CREATED"
    assert results["m_10"] == "CREATED"
    # all 12 exist after the call
    ok, missing = verify_folder_structure(date_path)
    assert ok, f"missing: {missing}"


# ─── T09 ──────────────────────────────────────────────────────────────────────
def test_T09_verify_all_present(tmp_path):
    """verify_folder_structure() returns (True, []) when all 12 are present."""
    date_path = tmp_path / "260922"
    date_path.mkdir()
    for name in SEGMENT_FOLDERS:
        (date_path / name).mkdir()
    ok, missing = verify_folder_structure(date_path)
    assert ok is True
    assert missing == []


# ─── T10 ──────────────────────────────────────────────────────────────────────
def test_T10_run_full_pipeline(tmp_path):
    """run() end-to-end: creates date folder + 12 segments, verdict=PASS."""
    result = run(root=tmp_path, override_date="2026-09-22")
    assert result["date"] == "260922"
    assert result["verdict"] == "PASS"
    assert result["all_present"] is True
    assert result["missing"] == []
    assert result["created_count"] == 12
    assert result["existing_count"] == 0
    # second run is idempotent
    result2 = run(root=tmp_path, override_date="2026-09-22")
    assert result2["verdict"] == "PASS"
    assert result2["created_count"] == 0
    assert result2["existing_count"] == 12
