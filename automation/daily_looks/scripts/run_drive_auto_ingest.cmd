@echo off
cd /d C:\c\todaypick-web
"C:\Users\Admin\AppData\Local\Programs\Python\Python310\python.exe" automation\daily_looks\scripts\drive_auto_ingest.py --poll-interval 30
