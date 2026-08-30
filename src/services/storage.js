import { CloudSettingsService } from './cloudSettings.js';

// Local storage manager for TodayPick
const STORAGE_KEYS = {
  SAVED_LOOKS: 'todaypick_saved_looks_v1',
  UI_CONFIG: 'todaypick_ui_config_v1',
  SEARCH_HISTORY: 'todaypick_search_history_v1'
};

const DEFAULT_MODE_BUTTON_SCALE = 2.0;

export class StorageService {
  static getSavedLooks() {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.SAVED_LOOKS);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  }

  static saveLook(look) {
    const looks = this.getSavedLooks();
    if (!looks.some(l => l.id === look.id && l.mode === look.mode)) {
      looks.unshift({
        id: look.id,
        mode: look.mode,
        title: look.title,
        image: look.image,
        totalPrice: look.totalPrice,
        savedAt: new Date().toISOString()
      });
      localStorage.setItem(STORAGE_KEYS.SAVED_LOOKS, JSON.stringify(looks));
      return true;
    }
    return false;
  }

  static removeLook(id, mode) {
    let looks = this.getSavedLooks();
    looks = looks.filter(l => !(l.id === id && l.mode === mode));
    localStorage.setItem(STORAGE_KEYS.SAVED_LOOKS, JSON.stringify(looks));
    return looks;
  }

  static isSaved(id, mode) {
    const looks = this.getSavedLooks();
    return looks.some(l => l.id === id && l.mode === mode);
  }

  static getUiConfig() {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.UI_CONFIG);
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  }

  // Merge instead of replace so independently managed settings survive saves.
  static saveUiConfig(cfg) {
    const current = this.getUiConfig() || {};
    localStorage.setItem(STORAGE_KEYS.UI_CONFIG, JSON.stringify({ ...current, ...cfg }));
  }

  static clearUiConfig() {
    localStorage.removeItem(STORAGE_KEYS.UI_CONFIG);
  }
}

function getModeButtonScale() {
  const cfg = StorageService.getUiConfig();
  const parsed = Number(cfg?.modeButtonScale);
  return Number.isFinite(parsed) ? Math.max(1, Math.min(2.2, parsed)) : DEFAULT_MODE_BUTTON_SCALE;
}

function ensureModeScaleStyles() {
  let style = document.getElementById('todaypick-mode-scale-style');
  if (!style) {
    style = document.createElement('style');
    style.id = 'todaypick-mode-scale-style';
    document.head.appendChild(style);
  }
  return style;
}

function applyModeButtonScale(scale) {
  const safe = Math.max(1, Math.min(2.2, Number(scale) || DEFAULT_MODE_BUTTON_SCALE));
  const style = ensureModeScaleStyles();
  const titlePx = 11.5 * safe;
  const subPx = 10.5 * safe;
  const arrowPx = 9 * safe;
  const tabPadY = 5 * safe;
  const tabPadX = 6 * safe;
  const tabsPad = 3 * safe;
  const gap = 3 * safe;
  const outerGap = 6 * safe;
  const radius = 10 * Math.min(safe, 1.7);
  const tabRadius = 7 * Math.min(safe, 1.7);
  const headerHeight = Math.round(72 + (safe - 1) * 38);

  style.textContent = `
    .app-header { min-height: ${headerHeight}px; height: ${headerHeight}px; }
    .mode-tabs { gap: ${outerGap}px; padding: ${tabsPad}px; border-radius: ${radius}px; }
    .mode-tab { padding: ${tabPadY}px ${tabPadX}px; gap: ${gap}px; border-radius: ${tabRadius}px; }
    .mode-tab-title { font-size: ${titlePx}px !important; line-height: 1.05; }
    .mode-tab-sub { font-size: ${subPx}px !important; line-height: 1.05; }
    .mode-tab-arrow { font-size: ${arrowPx}px !important; }
  `;
}

function collectPersistedSettings() {
  return {
    ui: StorageService.getUiConfig() || {},
    audio: {
      bgmEnabled: localStorage.getItem('todaypick_bgm_enabled') !== 'false',
      bgmVolume: Number(localStorage.getItem('todaypick_bgm_volume') ?? 0.55),
      sfxVolume: Number(localStorage.getItem('todaypick_sfx_volume') ?? 0.50)
    }
  };
}

function restorePersistedSettings(payload) {
  const settings = payload?.settings || payload;
  if (!settings || typeof settings !== 'object') return false;

  if (settings.ui && typeof settings.ui === 'object') {
    StorageService.saveUiConfig(settings.ui);
  }
  if (settings.audio && typeof settings.audio === 'object') {
    if (typeof settings.audio.bgmEnabled === 'boolean') {
      localStorage.setItem('todaypick_bgm_enabled', String(settings.audio.bgmEnabled));
    }
    if (Number.isFinite(Number(settings.audio.bgmVolume))) {
      localStorage.setItem('todaypick_bgm_volume', String(settings.audio.bgmVolume));
    }
    if (Number.isFinite(Number(settings.audio.sfxVolume))) {
      localStorage.setItem('todaypick_sfx_volume', String(settings.audio.sfxVolume));
    }
  }

  applyModeButtonScale(getModeButtonScale());
  return true;
}

function makeSettingItem() {
  const wrap = document.createElement('div');
  wrap.className = 'setting-item';
  wrap.id = 'setting-mode-button-scale';
  wrap.innerHTML = `
    <div class="setting-label-row">
      <span>여성/남성 버튼 크기</span>
      <span id="val-mode-button-scale">2.0x</span>
    </div>
    <input type="range" id="slider-mode-button-scale" class="setting-slider" min="1" max="2.2" step="0.1" value="2" />
  `;
  return wrap;
}

function makeGoogleSyncGroup() {
  const group = document.createElement('div');
  group.className = 'settings-group';
  group.id = 'settings-google-sync';
  group.innerHTML = `
    <h3 class="settings-group-title">Google 계정 설정 동기화</h3>
    <div class="setting-item">
      <div class="setting-label-row">
        <span>계정</span>
        <span id="google-sync-email">${localStorage.getItem('todaypick_google_account_email') || '연결 안 됨'}</span>
      </div>
      <p id="google-sync-status" style="font-size:12px; color:#6B7280; margin:6px 0 10px; line-height:1.45;">
        Google 계정에 설정을 저장하면 앱 업데이트 후에도 복원할 수 있습니다.
      </p>
      <div class="settings-btn-row">
        <button id="btn-google-connect" class="btn-secondary">Google 연결</button>
        <button id="btn-google-restore" class="btn-secondary">클라우드 불러오기</button>
      </div>
    </div>
  `;
  return group;
}

async function initSettingsEnhancements() {
  applyModeButtonScale(getModeButtonScale());

  const settingsView = document.getElementById('view-settings');
  if (!settingsView) return;

  const uiGroup = settingsView.querySelector('.settings-group');
  const saveRow = uiGroup?.querySelector('.settings-btn-row');
  if (uiGroup && saveRow && !document.getElementById('setting-mode-button-scale')) {
    const item = makeSettingItem();
    uiGroup.insertBefore(item, saveRow);

    const slider = item.querySelector('#slider-mode-button-scale');
    const value = item.querySelector('#val-mode-button-scale');
    const current = getModeButtonScale();
    slider.value = current;
    value.textContent = `${current.toFixed(1)}x`;

    slider.addEventListener('input', () => {
      const scale = Number(slider.value);
      value.textContent = `${scale.toFixed(1)}x`;
      applyModeButtonScale(scale);
    });
  }

  if (!document.getElementById('settings-google-sync')) {
    const systemGroup = Array.from(settingsView.querySelectorAll('.settings-group'))
      .find(el => el.querySelector('.settings-group-title')?.textContent?.includes('시스템'));
    const googleGroup = makeGoogleSyncGroup();
    if (systemGroup) settingsView.insertBefore(googleGroup, systemGroup);
    else settingsView.appendChild(googleGroup);
  }

  await CloudSettingsService.init();
  const status = document.getElementById('google-sync-status');
  const email = document.getElementById('google-sync-email');
  const btnConnect = document.getElementById('btn-google-connect');
  const btnRestore = document.getElementById('btn-google-restore');

  if (!CloudSettingsService.isConfigured() && status) {
    status.textContent = 'Google OAuth Client ID 설정 후 계정별 Drive 동기화가 활성화됩니다. 로컬 설정 저장은 정상 동작합니다.';
  }

  btnConnect?.addEventListener('click', async () => {
    try {
      status.textContent = 'Google 계정 연결 중...';
      const account = await CloudSettingsService.signIn();
      email.textContent = account || 'Google 계정 연결됨';
      status.textContent = 'Google Drive 설정 동기화가 연결되었습니다.';
    } catch (err) {
      status.textContent = `Google 연결 실패: ${err.message}`;
    }
  });

  btnRestore?.addEventListener('click', async () => {
    try {
      status.textContent = 'Google Drive에서 설정을 불러오는 중...';
      const cloud = await CloudSettingsService.loadSettings();
      if (!cloud) {
        status.textContent = 'Google Drive에 저장된 TodayPick 설정이 없습니다.';
        return;
      }
      restorePersistedSettings(cloud);
      email.textContent = CloudSettingsService.accountEmail || localStorage.getItem('todaypick_google_account_email') || 'Google 계정 연결됨';
      status.textContent = '클라우드 설정을 복원했습니다. 오디오 전체 적용은 앱을 다시 열면 완료됩니다.';
      const slider = document.getElementById('slider-mode-button-scale');
      const value = document.getElementById('val-mode-button-scale');
      const current = getModeButtonScale();
      if (slider) slider.value = current;
      if (value) value.textContent = `${current.toFixed(1)}x`;
    } catch (err) {
      status.textContent = `클라우드 불러오기 실패: ${err.message}`;
    }
  });

  const saveButton = document.getElementById('btn-save-settings');
  saveButton?.addEventListener('click', () => {
    const slider = document.getElementById('slider-mode-button-scale');
    const scale = slider ? Number(slider.value) : getModeButtonScale();
    StorageService.saveUiConfig({ modeButtonScale: scale });
    applyModeButtonScale(scale);

    // Defer cloud write so the existing main.js save handler can persist its fields first.
    setTimeout(async () => {
      if (!CloudSettingsService.isConfigured()) {
        if (status) status.textContent = '로컬 설정 저장 완료. Google OAuth Client ID 설정 후 계정별 Drive 저장이 활성화됩니다.';
        return;
      }
      try {
        if (status) status.textContent = 'Google Drive에 설정 저장 중...';
        await CloudSettingsService.saveSettings(collectPersistedSettings());
        if (email) email.textContent = CloudSettingsService.accountEmail || localStorage.getItem('todaypick_google_account_email') || 'Google 계정 연결됨';
        if (status) status.textContent = '설정이 로컬 + Google Drive에 저장되었습니다.';
      } catch (err) {
        if (status) status.textContent = `로컬 저장 완료 / Google Drive 저장 실패: ${err.message}`;
      }
    }, 0);
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSettingsEnhancements, { once: true });
} else {
  queueMicrotask(initSettingsEnhancements);
}
