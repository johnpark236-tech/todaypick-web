"""Offline checks; never connect to Drive or GCP."""
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE = ROOT / "automation/daily_looks/scripts/validate_chatgpt_publish_request.py"
SPEC = importlib.util.spec_from_file_location("request_validator", MODULE)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class RequestValidationTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads((ROOT / "publish_requests/tp_260923_f50_chatgpt_01.json").read_text())

    def test_real_f50_request_is_valid(self):
        result = VALIDATOR.validate(self.payload)
        self.assertEqual(result["segment"], "f_50")
        self.assertEqual(result["season"], "autumn")
        self.assertEqual(result["expected_image_count"], 10)

    def test_rejects_wrong_count(self):
        self.payload["expected_image_count"] = 9
        with self.assertRaises(ValueError):
            VALIDATOR.validate(self.payload)

    def test_rejects_bad_folder_date(self):
        self.payload["date_folder"] = "260932"
        with self.assertRaises(ValueError):
            VALIDATOR.validate(self.payload)

    def test_rejects_extra_fields(self):
        self.payload["shell_command"] = "echo unsafe"
        with self.assertRaises(ValueError):
            VALIDATOR.validate(self.payload)


if __name__ == "__main__":
    unittest.main()
