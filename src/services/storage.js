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
      sfxEnabled: localStorage.getItem('todaypick_sfx_enabled') !== 'false',
      bgmVolume: Number(localStorage.getItem('todaypick_bgm_volume') ?? 0.55),
      sfxVolume: Number(localStorage.getItem('todaypick_sfx_volume') ?? 0.35)
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
    if (typeof settings.audio.sfxEnabled === 'boolean') {
      localStorage.setItem('todaypick_sfx_enabled', String(settings.audio.sfxEnabled));
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

export function initSettingsEnhancements() {
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

  const saveButton = document.getElementById('btn-save-settings');
  saveButton?.addEventListener('click', () => {
    const slider = document.getElementById('slider-mode-button-scale');
    const scale = slider ? Number(slider.value) : getModeButtonScale();
    StorageService.saveUiConfig({ modeButtonScale: scale });
    applyModeButtonScale(scale);
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSettingsEnhancements, { once: true });
} else {
  queueMicrotask(initSettingsEnhancements);
}
