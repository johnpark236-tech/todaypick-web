@echo off
setlocal
cd /d %~dp0
echo [TodayPick] Starting Capacitor Build and Notify...
python tools\build_and_notify.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build pipeline failed!
    exit /b %ERRORLEVEL%
)
echo [SUCCESS] TodayPick Capacitor Build Complete!
endlocal
