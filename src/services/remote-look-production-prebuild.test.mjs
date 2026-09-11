import assert from 'node:assert/strict';
import fs from 'node:fs';
import { OutfitManager } from '../data/outfits.js';
import { RemoteLookService } from './remote-look-service.js';

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
  assert.equal(config.remoteLooks.indexUrl, 'https://storage.googleapis.com/todaypick-daily-looks-363284724091/production/index.json');

  localStorage.clear();
  const result = await RemoteLookService.loadCatalog(config, {
    season: 'autumn',
    gender: 'female',
    ageGroup: 20
  });
  assert.equal(result.source, 'remote');
  assert.ok(result.catalog);
  assert.equal(result.catalog.schema_version, 2);
  assert.equal(result.catalog.season, 'autumn');
  assert.equal(result.catalog.gender, 'female');
  assert.equal(result.catalog.age_group, 20);
  assert.equal(result.catalog.count, 20);
  assert.equal(result.catalog.looks[0].id, 'autumn_female_20_260910_01');
  assert.equal(result.catalog.looks[19].id, 'autumn_female_20_260911_10');

  const urls = result.catalog.looks.map(look => look.url);
  assert.equal(urls.length, 20);
  for (const url of urls) {
    assert.ok(url.startsWith('https://storage.googleapis.com/todaypick-daily-looks-363284724091/production/assets/'));
    assert.equal(url.includes('file://'), false);
    assert.equal(url.includes('localhost'), false);
  }
  const checks = await Promise.all(urls.map(head));
  assert.equal(checks.filter(item => item.ok && item.status === 200 && item.contentType === 'image/webp' && item.contentLength > 0).length, 20);

  const outfitManager = new OutfitManager();
  const applied = outfitManager.applyRemoteCatalog(result.catalog);
  assert.equal(applied.appliedSegments, 1);
  assert.equal(applied.appliedLooks, 20);
  assert.equal(outfitManager.getLooks('female_20s').length, 20);
  assert.equal(outfitManager.getLooks('female_20s').filter(look => look.image.startsWith('https://storage.googleapis.com/')).length, 20);

  console.log('remote-look production prebuild tests passed');
}

run();
