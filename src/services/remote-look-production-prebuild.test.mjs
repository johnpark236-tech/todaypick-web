import assert from 'node:assert/strict';
import fs from 'node:fs';
import { OutfitManager } from '../data/outfits.js';
import { RemoteLookService } from './remote-look-service.js';

const STORAGE_KEY = 'todaypick_remote_look_manifest_v1';

global.localStorage = {
  data: new Map(),
  getItem(key) {
    return this.data.has(key) ? this.data.get(key) : null;
  },
  setItem(key, value) {
    this.data.set(key, String(value));
  },
  removeItem(key) {
    this.data.delete(key);
  },
  clear() {
    this.data.clear();
  }
};

async function head(url) {
  const res = await fetch(url, { method: 'HEAD' });
  return {
    ok: res.ok,
    status: res.status,
    contentType: (res.headers.get('content-type') || '').split(';')[0],
    contentLength: Number(res.headers.get('content-length') || 0)
  };
}

async function run() {
  const config = JSON.parse(fs.readFileSync('public/config.json', 'utf-8'));
  assert.equal(config.remoteLooks.enabled, true);
  assert.equal(config.remoteLooks.manifestUrl, 'https://storage.googleapis.com/todaypick-daily-looks-363284724091/production/latest.json');

  localStorage.clear();
  let result = await RemoteLookService.load(config);
  assert.equal(result.source, 'remote');
  assert.ok(result.manifest);
  assert.equal(result.manifest.content_version, '260910_001');
  assert.deepEqual(Object.keys(result.manifest.segments).sort(), ['female_10', 'female_20', 'female_30']);

  const urls = Object.values(result.manifest.segments).flatMap(segment => segment.looks.map(look => look.url));
  assert.equal(urls.length, 30);
  for (const url of urls) {
    assert.ok(url.startsWith('https://storage.googleapis.com/todaypick-daily-looks-363284724091/production/assets/'));
    assert.equal(url.includes('staging_path'), false);
    assert.equal(url.includes('file://'), false);
    assert.equal(url.includes('localhost'), false);
  }
  const checks = await Promise.all(urls.map(head));
  assert.equal(checks.filter(item => item.ok && item.status === 200 && item.contentType === 'image/webp' && item.contentLength > 0).length, 30);

  const outfitManager = new OutfitManager();
  const bundledFemale40 = outfitManager.getLooks('female_40s')[0].image;
  const bundledMale10 = outfitManager.getLooks('male_10s')[0].image;
  const applied = outfitManager.applyRemoteManifest(result.manifest);
  assert.equal(applied.appliedSegments, 3);
  assert.equal(applied.appliedLooks, 30);
  assert.equal(outfitManager.getLooks('female_10s').filter(look => look.image.startsWith('https://storage.googleapis.com/')).length, 10);
  assert.equal(outfitManager.getLooks('female_20s').filter(look => look.image.startsWith('https://storage.googleapis.com/')).length, 10);
  assert.equal(outfitManager.getLooks('female_30s').filter(look => look.image.startsWith('https://storage.googleapis.com/')).length, 10);
  assert.equal(outfitManager.getLooks('female_40s')[0].image, bundledFemale40);
  assert.equal(outfitManager.getLooks('male_10s')[0].image, bundledMale10);

  const originalFetch = global.fetch;
  global.fetch = async () => ({ ok: false, status: 503 });
  result = await RemoteLookService.load(config);
  assert.equal(result.source, 'cache');
  assert.ok(result.manifest);

  localStorage.clear();
  result = await RemoteLookService.load(config);
  assert.equal(result.source, 'fallback');
  assert.equal(result.manifest, null);

  global.fetch = async () => ({
    ok: true,
    json: async () => ({ schema_version: 1, segments: { female_10: { looks: [{ id: 'bad', url: 'file:///bad.webp', sha256: 'x' }] } } })
  });
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ schema_version: 1, segments: { female_10: { looks: [] } } }));
  result = await RemoteLookService.load(config);
  assert.equal(result.source, 'fallback');
  assert.equal(result.manifest, null);
  global.fetch = originalFetch;

  console.log('remote-look production prebuild tests passed');
}

run();
