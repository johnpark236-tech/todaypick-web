import assert from 'node:assert/strict';
import { OutfitManager } from './outfits.js';
import { StorageService } from '../services/storage.js';

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

function catalog(count) {
  return {
    schema_version: 2,
    season: 'autumn',
    gender: 'female',
    age_group: 20,
    count,
    looks: Array.from({ length: count }, (_, index) => ({
      id: `autumn_female_20_260911_${String(index + 1).padStart(2, '0')}`,
      url: `https://cdn.example/autumn/female/20/look_${index + 1}.webp`,
      sha256: `${index + 1}`.padStart(64, 'b')
    }))
  };
}

function run() {
  localStorage.clear();
  assert.deepEqual(StorageService.getLookPreferences(), { lastGender: 'female', lastAgeGroup: 20, lastSeason: null });

  StorageService.saveLookPreferences({ lastGender: 'male', lastAgeGroup: 40, lastSeason: 'winter' });
  assert.deepEqual(StorageService.getLookPreferences(), { lastGender: 'male', lastAgeGroup: 40, lastSeason: 'winter' });
  assert.equal(JSON.parse(localStorage.getItem('todaypick_look_preferences_v1')).season, undefined);

  for (const count of [1, 10, 20, 100, 500]) {
    const manager = new OutfitManager();
    const applied = manager.applyRemoteCatalog(catalog(count));
    assert.equal(applied.appliedSegments, 1);
    assert.equal(applied.appliedLooks, count);
    assert.equal(manager.getLooks('female_20s').length, count);
    assert.equal(manager.getLooks('female_20s')[0].image.startsWith('https://cdn.example/'), true);
  }

  const manager = new OutfitManager();
  manager.applyRemoteCatalog(catalog(20));
  assert.equal(manager.getLooks('female_20s').length, 20);
  assert.equal(manager.resetRemoteCategory('female_20s'), true);
  assert.equal(manager.getLooks('female_20s').length, 10);
  assert.equal(manager.getLooks('female_20s')[0].image.startsWith('/assets/looks/'), true);

  const pageSize = 20;
  assert.equal(catalog(500).looks.slice(0, pageSize).length, 20);

  console.log('seasonal catalog tests passed');
}

run();
