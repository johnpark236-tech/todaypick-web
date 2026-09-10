const STORAGE_KEY = 'todaypick_remote_look_manifest_v1';

export const RemoteLookService = {
  async load(config = {}) {
    const remoteCfg = config.remoteLooks || {};

    if (!remoteCfg.enabled || !remoteCfg.manifestUrl) {
      return { manifest: null, source: 'disabled' };
    }

    const cached = this.getCachedManifest();

    try {
      const res = await fetch(`${remoteCfg.manifestUrl}${remoteCfg.manifestUrl.includes('?') ? '&' : '?'}t=${Date.now()}`, {
        cache: 'no-store'
      });
      if (!res.ok) throw new Error(`manifest fetch failed: ${res.status}`);
      const manifest = await res.json();
      const valid = validateManifest(manifest);
      if (!valid.ok) throw new Error(valid.reason);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(manifest));
      return { manifest, source: 'remote' };
    } catch (err) {
      console.warn('[RemoteLookService] using last-known-good or bundled fallback:', err);
      return { manifest: cached, source: cached ? 'cache' : 'fallback' };
    }
  },

  getCachedManifest() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const manifest = JSON.parse(raw);
      return validateManifest(manifest).ok ? manifest : null;
    } catch {
      return null;
    }
  }
};

function validateManifest(manifest) {
  if (!manifest || manifest.schema_version !== 1 || !manifest.segments) {
    return { ok: false, reason: 'invalid schema' };
  }
  for (const [segment, entry] of Object.entries(manifest.segments)) {
    if (!/^(female|male)_(10|20|30|40|50|60)$/.test(segment)) {
      return { ok: false, reason: `invalid segment: ${segment}` };
    }
    if (!Array.isArray(entry.looks) || entry.looks.length !== 10) {
      return { ok: false, reason: `segment ${segment} does not have 10 looks` };
    }
    for (const look of entry.looks) {
      if (!look || !look.url || !look.sha256) {
        return { ok: false, reason: `segment ${segment} has invalid look entry` };
      }
    }
  }
  return { ok: true };
}
