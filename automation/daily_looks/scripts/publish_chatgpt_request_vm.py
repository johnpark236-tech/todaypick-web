#!/usr/bin/env python3
"""One-shot VM publisher. Executed ONLY by explicit GitHub Actions dispatch.
Reuses VM REGISTER+SQLite. Never starts watchers or creates Drive backups.
"""
import argparse
import hashlib
import io
import json
import os
import signal
import pathlib
import re
import sqlite3
import subprocess
import sys
import tempfile
import urllib.parse
from datetime import datetime, timezone

import google.auth
from google.auth.transport.requests import AuthorizedSession
from googleapiclient.discovery import build

ROOT = pathlib.Path("/opt/todaypick-web")
DB = ROOT / "automation/daily_looks/runtime/cloud_single_first/state.sqlite3"
ENGINE = ROOT / "automation/daily_looks/scripts/agent_image_tools.py"
BUCKET = "todaypick-daily-looks-363284724091"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly",
          "https://www.googleapis.com/auth/devstorage.read_write"]
ID_RE = re.compile(r"^[A-Za-z0-9_-]{15,128}$")


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def drive_json(service, file_id):
    raw = service.files().get_media(fileId=file_id).execute()
    require(len(raw) <= 1024 * 1024, "JSON file exceeds 1 MiB")
    return json.loads(raw)


def info(service, file_id):
    return service.files().get(fileId=file_id, fields="id,name,mimeType,parents,trashed").execute()


def verify_request(req, service):
    require(req.get("schema_version") == 1 and req.get("source") == "chatgpt", "bad schema/source")
    date, segment = req.get("date_folder"), req.get("segment")
    require(isinstance(date, str) and re.fullmatch(r"[0-9]{6}", date), "invalid date")
    require(isinstance(segment, str) and re.fullmatch(r"[fm]_(10|20|30|40|50|60)", segment), "invalid segment")
    require(req.get("expected_image_count") == 10, "expected_image_count != 10")
    for key in ("drive_folder_id", "manifest_file_id", "metadata_file_id"):
        require(isinstance(req.get(key), str) and ID_RE.fullmatch(req[key]), f"invalid {key}")
    folder = info(service, req["drive_folder_id"])
    require(folder["name"] == segment and not folder.get("trashed"), "wrong target folder")
    parent = info(service, folder["parents"][0])
    require(parent["name"] == date and not parent.get("trashed"), "wrong date folder")
    root = info(service, parent["parents"][0])
    require(root["name"] == "TodayPick_user_config", "wrong Drive root")
    meta_info = info(service, req["metadata_file_id"])
    manifest_info = info(service, req["manifest_file_id"])
    for item, name in ((meta_info, "metadata.json"), (manifest_info, "manifest.json")):
        require(item["name"] == name and req["drive_folder_id"] in item.get("parents", [])
                and not item.get("trashed"), f"wrong {name} placement")
    metadata_raw = service.files().get_media(fileId=req["metadata_file_id"]).execute()
    require(len(metadata_raw) <= 1024 * 1024, "metadata too large")
    meta = json.loads(metadata_raw)
    manifest = drive_json(service, req["manifest_file_id"])
    for obj in (meta, manifest):
        require(obj.get("request_id") == req["request_id"]
                and obj.get("date_folder") == date and obj.get("segment") == segment,
                "request/metadata/manifest mismatch")
    require(manifest.get("upload_complete") is True
            and manifest.get("expected_image_count") == 10, "upload incomplete")
    require(manifest.get("metadata_sha256") == hashlib.sha256(metadata_raw).hexdigest(),
            "metadata SHA256 mismatch")
    files = manifest.get("files")
    looks = meta.get("looks")
    require(isinstance(files, list) and len(files) == 10
            and isinstance(looks, list) and len(looks) == 10, "must contain exactly 10 images")
    listing = service.files().list(q=f"'{req['drive_folder_id']}' in parents and trashed = false",
                                   fields="nextPageToken,files(id,name,mimeType)", pageSize=100).execute()
    require(not listing.get("nextPageToken"), "folder exceeds 100 entries")
    img_listing = {f["id"]: f for f in listing.get("files", [])
                   if f.get("mimeType", "").startswith("image/")}
    require(len(img_listing) == 10, "Drive folder must contain precisely ten images")
    seen_names = set()
    expected = {}
    for index, (file, look) in enumerate(zip(files, looks), start=1):
        name = f"LOOK_{index:02d}.png"
        require(file.get("index") == index and look.get("index") == index
                and file.get("file_name") == name and look.get("source_file") == name,
                "image ordering/naming mismatch")
        sha = file.get("sha256")
        require(isinstance(sha, str) and re.fullmatch(r"[a-f0-9]{64}", sha)
                and sha == look.get("image_sha256"), "image sha metadata mismatch")
        file_id = file.get("drive_file_id")
        require(file_id in img_listing and img_listing[file_id]["name"] == name,
                "Drive file ID/name mismatch")
        raw = service.files().get_media(fileId=file_id).execute()
        require(hashlib.sha256(raw).hexdigest() == sha, f"Drive image hash mismatch {name}")
        require(look.get("gender") == ("female" if segment.startswith("f") else "male")
                and look.get("age_group") == int(segment.split("_")[1]), "demographic mismatch")
        items = look.get("items")
        require(isinstance(look.get("title"), str) and look["title"].strip()
                and isinstance(items, list) and items, f"missing outfit metadata {name}")
        require(all(isinstance(item.get("searchKeyword"), str)
                    and item["searchKeyword"].strip()
                    and item.get("price") == 0 for item in items),
                f"missing shopping metadata {name}")
        require(sha not in seen_names, "duplicate source SHA inside request")
        seen_names.add(sha)
        expected[index] = (sha, look)
    require(ENGINE.is_file() and DB.is_file(), "VM REGISTER engine/SQLite DB missing")
    # Legacy REGISTER --date scans ALL segments. No unrelated unprocessed group
    # with a complete input set may be admitted to this user-scoped request.
    date_children = service.files().list(q=f"'{parent['id']}' in parents and trashed = false",
                                         fields="nextPageToken,files(id,name,mimeType)", pageSize=100).execute()
    require(not date_children.get("nextPageToken"), "date folder too large to audit")
    with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as con:
        for other in date_children.get("files", []):
            if other["name"] == segment or not re.fullmatch(r"[fm]_(10|20|30|40|50|60)", other["name"]):
                continue
            siblings = service.files().list(
                q=f"'{other['id']}' in parents and trashed = false",
                fields="nextPageToken,files(mimeType)", pageSize=100).execute()
            require(not siblings.get("nextPageToken"), "sibling folder too large")
            count = sum(f.get("mimeType", "").startswith("image/") for f in siblings.get("files", []))
            if count >= 10:
                name = ("female" if other["name"].startswith("f") else "male") + "_" + other["name"].split("_")[1]
                row = con.execute("SELECT status FROM processed_sets WHERE date_folder=? AND segment=? ORDER BY processed_at DESC LIMIT 1",
                                  (date, name)).fetchone()
                require(row is not None and row[0] in ("COMPLETE", "NOOP_DUPLICATE"),
                        f"unprocessed sibling {other['name']} would be inadvertently registered")
    return expected


def gcs_read():
    obj = "production/autumn/female_50.json"
    proc = subprocess.run(["gcloud", "storage", "cat", f"gs://{BUCKET}/{obj}"],
                          capture_output=True, check=True, timeout=30, text=True)
    return obj, json.loads(proc.stdout)


def publish(req, expected, dry_run):
    require(req["date_folder"] == "260923" and req["segment"] == "f_50",
            "first release is restricted to reviewed 260923/f_50 request")
    obj, before = gcs_read()
    require(before.get("schema_version") == 2 and isinstance(before.get("looks"), list), "bad catalog")
    previous = {x["id"]: x for x in before["looks"]}
    ids = [f"autumn_female_50_260923_{n:02d}" for n in range(1, 11)]
    have = [id_ in previous for id_ in ids]
    require(not any(have) or all(have), "partially published set: fail closed")
    if all(have):
        for i, id_ in enumerate(ids, 1):
            require(previous[id_].get("sha256") == expected[i][0],
                    "existing ID conflicts with requested image")
        if all(previous[id_].get("items") and previous[id_].get("title") for id_ in ids):
            print("NOOP_ALREADY_PUBLISHED_WITH_METADATA")
            return
    if dry_run:
        print("PREFLIGHT_PASS_DRIVE_SHA_AND_METADATA; PUBLISH_DRY_RUN")
        return
    if not all(have):
        cmd = [sys.executable, str(ENGINE), "REGISTER", "--date", req["date_folder"], "--no-dry-run",
               "--drive-sync-mode", "best_effort_source_mapping"]
        require(os.getloadavg()[0] < 4.0, "VM load too high for REGISTER")
        proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            stdout, stderr = proc.communicate(timeout=420)
        except subprocess.TimeoutExpired:
            # Terminate only the subprocess group spawned by THIS request.
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate()
            raise RuntimeError("REGISTER timed out; its own subprocess group was terminated")
        print("REGISTER_EXIT_CODE", proc.returncode)
        print(stdout[-3000:])
        require(proc.returncode == 0, f"REGISTER failed: {stderr[-1000:]}")
    obj, now = gcs_read()
    seen = {look["id"]: look for look in now["looks"]}
    require(all(id_ in seen for id_ in ids), "REGISTER did not create all requested IDs")
    for i, id_ in enumerate(ids, 1):
        require(seen[id_].get("sha256") == expected[i][0], f"new image hash mismatch: {id_}")
    # Merge precisely the requested metadata, preserving existing catalog fields.
    for i, id_ in enumerate(ids, 1):
        look = expected[i][1]
        seen[id_]["title"] = look["title"]
        seen[id_]["items"] = look["items"]
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/devstorage.read_write"])
    http = AuthorizedSession(creds)
    endpoint = f"https://storage.googleapis.com/storage/v1/b/{BUCKET}/o/{urllib.parse.quote(obj, safe='')}"
    meta_resp = http.get(endpoint, timeout=20)
    meta_resp.raise_for_status()
    generation = meta_resp.json()["generation"]
    now["count"] = len(now["looks"])
    now["updated_at"] = datetime.now(timezone.utc).isoformat()
    serialized = json.dumps(now, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    upload = http.post(f"https://storage.googleapis.com/upload/storage/v1/b/{BUCKET}/o",
                       params={"uploadType": "media", "name": obj, "ifGenerationMatch": generation},
                       data=serialized, headers={"Content-Type": "application/json"}, timeout=30)
    upload.raise_for_status()
    _, readback = gcs_read()
    final = {look["id"]: look for look in readback["looks"]}
    require(len(final) == len(seen), "readback count changed unexpectedly")
    require(readback.get("count") == len(final), "readback count field mismatch")
    for i, id_ in enumerate(ids, 1):
        require(final[id_].get("sha256") == expected[i][0]
                and final[id_].get("items") == expected[i][1]["items"]
                and final[id_].get("title") == expected[i][1]["title"],
                f"readback metadata failed: {id_}")
    print("GCS_POSTED_WITH_METADATA_AND_READBACK_OK", len(final))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=pathlib.Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    req = json.loads(args.request.read_text(encoding="utf-8"))
    require(req.get("request_id") == "tp_260923_f50_chatgpt_01", "unreviewed request ID")
    creds, _ = google.auth.default(scopes=SCOPES)
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    expected = verify_request(req, drive)
    publish(req, expected, args.dry_run)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("PUBLISH_FAILED:", type(error).__name__, str(error)[:1000], file=sys.stderr)
        sys.exit(1)
