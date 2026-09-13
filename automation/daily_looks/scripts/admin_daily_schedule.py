"""Admin control for the TodayPick daily generation systemd timer.

The UI time is always Asia/Seoul HH:MM. The VM currently runs the timer in UTC,
so this module writes a UTC systemd drop-in while preserving the KST source of
truth in daily_generation_schedule.json.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = PROJECT_ROOT / "automation" / "daily_looks" / "config" / "daily_generation_schedule.json"
TIMER_NAME = "todaypick-daily-auto-generate.timer"
SERVICE_NAME = "todaypick-daily-auto-generate.service"
DROPIN_DIR = Path("/etc/systemd/system") / f"{TIMER_NAME}.d"
DROPIN_PATH = DROPIN_DIR / "override.conf"
TIMER_STAMP_PATH = Path("/var/lib/systemd/timers") / f"stamp-{TIMER_NAME}"
KST = timezone(timedelta(hours=9), name="KST")
UTC = timezone.utc
TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
DEFAULT_TIME = "06:00"
TIMEZONE_NAME = "Asia/Seoul"


@dataclass(frozen=True)
class Schedule:
    enabled: bool
    time: str
    timezone: str = TIMEZONE_NAME
    revision: int = 0
    updated_at: str | None = None
    updated_by: str = "admin"
    next_run_at: str | None = None
    last_applied_timer_signature: str | None = None


def validate_hhmm(value: str) -> str:
    if not isinstance(value, str) or not TIME_RE.fullmatch(value):
        raise ValueError("time must be strict HH:MM in 24-hour format")
    return value


def kst_to_utc_hhmm(kst_time: str) -> str:
    validate_hhmm(kst_time)
    hour, minute = [int(part) for part in kst_time.split(":")]
    dt = datetime(2026, 1, 1, hour, minute, tzinfo=KST).astimezone(UTC)
    return f"{dt.hour:02d}:{dt.minute:02d}"


def utc_to_kst_hhmm(utc_time: str) -> str:
    validate_hhmm(utc_time)
    hour, minute = [int(part) for part in utc_time.split(":")]
    dt = datetime(2026, 1, 1, hour, minute, tzinfo=UTC).astimezone(KST)
    return f"{dt.hour:02d}:{dt.minute:02d}"


def timer_override_text(kst_time: str) -> str:
    utc_time = kst_to_utc_hhmm(kst_time)
    return (
        "[Timer]\n"
        f"# {kst_time}:00 Asia/Seoul = {utc_time}:00 UTC\n"
        "OnCalendar=\n"
        f"OnCalendar=*-*-* {utc_time}:00 UTC\n"
        "Persistent=true\n"
        f"Unit={SERVICE_NAME}\n"
    )


def calculate_next_run_at(kst_time: str, now: datetime | None = None) -> str:
    validate_hhmm(kst_time)
    current = now.astimezone(KST) if now else datetime.now(KST)
    hour, minute = [int(part) for part in kst_time.split(":")]
    candidate = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= current:
        candidate = candidate + timedelta(days=1)
    return candidate.isoformat(timespec="seconds")


def timer_signature(schedule: Schedule) -> str:
    return f"{schedule.time}|rev{int(schedule.revision)}|{schedule.timezone}"


def read_config(path: Path = CONFIG_PATH) -> Schedule:
    if not path.exists():
        return Schedule(enabled=True, time=DEFAULT_TIME, next_run_at=calculate_next_run_at(DEFAULT_TIME))
    data = json.loads(path.read_text(encoding="utf-8"))
    revision = int(data.get("revision", 0) or 0)
    time_value = validate_hhmm(data.get("time", DEFAULT_TIME))
    return Schedule(
        enabled=bool(data.get("enabled", True)),
        time=time_value,
        timezone=str(data.get("timezone") or TIMEZONE_NAME),
        revision=revision,
        updated_at=data.get("updated_at"),
        updated_by=str(data.get("updated_by") or "admin"),
        next_run_at=data.get("next_run_at") or calculate_next_run_at(time_value),
        last_applied_timer_signature=data.get("last_applied_timer_signature"),
    )


def write_config_atomic(schedule: Schedule, path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "enabled": bool(schedule.enabled),
        "time": validate_hhmm(schedule.time),
        "timezone": TIMEZONE_NAME,
        "revision": int(schedule.revision),
        "updated_at": schedule.updated_at,
        "updated_by": schedule.updated_by,
        "next_run_at": schedule.next_run_at or calculate_next_run_at(schedule.time),
        "last_applied_timer_signature": schedule.last_applied_timer_signature or timer_signature(schedule),
    }
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, text=True, capture_output=True)


def apply_systemd_override(kst_time: str) -> dict[str, Any]:
    validate_hhmm(kst_time)
    stop_proc = run_command(["systemctl", "stop", TIMER_NAME])
    DROPIN_DIR.mkdir(parents=True, exist_ok=True)
    DROPIN_PATH.write_text(timer_override_text(kst_time), encoding="utf-8")

    if os.name != "nt":
        TIMER_STAMP_PATH.parent.mkdir(parents=True, exist_ok=True)
        TIMER_STAMP_PATH.touch()

    results: dict[str, Any] = {
        "override_path": str(DROPIN_PATH),
        "timer_stop": {"returncode": stop_proc.returncode, "stderr": stop_proc.stderr.strip()},
        "stamp_path": str(TIMER_STAMP_PATH),
        "stamp_touched": os.name != "nt",
    }
    for label, args in (
        ("daemon_reload", ["systemctl", "daemon-reload"]),
        ("timer_start", ["systemctl", "start", TIMER_NAME]),
    ):
        proc = run_command(args)
        results[label] = {"returncode": proc.returncode, "stderr": proc.stderr.strip()}
        if proc.returncode != 0:
            raise RuntimeError(f"{label} failed: {proc.stderr.strip()}")
    results["readback"] = systemd_readback()
    return results


def systemd_readback() -> dict[str, Any]:
    data: dict[str, Any] = {"timer": TIMER_NAME}
    checks = {
        "enabled": ["systemctl", "is-enabled", TIMER_NAME],
        "active": ["systemctl", "is-active", TIMER_NAME],
        "list_timers": ["systemctl", "list-timers", TIMER_NAME, "--no-pager"],
    }
    for key, args in checks.items():
        proc = run_command(args)
        data[key] = {
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    if DROPIN_PATH.exists():
        text = DROPIN_PATH.read_text(encoding="utf-8")
        data["override"] = text
        match = re.search(r"OnCalendar=\*-\*-\* ([0-2]\d:[0-5]\d):00 UTC", text)
        if match:
            data["current_time"] = utc_to_kst_hhmm(match.group(1))
    return data


def update_schedule(kst_time: str, *, apply_systemd: bool = False, updated_by: str = "admin") -> dict[str, Any]:
    validate_hhmm(kst_time)
    before = read_config()
    revision = before.revision + 1 if before.time != kst_time else before.revision
    next_run_at = calculate_next_run_at(kst_time)
    updated = Schedule(
        enabled=True,
        time=kst_time,
        timezone=TIMEZONE_NAME,
        revision=revision,
        updated_at=datetime.now(KST).isoformat(timespec="seconds"),
        updated_by=updated_by,
        next_run_at=next_run_at,
    )
    updated = Schedule(
        **{
            **updated.__dict__,
            "last_applied_timer_signature": timer_signature(updated),
        }
    )
    result: dict[str, Any] = {
        "time": kst_time,
        "timezone": TIMEZONE_NAME,
        "revision_before": before.revision,
        "revision": updated.revision,
        "next_run_at": next_run_at,
        "schedule_changed": before.time != kst_time,
    }
    if apply_systemd:
        result["systemd"] = apply_systemd_override(kst_time)
    write_config_atomic(updated)
    return result


def trigger_run_now() -> dict[str, Any]:
    proc = run_command(["systemctl", "start", SERVICE_NAME])
    return {
        "service": SERVICE_NAME,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Control the TodayPick daily generation timer.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    set_parser = sub.add_parser("set")
    set_parser.add_argument("--time", required=True)
    set_parser.add_argument("--apply-systemd", action="store_true")
    restore_parser = sub.add_parser("restore")
    restore_parser.add_argument("--apply-systemd", action="store_true")
    sub.add_parser("run-now")

    args = parser.parse_args()
    if args.command == "status":
        payload = {"config": read_config().__dict__}
        if os.name != "nt":
            payload["systemd"] = systemd_readback()
    elif args.command == "set":
        payload = update_schedule(args.time, apply_systemd=args.apply_systemd)
    elif args.command == "restore":
        payload = update_schedule(DEFAULT_TIME, apply_systemd=args.apply_systemd)
    else:
        payload = trigger_run_now()

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
