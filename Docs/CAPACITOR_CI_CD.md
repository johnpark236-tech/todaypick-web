# TodayPick Capacitor CI/CD 가이드

본 문서는 TodayPick 오늘뭐입지 Capacitor 모바일 앱(`C:\c\todaypick-web`)의 GitHub Actions 자동화 파이프라인 구축, Secrets 설정, 빌드 및 알림 운영 가이드입니다.

---

## 1. 개요 및 파이프라인 흐름

```text
[코드 변경]
    │
    ▼ (git push / workflow_dispatch)
[GitHub Actions Runner (Ubuntu)]
    │
    ├─ 1. Node.js 22 & npm ci (캐시 적용)
    ├─ 2. Web App 빌드 (npm run build -> dist/)
    ├─ 3. Java 21 Temurin & Android SDK 설정
    ├─ 4. Capacitor Android 동기화 (npx cap sync android)
    ├─ 5. ANDROID_KEYSTORE_BASE64 디코딩 (임시 ci-release.keystore 복원)
    ├─ 6. Gradle 빌드 (assembleRelease / bundleRelease)
    ├─ 7. 산출물 표준화 & SHA256 / 파일 크기 계산
    ├─ 8. GitHub Artifact 업로드 (APK & AAB, 7일 보관)
    ├─ 9. Keystore 보안 삭제 (always 실행)
    ├─ 10. GitHub Step Summary 생성
    └─ 11. Telegram 빌드 결과 알림 (성공/실패)
```

- **Package ID**: `com.todaypick.app`
- **GameCI / Unity Docker 불필요**: 순수 웹 + Android Native 빌드로 빠르고 안정적 (빌드 시간 ~30초 대).

---

## 2. GitHub Secrets 설정

GitHub 저장소의 `Settings -> Secrets and variables -> Actions`에 다음 6개 항목을 등록합니다:

| Secret Name | 설명 | 획득 방법 |
| :--- | :--- | :--- |
| `ANDROID_KEYSTORE_BASE64` | `todaypick.keystore`의 Base64 인코딩 문자열 | 로컬 `python tools/encode_keystore_base64.py` 실행 후 `_keystore_base64.txt` 내용 복사 |
| `ANDROID_KEYSTORE_PASSWORD` | Android 키스토어 비밀번호 | 로컬 Windows 레지스트리 / 환경변수 `TODAYPICK_KEYSTORE_PASS` 값 |
| `ANDROID_KEY_ALIAS` | 키스토어 별칭 (기본값: `todaypick`) | `todaypick` |
| `ANDROID_KEY_PASSWORD` | 키스토어 키 별칭 비밀번호 | 로컬 Windows 레지스트리 / 환경변수 `TODAYPICK_KEYALIAS_PASS` 값 |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 알림 봇 토큰 | 기존 `TODAYPICK_TELEGRAM_BOT_TOKEN` 환경변수 |
| `TELEGRAM_CHAT_ID` | 텔레그램 알림 대상 채팅방 ID | 기존 `TODAYPICK_TELEGRAM_CHAT_ID` 환경변수 |

> **보안 주의사항**:
> - 비밀번호 및 키스토어 원본은 절대 Git에 커밋하지 않습니다.
> - `_keystore_base64.txt` 및 `ci-release.keystore`는 `.gitignore`에 등록되어 있습니다.

---

## 3. 로컬 키스토어 Base64 인코더 사용법

로컬에서 안전하게 GitHub Secret용 문자열을 추출하려면 다음 스크립트를 실행합니다:

```powershell
cd C:\c\todaypick-web
python tools\encode_keystore_base64.py
```

- 결과는 `C:\c\todaypick-web\_keystore_base64.txt`에 저장되며, 터미널 로그에는 Secret 문자열이 노출되지 않습니다.
- 생성된 텍스트 파일의 내용을 GitHub Secret `ANDROID_KEYSTORE_BASE64`에 붙여넣으면 됩니다.

---

## 4. 수동 빌드 (workflow_dispatch)

GitHub 저장소의 `Actions` 탭에서 **TodayPick Capacitor CI/CD Build** 워크플로를 선택하고 **Run workflow**를 클릭합니다:

- **Build Target**:
  - `all` (기본값: APK + AAB 모두 생성)
  - `apk` (테스터용 APK만 생성)
  - `aab` (Google Play 배포용 AAB만 생성)
- **Custom Android versionCode**:
  - 비워둘 경우 기본적으로 `22 + run_number`가 자동 지정됩니다.
  - 특정 버전 코드가 필요할 경우 직접 입력할 수 있습니다.

---

## 5. 산출물 다운로드 (Artifacts)

빌드가 완료되면 GitHub Actions 실행 페이지 하단 `Artifacts` 섹션에서 다운로드할 수 있습니다:

- `TodayPick-Capacitor-APK-<run_number>`: 설치 가능한 Release 서명 APK
- `TodayPick-Capacitor-AAB-<run_number>`: Google Play Console 업로드용 Release AAB
- 보관 기간: **7일**

---

## 6. 로컬 빌드 vs 클라우드 빌드 상호 보완

- **로컬 쾌속 빌드**:
  - `C:\c\todaypick-web\build_and_notify.bat`
  - 소요 시간: ~30초
  - 산출물: `G:\내 드라이브\TT_Project\TodayPick\tester\` 자동 복사 + Telegram 발송.
- **클라우드 CI/CD**:
  - `git push` 트리거
  - 소요 시간: ~2분 내외
  - 산출물: GitHub Artifacts 보관 + Telegram 발송.

---

## 7. 문제 해결 (Troubleshooting)

1. **GitHub Secrets 미등록 에러**:
   - `ANDROID_KEYSTORE_BASE64`가 등록되지 않은 경우 Gradle에서 서명 없이 빌드되거나 실패할 수 있습니다. 2절의 Secrets 목록을 등록하세요.
2. **versionCode 충돌**:
   - Google Play Console에 이미 업로드된 버전보다 낮으면 업로드가 거부됩니다. 콘솔의 최고 버전을 확인하고 필요 시 workflow_dispatch에서 `version_code`를 지정하세요.
3. **Coupang Worker 오류**:
   - 프론트엔드는 Cloudflare Worker(`https://todaypick-coupang-proxy.johnpark236.workers.dev`)를 통해 통신하므로, Worker 상태는 `GET /api/health`로 별도 모니터링합니다.
