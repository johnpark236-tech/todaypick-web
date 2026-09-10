import argparse
import hashlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = PROJECT_ROOT / "automation" / "daily_looks" / "config" / "remote_daily_looks.json"
FILENAME_RE = re.compile(r"^(여성|남성)\s*(10|20|30|40|50|60)대\.(png|jpg|jpeg|webp)$", re.IGNORECASE)
KST = timezone(timedelta(hours=9))
LOCAL_URL_RE = re.compile(r"^(?:[a-zA-Z]:[\\/]|file:|\\.\\.?[\\/]|/|http://(?:localhost|127\\.0\\.0\\.1)(?::\\d+)?(?:/|$))")
GCLOUD_BIN = shutil.which("gcloud") or shutil.which("gcloud.cmd") or "gcloud"


@dataclass
class SourceImage:
    path: Path
    gender: str
    age: int
    segment: str
    filename: str
    size: int
    mtime: float
    sha256: str


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def resolve_project_path(value):
    p = Path(value)
    if p.is_absolute():
        return p
    return PROJECT_ROOT / p


def today_yymmdd(date_arg=None):
    if date_arg:
        return date_arg
    return datetime.now(KST).strftime("%y%m%d")


def now_iso():
    return datetime.now(KST).isoformat(timespec="seconds")


def segment_from_match(match):
    gender = "female" if match.group(1) == "여성" else "male"
    age = int(match.group(2))
    return gender, age, f"{gender}_{age}"


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_ledger(path):
    if not path.exists():
        return {"schema_version": 1, "sources": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_ledger(path, ledger):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")


def is_file_stable(path, checks, interval):
    last = None
    for _ in range(checks):
        stat = path.stat()
        cur = (stat.st_size, stat.st_mtime_ns)
        if last is not None and cur != last:
            return False
        last = cur
        if interval > 0:
            time.sleep(interval)
    return True


def discover_sources(source_root, date_folder, cfg):
    folder = source_root / date_folder
    found = []
    if not folder.exists():
        return folder, found, "NO_DAILY_FOLDER"
    if not folder.is_dir():
        return folder, found, "TODAY_PATH_NOT_DIRECTORY"

    for path in sorted(folder.iterdir(), key=lambda p: p.name):
        if not path.is_file():
            continue
        match = FILENAME_RE.match(path.name)
        if not match:
            continue
        gender, age, segment = segment_from_match(match)
        if segment not in cfg["supported_segments"]:
            continue
        if not is_file_stable(path, cfg["file_stable_checks"], cfg["file_stable_interval_seconds"]):
            continue
        stat = path.stat()
        found.append(SourceImage(
            path=path,
            gender=gender,
            age=age,
            segment=segment,
            filename=path.name,
            size=stat.st_size,
            mtime=stat.st_mtime,
            sha256=sha256_file(path),
        ))
    return folder, found, "OK"


def validate_source(path, cfg):
    if not path.exists() or path.stat().st_size < 1024:
        return False, "file missing or too small", None
    mime, _ = mimetypes.guess_type(path.name)
    if mime not in {"image/png", "image/jpeg", "image/webp"}:
        return False, f"unsupported MIME guess: {mime}", None
    try:
        with Image.open(path) as im:
            im.verify()
        im = Image.open(path).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        return False, f"image decode failed: {exc}", None

    width, height = im.size
    if width < 1000 or height < 600:
        return False, f"image too small: {width}x{height}", None
    ratio = width / float(height)
    if not (1.35 <= ratio <= 1.85):
        return False, f"not a 2x5 atlas-like aspect ratio: {width}x{height}", None
    if cfg["expected_rows"] != 2 or cfg["expected_columns"] != 5:
        return False, "unsupported grid config", None
    return True, "PASS", im


def crop_source_image(im, out_dir, source, date_folder, cfg):
    out_dir.mkdir(parents=True, exist_ok=True)
    width, height = im.size
    cell_w = width / cfg["expected_columns"]
    cell_h = height / cfg["expected_rows"]
    target_ratio = cfg["cut_width"] / float(cfg["cut_height"])
    inset = cfg["crop_inset_ratio"]
    cut_files = []
    validations = []

    for idx in range(cfg["expected_rows"] * cfg["expected_columns"]):
        row = idx // cfg["expected_columns"]
        col = idx % cfg["expected_columns"]
        left = round(col * cell_w + cell_w * inset["left"])
        top = round(row * cell_h + cell_h * inset["top"])
        right = round((col + 1) * cell_w - cell_w * inset["right"])
        bottom = round((row + 1) * cell_h - cell_h * inset["bottom"])
        cell = im.crop((left, top, right, bottom))
        cw, ch = cell.size
        current_ratio = cw / float(ch)

        if current_ratio > target_ratio:
            new_w = round(ch * target_ratio)
            x0 = max(0, (cw - new_w) // 2)
            cell = cell.crop((x0, 0, x0 + new_w, ch))
        else:
            new_h = round(cw / target_ratio)
            y0 = max(0, (ch - new_h) // 2)
            cell = cell.crop((0, y0, cw, y0 + new_h))

        cut = cell.resize((cfg["cut_width"], cfg["cut_height"]), Image.Resampling.LANCZOS)
        tmp_path = out_dir / f"look_{idx + 1:02d}.webp"
        cut.save(tmp_path, "WEBP", quality=cfg["webp_quality"], method=6)
        file_sha = sha256_file(tmp_path)
        filename = f"look_{idx + 1:02d}_{file_sha[:12]}.webp"
        out_path = out_dir / filename
        if out_path.exists():
            out_path.unlink()
        tmp_path.rename(out_path)

        ok, reason = validate_cut(out_path, cfg)
        validations.append({"index": idx + 1, "status": "PASS" if ok else "FAIL", "reason": reason})
        cut_files.append({
            "index": idx + 1,
            "path": str(out_path),
            "filename": filename,
            "sha256": file_sha,
            "id": f"{source.segment}_{date_folder}_{idx + 1:02d}",
        })

    return all(v["status"] == "PASS" for v in validations), cut_files, validations


def validate_cut(path, cfg):
    try:
        with Image.open(path) as im:
            width, height = im.size
            im.verify()
    except Exception as exc:
        return False, f"decode failed: {exc}"
    if width != cfg["cut_width"] or height != cfg["cut_height"]:
        return False, f"wrong size: {width}x{height}"
    if path.stat().st_size < 10 * 1024:
        return False, "output too small"
    return True, "PASS"


def build_review_sheet(segment, date_folder, cut_files, review_root, cfg):
    review_dir = review_root / date_folder
    review_dir.mkdir(parents=True, exist_ok=True)
    thumb_w = 216
    thumb_h = 384
    pad = 18
    label_h = 34
    sheet = Image.new("RGB", (pad * 6 + thumb_w * 5, pad * 3 + (thumb_h + label_h) * 2), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        font = ImageFont.load_default()

    for item in cut_files:
        idx = item["index"] - 1
        row = idx // 5
        col = idx % 5
        x = pad + col * (thumb_w + pad)
        y = pad + row * (thumb_h + label_h + pad)
        im = Image.open(item["path"]).convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        sheet.paste(im, (x, y + label_h))
        draw.text((x, y), f"{item['index']:02d}", fill=(35, 35, 35), font=font)

    out = review_dir / f"{date_folder}_{segment}_review.jpg"
    sheet.save(out, "JPEG", quality=92)
    return out


def load_manifest(path):
    if not path.exists():
        return {
            "schema_version": 1,
            "published_at": None,
            "content_version": None,
            "segments": {},
            "previous_manifest": None,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def validate_public_asset_url(url):
    if not isinstance(url, str) or not url:
        return False
    if LOCAL_URL_RE.match(url):
        return False
    if not url.startswith("https://"):
        return False
    return True


def build_public_asset_url(remote_base_url, date_folder, source, item):
    url = f"{remote_base_url.rstrip('/')}/{date_folder}/{source.gender}/{source.age}/look_{item['index']:02d}_{item['sha256'][:12]}.webp"
    if not validate_public_asset_url(url):
        raise ValueError(f"invalid production asset URL: {url}")
    return url


def validate_complete_manifest(manifest, require_public_urls=False):
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return False, "invalid schema_version"
    segments = manifest.get("segments")
    if not isinstance(segments, dict):
        return False, "segments must be an object"
    for segment, entry in segments.items():
        if not re.match(r"^(female|male)_(10|20|30|40|50|60)$", segment):
            return False, f"invalid segment: {segment}"
        looks = entry.get("looks")
        if not isinstance(looks, list) or len(looks) != 10:
            return False, f"{segment} must have exactly 10 looks"
        for look in looks:
            if len(look.get("sha256", "")) != 64:
                return False, f"{segment} has invalid sha256"
            url = look.get("url")
            if require_public_urls and not validate_public_asset_url(url):
                return False, f"{segment} has non-public URL"
            if url is not None and not validate_public_asset_url(url):
                return False, f"{segment} has unsafe URL"
    return True, "PASS"


def build_manifest(base_manifest, processed, date_folder, remote_base_url, dry_run):
    manifest = dict(base_manifest)
    manifest["schema_version"] = 1
    manifest["published_at"] = now_iso()
    manifest["content_version"] = f"{date_folder}_{int(time.time())}"
    manifest["segments"] = dict(base_manifest.get("segments", {}))

    for source, cut_files in processed:
        looks = []
        for item in cut_files:
            url = None if dry_run else item.get("url") or build_public_asset_url(remote_base_url, date_folder, source, item)
            looks.append({
                "id": item["id"],
                "url": url,
                "staging_path": item["path"] if dry_run else None,
                "sha256": item["sha256"],
                "width": 648,
                "height": 1152,
            })
        manifest["segments"][source.segment] = {
            "source_date": date_folder,
            "source_file": source.filename,
            "source_sha256": source.sha256,
            "count": len(looks),
            "looks": looks,
        }
    return manifest


class FileSystemPublisher:
    def __init__(self, root, public_base_url, fail_upload=False, fail_url_validation=False, fail_manifest_validation=False, fail_switch=False):
        self.root = Path(root)
        self.public_base_url = public_base_url
        self.fail_upload = fail_upload
        self.fail_url_validation = fail_url_validation
        self.fail_manifest_validation = fail_manifest_validation
        self.fail_switch = fail_switch

    def read_current_latest(self):
        latest = self.root / "latest.json"
        return load_manifest(latest)

    def upload_asset(self, source_path, date_folder, source, item):
        if self.fail_upload:
            raise RuntimeError("mock upload failure")
        dest_dir = self.root / "assets" / date_folder / source.gender / str(source.age)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / Path(item["filename"]).name
        shutil.copy2(source_path, dest)
        url = build_public_asset_url(self.public_base_url, date_folder, source, item)
        return {"url": url, "path": str(dest)}

    def validate_asset_url(self, url):
        if self.fail_url_validation:
            return False
        return validate_public_asset_url(url)

    def write_versioned_manifest(self, content_version, manifest):
        if self.fail_manifest_validation:
            raise RuntimeError("mock manifest validation failure")
        ok, reason = validate_complete_manifest(manifest, require_public_urls=True)
        if not ok:
            raise RuntimeError(reason)
        manifest_dir = self.root / "manifests"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        path = manifest_dir / f"{content_version}.json"
        write_json(path, manifest)
        return path

    def switch_latest(self, manifest_path):
        if self.fail_switch:
            raise RuntimeError("mock latest switch failure")
        latest = self.root / "latest.json"
        previous = self.root / "previous.json"
        if latest.exists():
            shutil.copy2(latest, previous)
        tmp = self.root / "latest.tmp"
        shutil.copy2(manifest_path, tmp)
        os.replace(tmp, latest)

    def rollback_latest(self):
        previous = self.root / "previous.json"
        latest = self.root / "latest.json"
        if not previous.exists():
            return False
        tmp = self.root / "latest.rollback.tmp"
        shutil.copy2(previous, tmp)
        os.replace(tmp, latest)
        return True


class GcsPublisher:
    ASSET_CACHE_CONTROL = "public, max-age=31536000, immutable"
    LATEST_CACHE_CONTROL = "no-cache"
    MANIFEST_CACHE_CONTROL = "public, max-age=300"

    def __init__(self, bucket, project, prefix="staging"):
        self.bucket = bucket
        self.project = project
        self.prefix = prefix.strip("/")
        self.public_base_url = f"https://storage.googleapis.com/{bucket}/{self.prefix}/assets"
        self.latest_object = f"{self.prefix}/latest.json"
        self.previous_object = f"{self.prefix}/previous.json"
        self._object_cache = None

    def _run_gcloud(self, args):
        cmd = [GCLOUD_BIN, *args, "--project", self.project, "--quiet"]
        result = subprocess.run(cmd, text=True, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gcloud command failed")
        return result.stdout

    def _storage_url(self, object_name):
        return f"gs://{self.bucket}/{object_name}"

    def _public_url(self, object_name):
        return f"https://storage.googleapis.com/{self.bucket}/{object_name}"

    def _load_object_cache(self):
        result = subprocess.run(
            [GCLOUD_BIN, "storage", "ls", "--recursive", f"gs://{self.bucket}/{self.prefix}/", "--project", self.project, "--quiet"],
            text=True,
            capture_output=True,
        )
        if result.returncode != 0 and "One or more URLs matched no objects" not in result.stderr:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gcloud storage ls failed")
        prefix = f"gs://{self.bucket}/"
        objects = set()
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith(prefix) and not line.endswith(":"):
                objects.add(line[len(prefix):])
        self._object_cache = objects

    def _object_exists(self, object_name):
        if self._object_cache is None:
            self._load_object_cache()
        if object_name in self._object_cache:
            return True
        result = subprocess.run(
            [GCLOUD_BIN, "storage", "objects", "describe", self._storage_url(object_name), "--project", self.project, "--format=json", "--quiet"],
            text=True,
            capture_output=True,
        )
        exists = result.returncode == 0
        if exists:
            self._object_cache.add(object_name)
        return exists

    def read_current_latest(self):
        if not self._object_exists(self.latest_object):
            return load_manifest(Path("__missing_latest__.json"))
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "latest.json"
            self._run_gcloud(["storage", "cp", self._storage_url(self.latest_object), str(out)])
            return json.loads(out.read_text(encoding="utf-8"))

    def upload_asset(self, source_path, date_folder, source, item):
        object_name = f"{self.prefix}/assets/{source.gender}/{source.age}/{date_folder}/{Path(item['filename']).name}"
        if not self._object_exists(object_name):
            self._run_gcloud([
                "storage",
                "cp",
                "--content-type=image/webp",
                f"--cache-control={self.ASSET_CACHE_CONTROL}",
                str(source_path),
                self._storage_url(object_name),
            ])
            if self._object_cache is not None:
                self._object_cache.add(object_name)
        return {"url": self._public_url(object_name), "path": self._storage_url(object_name)}

    def validate_asset_url(self, url):
        if not validate_public_asset_url(url):
            return False
        try:
            request = Request(url, method="GET")
            with urlopen(request, timeout=20) as response:
                content_type = response.headers.get("Content-Type", "").split(";")[0].lower()
                length = response.headers.get("Content-Length")
                body = response.read(1)
                return response.status == 200 and content_type == "image/webp" and (body or (length and int(length) > 0))
        except (HTTPError, URLError, TimeoutError, ValueError):
            return False

    def write_versioned_manifest(self, content_version, manifest):
        ok, reason = validate_complete_manifest(manifest, require_public_urls=True)
        if not ok:
            raise RuntimeError(reason)
        object_name = f"{self.prefix}/manifests/{content_version}.json"
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / f"{content_version}.json"
            write_json(path, manifest)
            self._run_gcloud([
                "storage",
                "cp",
                "--content-type=application/json",
                f"--cache-control={self.MANIFEST_CACHE_CONTROL}",
                str(path),
                self._storage_url(object_name),
            ])
        if self._object_cache is not None:
            self._object_cache.add(object_name)
        return object_name

    def switch_latest(self, manifest_path):
        if self._object_exists(self.latest_object):
            self._run_gcloud(["storage", "cp", self._storage_url(self.latest_object), self._storage_url(self.previous_object)])
            self._object_cache.add(self.previous_object)
        self._run_gcloud([
            "storage",
            "cp",
            "--content-type=application/json",
            f"--cache-control={self.LATEST_CACHE_CONTROL}",
            self._storage_url(manifest_path),
            self._storage_url(self.latest_object),
        ])
        self._object_cache.add(self.latest_object)

    def rollback_latest(self):
        if not self._object_exists(self.previous_object):
            return False
        self._run_gcloud([
            "storage",
            "cp",
            "--content-type=application/json",
            f"--cache-control={self.LATEST_CACHE_CONTROL}",
            self._storage_url(self.previous_object),
            self._storage_url(self.latest_object),
        ])
        self._object_cache.add(self.latest_object)
        return True


def atomic_publish_segments(processed, date_folder, publisher):
    base_manifest = publisher.read_current_latest()
    uploaded = []
    for source, cut_files in processed:
        if len(cut_files) != 10:
            raise RuntimeError(f"{source.segment} does not have 10 assets")
        segment_uploads = []
        for item in cut_files:
            upload = publisher.upload_asset(item["path"], date_folder, source, item)
            if not publisher.validate_asset_url(upload["url"]):
                raise RuntimeError(f"URL validation failed: {upload['url']}")
            segment_uploads.append({**item, "url": upload["url"]})
        uploaded.append((source, segment_uploads))

    manifest = build_manifest(base_manifest, uploaded, date_folder, publisher.public_base_url, dry_run=False)
    ok, reason = validate_complete_manifest(manifest, require_public_urls=True)
    if not ok:
        raise RuntimeError(reason)
    manifest_path = publisher.write_versioned_manifest(manifest["content_version"], manifest)
    publisher.switch_latest(manifest_path)
    return manifest


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run(args):
    cfg = load_config()
    date_folder = today_yymmdd(args.date)
    source_root = Path(args.source_root or cfg["source_root"])
    state_path = resolve_project_path(cfg["state_path"])
    staging_root = resolve_project_path(cfg["staging_root"])
    review_root = resolve_project_path(cfg["review_root"])
    manifest_root = resolve_project_path(cfg["manifest_root"])
    manifest_latest = manifest_root / "latest.json"
    manifest_previous = manifest_root / "previous.json"
    manifest_preview = manifest_root / f"{date_folder}_preview.json"
    report_path = manifest_root / f"{date_folder}_dry_run_report.json"
    remote_base_url = args.remote_asset_base_url if args.remote_asset_base_url is not None else cfg["remote_asset_base_url"]

    folder, discovered, discovery_status = discover_sources(source_root, date_folder, cfg)
    ledger = load_ledger(state_path)
    processed = []
    skipped = []
    failed = []
    review_sheets = []

    for source in discovered:
        ledger_key = f"{date_folder}/{source.segment}/{source.filename}"
        previous = ledger["sources"].get(ledger_key)
        previously_done = previous and previous.get("sha256") == source.sha256 and previous.get("status") == "PUBLISHED"
        previously_dry_run = args.dry_run and previous and previous.get("sha256") == source.sha256 and previous.get("status") == "VALIDATED"
        if not args.force and (previously_done or previously_dry_run):
            skipped.append({"source_file": source.filename, "segment": source.segment, "reason": "SKIP_ALREADY_PUBLISHED"})
            continue

        ledger["sources"][ledger_key] = {
            "status": "PROCESSING",
            "source_path": str(source.path),
            "file_size": source.size,
            "modified_time": source.mtime,
            "sha256": source.sha256,
            "updated_at": now_iso(),
        }

        ok, reason, im = validate_source(source.path, cfg)
        if not ok:
            ledger["sources"][ledger_key]["status"] = "FAILED"
            ledger["sources"][ledger_key]["reason"] = reason
            failed.append({"source_file": source.filename, "segment": source.segment, "reason": reason})
            continue

        out_dir = staging_root / date_folder / source.gender / str(source.age)
        crop_ok, cut_files, validations = crop_source_image(im, out_dir, source, date_folder, cfg)
        if not crop_ok or len(cut_files) != 10:
            ledger["sources"][ledger_key]["status"] = "FAILED"
            ledger["sources"][ledger_key]["reason"] = "crop validation failed"
            failed.append({"source_file": source.filename, "segment": source.segment, "reason": "crop validation failed", "validations": validations})
            continue

        review_sheets.append(str(build_review_sheet(source.segment, date_folder, cut_files, review_root, cfg)))
        ledger["sources"][ledger_key]["status"] = "VALIDATED"
        ledger["sources"][ledger_key]["cuts"] = [{"index": c["index"], "sha256": c["sha256"], "path": c["path"]} for c in cut_files]
        processed.append((source, cut_files))

    base_manifest = load_manifest(manifest_preview if args.dry_run and manifest_preview.exists() else manifest_latest)
    production_manifest_blocked = False
    production_manifest_block_reason = ""
    if not args.dry_run and not validate_public_asset_url(f"{remote_base_url.rstrip('/')}/probe.webp"):
        production_manifest_blocked = True
        production_manifest_block_reason = "remote_asset_base_url must be a valid https public URL"
        manifest = base_manifest
    else:
        manifest = build_manifest(base_manifest, processed, date_folder, remote_base_url, args.dry_run)
    if args.dry_run or not production_manifest_blocked:
        write_json(manifest_preview, manifest)

    production_changed = False
    manifest_url = ""
    if args.publish_local and not args.dry_run and not production_manifest_blocked:
        if manifest_latest.exists():
            shutil.copy2(manifest_latest, manifest_previous)
            manifest["previous_manifest"] = "previous.json"
        write_json(manifest_latest, manifest)
        production_changed = True
        manifest_url = str(manifest_latest)
        for source, _ in processed:
            ledger_key = f"{date_folder}/{source.segment}/{source.filename}"
            ledger["sources"][ledger_key]["status"] = "PUBLISHED"

    save_ledger(state_path, ledger)

    report = {
        "DATE": date_folder,
        "TIMEZONE": cfg["timezone"],
        "SOURCE_FOLDER": str(folder),
        "DATE_FOLDER_DETECTION": discovery_status,
        "DISCOVERED_FILES": len(discovered),
        "PROCESSED_FILES": len(processed),
        "SKIPPED_FILES": skipped,
        "FAILED_FILES": failed,
        "PUBLISHED_SEGMENTS": [source.segment for source, _ in processed] if production_changed else [],
        "UNCHANGED_SEGMENTS": [s for s in cfg["supported_segments"] if s not in [source.segment for source, _ in processed]],
        "EXPECTED_ROWS": cfg["expected_rows"],
        "EXPECTED_COLUMNS": cfg["expected_columns"],
        "EXPECTED_CUT_COUNT": cfg["expected_rows"] * cfg["expected_columns"],
        "CUT_LOOKS": sum(len(cuts) for _, cuts in processed),
        "OUTPUT_FORMAT": cfg["output_format"],
        "MANIFEST_PREVIEW": str(manifest_preview),
        "MANIFEST_URL": manifest_url,
        "REVIEW_SHEETS": review_sheets,
        "PRODUCTION_CONTENT_CHANGED": production_changed,
        "PRODUCTION_MANIFEST_RESULT": "DRY_RUN_ONLY" if args.dry_run else ("BLOCKED" if production_manifest_blocked else "READY"),
        "PRODUCTION_MANIFEST_BLOCK_REASON": production_manifest_block_reason,
    }
    write_json(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failed else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TodayPick remote daily look sheet ingest pipeline")
    parser.add_argument("--date", help="YYMMDD date folder. Defaults to Asia/Seoul today.")
    parser.add_argument("--source-root", help="Google Drive synced TodayPick_user_config path.")
    parser.add_argument("--remote-asset-base-url", default=None, help="Production asset base URL for non-dry-run manifests.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Read, crop, validate, and write preview only.")
    parser.add_argument("--live", dest="dry_run", action="store_false", help="Allow local manifest publish when --publish-local is set.")
    parser.add_argument("--publish-local", action="store_true", help="Promote preview to local latest.json. Does not upload remote assets.")
    parser.add_argument("--force", action="store_true", help="Reprocess matching source hashes instead of using the ledger skip.")
    sys.exit(run(parser.parse_args()))
