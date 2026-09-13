"""Small local admin API for TodayPick daily generation schedule control."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from admin_daily_schedule import (
    DEFAULT_TIME,
    TIMER_NAME,
    TIMEZONE_NAME,
    read_config,
    systemd_readback,
    update_schedule,
    validate_hhmm,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUN_NOW_SCRIPT = PROJECT_ROOT / "automation" / "daily_looks" / "scripts" / "daily_auto_generate.py"
LOCK_PATH = PROJECT_ROOT / "automation" / "daily_looks" / "logs" / "daily_auto_generate.lock"
KST = timezone(timedelta(hours=9), name="KST")


def configured_password_ok(password: str) -> bool:
    expected_hash = os.environ.get("TODAYPICK_ADMIN_PASSWORD_SHA256", "").strip()
    expected_plain = os.environ.get("TODAYPICK_ADMIN_PASSWORD", "")
    if expected_hash:
        digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(digest, expected_hash)
    if expected_plain:
        return hmac.compare_digest(password, expected_plain)
    return False


def run_daily_generation_now() -> dict[str, Any]:
    if LOCK_PATH.exists():
        return {"success": False, "status": "RUNNING", "message": "daily generation lock exists"}
    python_bin = os.environ.get("TODAYPICK_PYTHON", "python")
    run_id = f"{datetime.now(KST).strftime('%Y-%m-%d__run-now__%H-%M-%S')}"
    proc = subprocess.run(
        [
            python_bin,
            str(RUN_NOW_SCRIPT),
            "--trigger-source",
            "run_now",
            "--run-id",
            run_id,
            "--force",
        ],
        cwd=str(PROJECT_ROOT),
        check=False,
        text=True,
        capture_output=True,
        timeout=60 * 60,
    )
    return {
        "success": proc.returncode == 0,
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "returncode": proc.returncode,
        "run_id": run_id,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


class AdminScheduleHandler(BaseHTTPRequestHandler):
    server_version = "TodayPickAdminSchedule/1.0"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _auth(self, body: dict[str, Any] | None = None) -> bool:
        password = self.headers.get("X-TodayPick-Admin-Password", "")
        if not password and body:
            password = str(body.get("password") or "")
        return configured_password_ok(password)

    def do_GET(self) -> None:
        if self.path != "/api/admin/daily-generation/schedule":
            self._send_json(404, {"success": False, "error": "not_found"})
            return
        if not self._auth():
            self._send_json(403, {"success": False, "error": "invalid_admin_password"})
            return
        config = read_config()
        payload: dict[str, Any] = {
            "success": True,
            "enabled": config.enabled,
            "time": config.time,
            "timezone": TIMEZONE_NAME,
            "revision": config.revision,
            "updated_at": config.updated_at,
            "updated_by": config.updated_by,
            "next_run_at": config.next_run_at,
            "timer": TIMER_NAME,
        }
        if os.name != "nt":
            payload["readback"] = systemd_readback()
        self._send_json(200, payload)

    def do_PUT(self) -> None:
        if self.path != "/api/admin/daily-generation/schedule":
            self._send_json(404, {"success": False, "error": "not_found"})
            return
        body = self._read_json()
        if not self._auth(body):
            self._send_json(403, {"success": False, "error": "invalid_admin_password"})
            return
        try:
            requested_time = validate_hhmm(str(body.get("time") or self.headers.get("X-TodayPick-Schedule-Time") or ""))
        except ValueError as exc:
            self._send_json(400, {"success": False, "error": "invalid_time", "message": str(exc)})
            return
        try:
            result = update_schedule(requested_time, apply_systemd=os.name != "nt")
        except Exception as exc:
            self._send_json(500, {"success": False, "error": "systemd_update_failed", "message": str(exc)})
            return
        self._send_json(200, {"success": True, **result})

    def do_POST(self) -> None:
        if self.path == "/api/admin/verify":
            body = self._read_json()
            if not self._auth(body):
                self._send_json(403, {"success": False, "error": "invalid_admin_password"})
                return
            self._send_json(200, {"success": True})
            return
        if self.path not in (
            "/api/admin/daily-generation/run-now",
            "/api/admin/daily-generation/restore-default",
        ):
            self._send_json(404, {"success": False, "error": "not_found"})
            return
        body = self._read_json()
        if not self._auth(body):
            self._send_json(403, {"success": False, "error": "invalid_admin_password"})
            return
        if self.path.endswith("/restore-default"):
            try:
                result = update_schedule(DEFAULT_TIME, apply_systemd=os.name != "nt")
            except Exception as exc:
                self._send_json(500, {"success": False, "error": "systemd_update_failed", "message": str(exc)})
                return
            self._send_json(200, {"success": True, **result})
            return
        self._send_json(200, run_daily_generation_now())


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the TodayPick admin schedule API.")
    parser.add_argument("--host", default=os.environ.get("TODAYPICK_ADMIN_API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("TODAYPICK_ADMIN_API_PORT", "8787")))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), AdminScheduleHandler)
    print(f"TodayPick admin schedule API listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
