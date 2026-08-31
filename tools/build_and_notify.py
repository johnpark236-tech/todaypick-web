# TodayPick Capacitor MVP Build, Deploy, and Notify Script
import os
import sys
import time
import shutil
import hashlib
import subprocess
import re
from pathlib import Path

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add TodayPick tools to import existing telegram_notify
sys.path.insert(0, r"C:\c\TodayPick\tools")
try:
    from telegram_notify import send_message, is_configured
except ImportError:
    send_message = None
    is_configured = lambda: False

ROOT_DIR = Path(r"C:\c\todaypick-web")
ANDROID_DIR = ROOT_DIR / "android"
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
DRIVE_TESTER_DIR = Path(r"G:\내 드라이브\TT_Project\TodayPick\tester")

version_text = (ROOT_DIR / "src" / "config" / "version.js").read_text(encoding="utf-8")
display_match = re.search(r"APP_DISPLAY_VERSION\s*=\s*'([^']+)'", version_text)
code_match = re.search(r"ANDROID_VERSION_CODE\s*=\s*(\d+)", version_text)
APP_DISPLAY_VERSION = display_match.group(1) if display_match else "v0.4"
ANDROID_VERSION_CODE = int(code_match.group(1)) if code_match else 51

t_start = time.time()

print("==================================================")
print(" TodayPick Capacitor MVP -- Build & Notify Pipeline")
print("==================================================")

# 1. NPM Build
print("\n[1/5] Building Web bundle (npm run build)...")
t0 = time.time()
p_npm = subprocess.run(["cmd.exe", "/c", "npm", "run", "build"], cwd=ROOT_DIR, capture_output=True, encoding="utf-8", errors="replace")
t_npm = round(time.time() - t0, 2)
if p_npm.returncode != 0:
    print("NPM BUILD FAILED:\n", p_npm.stderr)
    sys.exit(1)
if any((ROOT_DIR / "dist").rglob("*.mp3")) or any((ROOT_DIR / "dist").rglob("*.ogg")):
    print("NPM BUILD FAILED: embedded BGM audio file remained in dist")
    sys.exit(1)
print(f"  -> npm build OK; embedded BGM removed ({t_npm}s)")

# 2. Capacitor Sync
print("\n[2/5] Syncing Capacitor android...")
t0 = time.time()
p_sync = subprocess.run(["cmd.exe", "/c", "npx", "cap", "sync", "android"], cwd=ROOT_DIR, capture_output=True, encoding="utf-8", errors="replace")
t_sync = round(time.time() - t0, 2)
if p_sync.returncode != 0:
    print("CAPACITOR SYNC FAILED:\n", p_sync.stderr)
    sys.exit(1)
print(f"  -> Cap sync OK ({t_sync}s)")

# 3. Gradle Build (Release APK + AAB)
print("\n[3/5] Building Android Release APK & AAB (gradlew)...")
t0 = time.time()
env = os.environ.copy()
env["JAVA_HOME"] = r"C:\Program Files\Android\Android Studio\jbr"
env["ANDROID_HOME"] = r"C:\Users\Admin\AppData\Local\Android\Sdk"

gradle_cmd = ["cmd.exe", "/c", "gradlew.bat", "assembleRelease", "bundleRelease"]
p_gradle = subprocess.run(gradle_cmd, cwd=ANDROID_DIR, env=env, capture_output=True, encoding="utf-8", errors="replace")
t_gradle = round(time.time() - t0, 2)

if p_gradle.returncode != 0:
    print("GRADLE BUILD FAILED:\n", p_gradle.stderr[-1000:] if p_gradle.stderr else "Unknown error")
    sys.exit(1)
print(f"  -> Gradle build OK ({t_gradle}s)")

# 4. Verify outputs
apk_path = ANDROID_DIR / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk"
aab_path = ANDROID_DIR / "app" / "build" / "outputs" / "bundle" / "release" / "app-release.aab"

if not apk_path.exists():
    print("ERROR: APK not found at", apk_path)
    sys.exit(1)

apk_bytes = apk_path.stat().st_size
apk_mb = round(apk_bytes / (1024 * 1024), 2)
apk_sha = hashlib.sha256(apk_path.read_bytes()).hexdigest()

aab_bytes = aab_path.stat().st_size if aab_path.exists() else 0
aab_mb = round(aab_bytes / (1024 * 1024), 2)
aab_sha = hashlib.sha256(aab_path.read_bytes()).hexdigest() if aab_path.exists() else ""

print(f"  -> APK: {apk_path.name} ({apk_mb} MB, SHA256: {apk_sha[:16]}...)")
print(f"  -> AAB: {aab_path.name} ({aab_mb} MB, SHA256: {aab_sha[:16]}...)")

# 5. Copy to Google Drive
print("\n[4/5] Copying to Google Drive tester folder...")
t0 = time.time()
drive_copied = False
target_apk_name = f"TodayPick-{APP_DISPLAY_VERSION}-vc{ANDROID_VERSION_CODE}-audio-update-rootfix-260831.apk"
target_aab_name = f"TodayPick-{APP_DISPLAY_VERSION}-vc{ANDROID_VERSION_CODE}-audio-update-rootfix-260831.aab"

try:
    if DRIVE_TESTER_DIR.exists():
        dest_apk = DRIVE_TESTER_DIR / target_apk_name
        dest_aab = DRIVE_TESTER_DIR / target_aab_name
        shutil.copy2(apk_path, dest_apk)
        if aab_path.exists():
            shutil.copy2(aab_path, dest_aab)
        drive_copied = True
        print(f"  -> Copied to: {dest_apk}")
    else:
        print(f"  -> Drive path not accessible: {DRIVE_TESTER_DIR}")
except Exception as e:
    print(f"  -> Drive copy error: {e}")
t_drive = round(time.time() - t0, 2)

# 6. Telegram Notification
print("\n[5/5] Sending Telegram notification...")
t0 = time.time()
telegram_status = "SKIPPED"
if send_message:
    msg = (
        f"[TodayPick {APP_DISPLAY_VERSION} vc{ANDROID_VERSION_CODE} Audio/Update Rootfix Build PASS]\n\n"
        f"APK: {target_apk_name}\n"
        f"Size: {apk_mb} MB\n"
        f"AAB: {target_aab_name} ({aab_mb} MB)\n"
        f"Signing: todaypick.keystore (Release)\n"
        f"Package ID: com.todaypick.app\n"
        f"VersionCode: {ANDROID_VERSION_CODE}\n"
        f"UI Version: {APP_DISPLAY_VERSION}\n"
        "Embedded BGM MP3/OGG: NO\n"
        f"Drive: {'PASS' if drive_copied else 'FAIL'}\n\n"
        "--- 소요 시간 ---\n"
        f"Vite 빌드: {t_npm}초\n"
        f"Cap Sync: {t_sync}초\n"
        f"Gradle 빌드: {t_gradle}초\n"
        f"총 소요시간: {round(time.time() - t_start, 2)}초"
    )
    status, detail = send_message(msg)
    telegram_status = status
    print(f"  -> Telegram: {status} ({detail})")
else:
    print("  -> Telegram script not found, skipped.")
t_telegram = round(time.time() - t0, 2)

t_total = round(time.time() - t_start, 2)

# 7. Write logs/last_build_result.txt
res_file = LOGS_DIR / "last_build_result.txt"
lines = [
    "STATUS=PASS",
    f"NPM_BUILD_TIME_SEC={t_npm}",
    f"CAP_SYNC_TIME_SEC={t_sync}",
    f"GRADLE_TIME_SEC={t_gradle}",
    f"DRIVE_COPY_TIME_SEC={t_drive}",
    f"TELEGRAM_TIME_SEC={t_telegram}",
    f"TOTAL_TIME_SEC={t_total}",
    f"APK_SIZE_MB={apk_mb}",
    f"APK_SHA256={apk_sha}",
    f"AAB_SIZE_MB={aab_mb}",
    f"AAB_SHA256={aab_sha}",
    f"DRIVE_COPY={'PASS' if drive_copied else 'FAIL'}",
    f"TELEGRAM={telegram_status}",
    "PACKAGE_ID=com.todaypick.app",
    f"VERSION_CODE={ANDROID_VERSION_CODE}",
    f"UI_VERSION={APP_DISPLAY_VERSION}",
    "PHONE_TEST_READY=YES"
]
res_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\n[DONE] Build summary written to {res_file}")
print("==================================================")
print(f" TOTAL BUILD TIME: {t_total}s | STATUS: PASS")
print("==================================================")
