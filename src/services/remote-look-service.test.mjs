import assert from 'node:assert/strict';
import { RemoteLookService, getSeasonForMonth } from './remote-look-service.js';

const LEGACY_STORAGE_KEY = 'todaypick_remote_look_manifest_v1';

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

function looks(count, prefix = 'remote') {
  return Array.from({ length: count }, (_, index) => ({
    id: `${prefix}_${index + 1}`,
    url: `https://cdn.example/${prefix}/look_${index + 1}.webp`,
    sha256: `${index + 1}`.padStart(64, 'a')
  }));
}

function validManifest(urlPrefix = 'https://cdn.example') {
  return {
    schema_version: 1,
    segments: {
      female_10: {
        count: 10,
        looks: Array.from({ length: 10 }, (_, index) => ({
          id: `remote_${index + 1}`,
          url: `${urlPrefix}/look_${index + 1}.webp`,
          sha256: 'a'.repeat(64)
        }))
      }
    }
  };
}

async function run() {
  assert.equal(getSeasonForMonth(1), 'winter');
  assert.equal(getSeasonForMonth(2), 'winter');
  assert.equal(getSeasonForMonth(3), 'spring');
  assert.equal(getSeasonForMonth(5), 'spring');
  assert.equal(getSeasonForMonth(6), 'summer');
  assert.equal(getSeasonForMonth(8), 'summer');
  assert.equal(getSeasonForMonth(9), 'autumn');
  assert.equal(getSeasonForMonth(11), 'autumn');
  assert.equal(getSeasonForMonth(12), 'winter');

  localStorage.clear();
  let result = await RemoteLookService.load({ remoteLooks: { enabled: false, manifestUrl: '' } });
  assert.equal(result.source, 'disabled');
  assert.equal(result.manifest, null);

  localStorage.setItem(LEGACY_STORAGE_KEY, JSON.stringify(validManifest()));
  result = await RemoteLookService.load({ remoteLooks: { enabled: false, manifestUrl: '' } });
  assert.equal(result.source, 'disabled');
  assert.equal(result.manifest, null);

  localStorage.setItem(LEGACY_STORAGE_KEY, JSON.stringify({ schema_version: 1, segments: { female_10: { looks: [] } } }));
  result = await RemoteLookService.load({ remoteLooks: { enabled: false, manifestUrl: '' } });
  assert.equal(result.source, 'disabled');
  assert.equal(result.manifest, null);

  localStorage.setItem(LEGACY_STORAGE_KEY, '{bad json');
  result = await RemoteLookService.load({ remoteLooks: { enabled: false, manifestUrl: '' } });
  assert.equal(result.source, 'disabled');
  assert.equal(result.manifest, null);

  localStorage.setItem(LEGACY_STORAGE_KEY, JSON.stringify(validManifest()));
  result = await RemoteLookService.load({ remoteLooks: { enabled: true, manifestUrl: '' } });
  assert.equal(result.source, 'disabled');
  assert.equal(result.manifest, null);

  localStorage.clear();
  global.fetch = async () => ({ ok: true, json: async () => validManifest() });
  result = await RemoteLookService.load({ remoteLooks: { enabled: true, manifestUrl: 'https://cdn.example/latest.json' } });
  assert.equal(result.source, 'remote');
  assert.ok(result.manifest);

  global.fetch = async () => ({ ok: false, status: 503 });
  result = await RemoteLookService.load({ remoteLooks: { enabled: true, manifestUrl: 'https://cdn.example/latest.json' } });
  assert.equal(result.source, 'cache');
  assert.ok(result.manifest);

  localStorage.clear();
  result = await RemoteLookService.load({ remoteLooks: { enabled: true, manifestUrl: 'https://cdn.example/latest.json' } });
  assert.equal(result.source, 'fallback');
  assert.equal(result.manifest, null);

  const calls = [];
  global.fetch = async (url) => {
    calls.push(String(url).split('?')[0]);
    if (String(url).includes('index.json')) {
      return {
        ok: true,
        json: async () => ({
          schema_version: 2,
          seasons: {
            spring: {},
            summer: {},
            autumn: {
              female_20: 'https://cdn.example/production/autumn/female_20.json'
            },
            winter: {}
          }
        })
      };
    }
    return {
      ok: true,
      json: async () => ({
        schema_version: 2,
        season: 'autumn',
        gender: 'female',
        age_group: 20,
        count: 500,
        updated_at: '2026-09-11T05:00:00+09:00',
        looks: looks(500, 'autumn_female_20')
      })
    };
  };

  result = await RemoteLookService.loadCatalog(
    { remoteLooks: { enabled: true, indexUrl: 'https://cdn.example/production/index.json' } },
    { season: 'autumn', gender: 'female', ageGroup: 20 }
  );
  assert.equal(result.source, 'remote');
  assert.equal(result.catalog.count, 500);
  assert.deepEqual(calls, [
    'https://cdn.example/production/index.json',
    'https://cdn.example/production/autumn/female_20.json'
  ]);

  console.log('remote-look-service tests passed');
}

run();
