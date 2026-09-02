# TodayPick — LDCloud Test Deployment Pipeline

**Pipeline ID**: WO-260831-LDCLOUD-TEST-DEPLOY-0069  
**Status**: ACTIVE & OPERATIONAL  

---

## 1. 개요 및 파이프라인 흐름

TodayPick의 빌드 및 검수 프로세스는 다음 단계를 거쳐 운영됩니다:

```
[GitHub Actions CI/CD Build]
        ↓
[Canonical Release APK / AAB 생성]
        ↓
[Google Drive tester/ 자동 업로드]
        ↓
[Telegram 봇 APK 직접 전송 (sendDocument)]
        ↓
[로컬 PC: OPEN_LDCLOUD_DEPLOY.bat 실행 (더블클릭)]
        ↓
[sync_latest.py: 최신 APK 우선순위 탐색, aapt 검증, 원자적 갱신]
        ↓
[C:\\TodayPick_LDCloud_Latest\\TodayPick-LATEST.apk 최신 유지]
        ↓
[LDCloud Client 자동 감지/실행 & Staging 폴더 자동 오픈]
        ↓
[테스터: TodayPick-LATEST.apk 드래그앤드롭 → 다중 기기 일괄 설치]
        ↓
[다중 LDCloud Cloud Phone (Android 14) 동시 실검수]
```

---

## 2. 세부 구성 파일

| 위치 | 파일명 | 역할 |
| :--- | :--- | :--- |
| `C:\TodayPick_LDCloud_Latest\` | `TodayPick-LATEST.apk` | 항상 최신 정상 APK를 가리키는 고정 포인터 |
| `C:\TodayPick_LDCloud_Latest\` | `sync_latest.py` | 최신 APK 탐색, aapt 검증, 원자적 갱신 엔진 |
| `C:\TodayPick_LDCloud_Latest\` | `LATEST_INFO.txt` | 최신 APK 메타데이터 (VersionCode, SHA256, Size 등) |
| `C:\TodayPick_LDCloud_Latest\` | `OPEN_LDCLOUD_DEPLOY.bat` | Staging 폴더 내 원클릭 실행 배치 스크립트 |
| `C:\Users\Admin\OneDrive\바탕 화면\` | `OPEN_LDCLOUD_DEPLOY.bat` | **OneDrive 활성 바탕화면 원클릭 실행 런처 (실제 표시 화면)** |
| `C:\Users\Admin\Desktop\` | `OPEN_LDCLOUD_DEPLOY.bat` | 로컬 바탕화면 원클릭 실행 런처 (원본 보존) |
| `C:\c\todaypick-web\tools\ldcloud\` | `sync_latest.py` | Git 저장소 버전 관리용 엔진 소스 |
| `C:\c\todaypick-web\` | `OPEN_LDCLOUD_DEPLOY.bat` | Git 저장소 버전 관리용 배치 스크립트 |
| `C:\c\todaypick-web\docs\LDCLOUD_TEST_DEPLOY.md` | `LDCLOUD_TEST_DEPLOY.md` | 파이프라인 운영 및 다중 기기 배포 매뉴얼 |

---

## 3. 최신 APK 우선순위 탐색 규칙 (`sync_latest.py`)

1. **1순위**: 최신 GitHub Actions 빌드 아티팩트
2. **2순위**: Google Drive tester 폴더 (`G:\내 드라이브\TT_Project\TodayPick\tester\*CANONICAL*.apk`)
3. **3순위**: 로컬 릴리즈 빌드 산출물 (`android/app/build/outputs/apk/release/*.apk`)
4. **4순위**: 로컬 빌드 산출물 (`android/app/build/outputs/apk/*.apk`)
5. **5순위**: 사용자 다운로드 폴더 (`Downloads/TodayPick*.apk`)

### 검증 기준:
- `C:\LDCloud\aapt.exe`를 통해 `package: name='com.todaypick.app'` 유효성 검사.
- `versionCode`를 정수형으로 추출하여 최신 빌드를 우선 선택.
- `TodayPick-LATEST.tmp.apk` 임시 생성 후 SHA-256 일치 시 `TodayPick-LATEST.apk`로 원자적 교체.
- 오류 발생 시 기존 정상 APK를 보존하여 테스트 중단 방지.

---

## 4. LDCloud 다중 기기 일괄 설치 방법

1. 바탕화면(OneDrive 동기화 바탕화면 `C:\Users\Admin\OneDrive\바탕 화면\` 또는 로컬 `C:\Users\Admin\Desktop\`)의 `OPEN_LDCLOUD_DEPLOY.bat`를 더블클릭합니다.
2. 콘솔에서 최신 APK 정보(VersionCode, SHA-256, Size)가 확인되고, `LDCloud.exe`와 Staging 폴더 탐색기 창이 자동으로 열립니다.
3. 탐색기 창에 보이는 `TodayPick-LATEST.apk`를 마우스로 잡고 LDCloud 기기 화면으로 끌어다 놓습니다(Drag & Drop).
4. **다중 기기 테스트 시:**
   - LDCloud 상단 툴바의 **[동기 제어]** 또는 **[일괄 설치]** 메뉴를 활성화한 상태에서 드래그앤드롭하면 등록된 모든 클라우드 테스트 기기에 동시에 설치가 진행됩니다.
5. 설치 완료 후 앱을 실행하여 주요 기능 및 최근 변경 사항(예: 여성 10대 고품질 시트 등)을 집중 검수합니다.

---

## 5. 결론 및 원칙
- LDCloud는 공식 외부 API/CLI/ADB가 없으므로, 오작동을 유발할 수 있는 UI 매크로/화면 클릭 자동화를 지양하고 **안전한 반자동 1-Click Staging 파이프라인(`MANUAL_LAST_MILE=true`)**으로 운영합니다.
