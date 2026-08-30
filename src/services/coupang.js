// Coupang Worker Service
// Note: NO API secrets are included in the frontend.
// All requests go through Cloudflare Worker proxy.

export class CoupangService {
  constructor(workerUrl = 'https://todaypick-coupang-proxy.johnpark236.workers.dev') {
    this.workerUrl = workerUrl;
    this.cache = new Map();
  }

  async checkHealth() {
    try {
      const res = await fetch(`${this.workerUrl}/api/health`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn('[CoupangService] Health check failed:', err);
      return { status: 'error', error: err.message };
    }
  }

  async search(keyword) {
    if (!keyword || !keyword.trim()) return { ok: false, products: [] };
    const cleanKey = keyword.trim();
    if (this.cache.has(cleanKey)) {
      return this.cache.get(cleanKey);
    }
    try {
      const url = `${this.workerUrl}/api/search?keyword=${encodeURIComponent(cleanKey)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const result = {
        ok: data.ok !== false,
        mode: data.mode || 'unknown',
        keyword: cleanKey,
        products: data.products || [],
      };
      this.cache.set(cleanKey, result);
      return result;
    } catch (err) {
      console.error('[CoupangService] Search error:', err);
      return { ok: false, error: err.message, products: [] };
    }
  }

  async getDeeplink(productUrl) {
    if (!productUrl) return null;
    try {
      const res = await fetch(`${this.workerUrl}/api/deeplink`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ productUrl }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data.shortenUrl || null;
    } catch (err) {
      console.error('[CoupangService] Deeplink error:', err);
      return null;
    }
  }

  // Secure external navigation: Always goes through deeplink
  async openInCoupang(productUrl, fallbackUrl = null) {
    let target = null;
    try {
      target = await this.getDeeplink(productUrl);
    } catch (e) {
      console.warn('[CoupangService] Could not resolve deeplink:', e);
    }
    if (!target) {
      target = fallbackUrl || productUrl;
    }
    if (target) {
      window.open(target, '_blank', 'noopener,noreferrer');
    }
  }
}
