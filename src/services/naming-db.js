/**
 * TodayPick Naming Metadata DB (IndexedDB)
 * vc72 — 코디명 추천/선택/수정 이벤트 영구 저장
 *
 * DB:   todaypick_meta
 * Store: shareNamingEvents  — 공유 이벤트 전체 로그
 *        namingRegistry     — 중복 판정용 name registry
 *
 * 개인정보 저장 금지:
 *   - 실명/전화/이메일/위치 저장 안 함
 *   - 목적: 코디 네이밍 추천 품질 개선
 *
 * 미래 Cloudflare D1 동기화 대응 구조로 설계
 * REMOTE_SYNC_STATUS=NOT_IMPLEMENTED
 */

const DB_NAME    = 'todaypick_meta';
const DB_VERSION = 1;

const STORE_EVENTS   = 'shareNamingEvents';
const STORE_REGISTRY = 'namingRegistry';

// ── DB 초기화 ───────────────────────────────────────────────────
let _db = null;

function openDB() {
  if (_db) return Promise.resolve(_db);

  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);

    req.onupgradeneeded = (e) => {
      const db = e.target.result;

      // shareNamingEvents store
      if (!db.objectStoreNames.contains(STORE_EVENTS)) {
        const evStore = db.createObjectStore(STORE_EVENTS, { keyPath: 'shareId' });
        evStore.createIndex('lookId',         'lookId',         { unique: false });
        evStore.createIndex('normalizedName', 'normalizedName', { unique: false });
        evStore.createIndex('createdAt',      'createdAt',      { unique: false });
      }

      // namingRegistry store — 중복 검색용
      if (!db.objectStoreNames.contains(STORE_REGISTRY)) {
        const regStore = db.createObjectStore(STORE_REGISTRY, { keyPath: 'normalizedName' });
        regStore.createIndex('lookId',    'lookId',    { unique: false });
        regStore.createIndex('createdAt', 'createdAt', { unique: false });
      }
    };

    req.onsuccess = (e) => {
      _db = e.target.result;
      resolve(_db);
    };

    req.onerror = (e) => {
      console.error('[NamingDB] open error:', e.target.error);
      reject(e.target.error);
    };
  });
}

function tx(storeName, mode = 'readonly') {
  return openDB().then(db => {
    const transaction = db.transaction(storeName, mode);
    const store = transaction.objectStore(storeName);
    return { transaction, store };
  });
}

function promisify(req) {
  return new Promise((resolve, reject) => {
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror   = (e) => reject(e.target.error);
  });
}

// ── 공유 이벤트 저장 ────────────────────────────────────────────
/**
 * @param {object} event
 * @param {string} event.shareId
 * @param {string} event.lookId
 * @param {Array<{text:string, type:string}>} event.recommendations
 * @param {number} event.defaultRecommendationIndex
 * @param {number} event.selectedRecommendationIndex
 * @param {string} event.selectedRecommendation
 * @param {boolean} event.userEdited
 * @param {string} event.userInputName
 * @param {string} event.baseName
 * @param {string} event.resolvedName
 * @param {string} event.normalizedName
 * @param {string} event.createdAt   ISO8601
 * @param {number} event.appVersionCode
 * @param {string} event.uiVersion
 * @param {object} [event.lookMetadata]
 */
export async function saveShareNamingEvent(event) {
  try {
    const { store } = await tx(STORE_EVENTS, 'readwrite');
    await promisify(store.put(event));

    // namingRegistry 동시 업데이트
    await upsertNamingRegistry({
      normalizedName: event.normalizedName,
      baseName:       event.baseName,
      resolvedName:   event.resolvedName,
      lookId:         event.lookId,
      createdAt:      event.createdAt,
    });

    return true;
  } catch (err) {
    console.error('[NamingDB] saveShareNamingEvent error:', err);
    return false;
  }
}

// ── Registry upsert ─────────────────────────────────────────────
async function upsertNamingRegistry(entry) {
  try {
    const { store } = await tx(STORE_REGISTRY, 'readwrite');
    await promisify(store.put(entry));
  } catch (err) {
    console.warn('[NamingDB] upsertNamingRegistry error:', err);
  }
}

// ── 중복 판정: normalizedName 기준 기존 entry 모두 조회 ─────────
/**
 * @param {string} normalizedName
 * @returns {Promise<Array>}  registry entries with this normalizedName prefix
 */
export async function findRegistryByNormalizedName(normalizedName) {
  try {
    const { store } = await tx(STORE_REGISTRY, 'readonly');
    const idx = store.index('lookId'); // normalizedName은 keyPath이므로 get 직접 가능

    // normalizedName 정확 일치 조회 (키 자체)
    const exact = await promisify(store.get(normalizedName));

    // "(N)" suffix 패턴들도 검색하기 위해 range cursor 사용
    const lower = normalizedName;
    const upper = normalizedName + '\uffff';
    const range = IDBKeyRange.bound(lower, upper, false, false);

    const results = [];
    await new Promise((resolve, reject) => {
      const req = store.openCursor(range);
      req.onsuccess = (e) => {
        const cursor = e.target.result;
        if (cursor) {
          results.push(cursor.value);
          cursor.continue();
        } else {
          resolve();
        }
      };
      req.onerror = (e) => reject(e.target.error);
    });

    return results;
  } catch (err) {
    console.warn('[NamingDB] findRegistryByNormalizedName error:', err);
    return [];
  }
}

// ── 최근 이벤트 조회 ─────────────────────────────────────────────
export async function getRecentNamingEvents(limit = 50) {
  try {
    const { store } = await tx(STORE_EVENTS, 'readonly');
    const idx = store.index('createdAt');
    const range = IDBKeyRange.upperBound(new Date().toISOString());

    const results = [];
    await new Promise((resolve, reject) => {
      const req = idx.openCursor(range, 'prev');
      req.onsuccess = (e) => {
        const cursor = e.target.result;
        if (cursor && results.length < limit) {
          results.push(cursor.value);
          cursor.continue();
        } else {
          resolve();
        }
      };
      req.onerror = (e) => reject(e.target.error);
    });

    return results;
  } catch (err) {
    console.warn('[NamingDB] getRecentNamingEvents error:', err);
    return [];
  }
}

// ── DB warm-up (앱 시작 시 사전 열기) ──────────────────────────
export async function warmUpNamingDB() {
  try {
    await openDB();
  } catch (err) {
    console.warn('[NamingDB] warmUp failed (non-fatal):', err);
  }
}
