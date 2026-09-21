"""
T01-T20: Simple Manual Upload Watcher tests

T01-T08: classify_segment_folder
T09-T13: season_for_date_folder (via classify logic)
T14-T16: compute_input_set_hash / scan_image_files
T17-T18: scan_for_pending_inputs  (wrong image count filtered)
T19-T20: run_watcher stability / idempotency (dry_run mode with mocks)
"""

import hashlib
import io
import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

# ── add scripts dir to path ────────────────────────────────────────────────────
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_rgb_webp(width: int = 648, height: int = 1152) -> bytes:
    """Return a minimal in-memory WebP image of the given size."""
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=80)
    return buf.getvalue()


def _populate_folder(folder: Path, count: int = 10, w: int = 648, h: int = 1152) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(count):
        p = folder / f"img_{i:02d}.webp"
        p.write_bytes(_make_rgb_webp(w, h))
        paths.append(p)
    return paths


def _open_temp_db(tmp_path: Path) -> sqlite3.Connection:
    from simple_manual_upload_watcher import open_db
    return open_db(tmp_path / "state.db")


# ══════════════════════════════════════════════════════════════════════════════
# T01-T08  classify_segment_folder
# ══════════════════════════════════════════════════════════════════════════════

from simple_manual_upload_watcher import classify_segment_folder


class TestClassifySegmentFolder:
    def test_T01_f_10_returns_female_10(self):
        assert classify_segment_folder("f_10") == "female_10"

    def test_T02_m_60_returns_male_60(self):
        assert classify_segment_folder("m_60") == "male_60"

    def test_T03_f_20_returns_female_20(self):
        assert classify_segment_folder("f_20") == "female_20"

    def test_T04_m_30_returns_male_30(self):
        assert classify_segment_folder("m_30") == "male_30"

    def test_T05_uppercase_F_10_accepted(self):
        assert classify_segment_folder("F_10") == "female_10"

    def test_T06_invalid_f_99_returns_none(self):
        assert classify_segment_folder("f_99") is None

    def test_T07_invalid_female_10_wrong_format_returns_none(self):
        # Full "female_10" is not the user-facing short form; treated as invalid
        assert classify_segment_folder("female_10") is None

    def test_T08_empty_string_returns_none(self):
        assert classify_segment_folder("") is None


# ══════════════════════════════════════════════════════════════════════════════
# T09-T13  season classification (via season_for_date_folder)
# ══════════════════════════════════════════════════════════════════════════════

from remote_daily_looks import season_for_date_folder


class TestSeasonClassification:
    def test_T09_260921_is_autumn(self):
        assert season_for_date_folder("260921") == "autumn"

    def test_T10_261201_is_winter(self):
        assert season_for_date_folder("261201") == "winter"

    def test_T11_260415_is_spring(self):
        assert season_for_date_folder("260415") == "spring"

    def test_T12_260701_is_summer(self):
        assert season_for_date_folder("260701") == "summer"

    def test_T13_260115_is_winter(self):
        assert season_for_date_folder("260115") == "winter"


# ══════════════════════════════════════════════════════════════════════════════
# T14-T16  hash / file helpers
# ══════════════════════════════════════════════════════════════════════════════

from simple_manual_upload_watcher import compute_input_set_hash, scan_image_files


class TestHashAndScan:
    def test_T14_hash_deterministic(self, tmp_path):
        files = _populate_folder(tmp_path / "imgs", 10)
        h1 = compute_input_set_hash(files)
        h2 = compute_input_set_hash(files)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_T15_hash_changes_when_file_changes(self, tmp_path):
        folder = tmp_path / "imgs"
        files = _populate_folder(folder, 10)
        h1 = compute_input_set_hash(files)
        # overwrite first file with a visually different image (different color)
        img2 = Image.new("RGB", (648, 1152), color=(255, 0, 0))
        buf = io.BytesIO()
        img2.save(buf, "WEBP", quality=80)
        files[0].write_bytes(buf.getvalue())
        h2 = compute_input_set_hash(files)
        assert h1 != h2

    def test_T16_scan_image_files_ignores_non_images(self, tmp_path):
        folder = tmp_path / "imgs"
        folder.mkdir()
        (folder / "a.webp").write_bytes(_make_rgb_webp())
        (folder / "b.jpg").write_bytes(_make_rgb_webp(100, 100))
        (folder / "readme.txt").write_text("ignore me")
        (folder / "subfolder").mkdir()
        result = scan_image_files(folder)
        assert len(result) == 2
        assert all(p.suffix.lower() in {".jpg", ".webp"} for p in result)


# ══════════════════════════════════════════════════════════════════════════════
# T17-T18  scan_for_pending_inputs — count filtering
# ══════════════════════════════════════════════════════════════════════════════

from simple_manual_upload_watcher import scan_for_pending_inputs


class TestScanPendingInputs:
    def test_T17_nine_images_not_returned(self, tmp_path):
        folder = tmp_path / "260921" / "f_10"
        _populate_folder(folder, 9)
        con = _open_temp_db(tmp_path)
        result = scan_for_pending_inputs(tmp_path, con)
        assert result == []

    def test_T18_ten_images_returned(self, tmp_path):
        folder = tmp_path / "260921" / "f_10"
        _populate_folder(folder, 10)
        con = _open_temp_db(tmp_path)
        result = scan_for_pending_inputs(tmp_path, con)
        assert len(result) == 1
        p = result[0]
        assert p.date_folder == "260921"
        assert p.segment == "female_10"
        assert p.season == "autumn"
        assert p.seg_folder_name == "f_10"


# ══════════════════════════════════════════════════════════════════════════════
# T19-T20  run_watcher  (stability + idempotency, fully mocked GCS)
# ══════════════════════════════════════════════════════════════════════════════

from simple_manual_upload_watcher import run_watcher, STABILITY_SCANS_REQUIRED


class TestRunWatcher:
    def _mock_publish(self):
        seg_mock = MagicMock(return_value={
            "segment": "female_10",
            "before": 0,
            "appended": 10,
            "skipped_duplicates": 0,
            "after": 10,
            "url": "https://storage.googleapis.com/bucket/production/autumn/female_10.json",
        })
        idx_mock = MagicMock(return_value="https://storage.googleapis.com/bucket/production/index.json")
        return seg_mock, idx_mock

    def test_T19_stability_persists_across_process_restarts(self, tmp_path):
        """
        Stability count is stored in SQLite, not in-memory.
        First one-shot: detected (count=1, not processed).
        Second one-shot (same DB): count reaches 2 → processed.
        """
        folder = tmp_path / "260921" / "f_10"
        _populate_folder(folder, 10)
        db_path = tmp_path / "state.db"
        processed_segments = []

        def mock_process(pending, con_, dry_run=False):
            processed_segments.append(pending.segment)
            from simple_manual_upload_watcher import record_processing
            record_processing(con_, pending.input_set_hash, pending.date_folder,
                              pending.segment, pending.season,
                              "https://example.com/fake.json", "COMPLETE")
            return {
                "segment": pending.segment,
                "before": 0,
                "appended": 10,
                "skipped_duplicates": 0,
                "after": 10,
                "url": "https://example.com/fake.json",
            }

        with patch("simple_manual_upload_watcher.process_upload", side_effect=mock_process):
            # First scan: count=1, not processed
            run_watcher(dry_run=True, one_shot=True, user_config_root=tmp_path, state_db_path=db_path)
            assert processed_segments == [], "Must not process on first scan"

            # Second scan (same DB): count=2 → processed
            run_watcher(dry_run=True, one_shot=True, user_config_root=tmp_path, state_db_path=db_path)
            assert processed_segments == ["female_10"], "Must process on second scan"

    def test_T20_idempotency_already_complete(self, tmp_path):
        """An already-COMPLETE input_set_hash must not be re-processed."""
        folder = tmp_path / "260921" / "f_10"
        files = _populate_folder(folder, 10)
        con = _open_temp_db(tmp_path)

        from simple_manual_upload_watcher import compute_input_set_hash, record_processing
        h = compute_input_set_hash(files)
        record_processing(con, h, "260921", "female_10", "autumn",
                          "https://example.com/catalog.json", "COMPLETE")

        pending = scan_for_pending_inputs(tmp_path, con)
        assert pending == [], "Already-complete set must not appear in pending list"
