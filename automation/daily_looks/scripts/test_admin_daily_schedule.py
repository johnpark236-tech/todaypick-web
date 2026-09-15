import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import admin_daily_schedule as schedule


class AdminDailyScheduleTest(unittest.TestCase):
    def test_accepts_strict_hhmm(self):
        for value in ("00:00", "00:30", "06:00", "07:00", "13:30", "23:59"):
            self.assertEqual(schedule.validate_hhmm(value), value)

    def test_rejects_invalid_times(self):
        for value in ("24:00", "25:00", "12:60", "7:00", "abc", ""):
            with self.assertRaises(ValueError, msg=value):
                schedule.validate_hhmm(value)

    def test_kst_to_utc_conversion(self):
        self.assertEqual(schedule.kst_to_utc_hhmm("06:00"), "21:00")
        self.assertEqual(schedule.kst_to_utc_hhmm("07:00"), "22:00")
        self.assertEqual(schedule.kst_to_utc_hhmm("00:00"), "15:00")
        self.assertEqual(schedule.kst_to_utc_hhmm("23:59"), "14:59")

    def test_six_hour_slots(self):
        self.assertEqual(schedule.six_hour_slots("06:00"), ["00:00", "06:00", "12:00", "18:00"])

    def test_override_resets_existing_calendar(self):
        text = schedule.timer_override_text("07:00")
        self.assertIn("OnCalendar=\n", text)
        self.assertIn("OnCalendar=*-*-* 04:00:00 UTC", text)
        self.assertIn("OnCalendar=*-*-* 10:00:00 UTC", text)
        self.assertIn("OnCalendar=*-*-* 16:00:00 UTC", text)
        self.assertIn("OnCalendar=*-*-* 22:00:00 UTC", text)

    def test_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily_generation_schedule.json"
            schedule.write_config_atomic(schedule.Schedule(enabled=True, time="13:30", revision=4), path)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["time"], "13:30")
            self.assertEqual(data["revision"], 4)
            self.assertIn("next_run_at", data)
            self.assertEqual(schedule.read_config(path).time, "13:30")
            self.assertEqual(schedule.read_config(path).revision, 4)

    def test_next_run_future_time_stays_today(self):
        now = schedule.datetime(2026, 9, 13, 6, 20, tzinfo=schedule.KST)
        self.assertEqual(schedule.calculate_next_run_at("07:00", now), "2026-09-13T07:00:00+09:00")

    def test_next_run_past_time_moves_to_tomorrow(self):
        now = schedule.datetime(2026, 9, 13, 6, 20, tzinfo=schedule.KST)
        self.assertEqual(schedule.calculate_next_run_at("05:00", now), "2026-09-13T11:00:00+09:00")


if __name__ == "__main__":
    unittest.main()
