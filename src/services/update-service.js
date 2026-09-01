// TodayPick In-App Update Check Service (vc68)
// manifest-based: Cloudflare Worker/Pages endpoint → version JSON 비교
// startup + foreground resume + periodic check 세 경로 모두 지원

import { UPDATE_CONFIG } from '../config/update-config.js';
import { ANDROID_VERSION_CODE } from '../config/version.js';

class UpdateCheckSvc {
  constructor() {
    this._checking     = false;
    this._timer        = null;
    this._dismissedCode = null;   // 이 session에서 dismiss한 latestVersionCode
    this._lastPromptedAt = null;  // 마지막 팝업 표시 timestamp
    this._onUpdateFound = null;   // callback: (manifest, isForce) => void
    this._lastManifest  = null;
  }

  // callback 등록 — main.js에서 다이얼로그 표시 로직을 넘겨받음
  onUpdateFound(cb) { this._onUpdateFound = cb; }

  // ── fetch ──────────────────────────────────────────────────

  async fetchManifest() {
    const cfg = UPDATE_CONFIG;
    let url = cfg.manifestUrl;

    if (!url) {
      if (!cfg.useMock) return null;
      url = cfg.mockManifestPath;
    }
    url += (url.includes('?') ? '&' : '?') + '_t=' + Date.now();

    const ctrl = new AbortController();
    const tid  = setTimeout(() => ctrl.abort(), cfg.requestTimeoutMs);
    try {
      const res = await fetch(url, { cache: 'no-store', signal: ctrl.signal });
      clearTimeout(tid);
      if (!res.ok) return null;
      return await res.json();
    } catch {
      clearTimeout(tid);
      console.log('[UpdateCheck] unavailable');
      return null;
    }
  }

  // ── version comparison ─────────────────────────────────────

  // Returns: 'UP_TO_DATE' | 'UPDATE_AVAILABLE' | 'FORCE_UPDATE'
  compareVersions(manifest) {
    if (!manifest) return 'UP_TO_DATE';
    const latest  = Number(manifest.latestVersionCode)  || 0;
    const minimum = Number(manifest.minimumVersionCode) || 0;
    const current = ANDROID_VERSION_CODE;

    if (current < minimum) return 'FORCE_UPDATE';
    if (manifest.forceUpdate === true && latest > current) return 'FORCE_UPDATE';
    if (latest > current) return 'UPDATE_AVAILABLE';
    return 'UP_TO_DATE';
  }

  // ── cooldown / dismiss ─────────────────────────────────────

  shouldPrompt(latestCode) {
    if (this._dismissedCode === latestCode) return false;
    if (this._lastPromptedAt) {
      const elapsed = (Date.now() - this._lastPromptedAt) / 3600000;
      if (elapsed < UPDATE_CONFIG.dismissCooldownHours) return false;
    }
    return true;
  }

  // "나중에" 클릭 시 호출
  dismissVersion(latestCode) {
    this._dismissedCode  = latestCode;
    this._lastPromptedAt = Date.now();
  }

  // ── persistent timing ──────────────────────────────────────

  isCheckDue() {
    const state = this._loadState();
    if (!state.lastCheckedAt) return true;
    const elapsed = (Date.now() - state.lastCheckedAt) / 60000;
    return elapsed >= UPDATE_CONFIG.defaultCheckIntervalMinutes;
  }

  saveLastCheck() {
    const state = this._loadState();
    state.lastCheckedAt = Date.now();
    this._saveState(state);
  }

  _loadState() {
    try {
      const raw = localStorage.getItem(UPDATE_CONFIG.storageKey);
      return raw ? JSON.parse(raw) : {};
    } catch { return {}; }
  }

  _saveState(s) {
    try { localStorage.setItem(UPDATE_CONFIG.storageKey, JSON.stringify(s)); } catch {}
  }

  // ── Play Store ─────────────────────────────────────────────

  openPlayStore(urlFromManifest) {
    const url = urlFromManifest || 'https://play.google.com/store/apps/details?id=com.todaypick.app';
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  // ── main entry ─────────────────────────────────────────────

  // forceCheck=true: skip isCheckDue (startup / foreground resume 시)
  async checkForUpdate(forceCheck = false) {
    if (this._checking) return;
    if (!forceCheck && !this.isCheckDue()) return;
    this._checking = true;
    try {
      const manifest = await this.fetchManifest();
      this.saveLastCheck();
      if (!manifest) return;
      this._lastManifest = manifest;

      const status  = this.compareVersions(manifest);
      if (status === 'UP_TO_DATE') return;
      const isForce = status === 'FORCE_UPDATE';

      if (!isForce && !this.shouldPrompt(manifest.latestVersionCode)) return;
      this._lastPromptedAt = Date.now();

      if (this._onUpdateFound) {
        this._onUpdateFound(manifest, isForce);
      }
    } finally {
      this._checking = false;
    }
  }

  // ── periodic timer — single timer, replaced on each call ──

  startPeriodicCheck(intervalMinutes) {
    this.stopPeriodicCheck();
    const ms = (intervalMinutes || UPDATE_CONFIG.defaultCheckIntervalMinutes) * 60 * 1000;
    this._timer = setInterval(() => { this.checkForUpdate(false); }, ms);
  }

  stopPeriodicCheck() {
    if (this._timer) { clearInterval(this._timer); this._timer = null; }
  }

  // last fetched manifest (for play store URL, version display)
  getLastManifest() { return this._lastManifest; }
}

export const UpdateCheckService = new UpdateCheckSvc();
