# TodayPick ChatGPT → Drive → GitHub Actions → VM REGISTER → GCS

Status: **MERGED TO MASTER; GCS NOT PUBLISHED.** First queue push triggered Actions run 35869097202; request validation PASS, deliberate activation gate FAIL (environment variable unset). VM/REGISTER not invoked.

## Current reviewed input
- Request: `publish_requests/tp_260923_f50_chatgpt_01.json`
- Drive folder: `TodayPick_user_config/260923/f_50`
- 10 images + `metadata.json` + `manifest.json` are present.
- First release is intentionally hard-limited to this exact request ID and `f_50`. A later, independently reviewed change is needed to support all groups.

## Runtime architecture
`publish_queue/*.json` push to **master** (after deliberate activation), or a manual `workflow_dispatch` → GitHub runner validates request → obtains OIDC credentials through Workload Identity Federation → IAP SSH to existing VM → **single** VM publisher under `flock` → read-only Drive preflight (folder ancestry, 10 images, bytes SHA256, metadata and manifest) → existing VM REGISTER one-shot and SQLite shared state → merge title/items into GCS catalog with generation precondition → GCS readback.

No images in Git, no Drive copies or second backup, no always-on watchers, no GAS poll, no opening VM port 8787, no Play production release.

## Administrator one-time prerequisites (not yet configured)

1. In GCP create or identify a narrowly scoped deployment service account. Configure GitHub OIDC Workload Identity Federation restricted to `johnpark236-tech/todaypick-web`, the trusted branch **and** environment `todaypick-image-publish`. Bind `roles/iam.workloadIdentityUser` for that exact GitHub principal on the deployment service account.
2. Grant only required project/IAP/instance authorization to this identity: `roles/iap.tunnelResourceAccessor`, narrowly scoped VM access, and an explicitly verified OS Login account mapping. **Do not assume `Admin@` is valid with OS Login service-account credentials.** Test the login identity and directory permissions before enabling publishing. Prefer configuring a restricted VM execution account with access only to REGISTER files, state, and log directory. Avoid broad project admin roles.
3. In GitHub Settings → Environments create `todaypick-image-publish`, restrict deployment branch to master, and add required reviewer(s). Set environment secrets `GCP_WIF_PROVIDER` (provider resource name) and `GCP_DEPLOY_SA` (deployment service account email). Set environment variable `TODAYPICK_PUBLISH_ENABLED=true` **only after** tests and IAP login mapping are verified. No long-lived `GCP_SA_KEY` is required or recommended.
4. Confirm the VM service account still has read access to original Drive folder and GCS object read/write, Python venv, SQLite state, and that legacy watcher/GAS schedule remain OFF. Registration intentionally uses the existing VM service account for Drive/GCS.
5. Review PR #1 and merge only after safe static review. The new push trigger listens only to `publish_queue/*.json`, which is **absent from the PR**: merely merging it does not publish the staged request.
6. After the preceding checks, create a new file on **master** at `publish_queue/tp_260923_f50_chatgpt_01_activation.json` with:
   ```json
   {"request_path":"publish_requests/tp_260923_f50_chatgpt_01.json"}
   ```
   The queue push already triggered run [35869097202](https://github.com/johnpark236-tech/todaypick-web/actions/runs/35869097202); request validation passed and the explicit activation gate failed before VM access. **Do not create or push a duplicate queue file.** Once credentials, environment and IAP OS Login are configured, re-run failed jobs on that same run (or issue a new uniquely named queue file pointing to the SAME request JSON if a rerun is unavailable).
7. Verify Actions logs show `GCS_POSTED_WITH_METADATA_AND_READBACK_OK`; independently read the GCS catalog and then test female 50s/autumn in the **actually deployed** app. A web/VM catalog readback alone does not prove the installed Android bundle has the new `remoteLook.items` code or that Coupang API search returns products.

## Known preflight blockers and limits
- The existing VM REGISTER only accepts `--date`, so the wrapper audits sibling segments to prevent accidentally publishing a different, unprocessed complete set. If another unprocessed segment has ten images, it fails closed; don't bypass.
- Existing VM source is **not** present on GitHub; the wrapper invokes it on the VM. The GitHub runner must not initialize an independent SQLite database.
- GitHub Actions cannot be dispatched directly by the currently connected GitHub connector. After enabling, create a queue JSON commit on master through the connector instead.
- `google-github-actions/auth@v2` does not set up IAP/OS Login permissions by itself. A verified SSH connection is a prerequisite.
- The first deployment is restricted to `260923/f_50` and does **not** modify other age groups. A proper generalization needs separate tests.
- The requested images can be published without re-building Android. However **new app-side metadata handling will not appear in an already installed, old native bundle** until the code has reached its own deployment channel. Android Play release is explicitly separate.

## Live status checklist
- [x] 10 Drive images and associated metadata/manifest uploaded.
- [x] Registration request stored in feature branch.
- [x] GitHub Actions and VM wrapper committed to feature branch.
- [ ] GCP WIF + IAP + OS Login verified for GitHub identity (blocking activation).
- [ ] Environment configured and approved.
- [x] PR merged, first queue message pushed on master; fail-closed activation guard verified.
- [ ] First workflow run, VM dry-run, real GCS metadata readback completed.
- [ ] Actual deployed web/Android app image display and Coupang query verified.
