import base64
from pathlib import Path

# Local helper to prepare ANDROID_KEYSTORE_BASE64 for GitHub Secrets
KEYSTORE_PATH = Path(r"C:\c\TodayPick\_keystore\todaypick.keystore")
OUTPUT_PATH = Path(r"C:\c\todaypick-web\_keystore_base64.txt")

if not KEYSTORE_PATH.exists():
    print(f"[ERROR] Keystore not found at {KEYSTORE_PATH}")
    exit(1)

raw_bytes = KEYSTORE_PATH.read_bytes()
b64_str = base64.b64encode(raw_bytes).decode("ascii")

OUTPUT_PATH.write_text(b64_str, encoding="ascii")
print("[SUCCESS] Keystore successfully encoded to base64.")
print(f"[NOTE] The encoded string has been safely saved to: {OUTPUT_PATH}")
print("[SECURITY] The secret value is NOT printed to the terminal console.")
print("[INSTRUCTION] Copy the contents of _keystore_base64.txt into GitHub Secret 'ANDROID_KEYSTORE_BASE64'.")
