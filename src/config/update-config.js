// TodayPick 업데이트 체크 설정
// manifestUrl이 비어 있으면 실제 endpoint가 준비되지 않은 상태입니다.
// useMock=true일 때만 mockManifestPath를 사용합니다 (production에서 false 유지).
//
// PLAY UPDATE RELEASE ORDER:
//   1. AAB 생성
//   2. Play Console 업로드
//   3. Track 릴리스 활성화 확인
//   4. Play에서 새 버전 실제 제공 확인
//   5. 마지막으로 manifest의 latestVersionCode 갱신

export const UPDATE_CONFIG = {
  manifestUrl: '',                               // Cloudflare Worker/Pages URL (미설정)
  mockManifestPath: '/update-manifest.mock.json', // 로컬 테스트용 mock
  useMock: false,                                // production에서 반드시 false

  defaultCheckIntervalMinutes: 30,
  requestTimeoutMs: 5000,
  dismissCooldownHours: 6,

  storageKey: 'todaypick_update_state',
};
