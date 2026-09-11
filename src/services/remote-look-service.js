const LEGACY_STORAGE_KEY = 'todaypick_remote_look_manifest_v1';
const CATALOG_STORAGE_PREFIX = 'todaypick_remote_look_catalog_v2:';
const INDEX_STORAGE_KEY = 'todaypick_remote_look_index_v2';

const SEASONS = ['spring', 'summer', 'autumn', 'winter'];
const SEASON_LABELS = {
  spring: '봄',
  summer: '여름',
  autumn: '가을',
  winter: '겨울'
};

export function getSeasonForMonth(month) {
  const n = Number(month);
  if ([3, 4, 5].includes(n)) return 'spring';
  if ([6, 7, 8].includes(n)) return 'summer';
  if ([9, 10, 11].includes(n)) return 'autumn';
  return 'winter';
}

export function getCurrentSeason(date = new Date()) {
  return getSeasonForMonth(date.getMonth() + 1);
}

export function getSeasonLabel(season) {
  return SEASON_LABELS[season] || SEASON_LABELS.autumn;
}

export function makeCatalogKey(season, gender, ageGroup) {
  return `${season}/${gender}_${Number(ageGroup)}`;
}

export const RemoteLookService = {
  async load(config = {}) {
    const remoteCfg = config.remoteLooks || {};

    if (!remoteCfg.enabled || !remoteCfg.manifestUrl) {
      return { manifest: null, source: 'disabled' };
    }

    const cached = this.getCachedManifest();

    try {
      const manifest = await fetchJson(remoteCfg.manifestUrl);
      const valid = validateManifest(manifest);
      if (!valid.ok) throw new Error(valid.reason);
      localStorage.setItem(LEGACY_STORAGE_KEY, JSON.stringify(manifest));
      return { manifest, source: 'remote' };
    } catch (err) {
      console.warn('[RemoteLookService] using last-known-good or bundled fallback:', err);
      return { manifest: cached, source: cached ? 'cache' : 'fallback' };
    }
  },

  async loadCatalog(config = {}, selection = {}) {
    const remoteCfg = config.remoteLooks || {};
    const season = selection.season || getCurrentSeason();
    const gender = selection.gender || 'female';
    const ageGroup = Number(selection.ageGroup || 20);
    const cacheKey = CATALOG_STORAGE_PREFIX + makeCatalogKey(season, gender, ageGroup);

    if (!remoteCfg.enabled) {
      return { catalog: null, source: 'disabled' };
    }

    const cached = this.getCachedCatalog(cacheKey);

    try {
      const indexUrl = remoteCfg.indexUrl || remoteCfg.catalogIndexUrl;
      if (indexUrl) {
        const index = await this.loadIndex(indexUrl);
        const segment = `${gender}_${ageGroup}`;
        const catalogUrl = index?.seasons?.[season]?.[segment];
        if (!catalogUrl) {
          return { catalog: cached, source: cached ? 'cache' : 'empty' };
        }
        const catalog = await fetchJson(catalogUrl);
        const valid = validateCatalog(catalog, { season, gender, ageGroup });
        if (!valid.ok) throw new Error(valid.reason);
        localStorage.setItem(cacheKey, JSON.stringify(catalog));
        return { catalog, source: 'remote' };
      }

      const legacy = await this.load(config);
      if (!legacy.manifest) {
        return { catalog: cached, source: cached ? 'cache' : legacy.source };
      }
      const entry = legacy.manifest.segments?.[`${gender}_${ageGroup}`];
      if (!entry) return { catalog: cached, source: cached ? 'cache' : 'empty' };
      const catalog = legacyEntryToCatalog(entry, { season, gender, ageGroup });
      localStorage.setItem(cacheKey, JSON.stringify(catalog));
      return { catalog, source: legacy.source };
    } catch (err) {
      console.warn('[RemoteLookService] using cached catalog or bundled fallback:', err);
      return { catalog: cached, source: cached ? 'cache' : 'fallback' };
    }
  },

  async loadIndex(indexUrl) {
    const cached = this.getCachedIndex();
    try {
      const index = await fetchJson(indexUrl);
      const valid = validateIndex(index);
      if (!valid.ok) throw new Error(valid.reason);
      localStorage.setItem(INDEX_STORAGE_KEY, JSON.stringify(index));
      return index;
    } catch (err) {
      if (cached) return cached;
      throw err;
    }
  },

  getCachedManifest() {
    try {
      const raw = localStorage.getItem(LEGACY_STORAGE_KEY);
      if (!raw) return null;
      const manifest = JSON.parse(raw);
      return validateManifest(manifest).ok ? manifest : null;
    } catch {
      return null;
    }
  },

  getCachedIndex() {
    try {
      const raw = localStorage.getItem(INDEX_STORAGE_KEY);
      if (!raw) return null;
      const index = JSON.parse(raw);
      return validateIndex(index).ok ? index : null;
    } catch {
      return null;
    }
  },

  getCachedCatalog(cacheKey) {
    try {
      const raw = localStorage.getItem(cacheKey);
      if (!raw) return null;
      const catalog = JSON.parse(raw);
      return validateCatalog(catalog).ok ? catalog : null;
    } catch {
      return null;
    }
  }
};

async function fetchJson(url) {
  const res = await fetch(`${url}${url.includes('?') ? '&' : '?'}t=${Date.now()}`, {
    cache: 'no-store'
  });
  if (!res.ok) throw new Error(`manifest fetch failed: ${res.status}`);
  return res.json();
}

function validateIndex(index) {
  if (!index || index.schema_version !== 2 || !index.seasons || typeof index.seasons !== 'object') {
    return { ok: false, reason: 'invalid index schema' };
  }
  for (const season of Object.keys(index.seasons)) {
    if (!SEASONS.includes(season)) return { ok: false, reason: `invalid season: ${season}` };
    for (const [segment, url] of Object.entries(index.seasons[season] || {})) {
      if (!/^(female|male)_(10|20|30|40|50|60)$/.test(segment)) {
        return { ok: false, reason: `invalid segment: ${segment}` };
      }
      if (!validatePublicUrl(url)) return { ok: false, reason: `unsafe catalog url: ${segment}` };
    }
  }
  return { ok: true };
}

function validateManifest(manifest) {
  if (!manifest || manifest.schema_version !== 1 || !manifest.segments) {
    return { ok: false, reason: 'invalid schema' };
  }
  for (const [segment, entry] of Object.entries(manifest.segments)) {
    if (!/^(female|male)_(10|20|30|40|50|60)$/.test(segment)) {
      return { ok: false, reason: `invalid segment: ${segment}` };
    }
    const valid = validateLookList(entry.looks, { requirePublicUrls: true });
    if (!valid.ok) return { ok: false, reason: `segment ${segment} ${valid.reason}` };
  }
  return { ok: true };
}

function validateCatalog(catalog, expected = {}) {
  if (!catalog || catalog.schema_version !== 2) {
    return { ok: false, reason: 'invalid catalog schema' };
  }
  if (expected.season && catalog.season !== expected.season) return { ok: false, reason: 'season mismatch' };
  if (expected.gender && catalog.gender !== expected.gender) return { ok: false, reason: 'gender mismatch' };
  if (expected.ageGroup && Number(catalog.age_group) !== Number(expected.ageGroup)) {
    return { ok: false, reason: 'age mismatch' };
  }
  if (Number(catalog.count) !== catalog.looks?.length) {
    return { ok: false, reason: 'count mismatch' };
  }
  return validateLookList(catalog.looks, { requirePublicUrls: true });
}

function validateLookList(looks, { requirePublicUrls = false } = {}) {
  if (!Array.isArray(looks) || looks.length < 1) {
    return { ok: false, reason: 'must have at least 1 look' };
  }
  const ids = new Set();
  for (const look of looks) {
    if (!look || typeof look !== 'object') return { ok: false, reason: 'has invalid look entry' };
    if (!look.id || ids.has(look.id)) return { ok: false, reason: 'has invalid or duplicate look id' };
    ids.add(look.id);
    if (!look.sha256 || String(look.sha256).length !== 64) return { ok: false, reason: 'has invalid sha256' };
    if (requirePublicUrls && !validatePublicUrl(look.url)) return { ok: false, reason: 'has non-public URL' };
  }
  return { ok: true };
}

function validatePublicUrl(url) {
  return typeof url === 'string' && url.startsWith('https://') && !url.includes('localhost') && !url.startsWith('file:');
}

function legacyEntryToCatalog(entry, { season, gender, ageGroup }) {
  const looks = Array.isArray(entry.looks) ? entry.looks : [];
  return {
    schema_version: 2,
    season,
    gender,
    age_group: Number(ageGroup),
    count: looks.length,
    updated_at: entry.source_date || null,
    looks
  };
}
