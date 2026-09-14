import os
import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
