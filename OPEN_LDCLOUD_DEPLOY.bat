@echo off
chcp 65001 > nul
title TodayPick -> LDCloud Test Deploy Staging

echo ===================================================
echo   TodayPick LDCloud 1-Click Test Deploy Pipeline
echo ===================================================
echo.

set STAGING_DIR=C:\TodayPick_LDCloud_Latest
set STAGING_APK=%STAGING_DIR%\TodayPick-LATEST.apk
set LDCLOUD_EXE=C:\LDCloud\LDCloud.exe

if not exist "%STAGING_DIR%" (
    mkdir "%STAGING_DIR%"
)

echo [1/4] Synchronizing latest canonical APK...
python "%STAGING_DIR%\sync_latest.py"
if errorlevel 1 (
    echo [ERROR] Synchronization encountered an issue.
    pause
    exit /b 1
)

echo [2/4] Checking LDCloud Client...
tasklist /NH /FI "IMAGENAME eq LDCloud.exe" 2>nul | findstr /I "LDCloud.exe" >nul
if errorlevel 1 (
    echo Launching LDCloud Client...
    start "" "%LDCLOUD_EXE%"
) else (
    echo [OK] LDCloud Client is already running.
)

echo [3/4] Opening Staging folder in Windows Explorer...
start "" explorer.exe "%STAGING_DIR%"

echo.
echo ===================================================
echo   [4/4] USER ACTION GUIDE (1-CLICK DEPLOY)
echo ===================================================
echo  1. LDCloud 창과 탐색기 창이 준비되었습니다.
echo  2. 탐색기의 'TodayPick-LATEST.apk'를 드래그하여
echo     LDCloud의 테스트 기기 창으로 끌어다 놓으세요.
echo  3. 다중 기기 테스트 시 [동기 제어] 또는 기기 선택 창에서
echo     일괄 설치를 진행하세요.
echo  4. 설치 후 TodayPick 앱을 열어 실검수를 진행합니다.
echo ===================================================
echo.
