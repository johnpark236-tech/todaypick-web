import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import daily_auto_generate as daily


class DailyAutoGenerateRunIdentityTest(unittest.TestCase):
    def test_timer_run_key_includes_time_and_revision(self):
        run_key, meta = daily.make_run_identity(
            "2026-09-13",
            "260913",
            daily.GROUPS_ORDER,
            "timer",
            scheduled_time="07:00",
            schedule_revision=13,
        )
        self.assertEqual(run_key, "2026-09-13__07-00__rev13__timer__all")
        self.assertEqual(meta["date_folder"], "260913")
        self.assertEqual(meta["trigger_source"], "timer")

    def test_different_revision_allows_same_day_rerun(self):
        first, _ = daily.make_run_identity(
            "2026-09-13",
            "260913",
            daily.GROUPS_ORDER,
            "timer",
            scheduled_time="06:00",
            schedule_revision=12,
        )
        second, _ = daily.make_run_identity(
            "2026-09-13",
            "260913",
            daily.GROUPS_ORDER,
            "timer",
            scheduled_time="07:00",
            schedule_revision=13,
        )
        self.assertNotEqual(first, second)

    def test_same_slot_skips_but_new_revision_runs(self):
        old_ledger = daily.RUN_LEDGER_PATH
        old_log_root = daily.LOG_ROOT
        old_output_root = daily.OUTPUT_ROOT
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                daily.LOG_ROOT = root / "logs"
                daily.OUTPUT_ROOT = root / "output"
                daily.RUN_LEDGER_PATH = daily.LOG_ROOT / "daily_auto_generate_ledger.json"

                first = daily.run_generation(
                    target_group="female_10s",
                    dry_run=True,
                    upload_drive=False,
                    date_str="260913",
                    auto_ingest=False,
                    trigger_source="timer",
                    scheduled_time="07:00",
                    schedule_revision=13,
                )
                second = daily.run_generation(
                    target_group="female_10s",
                    dry_run=True,
                    upload_drive=False,
                    date_str="260913",
                    auto_ingest=False,
                    trigger_source="timer",
                    scheduled_time="07:00",
                    schedule_revision=13,
                )
                third = daily.run_generation(
                    target_group="female_10s",
                    dry_run=True,
                    upload_drive=False,
                    date_str="260913",
                    auto_ingest=False,
                    trigger_source="timer",
                    scheduled_time="07:00",
                    schedule_revision=14,
                )

                self.assertEqual(len(first["generation_results"]), 1)
                self.assertEqual(second["status"], "SKIP_ALREADY_COMPLETED")
                self.assertEqual(len(third["generation_results"]), 1)
        finally:
            daily.RUN_LEDGER_PATH = old_ledger
            daily.LOG_ROOT = old_log_root
            daily.OUTPUT_ROOT = old_output_root


if __name__ == "__main__":
    unittest.main()
