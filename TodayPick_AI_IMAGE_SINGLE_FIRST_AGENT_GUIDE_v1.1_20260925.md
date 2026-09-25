# TodayPick AI 이미지 생성 & 업로드 공식 지침서
**버전**: v1.1 | **작성일**: 2026-09-25 | **파일명**: TodayPick_AI_IMAGE_SINGLE_FIRST_AGENT_GUIDE_v1.1_20260925.md

---

## 목차
1. [전체 워크플로 요약](#1-전체-워크플로-요약)
2. [업로드 폴더 구조](#2-업로드-폴더-구조)
3. [STEP 1 — AI 이미지 생성](#3-step-1--ai-이미지-생성)
4. [STEP 2 — metadata.json 작성](#4-step-2--metadatajson-작성)
5. [STEP 3 — manifest.json 작성](#5-step-3--manifestjson-작성)
6. [STEP 4 — Google Drive 업로드](#6-step-4--google-drive-업로드)
7. [STEP 5 — 자동 등록 대기 및 확인](#7-step-5--자동-등록-대기-및-확인)
8. [세그먼트별 이미지 생성 가이드](#8-세그먼트별-이미지-생성-가이드)
9. [품질 기준 체크리스트](#9-품질-기준-체크리스트)
10. [오류 대응 FAQ](#10-오류-대응-faq)

---

## 1. 전체 워크플로 요약

```
[STEP 1] ChatGPT로 이미지 10장 생성
          ↓  LOOK_01.png ~ LOOK_10.png (1컷 1장, 배경·포즈 각각 다름)
[STEP 2] metadata.json 작성
          ↓  각 이미지의 코디 제목 + 아이템 정보 (아우터/상의/하의/신발)
[STEP 3] manifest.json 작성
          ↓  이미지 파일 목록 + SHA256 + Drive 파일 ID
[STEP 4] Google Drive 업로드
          ↓  이미지 10장 + metadata.json + manifest.json → 세그먼트 폴더에 업로드
[STEP 5] 자동 등록 대기 (5~20분)
          ↓  GAS 감지 → GitHub Actions → VM 처리 → GCS 업로드 → 앱 반영
```

> **3가지 조건이 모두 충족돼야 자동 등록 시작**
> - ✅ 이미지 파일 **10장 이상**
> - ✅ `metadata.json` **존재**
> - ✅ `manifest.json` **존재**

---

## 2. 업로드 폴더 구조

```
📁 TodayPick_user_config/
└── 📁 12월/               ← 월 폴더 (예: 12월, 9월)
    ├── 📁 f_20/           ← 여성 20대
    │   ├── LOOK_01.png
    │   ├── LOOK_02.png
    │   ├── ...
    │   ├── LOOK_10.png
    │   ├── metadata.json  ← 코디 정보 (필수)
    │   └── manifest.json  ← 파일 목록 (필수)
    ├── 📁 f_30/
    ├── 📁 f_40/
    ├── 📁 f_50/
    ├── 📁 f_60/
    ├── 📁 m_20/
    ├── 📁 m_30/
    ├── 📁 m_40/
    ├── 📁 m_50/
    └── 📁 m_60/
```

### 세그먼트 코드표

| 폴더 | 대상 | 스타일 방향 |
|------|------|------------|
| f_20 | 여성 20대 | 트렌디·캐주얼·스트릿 |
| f_30 | 여성 30대 | 세련된 오피스·미니멀 |
| f_40 | 여성 40대 | 우아한 클래식·커리어 |
| f_50 | 여성 50대 | 품격 있는 세미포멀 |
| f_60 | 여성 60대 | 편안하고 단아한 실버 |
| m_20 | 남성 20대 | 스트릿·스포티·캐주얼 |
| m_30 | 남성 30대 | 비즈니스 캐주얼·클린 |
| m_40 | 남성 40대 | 스마트 캐주얼·클래식 |
| m_50 | 남성 50대 | 격식 있는 캐주얼 |
| m_60 | 남성 60대 | 편안하고 품위 있는 |

> ⚠️ **`f_10`, `m_10` 폴더 사용 금지** — 앱에서 10대 세그먼트 제거됨

---

## 3. STEP 1 — AI 이미지 생성

### 파일 명명 규칙
```
LOOK_01.png
LOOK_02.png
...
LOOK_10.png
```
- 반드시 `LOOK_` 접두사 + 2자리 순번 + `.png`
- 총 **정확히 10장**

### 이미지 스펙

| 항목 | 권장값 | 최소값 |
|------|--------|--------|
| 해상도 | 941 × 1672 px | 540 × 960 px |
| 비율 | 9:16 세로형 | — |
| 포맷 | PNG (권장), JPEG, WebP | — |
| 파일 크기 | 1~5 MB | — |
| 색상 공간 | sRGB | — |

### 핵심 생성 원칙: 1컷 1장

**각 이미지는 독립된 1벌의 코디 사진**입니다.

| 항목 | 규칙 |
|------|------|
| 구도 | 전신(head-to-toe) 1인 |
| 배경 | **10장 모두 다른 배경** (카페, 공원, 스튜디오, 거리 등) |
| 포즈 | **10장 모두 다른 포즈** (정면, 사이드, 걷는 포즈, 팔짱 등) |
| 얼굴 | 흐릿하게 처리 또는 자연스럽게 비노출 |
| 계절 | 업로드 월의 계절에 맞는 소재·색상 |

### ChatGPT 이미지 생성 프롬프트 템플릿

```
[기본 구조]
A full-body fashion photo of a Korean [woman/man] in [her/his] [나이대], 
wearing [코디 설명]. 
Background: [배경 설명]. 
Pose: [포즈 설명]. 
Natural lighting, realistic style, whole body visible from head to toe.

[예시 — f_20 LOOK_01]
A full-body fashion photo of a Korean woman in her 20s, 
wearing an ivory short puffer jacket, ivory turtleneck knit, 
brown check mini skirt, and brown long boots. 
Background: cozy café interior with warm lighting. 
Pose: standing naturally, slight smile. 
Natural lighting, realistic fashion photo, whole body visible.

[예시 — f_20 LOOK_02]
A full-body fashion photo of a Korean woman in her 20s, 
wearing a taupe long coat, ivory knit dress, brown long boots. 
Background: outdoor park with autumn foliage. 
Pose: walking forward, looking slightly to the side. 
Natural daylight, realistic, full body head to toe.
```

> **배경 10가지 예시**: 카페 내부, 공원, 도심 거리, 화이트 스튜디오, 책상 앞, 쇼핑몰, 골목길, 자연광 실내, 건물 계단, 야외 벽면

> **포즈 10가지 예시**: 정면 서기, 걷는 포즈, 사이드 앵글, 팔짱 끼기, 손 주머니, 가방 들기, 계단 서기, 뒤돌아보기, 앉은 자세(전신), 기대는 포즈

---

## 4. STEP 2 — metadata.json 작성

### 파일 형식 (전체 구조)

```json
{
  "schema_version": 1,
  "request_id": "tp_dec_f20_chatgpt_01",
  "date_folder": "12월",
  "segment": "f_20",
  "looks": [
    {
      "index": 1,
      "source_file": "LOOK_01.png",
      "image_sha256": "6b080fbf9a6edbc9cdaef3286820eff890b6d338ace736a9b501cbb2488ab6ad",
      "gender": "female",
      "age_group": 20,
      "month": 12,
      "season": "winter",
      "title": "아이보리 패딩과 체크 미니스커트",
      "items": [
        {
          "slot": "아우터",
          "name": "아이보리 숏패딩",
          "searchKeyword": "여성 아이보리 숏패딩",
          "price": 0
        },
        {
          "slot": "상의",
          "name": "아이보리 터틀넥 니트",
          "searchKeyword": "여성 아이보리 터틀넥 니트",
          "price": 0
        },
        {
          "slot": "하의",
          "name": "브라운 체크 미니스커트",
          "searchKeyword": "여성 브라운 체크 미니스커트",
          "price": 0
        },
        {
          "slot": "신발",
          "name": "브라운 롱부츠",
          "searchKeyword": "여성 브라운 롱부츠",
          "price": 0
        }
      ],
      "status": "PENDING_GCS_LOOK_ID"
    }
  ]
}
```

### 필드 설명

| 필드 | 필수 | 설명 | 예시 |
|------|------|------|------|
| `schema_version` | ✅ | 항상 `1` | `1` |
| `request_id` | ✅ | `tp_월영문_세그먼트_도구_순번` | `"tp_dec_f20_chatgpt_01"` |
| `date_folder` | ✅ | 월 폴더명 | `"12월"` |
| `segment` | ✅ | 세그먼트 코드 | `"f_20"` |
| `looks[].index` | ✅ | 이미지 순번 (1~10) | `1` |
| `looks[].source_file` | ✅ | 이미지 파일명 | `"LOOK_01.png"` |
| `looks[].image_sha256` | ✅ | 이미지 SHA256 해시 | `"6b080f..."` |
| `looks[].gender` | ✅ | `"female"` 또는 `"male"` | `"female"` |
| `looks[].age_group` | ✅ | 나이 숫자 | `20` |
| `looks[].month` | ✅ | 월 숫자 | `12` |
| `looks[].season` | ✅ | `spring` / `summer` / `autumn` / `winter` | `"winter"` |
| `looks[].title` | ✅ | 앱 표시 제목 (한국어, 20자 이내) | `"아이보리 패딩과 체크 미니스커트"` |
| `looks[].items[].slot` | ✅ | `아우터` / `상의` / `하의` / `신발` / `원피스` / `가방` | `"아우터"` |
| `looks[].items[].name` | ✅ | 아이템 이름 | `"아이보리 숏패딩"` |
| `looks[].items[].searchKeyword` | ✅ | 검색 키워드 | `"여성 아이보리 숏패딩"` |
| `looks[].items[].price` | ✅ | 가격 (모를 때 `0`) | `0` |
| `looks[].status` | ✅ | 항상 `"PENDING_GCS_LOOK_ID"` | `"PENDING_GCS_LOOK_ID"` |

### SHA256 해시 구하는 방법

**Windows PowerShell:**
```powershell
Get-FileHash "C:\경로\LOOK_01.png" -Algorithm SHA256 | Select-Object -ExpandProperty Hash
```

**Mac / Linux Terminal:**
```bash
shasum -a 256 LOOK_01.png
```

**온라인 도구**: https://emn178.github.io/online-tools/sha256_checksum.html  
(파일을 드래그 앤 드롭하면 해시값 출력)

### 계절 판단표

| 월 | 계절 (`season` 값) |
|----|------------------|
| 3, 4, 5월 | `"spring"` |
| 6, 7, 8월 | `"summer"` |
| 9, 10, 11월 | `"autumn"` |
| 12, 1, 2월 | `"winter"` |

### 아이템 슬롯 사용 규칙

| 슬롯 | 사용 조건 |
|------|----------|
| `아우터` | 코트, 재킷, 패딩, 가디건 등 겉옷이 있을 때 |
| `상의` | 티셔츠, 니트, 블라우스, 셔츠 등 (원피스면 생략) |
| `하의` | 팬츠, 스커트 등 (원피스면 생략) |
| `원피스` | 원피스 착용 시 상의·하의 대신 사용 |
| `신발` | 항상 포함 |
| `가방` | 가방이 코디의 핵심 아이템일 때 |

---

## 5. STEP 3 — manifest.json 작성

### 파일 형식 (전체 구조)

```json
{
  "schema_version": 1,
  "request_id": "tp_dec_f20_chatgpt_01",
  "source": "chatgpt",
  "date_folder": "12월",
  "segment": "f_20",
  "gender": "female",
  "age_group": 20,
  "month": 12,
  "season": "winter",
  "expected_image_count": 10,
  "files": [
    {
      "index": 1,
      "file_name": "LOOK_01.png",
      "sha256": "6b080fbf9a6edbc9cdaef3286820eff890b6d338ace736a9b501cbb2488ab6ad",
      "width": 941,
      "height": 1672,
      "mime_type": "image/png",
      "drive_file_id": ""
    },
    {
      "index": 2,
      "file_name": "LOOK_02.png",
      "sha256": "64f9897dbafc87694d8f3fbbcb484aaf277fa170139585c8acfdcb2ff426e6a0",
      "width": 941,
      "height": 1672,
      "mime_type": "image/png",
      "drive_file_id": ""
    }
  ],
  "metadata_file": "metadata.json",
  "metadata_sha256": "",
  "upload_complete": true,
  "drive_folder_id": "",
  "note": "ChatGPT generated 10 images for female_20 winter season.",
  "metadata_file_id": ""
}
```

### 필드 설명

| 필드 | 필수 | 설명 |
|------|------|------|
| `schema_version` | ✅ | 항상 `1` |
| `request_id` | ✅ | metadata.json의 `request_id`와 **동일** |
| `source` | ✅ | 생성 도구: `"chatgpt"`, `"midjourney"`, `"dalle"`, `"fal"` |
| `date_folder` | ✅ | 월 폴더명 (예: `"12월"`) |
| `segment` | ✅ | 세그먼트 코드 (예: `"f_20"`) |
| `gender` | ✅ | `"female"` 또는 `"male"` |
| `age_group` | ✅ | 나이 숫자 (예: `20`) |
| `month` | ✅ | 월 숫자 (예: `12`) |
| `season` | ✅ | `"spring"` / `"summer"` / `"autumn"` / `"winter"` |
| `expected_image_count` | ✅ | 항상 `10` |
| `files[].index` | ✅ | 순번 (1~10) |
| `files[].file_name` | ✅ | 파일명 (예: `"LOOK_01.png"`) |
| `files[].sha256` | ✅ | 이미지 SHA256 해시 (metadata.json과 동일한 값) |
| `files[].width` | ✅ | 이미지 너비(px) |
| `files[].height` | ✅ | 이미지 높이(px) |
| `files[].mime_type` | ✅ | `"image/png"` 또는 `"image/jpeg"` |
| `files[].drive_file_id` | 선택 | Drive 업로드 후 파일 ID (업로드 전에는 `""` 가능) |
| `metadata_file` | ✅ | 항상 `"metadata.json"` |
| `metadata_sha256` | 선택 | metadata.json 파일의 SHA256 (없으면 `""`) |
| `upload_complete` | ✅ | 항상 `true` |
| `drive_folder_id` | 선택 | Drive 세그먼트 폴더 ID (없으면 `""`) |
| `note` | 선택 | 메모 |
| `metadata_file_id` | 선택 | Drive metadata.json 파일 ID (없으면 `""`) |

> **간소화 팁**: `drive_file_id`, `drive_folder_id`, `metadata_sha256`, `metadata_file_id`는 업로드 전에 비워도(`""`) 파이프라인이 동작합니다.

### request_id 작성 규칙
```
tp_<월영문약어>_<세그먼트>_<도구>_<순번>

예시:
  tp_dec_f20_chatgpt_01   ← 12월, 여성20대, ChatGPT, 첫 번째 배치
  tp_sep_m30_chatgpt_01   ← 9월, 남성30대, ChatGPT, 첫 번째 배치
  tp_dec_f50_chatgpt_02   ← 12월, 여성50대, ChatGPT, 두 번째 배치

월 약어: jan feb mar apr may jun jul aug sep oct nov dec
```

---

## 6. STEP 4 — Google Drive 업로드

### 업로드 체크리스트

업로드 전 세그먼트 폴더 내용 확인:

```
📁 f_20/
├── ✅ LOOK_01.png  (이미지 1)
├── ✅ LOOK_02.png  (이미지 2)
├── ✅ LOOK_03.png  (이미지 3)
├── ✅ LOOK_04.png  (이미지 4)
├── ✅ LOOK_05.png  (이미지 5)
├── ✅ LOOK_06.png  (이미지 6)
├── ✅ LOOK_07.png  (이미지 7)
├── ✅ LOOK_08.png  (이미지 8)
├── ✅ LOOK_09.png  (이미지 9)
├── ✅ LOOK_10.png  (이미지 10)
├── ✅ metadata.json
└── ✅ manifest.json
```

**총 12개 파일** (이미지 10 + 메타데이터 2)

### 권장 업로드 순서

```
1단계: LOOK_01.png ~ LOOK_09.png 업로드  ← 이미지 9장 먼저
2단계: metadata.json 작성 완료 후 업로드
3단계: manifest.json 작성 완료 후 업로드
4단계: LOOK_10.png 마지막으로 업로드     ← 10번째 이미지 = 자동 등록 시작 조건 충족
```

> **이유**: 10번째 이미지 업로드 시점에 이미 metadata.json + manifest.json이 존재해야  
> GAS가 세 조건 모두 충족된 것으로 감지하고 즉시 등록을 시작합니다.

---

## 7. STEP 5 — 자동 등록 대기 및 확인

### 자동화 파이프라인 흐름

```
Drive 세그먼트 폴더 (이미지 10장 + 2개 JSON)
    ↓ GAS 5분 폴링 (최대 5분 대기)
GitHub Actions 워크플로 dispatch
    ↓ VM SSH 접속 (1~2분)
cloud_drive_auto_ingest.py 실행
    ↓ Drive 다운로드 → WebP 변환 → GCS 업로드 (5~10분)
production/index.json + 시즌 카탈로그 업데이트
    ↓
앱 재시작 시 새 이미지 표시
```

**총 예상 소요 시간: 업로드 완료 후 10~20분**

### 등록 확인 방법

1. **GitHub Actions 로그 확인**  
   `https://github.com/johnpark236-tech/todaypick-web/actions` →  
   `TodayPick Drive Image Register` 워크플로 실행 여부 확인

2. **앱에서 확인**  
   앱 재시작 → 해당 성별/나이대 선택 → 새 코디 이미지 표시 여부 확인

---

## 8. 세그먼트별 이미지 생성 가이드

### 여성 세그먼트

#### f_20 — 여성 20대
**스타일**: 트렌디, 스트릿, Y2K, 캐주얼  
**주요 아이템**: 크롭 탑, 배기 팬츠, 오버핏 자켓, 미니스커트, 스니커즈  
**프롬프트 키워드**: `trendy casual`, `oversized`, `streetwear`, `Korean 20s woman`

```
예시 프롬프트:
"Full-body fashion photo of a Korean woman in her 20s wearing an oversized 
beige blazer, white crop top, wide-leg black pants, white sneakers. 
Background: urban street with brick walls. Pose: hands in pockets, 
looking at camera. Natural lighting, realistic."
```

#### f_30 — 여성 30대
**스타일**: 세련된 미니멀, 오피스 캐주얼  
**주요 아이템**: 슬림 팬츠, 블레이저, 실크 블라우스, 미디 스커트, 로퍼  
**프롬프트 키워드**: `minimal chic`, `office casual`, `Korean 30s woman`

#### f_40 — 여성 40대
**스타일**: 우아한 클래식, 커리어 룩  
**주요 아이템**: 트렌치코트, 니트 카디건, A라인 스커트, 앵클 부츠  
**프롬프트 키워드**: `elegant classic`, `career look`, `Korean 40s woman`

#### f_50 — 여성 50대
**스타일**: 품격 있는 세미포멀  
**주요 아이템**: 구조적 재킷, 무릎 아래 스커트, 니트, 낮은 굽 구두  
**프롬프트 키워드**: `refined semi-formal`, `sophisticated`, `Korean 50s woman`

#### f_60 — 여성 60대
**스타일**: 편안하고 단아한 실버 패션  
**주요 아이템**: 편안한 팬츠, 가디건, 플랫 슈즈  
**프롬프트 키워드**: `graceful silver fashion`, `comfortable`, `Korean 60s woman`

### 남성 세그먼트

#### m_20 — 남성 20대
**스타일**: 스트릿, 스포티, 캐주얼  
**주요 아이템**: 후드티, 카고 팬츠, 오버핏 티셔츠, 스니커즈  
**프롬프트 키워드**: `streetwear`, `sporty casual`, `Korean 20s man`

#### m_30 — 남성 30대
**스타일**: 비즈니스 캐주얼, 클린  
**주요 아이템**: 옥스포드 셔츠, 치노 팬츠, 더비 슈즈  
**프롬프트 키워드**: `smart business casual`, `clean`, `Korean 30s man`

#### m_40 — 남성 40대
**스타일**: 스마트 캐주얼, 클래식  
**주요 아이템**: 폴로 셔츠, 슬림 치노, 블레이저, 구두  
**프롬프트 키워드**: `smart casual classic`, `mature`, `Korean 40s man`

#### m_50 — 남성 50대
**스타일**: 격식 있는 캐주얼  
**주요 아이템**: 니트 폴로, 정장 팬츠, 드레스 슈즈  
**프롬프트 키워드**: `refined casual`, `distinguished`, `Korean 50s man`

#### m_60 — 남성 60대
**스타일**: 편안하고 품위 있는 실버 패션  
**주요 아이템**: 클래식 셔츠, 편안한 팬츠, 카디건, 가죽 슈즈  
**프롬프트 키워드**: `dignified silver fashion`, `comfortable`, `Korean 60s man`

---

## 9. 품질 기준 체크리스트

### 이미지 생성 후 확인

- [ ] 전신(머리~발)이 화면에 모두 보임
- [ ] 각 이미지마다 **배경이 다름** (10장 모두 다른 배경)
- [ ] 각 이미지마다 **포즈가 다름** (10장 모두 다른 포즈)
- [ ] 코디 아이템이 명확히 식별 가능
- [ ] 계절에 맞는 소재·색상 (겨울=두꺼운 소재, 여름=얇은 소재)
- [ ] 나이대에 맞는 스타일
- [ ] 조명이 고르게 분배됨 (너무 어둡거나 역광 아님)
- [ ] 파일명이 `LOOK_01.png` ~ `LOOK_10.png` 형식

### metadata.json 작성 후 확인

- [ ] 모든 10개 look 항목 포함
- [ ] `image_sha256` 값이 실제 이미지 파일과 일치
- [ ] `title`이 한국어로 작성됨 (20자 이내)
- [ ] 각 look에 아이템(`items`) 최소 2개 이상
- [ ] `status`가 모두 `"PENDING_GCS_LOOK_ID"`
- [ ] `request_id`가 manifest.json과 동일

### manifest.json 작성 후 확인

- [ ] `files` 배열에 10개 항목 모두 포함
- [ ] `sha256` 값이 metadata.json의 `image_sha256`와 동일
- [ ] `upload_complete`: `true`
- [ ] `expected_image_count`: `10`
- [ ] `request_id`가 metadata.json과 동일

---

## 10. 오류 대응 FAQ

**Q: 업로드 후 20분이 지나도 앱에 반영이 안 됩니다.**  
A: GitHub Actions 탭 확인 → `TodayPick Drive Image Register` 워크플로가 실행됐는지 확인. 실행 기록이 없으면 GAS가 감지 못한 것으로, manifest.json 또는 metadata.json 파일명 오타를 확인하세요.

**Q: manifest.json을 작성하기 어렵습니다. SHA256을 어떻게 구하나요?**  
A: Windows PowerShell에서 `Get-FileHash "파일경로" -Algorithm SHA256` 실행 또는 온라인 도구 사용 (위 STEP 2 참조).

**Q: LOOK_01.png ~ LOOK_10.png 이름이 아니라 다른 이름으로 저장했습니다.**  
A: Drive에 올리기 전에 파일명을 변경하거나, metadata.json/manifest.json의 `source_file`/`file_name` 필드를 실제 파일명으로 맞춰주세요.

**Q: 이미지를 잘못 생성했습니다. 수정 방법은?**  
A: 아직 등록 전(GAS 트리거 전)이라면 Drive에서 해당 파일을 교체하고 metadata.json/manifest.json의 SHA256 값도 새 파일로 갱신하세요.

**Q: 한 세그먼트만 업로드해도 되나요, 아니면 전체 10개 세그먼트를 다 올려야 하나요?**  
A: 하나씩 올려도 됩니다. GAS가 각 세그먼트별로 독립적으로 감지하고 처리합니다.

**Q: 같은 날짜·세그먼트에 두 번 업로드하면 어떻게 됩니까?**  
A: `request_id`가 같으면 파이프라인이 중복을 감지하고 건너뜁니다. 새 배치는 `request_id`의 마지막 순번을 올려주세요 (예: `_01` → `_02`).

---

*본 문서는 TodayPick 이미지 운영팀 내부 공식 지침서입니다.*  
*문의: johnpark236@gmail.com*
