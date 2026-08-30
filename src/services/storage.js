// Local storage manager for TodayPick
const STORAGE_KEYS = {
  SAVED_LOOKS: 'todaypick_saved_looks_v1',
  UI_CONFIG: 'todaypick_ui_config_v1',
  SEARCH_HISTORY: 'todaypick_search_history_v1'
};

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

  static saveUiConfig(cfg) {
    localStorage.setItem(STORAGE_KEYS.UI_CONFIG, JSON.stringify(cfg));
  }

  static clearUiConfig() {
    localStorage.removeItem(STORAGE_KEYS.UI_CONFIG);
  }
}
