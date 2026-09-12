# TodayPick Cloud Ingest Architecture

## Objective

TodayPick daily look ingestion is cloud-primary. A user uploads 2x5 source sheets into Google Drive under `TodayPick_user_config/YYMMDD`, and one cloud worker ingests each source independently. Windows is standby only and must not poll during normal operation.

## Selected Executor

The audited GCP project has an existing always-on Compute Engine VM named `tt-orchestra` in project `my-youtube-automation-497504`. The VM is running and has a service account with `cloud-platform` and `drive` scopes. No TodayPick Redis, PostgreSQL, FastAPI backend, Cloud Run Job, or TodayPick-specific queue was verified in this repo, so V2 uses the existing VM with a single Python worker and SQLite state.

## Flow

1. Cloud worker starts through systemd.
2. It computes the current KST `YYMMDD` folder, unless `--date` is provided for manual backfill.
3. It queries Google Drive API using root folder id `1WvKlV8B3xM9X21vl_47Oh6dTfBDFVUPd`.
4. It lists only direct children of the date folder and ignores `_Processed` and `_Failed` because they are folders.
5. It filters supported filenames: `여성10대` through `여성60대`, `남성10대` through `남성60대`, plus English `female_10` and `male_10` forms.
6. It checks SQLite state to skip completed metadata before downloading.
7. It downloads only candidate files, calculates SHA256, validates the source against MASTER v3 canonical geometry, crops 10 WEBP files using the production crop engine, and runs crop QA.
8. It uploads immutable assets to GCS, appends to the seasonal leaf catalog, and updates `production/index.json`.
9. It commits state as `COMPLETED`.
10. It moves the Drive source to `_Processed` when Drive write permission supports it. If move fails, state remains the source of truth.

## State Machine

`DISCOVERED -> DOWNLOADED -> VALIDATING -> PROCESSING -> QA_PASSED -> PUBLISHING -> COMPLETED`

Failure states:

`QA_FAILED`, `DOWNLOAD_FAILED`, `PUBLISH_FAILED`, `DLQ`

The implementation records the required fields in SQLite:

`drive_file_id`, `drive_parent_folder_id`, `date_folder`, `filename`, `mime_type`, `modified_time`, `source_sha256`, `season`, `segment`, `status`, `attempt_count`, timestamps, error details, and catalog before/after counts.

## State Store And Lock

State store: SQLite at `automation/daily_looks/runtime/cloud_drive_ingest/state.sqlite3`.

Lock backend: OS-level single-instance lock file at `automation/daily_looks/runtime/cloud_drive_ingest/worker.lock`.

Redis and PostgreSQL were not verified as TodayPick-owned infrastructure. They are not introduced for this volume. If multi-worker ingestion is needed later, replace `StateStore` with a DB-backed implementation and add a distributed lock.

## Idempotency

The pipeline has three layers:

1. Source identity: `drive_file_id + source_sha256`.
2. Look ID format: `{season}_{gender}_{age}_{YYMMDD}_{index}`.
3. Catalog dedup: existing `look.id` or `sha256` prevents duplicate append.

Drive move is organizational only. It is never the idempotency mechanism.

## DLQ

Cloud DLQ path:

`gs://todaypick-daily-looks-363284724091/automation/dlq/YYMMDD/segment/source_sha/`

Each DLQ entry contains:

`source.<ext>`, `metadata.json`, `error.json`

DLQ candidates include decode failure, invalid grid, crop failure, crop QA failure, WEBP validation failure, catalog validation failure, and unrecoverable Drive errors. Transient errors retry up to 3 attempts before DLQ.

## Production Safety

The worker never deletes existing GCS assets or Drive sources. Seasonal catalogs are cumulative append only. Existing looks stay first; new looks append after them. The app reads remote schema v2 catalogs, so no AAB or Google Play upload is required for catalog updates.

## Canonical Image/Cut Standard V3

New Google Drive source sheets must use `canonical_v3`.

`MASTER_GUIDE_NAME=TodayPick_2x5_10컷_이미지생성_커팅_지침서_MASTER_v3`

`MASTER_GUIDE_VERSION=v3`

Canonical source geometry:

`1313x1198`, `5x2`, logical cell `262.6x599`.

Canonical crop behavior:

- `second_row_top_overlap_ratio=0.0`
- no cross-row crop
- reject internal white separators wider than `4px`
- trim `2px` from internal canonical grid boundaries before final aspect crop to keep visible borders out of app previews
- top row excess trim bias `35:65`
- bottom row excess trim bias `65:35`
- production output size remains the current config value `648x1152`
- if target aspect fitting would crop the full body, use contain mode and fill the left/right/top/bottom empty areas with an enlarged blurred copy of the same cut
- row 1 and row 2 must have similar character scale, head clearance, and foot clearance
- row 1 bottom border artifacts and row 2 top-heavy placement are publish blockers
- generation-time correction is preferred; moving the row split upward by about `8-12px` is an exception fallback only
- visible white vertical panel separators around `8px` in ChatGPT browser generated sheets are publish blockers; regenerate with explicit no-border instructions

Generation quality requirements:

- every panel must use a natural seasonal lifestyle background, not a plain solid color only
- character height target is `70-78%` of the logical panel height, max `80%`, fail at or above `82%`
- keep at least `7%` clear panel height above hair and below shoes, and at least `6%` clear panel width on both left and right sides
- keep clear background above hair and below shoes so app display scaling does not crop heads or feet
- visible white borders, thick separators, adjacent-panel pixels, cropped heads, cropped shoes, sticker graphics, readable text, logos, and watermarks are publish blockers

Legacy behavior is preserved for explicit legacy/local workflows. New Drive ingest does not silently route non-canonical sources through legacy processing.

## Windows Standby

Windows local-sync polling is disabled in normal operation. The prior startup watcher command is retained as a `.disabled` file for manual failover only. Do not run Windows and Cloud workers at the same time.
