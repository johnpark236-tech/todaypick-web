import os
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

import single_first_daily_generate as v32


def options(**overrides):
    base = {
        "date_folder": "260915",
        "date_iso": "2026-09-15",
        "season": "winter",
        "segments": ["female_10"],
        "trigger_source": "timer",
        "scheduled_time": "06:00",
        "schedule_revision": 1,
        "run_id": "test-run",
    }
    base.update(overrides)
    return v32.SingleFirstOptions(**base)


class SingleFirstDailyGenerateTest(unittest.TestCase):
    def test_targets_are_120_singles_and_12_sheets_for_full_run(self):
        opts = options(segments=v32.SEGMENTS)
        self.assertEqual(len(opts.segments), 12)
        self.assertEqual(len(opts.segments) * 10, 120)

    def test_no_publish_without_visual_qa_or_provider(self):
        old_report_root = v32.REPORT_ROOT
        try:
            with tempfile.TemporaryDirectory() as tmp:
                v32.REPORT_ROOT = Path(tmp)
                with self.assertRaises(v32.SingleFirstCapabilityError):
                    v32.run_single_first_daily_generation(options(publish=True, smoke=False))
        finally:
            v32.REPORT_ROOT = old_report_root

    def test_smoke_single_first_roundtrip(self):
        old_report_root = v32.REPORT_ROOT
        try:
            with tempfile.TemporaryDirectory() as tmp:
                v32.REPORT_ROOT = Path(tmp)
                report = v32.run_single_first_daily_generation(options(smoke=True, publish=False))
        finally:
            v32.REPORT_ROOT = old_report_root
        segment = report["segments"]["female_10"]
        self.assertEqual(segment["single_generation_count"], 10)
        self.assertEqual(segment["visual_qa_count"], 10)
        self.assertEqual(segment["sheet_count"], 1)
        self.assertEqual(segment["roundtrip_mapping"], "10/10")
        self.assertFalse(segment["publish"])

    def test_vm_provider_capability_requires_explicit_single_first_provider(self):
        old_provider = os.environ.pop("TODAYPICK_SINGLE_FIRST_PROVIDER", None)
        old_gemini = os.environ.pop("GEMINI_API_KEY", None)
        old_google = os.environ.pop("GOOGLE_API_KEY", None)
        try:
            capability = v32.provider_capability()
            self.assertFalse(capability["capable"])
        finally:
            if old_provider is not None:
                os.environ["TODAYPICK_SINGLE_FIRST_PROVIDER"] = old_provider
            if old_gemini is not None:
                os.environ["GEMINI_API_KEY"] = old_gemini
            if old_google is not None:
                os.environ["GOOGLE_API_KEY"] = old_google

    def make_manual_input(self, root: Path, segment="female_10", qa_count=10, wrong_size_index=None, missing_index=None):
        segment_dir = root / "260915" / "single_first" / "winter" / segment
        segment_dir.mkdir(parents=True)
        cuts = []
        for index in range(1, 11):
            if missing_index == index:
                continue
            path = segment_dir / f"{index:02d}.png"
            size = (320, 480) if wrong_size_index == index else (v32.SINGLE_CUT_WIDTH, v32.SINGLE_CUT_HEIGHT)
            image = Image.new("RGB", size, ((index * 23) % 255, 100, 170))
            for x in range(0, size[0], 5):
                for y in range(0, size[1], 7):
                    image.putpixel((x, y), ((index * 31 + x) % 255, (100 + y) % 255, (170 + x + y) % 255))
            image.save(path, "PNG")
        for index in range(1, qa_count + 1):
            cuts.append({
                "segment": segment,
                "index": index,
                "HEAD_VISIBLE": True,
                "HAIR_VISIBLE": True,
                "FEET_VISIBLE": True,
                "ONE_PERSON_ONLY": True,
                "NO_ADJACENT_PERSON": True,
                "AGE_MATCH": True,
                "GENDER_MATCH": True,
                "SEASON_MATCH": True,
                "QA_SCORE": 95,
            })
        (segment_dir / "visual_qa.json").write_text(json.dumps({"cuts": cuts}, ensure_ascii=False, indent=2), encoding="utf-8")
        return root / "260915" / "single_first" / "winter"

    def make_all_manual_inputs(self, root: Path):
        for segment in v32.SEGMENTS:
            self.make_manual_input(root, segment=segment)
        return root / "260915" / "single_first" / "winter"

    def run_manual(self, input_base: Path, **overrides):
        old_report_root = v32.REPORT_ROOT
        old_prepared_root = v32.PREPARED_ROOT
        try:
            with tempfile.TemporaryDirectory() as tmp:
                v32.REPORT_ROOT = Path(tmp) / "reports"
                v32.PREPARED_ROOT = Path(tmp) / "prepared"
                kwargs = {"mode": "manual", "manual_input_base": input_base, "publish": False}
                kwargs.update(overrides)
                opts = options(**kwargs)
                return v32.run_single_first_daily_generation(opts)
        finally:
            v32.REPORT_ROOT = old_report_root
            v32.PREPARED_ROOT = old_prepared_root

    def test_manual_approved_single_input_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self.make_manual_input(Path(tmp))
            report = self.run_manual(base)
        self.assertEqual(report["status"], "VERIFIED")
        self.assertEqual(report["segments"]["female_10"]["single_count"], 10)
        self.assertEqual(report["segments"]["female_10"]["roundtrip_mapping"], "10/10")

    def test_manual_missing_single_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self.make_manual_input(Path(tmp), missing_index=7)
            with self.assertRaises(RuntimeError):
                self.run_manual(base)

    def test_manual_wrong_size_single_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self.make_manual_input(Path(tmp), wrong_size_index=3)
            with self.assertRaises(RuntimeError):
                self.run_manual(base)

    def test_manual_visual_qa_missing_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self.make_manual_input(Path(tmp))
            (base / "female_10" / "visual_qa.json").unlink()
            with self.assertRaises(RuntimeError):
                self.run_manual(base)

    def test_manual_visual_qa_9_of_10_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self.make_manual_input(Path(tmp), qa_count=9)
            with self.assertRaises(RuntimeError):
                self.run_manual(base)

    def test_publish_gate_requires_valid_assets_and_backup_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self.make_all_manual_inputs(Path(tmp))
            report = self.run_manual(base, segments=v32.SEGMENTS, publish=True)
        self.assertEqual(report["status"], "PUBLISH_READY")
        self.assertTrue(report["segments"]["female_10"]["backup_path"])

    def test_publish_gate_blocks_invalid_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self.make_all_manual_inputs(Path(tmp))
            (base / "female_10" / "01.png").unlink()
            with self.assertRaises(RuntimeError):
                self.run_manual(base, segments=v32.SEGMENTS, publish=True)


if __name__ == "__main__":
    unittest.main()
