# Google Play Console Internal Testing Track 자동 배포 가이드

**프로젝트**: TodayPick (com.todaypick.app)  
**배포 방식**: GitHub Actions CI/CD 자동 업로드 (
0adkll/upload-google-play@v1)  
**대상 트랙**: Internal Testing (내부 테스트)

---

## 1. 개요 및 장점

- **기존 방식**: 빌드 시마다 APK 파일을 직접 다운로드하여 기기에 수동 설치
- **Google Play Internal Testing 트랙 적용 후**:
  - 테스터는 **최초 1회** 내부 테스트 초대 링크에서 '테스트 참여' 및 앱 설치를 완료하면 끝.
  - 이후 GitHub Actions에서 새 버전(AAB)이 빌드될 때마다 **Google Play 스토어를 통해 일반 앱처럼 백그라운드 자동 업데이트** 수신.
  - 별도 APK 파일 복사/설치 불필요.
  - 기존 **Telegram APK 전송, Google Drive tester 보관, LDCloud 1-Click Staging**은 Fallback으로 100% 정상 유지.

---

## 2. 사전 필수 1단계: 최초 1회 AAB 수동 업로드 (Google Play 정책)

> ⚠️ **중요 (Google Play 정책)**  
> Google Play Developer API를 통한 자동 배포(upload-google-play)를 사용하려면, **해당 앱의 첫 번째 AAB를 Google Play Console 웹사이트에서 반드시 1회 수동으로 업로드하여 앱을 생성**해 두어야 합니다.

1. 최신 빌드된 Signed AAB 다운로드:
   - 경로: G:\내 드라이브\TT_Project\TodayPick\tester\TodayPick-Capacitor-CANONICAL-1.0.0-vc43.aab
2. [Google Play Console](https://play.google.com/console) 접속
3. TodayPick 앱 선택 (없다면 앱 생성: 패키지명 com.todaypick.app)
4. 좌측 메뉴 **테스트 > 내부 테스트 (Internal testing)** 이동
5. **새 버전 만들기** 클릭 후 다운로드한 .aab 파일을 드래그하여 업로드
6. 버전 저장 및 출시 완료

---

## 3. 사전 필수 2단계: 서비스 계정(Service Account) 생성 및 키 발급

1. **Google Cloud Console / Play Console 연동**:
   - Google Play Console > **설정 > API 액세스 (API access)** 이동
   - Google Cloud 프로젝트와 연결
2. **서비스 계정 만들기**:
   - **새 서비스 계정 만들기** 클릭 > Google Cloud 콘솔로 이동
   - 서비스 계정 이름: 	odaypick-play-deployer
   - 역할(Role): 서비스 계정 사용자 (Service Account User) 부여
3. **JSON 키 생성 및 다운로드**:
   - 생성된 서비스 계정 클릭 > **키 (Keys)** 탭 > **키 추가 > 새 키 만들기 > JSON** 선택
   - 다운로드된 JSON 파일(예: pc-api-...json)을 안전한 로컬 경로에 보관.
4. **Google Play Console 권한 부여**:
   - Google Play Console > **사용자 및 권한 (Users and permissions)** 이동
   - 새로 생성된 서비스 계정 이메일 초대
   - **앱 권한** 탭에서 TodayPick 선택
   - 권한:
     - 출시 관리 (Release management)
     - 내부 테스트 트랙에 앱 출시 (Release apps to testing tracks)
     - 프로덕션 트랙 출시 등 필요한 릴리즈 권한 체크 후 저장.

---

## 4. GitHub Secret 등록 (1회 설정)

다운로드한 서비스 계정 JSON 파일의 **전체 텍스트 내용**을 복사하여 GitHub Secrets에 등록합니다.

- **저장소**: https://github.com/johnpark236-tech/todaypick-web/settings/secrets/actions
- **Secret 이름**: PLAY_CONSOLE_SERVICE_ACCOUNT_JSON
- **Secret 값**: JSON 파일의 내용 전체 (중괄호 { ... } 포함)

> 🔒 **보안 보장**:
> 서비스 계정 키는 GitHub Secrets에 안전하게 암호화 보관되며, GitHub Actions 실행 로그나 커밋, 코드베이스에 절대 노출되지 않습니다.

---

## 5. 테스터 초대 및 앱 설치 방법

1. Google Play Console > **내부 테스트 > 테스터 (Testers)** 탭 이동
2. 테스터 이메일 그룹(예: 	odaypick-testers) 생성 후 검수자들의 Google 계정(Gmail) 추가
3. **참여 링크 복사 (How testers join your test)**
4. 테스터가 안드로이드 폰에서 해당 링크를 열고 **[프로그램 참여]** 클릭 후 **Google Play에서 다운로드** 버튼 터치
5. 이후부터는 새 버전 빌드 시 Google Play 앱 업데이트를 통해 자동으로 최신 버전이 반영됩니다.
