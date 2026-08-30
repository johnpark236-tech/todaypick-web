/**
 * TodayPick Google Drive Cloud Settings Sync Service
 * Uses Google OAuth 2.0 and Drive appDataFolder for private user settings sync
 */

const DRIVE_FILE_NAME = 'TodayPick-settings.json';
const SCOPES = 'https://www.googleapis.com/auth/drive.appdata https://www.googleapis.com/auth/userinfo.email';

export class GoogleSyncService {
  constructor(clientId) {
    this.clientId = clientId || '363284724091-g5q91b5vh37hncm6e1v7lnephljhhj27.apps.googleusercontent.com';
    this.accessToken = null;
    this.tokenExpiresAt = 0;
    this.userEmail = null;
    this.userSub = null;
    this.lastSyncTime = null;
    this.tokenClient = null;

    this.restoreSession();
  }

  restoreSession() {
    try {
      const saved = localStorage.getItem('todaypick_google_session');
      if (saved) {
        const data = JSON.parse(saved);
        if (data.accessToken && Date.now() < data.tokenExpiresAt) {
          this.accessToken = data.accessToken;
          this.tokenExpiresAt = data.tokenExpiresAt;
          this.userEmail = data.userEmail;
          this.userSub = data.userSub;
          this.lastSyncTime = data.lastSyncTime;
        } else {
          localStorage.removeItem('todaypick_google_session');
        }
      }
    } catch (e) {
      console.warn('[GoogleSync] Failed to restore session:', e);
    }
  }

  saveSession() {
    try {
      localStorage.setItem('todaypick_google_session', JSON.stringify({
        accessToken: this.accessToken,
        tokenExpiresAt: this.tokenExpiresAt,
        userEmail: this.userEmail,
        userSub: this.userSub,
        lastSyncTime: this.lastSyncTime
      }));
    } catch (e) {
      console.warn('[GoogleSync] Failed to save session:', e);
    }
  }

  clearSession() {
    this.accessToken = null;
    this.tokenExpiresAt = 0;
    this.userEmail = null;
    this.userSub = null;
    this.lastSyncTime = null;
    localStorage.removeItem('todaypick_google_session');
  }

  isConnected() {
    return Boolean(this.accessToken && Date.now() < this.tokenExpiresAt);
  }

  getUserEmail() {
    return this.userEmail || '';
  }

  getLastSyncTime() {
    return this.lastSyncTime;
  }

  /**
   * Initialize Google Identity Services if available
   */
  async initGis() {
    if (window.google?.accounts?.oauth2) {
      return true;
    }
    return new Promise((resolve) => {
      if (document.getElementById('gsi-client-script')) {
        return resolve(Boolean(window.google?.accounts?.oauth2));
      }
      const script = document.createElement('script');
      script.id = 'gsi-client-script';
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = () => resolve(Boolean(window.google?.accounts?.oauth2));
      script.onerror = () => resolve(false);
      document.head.appendChild(script);
    });
  }

  /**
   * Connect Google Account
   */
  async connect() {
    await this.initGis();

    return new Promise((resolve, reject) => {
      // Flow 1: Google Identity Services Token Client
      if (window.google?.accounts?.oauth2) {
        try {
          this.tokenClient = window.google.accounts.oauth2.initTokenClient({
            client_id: this.clientId,
            scope: SCOPES,
            callback: async (response) => {
              if (response.error) {
                return reject(new Error(response.error_description || response.error));
              }
              this.accessToken = response.access_token;
              this.tokenExpiresAt = Date.now() + (parseInt(response.expires_in, 10) || 3500) * 1000;

              // Fetch User Profile
              await this.fetchUserProfile();
              this.saveSession();
              resolve({ success: true, email: this.userEmail });
            }
          });
          this.tokenClient.requestAccessToken({ prompt: 'consent' });
          return;
        } catch (e) {
          console.warn('[GoogleSync] GIS TokenClient init error, trying web popup fallback:', e);
        }
      }

      // Flow 2: OAuth 2.0 Web Popup / Redirect fallback for Desktop / Installed Client ID
      const redirectUri = window.location.origin;
      const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
        `client_id=${encodeURIComponent(this.clientId)}&` +
        `redirect_uri=${encodeURIComponent(redirectUri)}&` +
        `response_type=token&` +
        `scope=${encodeURIComponent(SCOPES)}&` +
        `prompt=select_account`;

      const popup = window.open(authUrl, 'GoogleAuth', 'width=500,height=600');
      if (!popup) {
        return reject(new Error('Popup blocked by browser. Please allow popups for Google Login.'));
      }

      const checkTimer = setInterval(() => {
        try {
          if (popup.closed) {
            clearInterval(checkTimer);
            if (!this.isConnected()) {
              reject(new Error('Google login window closed.'));
            }
          }
          const hash = popup.location.hash;
          if (hash && hash.includes('access_token')) {
            clearInterval(checkTimer);
            const params = new URLSearchParams(hash.substring(1));
            const token = params.get('access_token');
            const expiresIn = params.get('expires_in') || '3600';
            popup.close();

            this.accessToken = token;
            this.tokenExpiresAt = Date.now() + parseInt(expiresIn, 10) * 1000;
            this.fetchUserProfile().then(() => {
              this.saveSession();
              resolve({ success: true, email: this.userEmail });
            }).catch(reject);
          }
        } catch (err) {
          // Cross-origin until redirect
        }
      }, 500);
    });
  }

  async fetchUserProfile() {
    if (!this.accessToken) return;
    try {
      const res = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
        headers: { Authorization: `Bearer ${this.accessToken}` }
      });
      if (res.ok) {
        const info = await res.json();
        this.userEmail = info.email;
        this.userSub = info.sub;
      }
    } catch (e) {
      console.warn('[GoogleSync] Failed to fetch user profile:', e);
    }
  }

  /**
   * Save settings payload to Google Drive appDataFolder
   */
  async saveSettingsToCloud(settingsData) {
    if (!this.isConnected()) {
      return { success: false, reason: 'NOT_CONNECTED' };
    }

    const payload = {
      version: 1,
      appName: 'TodayPick',
      updatedAt: new Date().toISOString(),
      userEmail: this.userEmail,
      userSub: this.userSub,
      settings: settingsData
    };

    try {
      // 1. Check if TodayPick-settings.json exists in appDataFolder
      const existingFileId = await this.findSettingsFileId();

      const metadata = {
        name: DRIVE_FILE_NAME,
        mimeType: 'application/json',
        ...(existingFileId ? {} : { parents: ['appDataFolder'] })
      };

      const boundary = 'foo_bar_todaypick_sync';
      const delimiter = `\r\n--${boundary}\r\n`;
      const closeDelimiter = `\r\n--${boundary}--`;

      const multipartRequestBody =
        delimiter +
        'Content-Type: application/json; charset=UTF-8\r\n\r\n' +
        JSON.stringify(metadata) +
        delimiter +
        'Content-Type: application/json\r\n\r\n' +
        JSON.stringify(payload, null, 2) +
        closeDelimiter;

      let url = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart';
      let method = 'POST';

      if (existingFileId) {
        url = `https://www.googleapis.com/upload/drive/v3/files/${existingFileId}?uploadType=multipart`;
        method = 'PATCH';
      }

      const res = await fetch(url, {
        method: method,
        headers: {
          Authorization: `Bearer ${this.accessToken}`,
          'Content-Type': `multipart/related; boundary=${boundary}`
        },
        body: multipartRequestBody
      });

      if (!res.ok) {
        const errText = await res.text();
        console.error('[GoogleSync] Drive save failed:', errText);
        return { success: false, reason: 'DRIVE_API_ERROR', details: errText };
      }

      this.lastSyncTime = payload.updatedAt;
      this.saveSession();
      return { success: true, updatedAt: payload.updatedAt };
    } catch (e) {
      console.error('[GoogleSync] Cloud save error:', e);
      return { success: false, reason: 'NETWORK_ERROR', error: e.message };
    }
  }

  /**
   * Load settings payload from Google Drive appDataFolder
   */
  async loadSettingsFromCloud() {
    if (!this.isConnected()) {
      return { success: false, reason: 'NOT_CONNECTED' };
    }

    try {
      const fileId = await this.findSettingsFileId();
      if (!fileId) {
        return { success: false, reason: 'NO_CLOUD_FILE_YET' };
      }

      const res = await fetch(`https://www.googleapis.com/drive/v3/files/${fileId}?alt=media`, {
        headers: { Authorization: `Bearer ${this.accessToken}` }
      });

      if (!res.ok) {
        return { success: false, reason: 'DRIVE_FETCH_ERROR' };
      }

      const cloudData = await res.json();
      this.lastSyncTime = cloudData.updatedAt || new Date().toISOString();
      this.saveSession();
      return { success: true, data: cloudData };
    } catch (e) {
      console.error('[GoogleSync] Cloud load error:', e);
      return { success: false, reason: 'NETWORK_ERROR', error: e.message };
    }
  }

  async findSettingsFileId() {
    const q = encodeURIComponent(`name = '${DRIVE_FILE_NAME}' and trashed = false`);
    const res = await fetch(
      `https://www.googleapis.com/drive/v3/files?spaces=appDataFolder&q=${q}&fields=files(id,name,modifiedTime)`,
      {
        headers: { Authorization: `Bearer ${this.accessToken}` }
      }
    );
    if (res.ok) {
      const data = await res.json();
      if (data.files && data.files.length > 0) {
        return data.files[0].id;
      }
    }
    return null;
  }
}
