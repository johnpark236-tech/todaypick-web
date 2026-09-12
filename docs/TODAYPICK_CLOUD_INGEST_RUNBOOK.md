# TodayPick Cloud Ingest Runbook

## Start Continuous Worker

Copy `automation/daily_looks/cloud/todaypick-cloud-drive-ingest.service` to `/etc/systemd/system/`, adjust `WorkingDirectory` and `ExecStart` if the repo path is not `/opt/todaypick-web`, then run:

```bash
cd /opt/todaypick-web
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r automation/daily_looks/cloud/requirements.txt

sudo systemctl daemon-reload
sudo systemctl enable --now todaypick-cloud-drive-ingest.service
sudo systemctl status todaypick-cloud-drive-ingest.service
```

## Timer Alternative

Use the timer only if you prefer scheduled reconciliation instead of a continuous worker:

```bash
sudo cp automation/daily_looks/cloud/todaypick-cloud-drive-ingest-once.service /etc/systemd/system/
sudo cp automation/daily_looks/cloud/todaypick-cloud-drive-ingest.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now todaypick-cloud-drive-ingest.timer
sudo systemctl list-timers todaypick-cloud-drive-ingest.timer
```

Do not enable the continuous service and timer at the same time.

## Stop

```bash
sudo systemctl stop todaypick-cloud-drive-ingest.service
sudo systemctl disable todaypick-cloud-drive-ingest.service
```

## Logs

```bash
journalctl -u todaypick-cloud-drive-ingest.service -f
tail -f /opt/todaypick-web/automation/daily_looks/logs/cloud_drive_auto_ingest.log
```

## Status

```bash
sqlite3 /opt/todaypick-web/automation/daily_looks/runtime/cloud_drive_ingest/state.sqlite3 \
  "select status, date_folder, segment, filename, attempt_count, catalog_before, catalog_after, updated_at from sources order by updated_at desc limit 20;"
```

## Manual Backfill

```bash
.venv/bin/python automation/daily_looks/scripts/cloud_drive_auto_ingest.py --once --date 260912 --poll-interval 120
```

## Dry Run

Dry run downloads, validates, crops, and builds the candidate publish report without changing production catalogs or moving Drive sources:

```bash
.venv/bin/python automation/daily_looks/scripts/cloud_drive_auto_ingest.py --once --date 260912 --dry-run --no-drive-move --poll-interval 120
```

## DLQ Review

```bash
gcloud storage ls --recursive gs://todaypick-daily-looks-363284724091/automation/dlq/
gcloud storage cp gs://todaypick-daily-looks-363284724091/automation/dlq/260912/female_30/<sha>/metadata.json -
gcloud storage cp gs://todaypick-daily-looks-363284724091/automation/dlq/260912/female_30/<sha>/error.json -
```

To reprocess a corrected source, upload a new file into the date root folder. A new SHA is treated as a new source.

## Windows Failover

Normal operation:

`WINDOWS_ACTIVE_POLLER=NO`

Failover is manual only:

1. Stop or confirm failure of the cloud worker.
2. Confirm no cloud process is polling Drive.
3. Rename the Windows startup file from `TodayPick-Daily-Look-AutoIngest.cmd.disabled` back to `.cmd`, or run `automation\daily_looks\scripts\run_drive_auto_ingest.cmd` manually.
4. After cloud recovery, stop the Windows watcher and disable the startup file again.

Never run Windows and Cloud pollers at the same time.
