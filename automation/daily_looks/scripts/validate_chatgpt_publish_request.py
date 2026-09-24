#!/usr/bin/env python3
"""Validate a user-requested TodayPick Drive publication envelope; NEVER publishes."""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys

ALLOWED_SEGMENTS = {f"{gender}_{age}" for gender in ("f", "m") for age in (10,20,30,40,50,60)}
SEASONS = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring",
           5: "spring", 6: "summer", 7: "summer", 8: "summer",
           9: "autumn", 10: "autumn", 11: "autumn"}
REQUIRED = {"schema_version", "request_id", "date_folder", "segment", "drive_folder_id",
            "manifest_file_id", "metadata_file_id", "expected_image_count", "source"}

def fail(message):
    raise ValueError(message)

def validate(payload):
    if not isinstance(payload, dict):
        fail("request must be an object")
    unknown = set(payload) - REQUIRED
    missing = REQUIRED - set(payload)
    if missing or unknown:
        fail(f"missing={sorted(missing)} unexpected={sorted(unknown)}")
    if payload["schema_version"] != 1 or isinstance(payload["schema_version"], bool):
        fail("schema_version must equal 1")
    if payload["source"] not in ("chatgpt", "gas_auto"):
        fail("source must be chatgpt or gas_auto")
    if not isinstance(payload["request_id"], str) or not re.fullmatch(r"tp_[a-zA-Z0-9_-]{8,80}", payload["request_id"]):
        fail("invalid request_id")
    date = payload["date_folder"]
    if not isinstance(date, str) or not re.fullmatch(r"\d{6}", date):
        fail("date_folder must be YYMMDD")
    try:
        parsed = dt.datetime.strptime(date, "%y%m%d")
    except ValueError:
        fail("invalid date")
    if parsed.year < 2026 or parsed.year > 2099:
        fail("date out of range")
    if payload["segment"] not in ALLOWED_SEGMENTS:
        fail("invalid segment")
    for key in ("drive_folder_id", "manifest_file_id", "metadata_file_id"):
        value = payload[key]
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{15,128}", value):
            fail(f"invalid {key}")
    if type(payload["expected_image_count"]) is not int or payload["expected_image_count"] != 10:
        fail("expected_image_count must be integer 10")
    return {"request_id": payload["request_id"], "date_folder": date,
            "segment": payload["segment"], "season": SEASONS[parsed.month],
            "expected_image_count": 10, "status": "VALIDATED_NOT_PUBLISHED"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=pathlib.Path)
    args = parser.parse_args()
    root = pathlib.Path("publish_requests").resolve()
    source = args.path.resolve()
    if source.parent != root or not re.fullmatch(r"[A-Za-z0-9_-]+\.json", source.name):
        fail("request must be a direct JSON child of publish_requests/")
    if source.is_symlink() or source.stat().st_size > 8192:
        fail("symlink or oversized request not allowed")
    result = validate(json.loads(source.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"INVALID_REQUEST: {exc}", file=sys.stderr)
        sys.exit(2)
