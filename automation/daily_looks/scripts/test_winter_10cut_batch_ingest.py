"""Tests for Winter 12-Segment 10-Cut Batch Ingest Pipeline."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from batch_winter_10cut_expansion import (
    ALL_WINTER_SEGMENTS,
    CANONICAL_WIDTH,
    CANONICAL_HEIGHT,
    SEGMENT_TO_KR,
    discover_source_sheet,
    validate_source_sheet,
)


class Winter10CutBatchIngestTest(unittest.TestCase):
    def test_target_segments_all_12_present(self):
        self.assertEqual(len(ALL_WINTER_SEGMENTS), 12)
        expected = [
            "female_10", "female_20", "female_30", "female_40", "female_50", "female_60",
            "male_10", "male_20", "male_30", "male_40", "male_50", "male_60",
        ]
        self.assertEqual(ALL_WINTER_SEGMENTS, expected)

    def test_segment_to_kr_mapping_complete(self):
        for seg in ALL_WINTER_SEGMENTS:
            self.assertIn(seg, SEGMENT_TO_KR)
            self.assertTrue(SEGMENT_TO_KR[seg].endswith("대"))

    def test_source_validation_rejects_non_canonical_dimensions(self):
        with tempfile.TemporaryDirectory() as td:
            bad_img = Path(td) / "bad.png"
            im = Image.new("RGB", (1280, 1168), "white")
            im.save(bad_img)

            valid, reason, meta = validate_source_sheet(bad_img)
            self.assertFalse(valid)
            self.assertIn("Non-canonical dimension", reason)

    def test_source_validation_accepts_canonical_dimensions(self):
        with tempfile.TemporaryDirectory() as td:
            good_img = Path(td) / "good.png"
            im = Image.new("RGB", (CANONICAL_WIDTH, CANONICAL_HEIGHT), "white")
            im.save(good_img)

            valid, reason, meta = validate_source_sheet(good_img)
            self.assertTrue(valid)
            self.assertEqual(reason, "OK")
            self.assertEqual(meta["width"], 1313)
            self.assertEqual(meta["height"], 1198)
            self.assertTrue(len(meta["sha256"]) == 64)

    def test_discover_source_sheet_finds_kr_named_files(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            proc = base / "_Processed"
            proc.mkdir()
            test_file = proc / "겨울_여성10대_260914.png"
            test_file.write_bytes(b"dummy")

            found = discover_source_sheet(base, "female_10", "260914")
            self.assertIsNotNone(found)
            self.assertEqual(found.resolve(), test_file.resolve())

    def test_discover_source_sheet_returns_none_if_missing(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            found = discover_source_sheet(base, "female_20", "260914")
            self.assertIsNone(found)

    def test_winter_set_id_format(self):
        # Format: winter_<gender>_<age>_<date>_<sourcehash8>
        date = "260914"
        sha = "abcdef1234567890" * 4
        for seg in ALL_WINTER_SEGMENTS:
            gender, age = seg.split("_")
            set_id = f"winter_{gender}_{age}_{date}_{sha[:8]}"
            self.assertTrue(set_id.startswith(f"winter_{seg}_{date}_"))
            self.assertEqual(len(set_id.split("_")), 5)

    def test_winter_sheet_url_format(self):
        date = "260914"
        for seg in ALL_WINTER_SEGMENTS:
            gender, age = seg.split("_")
            sheet_object = f"production/sheets/winter/{date}/{gender}/{age}/sheet.png"
            expected_url = f"https://storage.googleapis.com/todaypick-daily-looks-363284724091/{sheet_object}"
            self.assertIn("/winter/", expected_url)
            self.assertTrue(expected_url.endswith("/sheet.png"))


if __name__ == "__main__":
    unittest.main()
