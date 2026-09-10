import assert from 'node:assert/strict';
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

function validManifest(urlPrefix = 'https://cdn.example') {
  return {
    schema_version: 1,
    segments: {
      female_10: {
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
  localStorage.clear();
  let result = await RemoteLookService.load({ remoteLooks: { enabled: false, manifestUrl: '' } });
  assert.equal(result.source, 'disabled');
  assert.equal(result.manifest, null);

  localStorage.setItem(STORAGE_KEY, JSON.stringify(validManifest()));
  result = await RemoteLookService.load({ remoteLooks: { enabled: false, manifestUrl: '' } });
  assert.equal(result.source, 'disabled');
  assert.equal(result.manifest, null);

  localStorage.setItem(STORAGE_KEY, JSON.stringify({ schema_version: 1, segments: { female_10: { looks: [] } } }));
  result = await RemoteLookService.load({ remoteLooks: { enabled: false, manifestUrl: '' } });
  assert.equal(result.source, 'disabled');
  assert.equal(result.manifest, null);

  localStorage.setItem(STORAGE_KEY, '{bad json');
  result = await RemoteLookService.load({ remoteLooks: { enabled: false, manifestUrl: '' } });
  assert.equal(result.source, 'disabled');
  assert.equal(result.manifest, null);

  localStorage.setItem(STORAGE_KEY, JSON.stringify(validManifest()));
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

  console.log('remote-look-service tests passed');
}

run();
