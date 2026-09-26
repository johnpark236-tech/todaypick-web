#!/usr/bin/env python3
"""Apply reviewed TodayPick metadata to already-published schema-v2 GCS looks.

This updates title/items/totalPrice only for exact look IDs from one date batch.
Image URL, SHA256, dimensions, IDs, and all unrelated catalog entries are preserved.
A versioned snapshot of the active catalog is created before the metadata write.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from append_seasonal_catalog_from_staging import (
    CACHE_NO_CACHE,
    CACHE_VERSIONED_JSON,
    object_exists,
    read_json_object,
    run_gcloud,
    storage_url,
    upload_json,
)


def canonical_segment(value: str) -> str:
    value = value.strip()
    if value.startswith("f_"):
        return "female_" + value.split("_", 1)[1]
    if value.startswith("m_"):
        return "male_" + value.split("_", 1)[1]
    return value


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True)
    p.add_argument("--season", required=True, choices=["spring", "summer", "autumn", "winter"])
    p.add_argument("--segment", required=True)
    p.add_argument("--metadata", required=True)
    args = p.parse_args()

    metadata_path = Path(args.metadata)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    segment = canonical_segment(args.segment)
    meta_segment = canonical_segment(str(metadata.get("segment", "")))
    if meta_segment != segment:
        raise SystemExit(f"metadata segment mismatch: {meta_segment} != {segment}")

    active_object = f"production/{args.season}/{segment}.json"
    if not object_exists(active_object):
        raise SystemExit(f"catalog missing: {active_object}")

    catalog = read_json_object(active_object)
    looks = catalog.get("looks", [])
    by_id = {look.get("id"): look for look in looks if look.get("id")}

    updated = []
    for entry in metadata.get("looks", []):
        index = int(entry["index"])
        look_id = f"{args.season}_{segment}_{args.date}_{index:02d}"
        target = by_id.get(look_id)
        if target is None:
            raise SystemExit(f"published look not found: {look_id}")

        clean_items = []
        for item in entry.get("items", []):
            clean_items.append({
                "slot": item.get("slot", ""),
                "name": item.get("name", ""),
                "searchKeyword": item.get("searchKeyword", ""),
                "price": int(item.get("price") or 0),
            })
        target["title"] = entry.get("title", target.get("title", ""))
        target["items"] = clean_items
        target["totalPrice"] = sum(int(item.get("price") or 0) for item in clean_items)
        target["metadata_request_id"] = metadata.get("request_id")
        target["metadata_source_file"] = entry.get("source_file")
        updated.append(look_id)

    catalog["updated_at"] = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    ).isoformat()

    snapshot = (
        f"production/{args.season}/manifests/"
        f"{segment}_metadata_{args.date}_{int(time.time())}.json"
    )
    run_gcloud(["storage", "cp", storage_url(active_object), storage_url(snapshot)])
    upload_json(catalog, active_object, CACHE_NO_CACHE)

    print(json.dumps({
        "status": "PASS",
        "catalog": active_object,
        "snapshot": snapshot,
        "updated_count": len(updated),
        "updated_ids": updated,
        "metadata_request_id": metadata.get("request_id"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
