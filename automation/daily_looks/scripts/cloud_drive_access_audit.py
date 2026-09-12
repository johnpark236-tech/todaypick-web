import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="Audit TodayPick Google Drive API access from the current runtime.")
    parser.add_argument("--root-folder-id", default="1WvKlV8B3xM9X21vl_47Oh6dTfBDFVUPd")
    args = parser.parse_args()

    from googleapiclient.discovery import build
    import google.auth

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/drive"])
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)

    report = {
        "root_folder_id": args.root_folder_id,
        "root_get": "UNKNOWN",
        "root_list": "UNKNOWN",
        "children": [],
        "error": None,
    }
    try:
        report["root"] = service.files().get(
            fileId=args.root_folder_id,
            fields="id,name,mimeType,capabilities",
            supportsAllDrives=True,
        ).execute()
        report["root_get"] = "PASS"
    except Exception as exc:
        report["root_get"] = "FAIL"
        report["error"] = repr(exc)

    try:
        result = service.files().list(
            q=f"'{args.root_folder_id}' in parents and trashed = false",
            fields="files(id,name,mimeType,modifiedTime)",
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            orderBy="name",
        ).execute()
        report["children"] = result.get("files", [])
        report["root_list"] = "PASS"
    except Exception as exc:
        report["root_list"] = "FAIL"
        report["error"] = repr(exc)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["root_get"] == "PASS" and report["root_list"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
