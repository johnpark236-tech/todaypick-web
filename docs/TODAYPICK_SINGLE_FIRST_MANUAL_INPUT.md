# TodayPick Single-First Manual Input Runbook

This runbook is for MASTER v3.2 operation when autonomous image generation is
unavailable. It keeps production publish blocked unless approved independent
single-cut assets and visual QA are present.

## Input Contract

Place approved single images under:

```text
G:\내 드라이브\TodayPick_user_config\<YYMMDD>\single_first\<season>\<segment>\
```

Example:

```text
G:\내 드라이브\TodayPick_user_config\260915\single_first\winter\female_10\
```

Each segment folder must contain:

```text
01.png
02.png
03.png
04.png
05.png
06.png
07.png
08.png
09.png
10.png
visual_qa.json
```

Allowed image extensions are `.png`, `.webp`, `.jpg`, and `.jpeg`, but each
decoded image must be exactly `648x1152`.

## Visual QA Manifest

`visual_qa.json` must contain 10 records. Each record must include the segment,
index, all required PASS booleans, and `QA_SCORE >= 90`.

Required fields:

```json
{
  "segment": "female_10",
  "index": 1,
  "HEAD_VISIBLE": true,
  "HAIR_VISIBLE": true,
  "FEET_VISIBLE": true,
  "ONE_PERSON_ONLY": true,
  "NO_ADJACENT_PERSON": true,
  "AGE_MATCH": true,
  "GENDER_MATCH": true,
  "SEASON_MATCH": true,
  "QA_SCORE": 95
}
```

## Prepare / Verify

Prepare and verify one segment without publishing:

```powershell
python automation\daily_looks\scripts\daily_auto_generate.py `
  --single-first-mode manual `
  --manual-input-base "G:\내 드라이브\TodayPick_user_config\260915\single_first\winter" `
  --group female_10 `
  --date 260915 `
  --season winter `
  --prepare-only `
  --verify-only `
  --no-auto-ingest `
  --no-drive-upload
```

The pipeline verifies:

- 10 consecutive singles exist
- each single is exactly `648x1152`
- `visual_qa.json` exists
- visual QA is `10/10 PASS`
- deterministic `1313x1198` 5x2 sheet composition succeeds
- roundtrip mapping is `10/10`

## Publish Gate

Production publish must not be attempted until all 12 segment folders exist and
pass the same checks. The publish gate refuses partial segment sets.

```powershell
python automation\daily_looks\scripts\daily_auto_generate.py `
  --single-first-mode manual `
  --manual-input-base "G:\내 드라이브\TodayPick_user_config\260915\single_first\winter" `
  --group all `
  --date 260915 `
  --season winter `
  --publish
```

Current implementation prepares a publish-ready report and backup path metadata.
Production object writes remain blocked unless approved assets are present and
the v3.2 gate passes.

## Safety Rules

- Do not use AI-generated 2x5 sheets as authoritative production singles.
- Do not publish without `visual_qa.json`.
- Do not publish partial segments.
- Do not delete existing winter active catalogs.
- Do not use placeholders or dummy images for production.
