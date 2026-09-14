import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import admin_daily_schedule_api as api


class AdminScheduleSingleFirstRoutingTest(unittest.TestCase):
    def test_run_now_uses_single_first_live_entrypoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            unlocked = Path(tmp) / "missing.lock"
            with mock.patch.object(api, "LOCK_PATH", unlocked):
                with mock.patch.object(api.subprocess, "run") as run:
                    run.return_value.returncode = 0
                    run.return_value.stdout = ""
                    run.return_value.stderr = ""
                    result = api.run_daily_generation_now()

        argv = run.call_args.args[0]
        self.assertIn(str(api.RUN_NOW_SCRIPT), argv)
        self.assertIn("--live-api", argv)
        self.assertIn("--trigger-source", argv)
        self.assertIn("run_now", argv)
        self.assertIn("--run-id", argv)
        self.assertEqual(result["status"], "PASS")

    def test_global_lock_blocks_run_now_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            locked = Path(tmp) / "daily.lock"
            locked.write_text("locked", encoding="utf-8")
            with mock.patch.object(api, "LOCK_PATH", locked):
                result = api.run_daily_generation_now()
        self.assertEqual(result["status"], "RUNNING")

    def test_run_now_does_not_use_legacy_shortcut(self):
        with tempfile.TemporaryDirectory() as tmp:
            unlocked = Path(tmp) / "missing.lock"
            with mock.patch.object(api, "LOCK_PATH", unlocked):
                with mock.patch.object(api.subprocess, "run") as run:
                    run.return_value.returncode = 0
                    run.return_value.stdout = ""
                    run.return_value.stderr = ""
                    result = api.run_daily_generation_now()

        argv = run.call_args.args[0]
        self.assertIn(str(api.RUN_NOW_SCRIPT), argv)
        self.assertIn("--live-api", argv)
        self.assertIn("--trigger-source", argv)
        self.assertIn("run_now", argv)
        self.assertIn("--run-id", argv)
        self.assertNotIn("--dry-run", argv)
        self.assertEqual(result["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
