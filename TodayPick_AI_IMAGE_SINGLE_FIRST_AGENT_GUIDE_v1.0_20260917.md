# TodayPick AI 이미지 생성 공식 지침서
**버전**: v1.0 | **작성일**: 2026-09-17 | **파일명**: TodayPick_AI_IMAGE_SINGLE_FIRST_AGENT_GUIDE_v1.0_20260917.md

---

## 목차
1. [개요](#1-개요)
2. [업로드 폴더 구조](#2-업로드-폴더-구조)
3. [이미지 스펙](#3-이미지-스펙)
4. [메타데이터 파일 형식](#4-메타데이터-파일-형식)
5. [세그먼트별 프롬프트 가이드라인](#5-세그먼트별-프롬프트-가이드라인)
6. [업로드 워크플로 (단계별)](#6-업로드-워크플로-단계별)
7. [자동 등록 파이프라인 설명](#7-자동-등록-파이프라인-설명)
8. [품질 기준 및 거부 사유](#8-품질-기준-및-거부-사유)
9. [자주 묻는 질문 (FAQ)](#9-자주-묻는-질문-faq)

---

## 1. 개요

이 지침서는 TodayPick 앱에 표시되는 패션 코디 이미지를 AI 이미지 생성 도구(ChatGPT, Midjourney, DALL·E 등)로 생성하고 Google Drive에 업로드할 때 따라야 하는 공식 절차를 기술합니다.

### 핵심 원칙
- **1 세그먼트 = 이미지 10장**: 하나의 인구통계 폴더에 정확히 10장의 이미지를 올려야 자동 등록이 시작됩니다.
- **원본 보존**: 업로드한 이미지는 파이프라인이 복사·변환합니다. 업로드 후 원본을 삭제하지 마십시오.
- **10대(f_10, m_10) 제외**: 앱에서 10대 세그먼트가 제거되었으므로 해당 폴더에는 이미지를 올리지 않습니다.
- **날짜 기준 계절**: 업로드 날짜의 월(月)이 계절을 결정합니다 (3~5월=봄, 6~8월=여름, 9~11월=가을, 12·1·2월=겨울).

---

## 2. 업로드 폴더 구조

Google Drive의 **TodayPick_user_config** 폴더 아래에 다음 구조로 업로드합니다.

```
📁 TodayPick_user_config/         ← Drive ID: 1WvKlV8B3xM9X21vl_47Oh6dTfBDFVUPd
└── 📁 YYMMDD/                    ← 6자리 날짜 (예: 260925 = 2026년 9월 25일)
    ├── 📁 f_20/                  ← 여성 20대  (이미지 10장 + metadata.json)
    ├── 📁 f_30/                  ← 여성 30대
    ├── 📁 f_40/                  ← 여성 40대
    ├── 📁 f_50/                  ← 여성 50대
    ├── 📁 f_60/                  ← 여성 60대
    ├── 📁 m_20/                  ← 남성 20대
    ├── 📁 m_30/                  ← 남성 30대
    ├── 📁 m_40/                  ← 남성 40대
    ├── 📁 m_50/                  ← 남성 50대
    └── 📁 m_60/                  ← 남성 60대
```

> **참고**: `f_10`, `m_10` 폴더는 앱에서 제거된 세그먼트이므로 사용하지 않습니다.  
> 날짜 폴더(`YYMMDD`)와 세그먼트 폴더(`f_20` 등)는 GAS 자동화가 매일 00:01 KST에 미리 생성합니다.

### 세그먼트 코드 대응표

| 폴더명 | 성별 | 나이대 | 스타일 방향 |
|--------|------|--------|------------|
| f_20   | 여성 | 20대   | 트렌디·캐주얼·스트릿 |
| f_30   | 여성 | 30대   | 세련된 오피스·미니멀 |
| f_40   | 여성 | 40대   | 우아한 클래식·커리어 |
| f_50   | 여성 | 50대   | 품격 있는 세미포멀 |
| f_60   | 여성 | 60대   | 편안하고 단아한 실버 |
| m_20   | 남성 | 20대   | 스트릿·스포티·캐주얼 |
| m_30   | 남성 | 30대   | 비즈니스 캐주얼·클린 |
| m_40   | 남성 | 40대   | 스마트 캐주얼·클래식 |
| m_50   | 남성 | 50대   | 격식 있는 캐주얼 |
| m_60   | 남성 | 60대   | 편안하고 품위 있는 |

---

## 3. 이미지 스펙

### 권장 사양
| 항목 | 값 |
|------|----|
| 해상도 | 648 × 1152 px (9:16 비율) |
| 최소 해상도 | 540 × 960 px |
| 포맷 | PNG, JPEG, WebP |
| 색상 공간 | sRGB |
| 파일 크기 | 이미지당 500 KB ~ 5 MB |
| 배경 | 단색 또는 심플한 실내/실외 배경 권장 |

> 파이프라인이 최종적으로 648×1152 WebP로 변환합니다. 원본 비율이 9:16에 가까울수록 품질이 좋습니다.

### 파일 명명 규칙
```
tp_<YYMMDD>_<segment>_<tool>_<00~09>.{png|jpg|webp}

예시:
  tp_260925_f50_chatgpt_00.png
  tp_260925_f50_chatgpt_01.png
  ...
  tp_260925_f50_chatgpt_09.png
```

| 구성 요소 | 설명 | 예시 |
|-----------|------|------|
| `YYMMDD`  | 6자리 날짜 | `260925` |
| `segment` | 성별+나이 코드 | `f50`, `m30` |
| `tool`    | 생성 도구 | `chatgpt`, `midjourney`, `dalle`, `fal` |
| `00~09`   | 순번 (2자리) | `00`, `01`, `09` |

> 파일명이 이 형식과 다르면 파이프라인이 해당 파일을 무시합니다. 반드시 형식을 지켜주세요.

---

## 4. 메타데이터 파일 형식

각 세그먼트 폴더에 `metadata.json` 파일을 함께 업로드합니다.

```json
{
  "version": 1,
  "date": "260925",
  "segment": "f_50",
  "season": "autumn",
  "generator": "chatgpt",
  "prompt_version": "v1.0",
  "operator": "johnpark236@gmail.com",
  "notes": "여성 50대 가을 코디 — 편안한 니트 레이어링",
  "images": [
    {
      "filename": "tp_260925_f50_chatgpt_00.png",
      "title": "베이지 니트 가디건 코디",
      "description": "따뜻한 베이지 니트 가디건에 다크 슬랙스 조합. 가을 산책 룩.",
      "tags": ["니트", "가디건", "캐주얼", "가을", "베이지"]
    },
    {
      "filename": "tp_260925_f50_chatgpt_01.png",
      "title": "버건디 터틀넥 코디",
      "description": "버건디 터틀넥과 체크 미디 스커트. 우아한 가을 오피스 룩.",
      "tags": ["터틀넥", "체크스커트", "오피스", "가을", "버건디"]
    }
  ]
}
```

### 메타데이터 필드 설명

| 필드 | 필수 | 설명 |
|------|------|------|
| `version` | ✅ | 항상 `1` |
| `date` | ✅ | YYMMDD 형식 |
| `segment` | ✅ | `f_20`~`m_60` |
| `season` | ✅ | `spring` / `summer` / `autumn` / `winter` |
| `generator` | ✅ | 사용한 AI 도구명 (`chatgpt`, `midjourney`, `dalle`, `fal`, `picsart`) |
| `prompt_version` | ✅ | 프롬프트 버전 (`v1.0`) |
| `operator` | ✅ | 업로드 담당자 이메일 |
| `notes` | 선택 | 자유 메모 |
| `images[].filename` | ✅ | 이미지 파일명 (확장자 포함) |
| `images[].title` | ✅ | 앱에 표시될 코디 제목 (15자 이내 권장) |
| `images[].description` | 선택 | 코디 상세 설명 |
| `images[].tags` | 선택 | 검색·필터용 태그 배열 |

> `metadata.json`이 없어도 파이프라인은 동작하지만, `title`이 자동 생성됩니다. 품질을 위해 메타데이터를 항상 포함하십시오.

---

## 5. 세그먼트별 프롬프트 가이드라인

### 공통 원칙
- **전신(full body) 이미지**: 머리 끝에서 발 끝까지 보이는 구도
- **정면 또는 3/4 앵글**: 코디 전체가 잘 보이는 각도
- **얼굴 노출 최소화**: 얼굴은 흐릿하거나 자연스럽게 처리
- **배경 단순**: 흰 벽, 원목 인테리어, 야외 자연광 등 코디가 돋보이는 배경
- **실제 패션 스타일**: 현실에서 입을 수 있는 코디 (과도한 판타지 제외)
- **계절감**: 계절에 맞는 소재·색상·레이어링

### 여성 세그먼트별 스타일 가이드

#### f_20 (여성 20대)
- 트렌디, 스트릿, Y2K, 미니멀 캐주얼
- 색상: 파스텔, 무채색, 포인트 컬러
- 아이템: 크롭 탑, 배기 팬츠, 오버핏 자켓, 미니스커트, 스니커즈
- ChatGPT 예시 프롬프트: *"A full-body fashion photo of a Korean woman in her 20s wearing a trendy casual outfit: oversized beige blazer, white crop top, wide-leg black pants, white sneakers. Simple white studio background. Autumn fashion. Natural lighting."*

#### f_30 (여성 30대)
- 세련된 미니멀, 오피스 캐주얼, 워크웨어
- 색상: 뉴트럴 (크림, 카키, 네이비, 버건디)
- 아이템: 슬림 팬츠, 블레이저, 실크 블라우스, 미디 스커트, 로퍼
- 예시: *"Korean woman in her 30s, sleek minimal work outfit: navy blazer, cream silk blouse, tailored slim trousers, pointed toe loafers. Neutral indoor background."*

#### f_40 (여성 40대)
- 우아한 클래식, 커리어 룩, 품위 있는 캐주얼
- 색상: 카멜, 버건디, 올리브, 차콜
- 아이템: 트렌치코트, 니트 카디건, A라인 스커트, 앵클 부츠
- 예시: *"Elegant Korean woman in her 40s, classic autumn fashion: camel trench coat, dark turtleneck, A-line midi skirt, ankle boots. Sophisticated and poised."*

#### f_50 (여성 50대)
- 품격 있는 세미포멀, 편안하고 세련된 스타일
- 색상: 베이지, 와인, 다크 네이비, 다크 그린
- 아이템: 무릎 아래 스커트, 구조적 재킷, 니트, 낮은 굽 구두
- 예시: *"Korean woman in her 50s, refined semi-formal look: wine-colored structured jacket, beige blouse, knee-length skirt, low heeled pumps. Dignified and warm."*

#### f_60 (여성 60대)
- 편안하고 단아한 실버 패션, 활동적 실용성
- 색상: 라이트 그레이, 소프트 핑크, 아이보리, 차분한 컬러
- 아이템: 편안한 팬츠, 가디건, 구조 없는 재킷, 플랫 슈즈
- 예시: *"Korean woman in her 60s, comfortable and graceful silver fashion: light gray cardigan, ivory trousers, flat comfortable shoes. Natural daylight background."*

#### m_20 (남성 20대)
- 스트릿, 스포티, 캐주얼
- 아이템: 후드티, 카고 팬츠, 오버핏 티셔츠, 스니커즈, 볼캡
- 예시: *"Korean man in his 20s, streetwear look: oversized white hoodie, dark cargo pants, chunky sneakers. Urban background, casual style."*

#### m_30 (남성 30대)
- 비즈니스 캐주얼, 클린, 스마트
- 아이템: 옥스포드 셔츠, 치노 팬츠, 더비 슈즈, 하프 코트
- 예시: *"Korean man in his 30s, smart business casual: navy oxford shirt, khaki chino pants, brown leather derby shoes. Clean minimal indoor background."*

#### m_40 (남성 40대)
- 스마트 캐주얼, 클래식, 성숙한 트렌디
- 아이템: 폴로 셔츠, 슬림 치노, 블레이저, 구두
- 예시: *"Korean man in his 40s, smart casual classic look: charcoal blazer, white polo shirt, dark chino pants, leather loafers. Polished and mature."*

#### m_50 (남성 50대)
- 격식 있는 캐주얼, 중후한 스타일
- 아이템: 니트 폴로, 정장 팬츠, 가죽 벨트, 드레스 슈즈
- 예시: *"Korean man in his 50s, refined casual: merino wool polo, dark dress trousers, leather belt, oxford shoes. Distinguished and comfortable."*

#### m_60 (남성 60대)
- 편안하고 품위 있는 실버 패션
- 아이템: 클래식 셔츠, 편안한 팬츠, 카디건, 편안한 가죽 슈즈
- 예시: *"Korean man in his 60s, comfortable and dignified silver fashion: classic plaid shirt, comfortable dark trousers, brown leather shoes. Natural warm lighting."*

---

## 6. 업로드 워크플로 (단계별)

### Step 1: 날짜 폴더 확인
Google Drive → TodayPick_user_config → 오늘 날짜 폴더(YYMMDD) 확인
- GAS가 매일 00:01 KST에 자동 생성
- 없으면 수동으로 `YYMMDD` 폴더를 만들고 그 안에 `f_20`, `f_30`, ... 폴더를 생성

### Step 2: AI 이미지 생성
- 세그먼트별로 정확히 **10장** 생성
- 파일명은 `tp_YYMMDD_fXX_chatgpt_00.png` ~ `tp_YYMMDD_fXX_chatgpt_09.png` 형식 준수
- 품질 기준 (Section 8) 사전 확인

### Step 3: metadata.json 작성
- Section 4 형식에 맞춰 `metadata.json` 작성
- 각 이미지의 `title`을 한국어로 작성 (예: "캐멀 트렌치코트 코디")

### Step 4: 업로드
```
TodayPick_user_config/
└── 260925/
    └── f_50/
        ├── tp_260925_f50_chatgpt_00.png  ← 이미지 10장
        ├── tp_260925_f50_chatgpt_01.png
        ├── ...
        ├── tp_260925_f50_chatgpt_09.png
        └── metadata.json                  ← 메타데이터
```

### Step 5: 자동 등록 대기
- GAS가 1분마다 Drive를 스캔
- 해당 폴더에 이미지 10장이 감지되면 GitHub Actions 워크플로 자동 실행
- VM이 이미지를 처리하고 GCS에 게시 (보통 5~15분 소요)
- 앱을 재시작하거나 새로고침하면 새 이미지가 표시됨

### Step 6: 결과 확인
앱에서 해당 인구통계 그룹 선택 후 코디 이미지 확인
- 새 이미지가 표시되면 등록 성공
- 문제 발생 시 GitHub Actions 탭 → `TodayPick Drive Image Register` 워크플로 로그 확인

---

## 7. 자동 등록 파이프라인 설명

```
사용자 (Drive 업로드)
    ↓  (이미지 10장 + metadata.json)
Google Drive: TodayPick_user_config/YYMMDD/f_XX/
    ↓  (1분마다 스캔)
GAS: TodayPickDriveAutoRegisterGAS.js
    ↓  (이미지 10장 감지 → workflow_dispatch)
GitHub Actions: todaypick-drive-image-register.yml
    ↓  (IAP SSH)
VM: tt-orchestra
    ↓  (cloud_drive_auto_ingest.py --date YYMMDD --once)
처리 단계:
  1. Drive에서 이미지 다운로드
  2. 648×1152 WebP 변환 + 기술 QA
  3. SHA-256 중복 확인
  4. GCS 업로드 (production/YYMMDD/...)
  5. 시즌 카탈로그 JSON 업데이트
  6. production/index.json 업데이트
    ↓
앱 (Capacitor Android)
  → GCS index.json 로드 → 카탈로그 URL 조회 → 이미지 URL 표시
```

### GAS 처리 로직
1. `TodayPick_user_config` 루트에서 `YYMMDD` 형식 폴더 목록 조회
2. 이미 처리된 날짜는 Script Properties에 기록되어 있어 스킵
3. 각 날짜 폴더의 비-10대 세그먼트(f_20~m_60)에서 이미지 10장 이상 감지 시 트리거
4. GitHub Actions API `workflow_dispatch` 호출 (GH_TOKEN 사용)
5. 처리 완료된 날짜를 Script Properties에 기록 (재처리 방지)

---

## 8. 품질 기준 및 거부 사유

### 자동 거부 (파이프라인)
| 거부 사유 | 설명 |
|-----------|------|
| 파일명 불일치 | `tp_YYMMDD_fXX_tool_NN.ext` 형식 아님 |
| 이미지 10장 미만 | 폴더에 10장 미만의 이미지 |
| 비율 오류 | 극단적으로 가로가 넓은 이미지 (최소 0.4 너비/높이 비율 이상) |
| 해상도 미달 | 540×960 미만 |
| 미지원 포맷 | JPEG/PNG/WebP 이외 |
| 중복 이미지 | SHA-256 해시가 기존 등록 이미지와 동일 |

### 권장 품질 기준 (수동 검토)
- [ ] 전신이 화면에 다 보임
- [ ] 코디 아이템이 명확히 식별 가능
- [ ] 조명이 고르게 분배됨 (너무 어둡거나 밝지 않음)
- [ ] 배경이 코디를 가리지 않음
- [ ] 나이대에 맞는 스타일 (20대 스타일을 60대 폴더에 올리지 않음)
- [ ] 계절감이 맞음 (9월에 생성 = 가을 코디)
- [ ] 패션 아이템이 현실적으로 구매 가능한 스타일

---

## 9. 자주 묻는 질문 (FAQ)

**Q: 이미지를 올렸는데 앱에 바로 안 보여요.**  
A: GAS가 1분마다 스캔하고 VM 처리에 5~15분이 걸립니다. 총 15~20분 후 앱을 재시작해서 확인해주세요.

**Q: 오늘 날짜 폴더가 Drive에 없어요.**  
A: GAS 일별 폴더 생성 스크립트(`TodayPick_Daily_Input_Folders`)가 00:01 KST에 생성합니다. 그 이전이라면 수동으로 `YYMMDD` 폴더와 세그먼트 폴더를 만드세요.

**Q: 여러 세그먼트를 한 번에 올려도 되나요?**  
A: 네, 여러 폴더에 동시에 올려도 됩니다. GAS가 각 세그먼트를 감지해 처리합니다.

**Q: 이미지를 잘못 올렸을 때 수정 방법은?**  
A: 아직 처리 전(10장 미만이거나 등록이 안 된 상태)이면 Drive에서 파일을 교체하면 됩니다. 이미 처리가 완료됐다면 관리자에게 문의하세요.

**Q: metadata.json 없이 이미지만 올려도 되나요?**  
A: 기술적으로는 동작하지만, 앱에 표시되는 코디 제목이 파일명 기반으로 자동 생성됩니다. 사용자 경험을 위해 metadata.json을 항상 포함하는 것을 강력히 권장합니다.

**Q: 이전에 올린 이미지를 다시 올리면 어떻게 되나요?**  
A: SHA-256 해시 기반 중복 확인으로 이미 등록된 이미지는 건너뜁니다. 새 이미지만 등록됩니다.

**Q: GAS 1분 폴링은 유료인가요?**  
A: Apps Script 트리거는 무료 티어에서 분당 1회 실행이 가능합니다. 하루 1,440회 실행으로 무료 실행 한도(하루 6분/무료 계정 기준)를 초과할 수 있어 Google Workspace 계정이 권장됩니다.

---

*본 문서는 TodayPick 개발팀 내부 공식 지침서입니다. 외부 배포 시 민감한 폴더 ID 및 이메일 정보를 제거하십시오.*
