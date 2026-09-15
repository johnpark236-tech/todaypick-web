import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import daily_auto_generate as daily
import prompt_rotation as rotation


class PromptRotationTest(unittest.TestCase):
    def test_rotation_has_exactly_48_entries(self):
        self.assertEqual(len(rotation.ROTATION), 48)
        self.assertEqual(len(set(rotation.ROTATION)), 48)

    def test_rotation_starts_autumn_female_10(self):
        self.assertEqual(rotation.ROTATION[0], "autumn_female_10")

    def test_rotation_order_female_10_to_60(self):
        self.assertEqual(rotation.ROTATION[:6], [
            "autumn_female_10",
            "autumn_female_20",
            "autumn_female_30",
            "autumn_female_40",
            "autumn_female_50",
            "autumn_female_60",
        ])

    def test_rotation_then_male_10_to_60(self):
        self.assertEqual(rotation.ROTATION[6:12], [
            "autumn_male_10",
            "autumn_male_20",
            "autumn_male_30",
            "autumn_male_40",
            "autumn_male_50",
            "autumn_male_60",
        ])

    def test_rotation_season_order_autumn_winter_spring_summer(self):
        self.assertEqual([item.split("_", 1)[0] for item in rotation.ROTATION[0::12]], ["autumn", "winter", "spring", "summer"])

    def test_rotation_wraps_after_summer_male_60(self):
        self.assertEqual(rotation.ROTATION[-1], "summer_male_60")
        cursor = {"rotation_index": 47, "cycle_number": 1, "current_segment": "summer_male_60"}
        with tempfile.TemporaryDirectory() as tmp:
            updated = rotation.advance_after_success(cursor, "run", Path(tmp) / "cursor.json")
        self.assertEqual(updated["rotation_index"], 0)
        self.assertEqual(updated["current_segment"], "autumn_female_10")
        self.assertEqual(updated["cycle_number"], 2)

    def test_cursor_persists_after_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cursor.json"
            first = rotation.load_cursor(path)
            first["rotation_index"] = 5
            first["current_segment"] = "autumn_female_60"
            rotation.write_json_atomic(path, first)
            second = rotation.load_cursor(path)
        self.assertEqual(second["rotation_index"], 5)
        self.assertEqual(second["current_segment"], "autumn_female_60")

    def test_cursor_advances_only_after_publish_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cursor.json"
            cursor = rotation.load_cursor(path)
            rotation.save_attempt(cursor, "run", path)
            self.assertEqual(rotation.load_cursor(path)["rotation_index"], 0)
            advanced = rotation.advance_after_success(cursor, "run", path)
            self.assertEqual(advanced["rotation_index"], 1)

    def test_cursor_does_not_advance_on_generation_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cursor.json"
            cursor = rotation.load_cursor(path)
            rotation.save_attempt(cursor, "failed-run", path)
            self.assertEqual(rotation.load_cursor(path)["rotation_index"], 0)

    def test_cursor_does_not_advance_on_qa_failure(self):
        self.test_cursor_does_not_advance_on_generation_failure()

    def test_cursor_does_not_advance_on_publish_failure(self):
        self.test_cursor_does_not_advance_on_generation_failure()

    def test_prompt_mapping_48_of_48(self):
        result = rotation.validate_prompt_library()
        self.assertTrue(result["ok"], result["failures"])
        self.assertEqual(result["file_count"], 48)

    def test_prompt_sha_recorded(self):
        target = rotation.target_for_index(0, 1)
        prompt = rotation.load_prompt_for_target(target)
        self.assertEqual(len(prompt["sha256"]), 64)
        self.assertIn("03_AUTUMN", prompt["gcs_object"])

    def test_schedule_interval_six_hours(self):
        self.assertEqual(daily.PRODUCTION_INTERVAL_HOURS, 6)

    def test_run_now_uses_current_cursor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cursor_path = root / "cursor.json"
            cursor = rotation.initial_cursor()
            cursor["rotation_index"] = 2
            cursor["current_segment"] = "autumn_female_30"
            rotation.write_json_atomic(cursor_path, cursor)
            old_cursor = daily.CURSOR_PATH
            old_ledger = daily.RUN_LEDGER_PATH
            old_log = daily.LOG_ROOT
            try:
                daily.CURSOR_PATH = cursor_path
                daily.LOG_ROOT = root / "logs"
                daily.RUN_LEDGER_PATH = daily.LOG_ROOT / "daily_auto_generate_ledger.json"
                with mock.patch.object(daily, "run_single_first_daily_generation") as orchestrator:
                    orchestrator.return_value = {"status": "PUBLISHED", "single_target": 10, "sheet_target": 1, "report_path": "report.json"}
                    daily.run_generation(
                        dry_run=False,
                        live_api=True,
                        upload_drive=False,
                        date_str="260915",
                        auto_ingest=False,
                        trigger_source="run_now",
                    )
                opts = orchestrator.call_args.args[0]
                self.assertEqual(opts.season, "autumn")
                self.assertEqual(opts.segments, ["female_30"])
                self.assertEqual(rotation.load_cursor(cursor_path)["current_segment"], "autumn_female_40")
            finally:
                daily.CURSOR_PATH = old_cursor
                daily.RUN_LEDGER_PATH = old_ledger
                daily.LOG_ROOT = old_log

    def test_global_lock_prevents_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_lock = daily.RUN_LOCK_PATH
            daily.RUN_LOCK_PATH = Path(tmp) / "daily_auto_generate.lock"
            try:
                self.assertTrue(daily.acquire_run_lock())
                self.assertFalse(daily.acquire_run_lock())
            finally:
                daily.release_run_lock()
                daily.RUN_LOCK_PATH = old_lock

    def test_new_set_appended_first(self):
        old = [look("old_01", "oldset", True), look("legacy_01", None, False)]
        new = [look("new_01", "newset", True)]
        result = rotation.accumulate_new_set_first(old, new)
        self.assertEqual([item["id"] for item in result["looks"]], ["new_01", "old_01"])

    def test_previous_single_first_sets_preserved(self):
        old = [look("old_01", "oldset", True), look("old_02", "oldset", True)]
        result = rotation.accumulate_new_set_first(old, [look("new_01", "newset", True)])
        self.assertEqual(result["preserved_single_first"], 2)
        self.assertEqual(len(result["looks"]), 3)

    def test_existing_catalog_single_first_preserves_unflagged_looks(self):
        old = [
            {
                "id": "old_01",
                "sha256": "old_sha",
                "set_id": "winter_female_10_260915_b0af78e2",
                "sheet_url": "https://example.invalid/sheet.png",
                "cut_index": 1,
            }
        ]
        result = rotation.accumulate_new_set_first(
            old,
            [look("new_01", "newset", True)],
            existing_catalog={"single_first": True},
        )
        self.assertEqual([item["id"] for item in result["looks"]], ["new_01", "old_01"])
        self.assertEqual(result["legacy_removed"], 0)
        self.assertEqual(result["preserved_single_first"], 1)

    def test_legacy_sheet_first_removed_after_success(self):
        result = rotation.accumulate_new_set_first([look("legacy_01", None, False)], [look("new_01", "newset", True)])
        self.assertEqual(result["legacy_removed"], 1)
        self.assertEqual([item["id"] for item in result["looks"]], ["new_01"])

    def test_legacy_not_removed_before_success(self):
        existing = [look("legacy_01", None, False)]
        self.assertEqual(existing[0]["id"], "legacy_01")

    def test_backup_created_before_catalog_swap(self):
        run_id = rotation.build_rotation_run_id("2026-09-15", "06:00", 1, "timer", rotation.target_for_index(0, 1))
        backup = f"production_backups/260915/{run_id}/autumn/female_10/"
        self.assertIn("production_backups/260915/", backup)

    def test_authoritative_single_is_not_roundtrip_crop(self):
        new = [look("new_01", "newset", True)]
        result = rotation.accumulate_new_set_first([], new)
        self.assertEqual(result["looks"][0]["generation_method"], "single_first")
        self.assertEqual(result["looks"][0]["pipeline_version"], "v3.2")

    def test_sheet_derived_from_approved_singles(self):
        new = [look("new_01", "newset", True)]
        self.assertTrue(rotation.is_single_first_look(new[0]))


def look(look_id, set_id, single_first):
    data = {
        "id": look_id,
        "url": f"https://cdn.example/{look_id}.webp",
        "sha256": look_id.encode().hex().ljust(64, "0")[:64],
        "width": 648,
        "height": 1152,
        "cut_index": 1,
    }
    if set_id:
        data["set_id"] = set_id
        data["sheet_url"] = f"https://cdn.example/{set_id}.png"
    if single_first:
        data["generation_method"] = "single_first"
        data["pipeline_version"] = "v3.2"
        data["single_first"] = True
    else:
        data["generation_method"] = "sheet_first_legacy"
        data["pipeline_version"] = "legacy"
    return data


if __name__ == "__main__":
    unittest.main()
