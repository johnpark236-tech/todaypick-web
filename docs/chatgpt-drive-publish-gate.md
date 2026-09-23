# TodayPick ChatGPT → Drive → Actions — integration gate (NOT LIVE)

This isolated branch adds a **non-publishing** GitHub Actions request validator.
It never reads Drive, changes GCS/catalog, starts the legacy watcher, exposes VM port 8787, or uploads to Play.
Do not merge and claim integrated publishing is complete.

## Request contract
One JSON file per explicit user request at `publish_requests/<request-id>.json`, with only:

```json
{
  "schema_version": 1,
  "request_id": "tp_260923_f10_unique01",
  "date_folder": "260923",
  "segment": "f_10",
  "drive_folder_id": "<actual target Drive folder ID>",
  "manifest_file_id": "<actual uploaded manifest file ID>",
  "metadata_file_id": "<actual uploaded metadata file ID>",
  "expected_image_count": 10,
  "source": "chatgpt"
}
```

No image bytes or credentials go in Git. The file is created **after** 10 independent source images, per-image metadata, and the manifest are uploaded to Drive and the resulting file IDs verified.

## Critical outstanding integration work
- The default GitHub branch presently does not contain `agent_image_tools.py`; reported Code/Codex VM/local changes must be reconciled before implementing a real publisher.
- The default branch `src/data/outfits.js` does not yet prefer remote `title`/`items`; do not claim Coupang integration is live on the installed app.
- Current connected ChatGPT Drive upload accepts a connector file reference. Verify image-generation output can actually be transferred as that reference and that all ten independent images exist before any request.
- Configure Drive read-only access to source images/metadata and GCS writer credentials with minimum permissions, without exposing any OAuth/token material.
- Implement a *single invocation* REGISTER with shared DB state and exclusive catalog lock; verify all ten images and metadata 1:1, SHA256, schema, dedupe and app readback before reporting success.
- Drive original is sufficient; do not require copy to 00_MAIN_IMAGES or _IMAGE_ARCHIVE.
- Existing `todaypick-daily-look-generation.yml` includes a daily schedule; audit and disable independently of this gated workflow if the user's OFF policy requires it.
- Validate with a new, user-approved non-duplicate 10-image set in a staging environment. Preserve existing GCS images and production catalog.
- Existing GAS 5-minute poll, VM watchers, and public 8787 webhook must remain off.

Status: REQUEST_GATE_ONLY. No end-to-end test, no production deployment.
