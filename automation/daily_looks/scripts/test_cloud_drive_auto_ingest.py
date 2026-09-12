import json
import sqlite3
import sys
from pathlib import Path

from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import cloud_drive_auto_ingest as cloud  # noqa: E402


class FakeDrive:
    def __init__(self, files=None):
        self.files = files or []
        self.downloads = 0
        self.moves = []
        self.folders = {"root/260912": "date-folder-id"}

    def find_child_folder(self, parent_id, name):
        return self.folders.get(f"{parent_id}/{name}") or self.folders.get(f"root/{name}")

    def ensure_child_folder(self, parent_id, name):
        folder_id = f"{parent_id}-{name}"
        self.folders[f"{parent_id}/{name}"] = folder_id
        return folder_id

    def list_source_files(self, date_folder_id):
        return list(self.files)

    def download_file(self, file_id, destination):
        self.downloads += 1
        source = next(item for item in self.files if item.id == file_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.payload)

    def move_file(self, file_id, old_parent_id, new_parent_id):
        self.moves.append((file_id, old_parent_id, new_parent_id))


class FakeDlq:
    def __init__(self):
        self.items = []

    def write(self, source_path, metadata, error):
        self.items.append((source_path, metadata, error))
        return f"gs://test-dlq/{metadata['date_folder']}/{metadata['segment']}/{metadata['sha256']}/"


def make_sheet(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1600, 1000), (240, 240, 235))
    colors = [
        (220, 120, 120),
        (120, 180, 220),
        (160, 210, 150),
        (230, 200, 120),
        (180, 150, 220),
        (120, 160, 180),
        (230, 160, 180),
        (170, 210, 210),
        (210, 170, 130),
        (170, 170, 170),
    ]
    w = 1600 // 5
    h = 1000 // 2
    for idx, color in enumerate(colors):
        row, col = divmod(idx, 5)
        for x in range(col * w + 20, (col + 1) * w - 20):
            for y in range(row * h + 20, (row + 1) * h - 20):
                if (x + y) % 7 == 0:
                    image.putpixel((x, y), color)
    image.save(path)
    return path.read_bytes()


def drive_file(payload, file_id="file-1", name="여성20대.png", md5="md5-a"):
    return cloud.DriveFile(
        id=file_id,
        name=name,
        mime_type="image/png",
        modified_time="2026-09-12T00:00:00.000Z",
        size=len(payload),
        md5_checksum=md5,
        parent_id="date-folder-id",
    )


def state_rows(db_path):
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    rows = [dict(row) for row in db.execute("SELECT * FROM sources ORDER BY updated_at")]
    db.close()
    return rows


def test_happy_path_and_repoll_skip(tmp_path, monkeypatch):
    payload = make_sheet(tmp_path / "source.png")
    file_meta = drive_file(payload)
    file_meta.payload = payload
    fake_drive = FakeDrive([file_meta])
    fake_dlq = FakeDlq()
    state = cloud.StateStore(tmp_path / "state.sqlite3")

    counts = {"before": 20, "after": 30}
    monkeypatch.setattr(cloud, "RUNTIME_ROOT", tmp_path / "runtime")
    monkeypatch.setattr(cloud, "get_segment_count", lambda season, segment: counts["before"])
    monkeypatch.setattr(cloud, "publish_segments_from_staging", lambda *args, **kwargs: {
        "segments": [{
            "segment": "female_20",
            "before": counts["before"],
            "after": counts["after"],
            "appended": 10,
            "skipped_duplicates": 0,
            "url": "https://example.test/female_20.json",
        }]
    })

    worker = cloud.CloudDriveIngestWorker(fake_drive, state, fake_dlq, "root", dry_run=False)
    first = worker.scan_once("260912")
    assert first["results"][0]["status"] == "COMPLETED"
    assert fake_drive.downloads == 1
    rows = state_rows(tmp_path / "state.sqlite3")
    assert any(row["status"] == "COMPLETED" and row["catalog_after"] == 30 for row in rows)
    assert fake_drive.moves

    second = worker.scan_once("260912")
    assert second["results"][0]["status"] == "SKIP_COMPLETED_METADATA"
    assert fake_drive.downloads == 1
    assert fake_dlq.items == []


def test_bad_source_goes_to_dlq_without_publish(tmp_path, monkeypatch):
    payload = b"not an image"
    file_meta = drive_file(payload, file_id="bad-1", name="남성30대.png", md5="md5-b")
    file_meta.payload = payload
    fake_drive = FakeDrive([file_meta])
    fake_dlq = FakeDlq()
    state = cloud.StateStore(tmp_path / "state.sqlite3")
    publish_calls = []

    monkeypatch.setattr(cloud, "RUNTIME_ROOT", tmp_path / "runtime")
    monkeypatch.setattr(cloud, "publish_segments_from_staging", lambda *args, **kwargs: publish_calls.append(args))
    monkeypatch.setattr(cloud, "notify_failure", lambda *args, **kwargs: "NOTIFIED")

    worker = cloud.CloudDriveIngestWorker(fake_drive, state, fake_dlq, "root", dry_run=False)
    result = worker.scan_once("260912")
    assert result["results"][0]["status"] == "DLQ"
    assert fake_dlq.items
    assert fake_dlq.items[0][1]["segment"] == "male_30"
    assert publish_calls == []
    rows = state_rows(tmp_path / "state.sqlite3")
    assert any(row["status"] == "DLQ" for row in rows)


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))
