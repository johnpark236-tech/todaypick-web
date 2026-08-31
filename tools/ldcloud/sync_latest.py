import os
import sys
import shutil
import hashlib
import re
import subprocess
from datetime import datetime
from pathlib import Path

STAGING_DIR = Path(r"C:\TodayPick_LDCloud_Latest")
STAGING_DIR.mkdir(parents=True, exist_ok=True)
STAGING_APK = STAGING_DIR / "TodayPick-LATEST.apk"
STAGING_TMP = STAGING_DIR / "TodayPick-LATEST.tmp.apk"
INFO_FILE = STAGING_DIR / "LATEST_INFO.txt"
AAPT_EXE = Path(r"C:\LDCloud\aapt.exe")

def log(msg):
    print(f"[sync_latest] {msg}")

def get_apk_details(apk_path: Path):
    """Inspects package name, versionCode, and versionName using aapt."""
    if not AAPT_EXE.exists():
        return None
    try:
        res = subprocess.run(
            [str(AAPT_EXE), "dump", "badging", str(apk_path)],
            capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=10
        )
        if res.returncode != 0:
            return None
        
        m_pkg = re.search(r"package:\s+name='([^']+)'\s+versionCode='(\d+)'\s+versionName='([^']+)'", res.stdout)
        if m_pkg:
            return {
                "package_id": m_pkg.group(1),
                "version_code": int(m_pkg.group(2)),
                "version_name": m_pkg.group(3)
            }
    except Exception as e:
        log(f"Error inspecting {apk_path.name}: {e}")
    return None

def find_candidate_apks():
    """Searches priority locations for valid TodayPick APKs."""
    candidates = []
    
    # Priority 2: Google Drive tester location
    drive_tester = Path(r"G:\내 드라이브\TT_Project\TodayPick\tester")
    if drive_tester.exists():
        for f in drive_tester.glob("*.apk"):
            candidates.append((f, "Google Drive tester", 2))

    # Priority 3: Local release build output
    local_rel = Path(r"C:\c\todaypick-web\android\app\build\outputs\apk\release")
    if local_rel.exists():
        for f in local_rel.glob("*.apk"):
            candidates.append((f, "Local Release Output", 3))

    # Priority 4: Local general build output
    local_gen = Path(r"C:\c\todaypick-web\android\app\build\outputs\apk")
    if local_gen.exists():
        for f in local_gen.glob("*.apk"):
            candidates.append((f, "Local Build Output", 4))

    # Priority 5: User Downloads
    downloads = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
    if downloads.exists():
        for f in downloads.glob("TodayPick*.apk"):
            candidates.append((f, "User Downloads", 5))

    valid_candidates = []
    for f, source_name, prio in candidates:
        if not f.is_file() or f.stat().st_size < 1000000:
            continue
        details = get_apk_details(f)
        if details and details["package_id"] == "com.todaypick.app":
            valid_candidates.append({
                "path": f,
                "source": source_name,
                "priority": prio,
                "mtime": f.stat().st_mtime,
                "version_code": details["version_code"],
                "version_name": details["version_name"],
                "size": f.stat().st_size
            })
            
    return valid_candidates

def sync():
    log("Scanning candidate sources for latest TodayPick APK...")
    candidates = find_candidate_apks()
    
    if not candidates:
        log("No valid com.todaypick.app candidates found!")
        if STAGING_APK.exists():
            log("STATUS=STALE_USING_PREVIOUS_STAGING_APK")
            return True
        else:
            log("STATUS=BLOCKED (No staging APK available)")
            return False

    # Sort candidates by:
    # 1. version_code (descending)
    # 2. priority (ascending: 1 > 2 > 3 > ...)
    # 3. mtime (descending)
    candidates.sort(key=lambda c: (c["version_code"], -c["priority"], c["mtime"]), reverse=True)
    best = candidates[0]
    
    log(f"Best Candidate: {best['path'].name}")
    log(f"  Source:       {best['source']}")
    log(f"  VersionCode:  {best['version_code']} (VersionName: {best['version_name']})")
    log(f"  Size:         {best['size']:,} bytes")
    
    # Calculate candidate hash
    best_bytes = best["path"].read_bytes()
    best_sha = hashlib.sha256(best_bytes).hexdigest()
    log(f"  SHA256:       {best_sha}")

    # Check if existing staged APK is already identical
    already_identical = False
    if STAGING_APK.exists():
        existing_sha = hashlib.sha256(STAGING_APK.read_bytes()).hexdigest()
        if existing_sha == best_sha:
            already_identical = True
            log("Staged APK is already up-to-date with this exact build.")

    if not already_identical:
        log("Performing atomic replacement into TodayPick-LATEST.apk...")
        try:
            # 1. Copy to tmp
            shutil.copy2(best["path"], STAGING_TMP)
            
            # 2. Verify tmp
            tmp_sha = hashlib.sha256(STAGING_TMP.read_bytes()).hexdigest()
            assert tmp_sha == best_sha, "Tmp hash mismatch!"
            
            # 3. Atomic replace
            STAGING_TMP.replace(STAGING_APK)
            log("Atomic replace successful: TodayPick-LATEST.apk updated.")
        except Exception as e:
            log(f"Atomic replacement failed: {e}")
            if STAGING_TMP.exists():
                STAGING_TMP.unlink(missing_ok=True)
            if STAGING_APK.exists():
                log("Retaining previous staging APK (SYNC_FAILED).")
            else:
                log("STATUS=BLOCKED")
                return False

    # Update LATEST_INFO.txt
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info_content = f"""TODAYPICK LATEST TEST APK
UPDATED_AT={now_str}
APK=TodayPick-LATEST.apk
PACKAGE_ID=com.todaypick.app
VERSION_CODE={best['version_code']}
VERSION_NAME={best['version_name']}
SOURCE={best['source']} ({best['path'].name})
SHA256={best_sha}
SIZE={best['size']:,} bytes ({round(best['size'] / 1048576, 2)} MB)
STATUS=READY
"""
    INFO_FILE.write_text(info_content, encoding="utf-8")
    log(f"Updated metadata in: {INFO_FILE}")
    
    print("\n" + "="*50)
    print(" TodayPick -> LDCloud Test Deploy Staging Info")
    print("="*50)
    print(f" VERSION_CODE : {best['version_code']}")
    print(f" VERSION_NAME : {best['version_name']}")
    print(f" APK          : TodayPick-LATEST.apk")
    print(f" SIZE         : {round(best['size'] / 1048576, 2)} MB ({best['size']:,} bytes)")
    print(f" SHA256       : {best_sha}")
    print(f" SOURCE       : {best['source']}")
    print(f" STATUS       : READY")
    print("="*50 + "\n")
    return True

if __name__ == "__main__":
    success = sync()
    sys.exit(0 if success else 1)
