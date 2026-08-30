const DRIVE_SCOPE = 'openid email https://www.googleapis.com/auth/drive.appdata';
const SETTINGS_FILE_NAME = 'TodayPick-settings.json';

class CloudSettingsServiceImpl {
  constructor() {
    this.clientId = '';
    this.accessToken = '';
    this.accountEmail = '';
    this.tokenClient = null;
    this.initialized = false;
  }

  async init() {
    if (this.initialized) return;
    this.initialized = true;
    try {
      const cfg = await fetch('/config.json').then(r => r.json());
      this.clientId = String(cfg.googleOAuthClientId || '').trim();
    } catch {
      this.clientId = '';
    }
  }

  isConfigured() {
    return Boolean(this.clientId);
  }

  async loadIdentityScript() {
    if (window.google?.accounts?.oauth2) return;
    await new Promise((resolve, reject) => {
      const existing = document.querySelector('script[data-todaypick-google-identity]');
      if (existing) {
        existing.addEventListener('load', resolve, { once: true });
        existing.addEventListener('error', reject, { once: true });
        return;
      }
      const s = document.createElement('script');
      s.src = 'https://accounts.google.com/gsi/client';
      s.async = true;
      s.defer = true;
      s.dataset.todaypickGoogleIdentity = '1';
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  async signIn() {
    await this.init();
    if (!this.clientId) {
      throw new Error('Google OAuth Client ID가 설정되지 않았습니다.');
    }
    await this.loadIdentityScript();

    const token = await new Promise((resolve, reject) => {
      this.tokenClient = window.google.accounts.oauth2.initTokenClient({
        client_id: this.clientId,
        scope: DRIVE_SCOPE,
        callback: (response) => {
          if (response?.error) reject(new Error(response.error));
          else resolve(response.access_token);
        }
      });
      this.tokenClient.requestAccessToken({ prompt: '' });
    });

    this.accessToken = token;
    const profile = await fetch('https://openidconnect.googleapis.com/v1/userinfo', {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (profile.ok) {
      const data = await profile.json();
      this.accountEmail = data.email || '';
      if (this.accountEmail) localStorage.setItem('todaypick_google_account_email', this.accountEmail);
    }
    return this.accountEmail;
  }

  headers(extra = {}) {
    if (!this.accessToken) throw new Error('Google 로그인이 필요합니다.');
    return { Authorization: `Bearer ${this.accessToken}`, ...extra };
  }

  async findSettingsFile() {
    const q = encodeURIComponent(`name='${SETTINGS_FILE_NAME}' and trashed=false`);
    const res = await fetch(`https://www.googleapis.com/drive/v3/files?spaces=appDataFolder&q=${q}&fields=files(id,name,modifiedTime)`, {
      headers: this.headers()
    });
    if (!res.ok) throw new Error(`Drive 조회 실패 (${res.status})`);
    const data = await res.json();
    return data.files?.[0] || null;
  }

  async loadSettings() {
    if (!this.accessToken) await this.signIn();
    const file = await this.findSettingsFile();
    if (!file) return null;
    const res = await fetch(`https://www.googleapis.com/drive/v3/files/${file.id}?alt=media`, {
      headers: this.headers()
    });
    if (!res.ok) throw new Error(`Drive 설정 불러오기 실패 (${res.status})`);
    return res.json();
  }

  async saveSettings(payload) {
    if (!this.accessToken) await this.signIn();
    const body = JSON.stringify({
      schemaVersion: 1,
      accountEmail: this.accountEmail || localStorage.getItem('todaypick_google_account_email') || '',
      savedAt: new Date().toISOString(),
      settings: payload
    }, null, 2);

    const existing = await this.findSettingsFile();
    if (existing) {
      const res = await fetch(`https://www.googleapis.com/upload/drive/v3/files/${existing.id}?uploadType=media`, {
        method: 'PATCH',
        headers: this.headers({ 'Content-Type': 'application/json; charset=UTF-8' }),
        body
      });
      if (!res.ok) throw new Error(`Drive 설정 업데이트 실패 (${res.status})`);
      return existing.id;
    }

    const boundary = `todaypick_${Date.now()}`;
    const multipart = [
      `--${boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n${JSON.stringify({ name: SETTINGS_FILE_NAME, parents: ['appDataFolder'] })}\r\n`,
      `--${boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n${body}\r\n`,
      `--${boundary}--`
    ].join('');

    const res = await fetch('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id', {
      method: 'POST',
      headers: this.headers({ 'Content-Type': `multipart/related; boundary=${boundary}` }),
      body: multipart
    });
    if (!res.ok) throw new Error(`Drive 설정 생성 실패 (${res.status})`);
    const data = await res.json();
    return data.id;
  }
}

export const CloudSettingsService = new CloudSettingsServiceImpl();
