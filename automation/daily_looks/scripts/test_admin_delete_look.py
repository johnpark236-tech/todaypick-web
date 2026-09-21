"""
TodayPick Admin Delete — T01-T14 테스트 스위트
운영 이미지/카탈로그/Drive/SQLite를 건드리지 않고 mock으로만 검증.
모든 delete_look() 호출은 state_db_path=<tmp> 와 drive=<mock> 을 명시적으로 전달.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import admin_delete_look as adl

# ── fake data ─────────────────────────────────────────────────────────────────

SEASON = "autumn"
SEGMENT = "female_10"
TARGET_LOOK_ID = "autumn_female_10_260921_08"
TARGET_SHA = hashlib.sha256(TARGET_LOOK_ID.encode()).hexdigest()
OTHER_LOOK_ID = "autumn_female_10_260921_01"
OTHER_SHA = hashlib.sha256(OTHER_LOOK_ID.encode()).hexdigest()
CATALOG_OBJECT = f"production/{SEASON}/{SEGMENT}.json"
FAKE_IMAGE = hashlib.sha256(b"fake_image").digest() * 4  # 128 bytes, deterministic


def _look(look_id: str, sha: str | None = None) -> dict:
    s = sha or hashlib.sha256(look_id.encode()).hexdigest()
    return {
        "id": look_id,
        "url": f"https://storage.googleapis.com/todaypick-daily-looks-363284724091/"
               f"production/assets/autumn/260921/female/10/look_{look_id[-2:]}_{s[:12]}.webp",
        "sha256": s,
        "width": 648,
        "height": 1152,
    }


TARGET_LOOK = _look(TARGET_LOOK_ID, TARGET_SHA)
OTHER_LOOK = _look(OTHER_LOOK_ID, OTHER_SHA)


def _catalog(looks: list[dict]) -> dict:
    gender, age = SEGMENT.split("_")
    return {
        "schema_version": 2,
        "season": SEASON,
        "gender": gender,
        "age_group": int(age),
        "segment": SEGMENT,
        "count": len(looks),
        "updated_at": "2026-09-21T12:00:00+09:00",
        "last_source_date": "260921",
        "looks": looks,
    }


INDEX = {
    "schema_version": 1,
    "segments": {SEASON: {SEGMENT: f"https://storage.googleapis.com/todaypick-daily-looks-363284724091/{CATALOG_OBJECT}"}},
    "updated_at": "2026-09-21T12:00:00+09:00",
}

# ── mock Drive clients ─────────────────────────────────────────────────────────

class MockDrive:
    """In-memory Drive that correctly roundtrips bytes."""

    def __init__(self):
        self._folders: dict[tuple, str] = {}
        self._files: dict[str, bytes] = {}
        self._n = 0

    def _id(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}_{self._n:04d}"

    def get_or_create_folder(self, parent_id: str, name: str) -> str:
        key = (parent_id, name)
        if key not in self._folders:
            self._folders[key] = self._id("folder")
        return self._folders[key]

    def upload_bytes(self, parent_id: str, name: str, data: bytes, mime_type: str) -> str:
        fid = self._id("file")
        self._files[fid] = data
        return fid

    def get_file_metadata(self, file_id: str) -> dict:
        return {"id": file_id, "size": str(len(self._files.get(file_id, b""))), "name": "?"}

    def read_bytes(self, file_id: str) -> bytes:
        return self._files[file_id]


class BrokenDrive(MockDrive):
    """Drive whose read_bytes always returns garbage → hash mismatch."""

    def read_bytes(self, file_id: str) -> bytes:
        return b"CORRUPTED"


# ── GCS patch context ─────────────────────────────────────────────────────────

class _GcsPatch:
    """
    Patches GCS-level I/O in admin_delete_look.
    Drive and state_db_path are passed explicitly to delete_look() — not patched here.
    """

    def __init__(self, catalog: dict, image_bytes: bytes = FAKE_IMAGE):
        self._catalog = catalog
        self._image_bytes = image_bytes
        self._patches: list = []
        self.uploaded: list[tuple[dict, str]] = []

    def _fake_read_gcs_json(self, obj: str) -> dict:
        if "index" in obj:
            return dict(INDEX)
        return self._catalog

    def _track_upload(self, data: dict, obj: str, *a, **kw) -> None:
        self.uploaded.append((data, obj))

    def __enter__(self) -> "_GcsPatch":
        self._patches = [
            patch.object(adl, "_object_exists", return_value=True),
            patch.object(adl, "_read_gcs_json", side_effect=self._fake_read_gcs_json),
            patch.object(adl, "_upload_gcs_json", side_effect=self._track_upload),
            patch.object(adl, "_run_gcloud", return_value=""),
            patch.object(adl, "_download_url_bytes", return_value=self._image_bytes),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *_):
        for p in reversed(self._patches):
            p.stop()

    def active_catalog_uploads(self) -> list[dict]:
        return [d for d, obj in self.uploaded if obj == CATALOG_OBJECT]

    def index_uploads(self) -> list[dict]:
        return [d for d, obj in self.uploaded if "index" in obj]


# ── request builder ───────────────────────────────────────────────────────────

def _req(look_id: str = TARGET_LOOK_ID, dry_run: bool = False) -> adl.AdminDeleteRequest:
    return adl.AdminDeleteRequest(
        season=SEASON,
        segment=SEGMENT,
        look_id=look_id,
        deleted_by="test_admin",
        dry_run=dry_run,
    )


def _delete(request: adl.AdminDeleteRequest,
            db: Path,
            drive: MockDrive | None = None) -> adl.AdminDeleteResult:
    """Call delete_look with explicit state_db_path and drive injection."""
    return adl.delete_look(request, state_db_path=db, drive=drive or MockDrive())


# ══════════════════════════════════════════════════════════════════════════════
# T01: 관리자 삭제 요청 정상 처리
# ══════════════════════════════════════════════════════════════════════════════
class T01_NormalDeleteFlow(unittest.TestCase):
    def test_delete_succeeds_and_all_flags_set(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog([TARGET_LOOK, OTHER_LOOK])):
                result = _delete(_req(), db)
        self.assertTrue(result.success, result.error)
        self.assertTrue(result.look_found)
        self.assertTrue(result.backup_hash_verified)
        self.assertTrue(result.tombstone_recorded)
        self.assertTrue(result.index_updated)
        self.assertEqual(result.look_id, TARGET_LOOK_ID)


# ══════════════════════════════════════════════════════════════════════════════
# T02: 삭제 대상 고유 식별 — 정확히 TARGET만 제거
# ══════════════════════════════════════════════════════════════════════════════
class T02_UniqueLookIdentification(unittest.TestCase):
    def test_only_target_removed_from_active_catalog(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog([TARGET_LOOK, OTHER_LOOK])) as gcs:
                _delete(_req(), db)
            final = gcs.active_catalog_uploads()
        self.assertTrue(final, "Active catalog must be uploaded")
        ids = [l["id"] for l in final[-1]["looks"]]
        self.assertNotIn(TARGET_LOOK_ID, ids)
        self.assertIn(OTHER_LOOK_ID, ids)


# ══════════════════════════════════════════════════════════════════════════════
# T03: Google Drive 백업 생성 확인
# ══════════════════════════════════════════════════════════════════════════════
class T03_DriveBackupCreated(unittest.TestCase):
    def test_drive_backup_folder_id_populated(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            drive = MockDrive()
            with _GcsPatch(_catalog([TARGET_LOOK])):
                result = _delete(_req(), db, drive)
        self.assertIsNotNone(result.drive_backup_folder_id)
        self.assertIn(adl.DELETED_BACKUP_FOLDER_NAME, result.drive_backup_path or "")

    def test_three_files_uploaded_to_drive(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            drive = MockDrive()
            with _GcsPatch(_catalog([TARGET_LOOK])):
                _delete(_req(), db, drive)
        # original.webp + deletion_record.json + restore_manifest.json = 3 files
        self.assertGreaterEqual(len(drive._files), 3)


# ══════════════════════════════════════════════════════════════════════════════
# T04: 원본 이미지 해시 검증
# ══════════════════════════════════════════════════════════════════════════════
class T04_HashVerification(unittest.TestCase):
    def test_backup_hash_verified_true(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog([TARGET_LOOK])):
                result = _delete(_req(), db)
        self.assertTrue(result.backup_hash_verified)

    def test_restore_manifest_contains_correct_sha256(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            drive = MockDrive()
            with _GcsPatch(_catalog([TARGET_LOOK])):
                _delete(_req(), db, drive)
        manifests = [
            json.loads(v)
            for v in drive._files.values()
            if isinstance(v, bytes) and v.strip().startswith(b"{") and b"restore_note" in v
        ]
        self.assertTrue(manifests, "restore_manifest.json not found in Drive")
        self.assertEqual(manifests[0]["sha256"], TARGET_SHA)


# ══════════════════════════════════════════════════════════════════════════════
# T05: 백업 실패 시 삭제 중단 — CRITICAL SAFETY TEST
# ══════════════════════════════════════════════════════════════════════════════
class T05_BackupFailureBlocksDeletion(unittest.TestCase):
    def test_broken_drive_hash_mismatch_blocks_catalog_modify(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            broken = BrokenDrive()
            with _GcsPatch(_catalog([TARGET_LOOK])) as gcs:
                result = _delete(_req(), db, broken)
            active_uploads = gcs.active_catalog_uploads()

        self.assertFalse(result.success, "Delete must fail on hash mismatch")
        self.assertFalse(result.backup_hash_verified)
        self.assertEqual(len(active_uploads), 0, "Active catalog must NOT be modified")

    def test_error_message_mentions_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            broken = BrokenDrive()
            with _GcsPatch(_catalog([TARGET_LOOK])):
                result = _delete(_req(), db, broken)
        self.assertIn("HASH", (result.error or "").upper())


# ══════════════════════════════════════════════════════════════════════════════
# T06: active catalog에서 이미지 제외
# ══════════════════════════════════════════════════════════════════════════════
class T06_RemovedFromActiveCatalog(unittest.TestCase):
    def test_catalog_count_decremented(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog([TARGET_LOOK, OTHER_LOOK])):
                result = _delete(_req(), db)
        self.assertEqual(result.catalog_before_count, 2)
        self.assertEqual(result.catalog_after_count, 1)

    def test_remove_look_util_correct(self):
        cat = _catalog([TARGET_LOOK, OTHER_LOOK])
        new_cat, removed = adl.remove_look_from_catalog(cat, TARGET_LOOK_ID)
        self.assertIsNotNone(removed)
        self.assertEqual(removed["id"], TARGET_LOOK_ID)
        ids = [l["id"] for l in new_cat["looks"]]
        self.assertNotIn(TARGET_LOOK_ID, ids)
        self.assertIn(OTHER_LOOK_ID, ids)
        self.assertEqual(new_cat["count"], 1)


# ══════════════════════════════════════════════════════════════════════════════
# T07: 1컷 보기에서 삭제 이미지 미노출
# ══════════════════════════════════════════════════════════════════════════════
class T07_SingleViewNotShown(unittest.TestCase):
    def test_look_absent_in_final_catalog(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog([TARGET_LOOK, OTHER_LOOK])) as gcs:
                _delete(_req(), db)
            finals = gcs.active_catalog_uploads()
        self.assertTrue(finals)
        ids = [l["id"] for l in finals[-1].get("looks", [])]
        self.assertNotIn(TARGET_LOOK_ID, ids)


# ══════════════════════════════════════════════════════════════════════════════
# T08: 10컷 보기에서 삭제 이미지 미노출
# ══════════════════════════════════════════════════════════════════════════════
class T08_TenCutViewNotShown(unittest.TestCase):
    def test_exactly_one_look_removed_from_ten(self):
        looks = [_look(f"autumn_female_10_260921_{i:02d}") for i in range(1, 11)]
        target = looks[7]

        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog(looks)) as gcs:
                req = adl.AdminDeleteRequest(SEASON, SEGMENT, target["id"], "test_admin")
                _delete(req, db)
            finals = gcs.active_catalog_uploads()

        ids = [l["id"] for l in finals[-1].get("looks", [])]
        self.assertNotIn(target["id"], ids)
        self.assertEqual(len(ids), 9)


# ══════════════════════════════════════════════════════════════════════════════
# T09: 더보기 세그먼트에서 삭제 이미지 미노출 (index.json 갱신)
# ══════════════════════════════════════════════════════════════════════════════
class T09_IndexUpdated(unittest.TestCase):
    def test_index_updated_flag_true(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog([TARGET_LOOK])):
                result = _delete(_req(), db)
        self.assertTrue(result.index_updated)

    def test_index_upload_happened(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog([TARGET_LOOK])) as gcs:
                _delete(_req(), db)
            self.assertTrue(gcs.index_uploads(), "index.json must be uploaded")


# ══════════════════════════════════════════════════════════════════════════════
# T10: 앱 재실행 후 삭제 상태 유지 — SQLite tombstone 영속성
# ══════════════════════════════════════════════════════════════════════════════
class T10_TombstonePersistsAcrossRestarts(unittest.TestCase):
    def test_tombstone_survives_db_reopen(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog([TARGET_LOOK])):
                result = _delete(_req(), db)
            self.assertTrue(result.tombstone_recorded)

            # Simulate restart: read DB fresh
            self.assertTrue(adl.is_look_tombstoned(TARGET_LOOK_ID, db))

            con = sqlite3.connect(str(db))
            row = con.execute(
                "SELECT sha256, deleted_by FROM deleted_looks WHERE look_id=?",
                (TARGET_LOOK_ID,)
            ).fetchone()
            con.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], TARGET_SHA)
        self.assertEqual(row[1], "test_admin")


# ══════════════════════════════════════════════════════════════════════════════
# T11: 삭제 이미지 자동 재등록 방지 — tombstone이 dedupe_append를 차단
# ══════════════════════════════════════════════════════════════════════════════
class T11_TombstoneBlocksReregistration(unittest.TestCase):
    def test_tombstoned_sha_blocked_in_dedupe_append(self):
        from append_seasonal_catalog_from_staging import dedupe_append
        merged, appended, skipped = dedupe_append(
            [], [TARGET_LOOK.copy()], frozenset([TARGET_SHA])
        )
        self.assertEqual(appended, 0)
        self.assertEqual(skipped, 1)
        self.assertEqual(len(merged), 0)

    def test_non_tombstoned_sha_allowed(self):
        from append_seasonal_catalog_from_staging import dedupe_append
        merged, appended, skipped = dedupe_append(
            [], [OTHER_LOOK.copy()], frozenset([TARGET_SHA])
        )
        self.assertEqual(appended, 1)
        self.assertEqual(skipped, 0)

    def test_post_delete_scan_cannot_reregister(self):
        """Delete → load tombstones → re-ingest attempt → must be blocked."""
        from append_seasonal_catalog_from_staging import dedupe_append

        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog([TARGET_LOOK])):
                result = _delete(_req(), db)
            self.assertTrue(result.tombstone_recorded)

            tombstoned = adl.load_deleted_sha256s(db)
            self.assertIn(TARGET_SHA, tombstoned)

            merged, appended, skipped = dedupe_append(
                [], [TARGET_LOOK.copy()], tombstoned
            )
        self.assertEqual(appended, 0, "Tombstoned look must not be re-registered")


# ══════════════════════════════════════════════════════════════════════════════
# T12: 기존 정상 SINGLE-FIRST 세트 보존
# ══════════════════════════════════════════════════════════════════════════════
class T12_ExistingLooksPreserved(unittest.TestCase):
    def test_nine_other_looks_intact_after_delete(self):
        looks = [_look(f"autumn_female_10_260921_{i:02d}") for i in range(1, 11)]
        target = looks[7]
        others = [l for l in looks if l["id"] != target["id"]]

        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog(looks)) as gcs:
                req = adl.AdminDeleteRequest(SEASON, SEGMENT, target["id"], "test_admin")
                _delete(req, db)
            finals = gcs.active_catalog_uploads()

        final_ids = {l["id"] for l in finals[-1].get("looks", [])}
        for other in others:
            self.assertIn(other["id"], final_ids, f"{other['id']} was incorrectly removed")
        self.assertNotIn(target["id"], final_ids)

    def test_catalog_snapshot_object_recorded(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog([TARGET_LOOK])):
                result = _delete(_req(), db)
        self.assertIsNotNone(result.catalog_snapshot_object)
        self.assertIn("deleted_snapshots", result.catalog_snapshot_object)


# ══════════════════════════════════════════════════════════════════════════════
# T13: 복구 메타데이터 저장 확인
# ══════════════════════════════════════════════════════════════════════════════
class T13_RestoreMetadataSaved(unittest.TestCase):
    def test_restore_manifest_required_fields(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            drive = MockDrive()
            with _GcsPatch(_catalog([TARGET_LOOK])):
                _delete(_req(), db, drive)

        manifests = [
            json.loads(v)
            for v in drive._files.values()
            if isinstance(v, bytes) and v.strip().startswith(b"{") and b"restore_note" in v
        ]
        self.assertTrue(manifests)
        m = manifests[0]
        for field in ("look_id", "season", "segment", "original_url", "sha256",
                      "catalog_snapshot", "deleted_at", "restore_note"):
            self.assertIn(field, m, f"Missing field in restore_manifest: {field}")
        self.assertEqual(m["look_id"], TARGET_LOOK_ID)
        self.assertEqual(m["sha256"], TARGET_SHA)

    def test_tombstone_row_has_backup_path_and_folder(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog([TARGET_LOOK])):
                _delete(_req(), db)
            con = sqlite3.connect(str(db))
            row = con.execute(
                "SELECT backup_drive_path, backup_drive_folder_id FROM deleted_looks WHERE look_id=?",
                (TARGET_LOOK_ID,)
            ).fetchone()
            con.close()

        self.assertIsNotNone(row)
        self.assertIsNotNone(row[0], "backup_drive_path must not be None")
        self.assertIsNotNone(row[1], "backup_drive_folder_id must not be None")


# ══════════════════════════════════════════════════════════════════════════════
# T14: 중복 삭제 요청 안전 처리
# ══════════════════════════════════════════════════════════════════════════════
class T14_DuplicateDeleteSafe(unittest.TestCase):
    def test_second_delete_blocked_gracefully(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog([TARGET_LOOK])):
                result1 = _delete(_req(), db)
            self.assertTrue(result1.success)

            # Second delete attempt — look no longer in catalog + already tombstoned
            with _GcsPatch(_catalog([])):
                result2 = _delete(_req(), db)

        self.assertFalse(result2.success, "Duplicate delete must not succeed")
        self.assertIsNotNone(result2.error)

    def test_duplicate_delete_does_not_corrupt_tombstone(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog([TARGET_LOOK])):
                _delete(_req(), db)
            with _GcsPatch(_catalog([])):
                _delete(_req(), db)

            # Tombstone row must still be exactly 1, not duplicated or deleted
            con = sqlite3.connect(str(db))
            count = con.execute(
                "SELECT COUNT(*) FROM deleted_looks WHERE look_id=?", (TARGET_LOOK_ID,)
            ).fetchone()[0]
            con.close()

        self.assertEqual(count, 1, "Tombstone row count must remain 1")


# ── utility unit tests ────────────────────────────────────────────────────────

class TUtil_RemoveLook(unittest.TestCase):
    def test_not_found_returns_original(self):
        cat = _catalog([OTHER_LOOK])
        new_cat, removed = adl.remove_look_from_catalog(cat, TARGET_LOOK_ID)
        self.assertIsNone(removed)
        self.assertEqual(len(new_cat["looks"]), 1)

    def test_empty_catalog(self):
        cat = _catalog([])
        new_cat, removed = adl.remove_look_from_catalog(cat, TARGET_LOOK_ID)
        self.assertIsNone(removed)


class TUtil_IsTombstoned(unittest.TestCase):
    def test_false_when_db_missing(self):
        self.assertFalse(adl.is_look_tombstoned("any", Path("/nonexistent/state.sqlite3")))

    def test_true_after_delete(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "state.sqlite3"
            with _GcsPatch(_catalog([TARGET_LOOK])):
                _delete(_req(), db)
            self.assertTrue(adl.is_look_tombstoned(TARGET_LOOK_ID, db))
            self.assertFalse(adl.is_look_tombstoned("nonexistent_id", db))


if __name__ == "__main__":
    unittest.main(verbosity=2)
