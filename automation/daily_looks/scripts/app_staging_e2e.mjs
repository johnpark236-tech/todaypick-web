import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const PROJECT = 'my-youtube-automation-497504';
const BUCKET = 'todaypick-daily-looks-363284724091';
const DATE = '260910';
const BASE_URL = process.env.TODAYPICK_E2E_BASE_URL || 'http://127.0.0.1:4173';
const STAGING_LATEST_URL = `https://storage.googleapis.com/${BUCKET}/staging/latest.json`;
const CHROME = process.env.CHROME_PATH || 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe';

function runPython(args) {
  const result = spawnSync('python', args, { encoding: 'utf-8', cwd: process.cwd() });
  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || `python ${args.join(' ')} failed`);
  }
  return result.stdout.trim() ? JSON.parse(result.stdout.trim()) : {};
}

async function sleep(ms) {
  await new Promise(resolve => setTimeout(resolve, ms));
}

async function waitFor(fn, timeout = 30000) {
  const start = Date.now();
  let lastError;
  while (Date.now() - start < timeout) {
    try {
      const value = await fn();
      if (value) return value;
    } catch (error) {
      lastError = error;
    }
    await sleep(250);
  }
  throw lastError || new Error('Timed out waiting for condition');
}

class CdpPage {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.events = [];
  }

  async open() {
    await new Promise((resolve, reject) => {
      this.ws.addEventListener('open', resolve, { once: true });
      this.ws.addEventListener('error', reject, { once: true });
    });
    this.ws.addEventListener('message', (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(msg.error.message));
        else resolve(msg.result);
        return;
      }
      if (msg.method) this.events.push(msg);
    });
    await this.send('Page.enable');
    await this.send('Runtime.enable');
    await this.send('Network.enable');
  }

  send(method, params = {}) {
    const id = this.nextId++;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
    });
  }

  async navigate(url) {
    this.events = [];
    await this.send('Page.navigate', { url });
    await waitFor(() => this.events.some(event => event.method === 'Page.loadEventFired'), 30000);
  }

  async evaluate(expression, awaitPromise = true) {
    const result = await this.send('Runtime.evaluate', {
      expression,
      awaitPromise,
      returnByValue: true,
      userGesture: true,
    });
    if (result.exceptionDetails) {
      throw new Error(result.exceptionDetails.text || 'Runtime.evaluate failed');
    }
    return result.result.value;
  }

  async close() {
    this.ws.close();
  }
}

async function launchChrome() {
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'todaypick-cdp-'));
  const port = 9229;
  const chrome = spawn(CHROME, [
    '--headless=new',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    'about:blank',
  ], { stdio: 'ignore' });
  await waitFor(async () => {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/version`);
      return res.ok ? res.json() : null;
    } catch {
      return null;
    }
  }, 30000);
  const target = await waitFor(async () => {
    const res = await fetch(`http://127.0.0.1:${port}/json/list`);
    if (!res.ok) return null;
    const targets = await res.json();
    return targets.find(item => item.type === 'page' && item.webSocketDebuggerUrl);
  }, 30000);
  const page = new CdpPage(target.webSocketDebuggerUrl);
  await page.open();
  return {
    page,
    async close() {
      await page.close();
      chrome.kill();
    }
  };
}

async function waitForApp(page) {
  try {
    await waitFor(async () => page.evaluate('Boolean(window.todaypickTest && window.todaypickTest.getState().mainImageSrc)'), 30000);
  } catch (error) {
    const diagnostics = await page.evaluate(`({
      url: location.href,
      readyState: document.readyState,
      hasHook: Boolean(window.todaypickTest),
      mainSrc: document.getElementById('main-character-img')?.src || '',
      bodyText: document.body?.innerText?.slice(0, 500) || ''
    })`).catch(evalError => ({ evalError: String(evalError) }));
    const recentEvents = page.events
      .filter(event => ['Runtime.exceptionThrown', 'Log.entryAdded', 'Network.loadingFailed'].includes(event.method))
      .slice(-10);
    throw new Error(`Timed out waiting for app: ${JSON.stringify({ diagnostics, recentEvents }, null, 2)}`);
  }
}

async function snapshot(page) {
  return page.evaluate(`(() => {
    const modes = ['female_10s', 'female_20s', 'female_30s', 'female_40s', 'male_10s'];
    const looks = Object.fromEntries(modes.map(mode => [mode, window.todaypickTest.getLooks(mode).map(look => ({
      id: look.id,
      image: look.image,
      thumbnail: look.thumbnail,
      remoteLookId: look.remoteLookId || null
    }))]));
    return {
      config: window.todaypickTest.getConfig(),
      buildId: window.todaypickTest.getBuildId(),
      state: window.todaypickTest.getState(),
      looks
    };
  })()`);
}

async function imageChecks(page, urls) {
  return page.evaluate(`(async () => {
    const urls = ${JSON.stringify(urls)};
    return Promise.all(urls.map(url => new Promise(resolve => {
      const img = new Image();
      img.onload = () => resolve({ url, ok: true, width: img.naturalWidth, height: img.naturalHeight });
      img.onerror = () => resolve({ url, ok: false, width: 0, height: 0 });
      img.src = url;
    })));
  })()`);
}

async function manifestVersion(page) {
  return page.evaluate(`fetch(window.todaypickTest.getConfig().remoteLooks.manifestUrl, { cache: 'no-store' })
    .then(res => res.json())
    .then(json => json.content_version)`);
}

async function refresh(page) {
  await page.evaluate('window.todaypickTest.refreshRemoteLooks({ rerender: true }).then(() => true)');
  await sleep(500);
}

function countRequests(page, prefix) {
  return page.events.filter(event => event.method === 'Network.requestWillBeSent' && event.params.request.url.startsWith(prefix)).length;
}

async function main() {
  runPython(['automation/daily_looks/scripts/publish_staging_manifest_variant.py', '--project', PROJECT, '--bucket', BUCKET, '--date', DATE, '--variant', 'a']);

  const browser = await launchChrome();
  const { page } = browser;
  try {
    await page.navigate(`${BASE_URL}/?remoteLooks=disabled`);
    await waitForApp(page);
    const disabled = await snapshot(page);
    assert.equal(disabled.config.remoteLooks.enabled, false);
    assert.equal(disabled.looks.female_10s.some(look => look.image.startsWith('https://storage.googleapis.com/')), false);
    const disabledGcsRequests = countRequests(page, STAGING_LATEST_URL);

    await page.navigate(`${BASE_URL}/?remoteLooksManifest=${encodeURIComponent(STAGING_LATEST_URL)}`);
    await waitForApp(page);
    const snapA = await snapshot(page);
    const enabledManifestRequests = countRequests(page, STAGING_LATEST_URL);
    assert.equal(snapA.config.remoteLooks.enabled, true);
    for (const mode of ['female_10s', 'female_20s', 'female_30s']) {
      assert.equal(snapA.looks[mode].filter(look => look.image.startsWith(`https://storage.googleapis.com/${BUCKET}/staging/assets/`)).length, 10);
    }
    assert.equal(snapA.looks.female_40s.some(look => look.image.startsWith('https://storage.googleapis.com/')), false);
    assert.equal(snapA.looks.male_10s.some(look => look.image.startsWith('https://storage.googleapis.com/')), false);
    const urlsA = ['female_10s', 'female_20s', 'female_30s'].flatMap(mode => snapA.looks[mode].map(look => look.image));
    const loadedA = await imageChecks(page, urlsA);
    assert.equal(loadedA.filter(item => item.ok).length, 30);

    const buildA = JSON.stringify(snapA.buildId);
    const versionA = await manifestVersion(page);
    const hashA = snapA.looks.female_10s[0].image.match(/look_01_([a-f0-9]+)\.webp/)?.[1];

    const variantB = runPython(['automation/daily_looks/scripts/publish_staging_manifest_variant.py', '--project', PROJECT, '--bucket', BUCKET, '--date', DATE, '--variant', 'b']);
    await refresh(page);
    const snapB = await snapshot(page);
    const versionB = await manifestVersion(page);
    const hashB = snapB.looks.female_10s[0].image.match(/look_01_([a-f0-9]+)\.webp/)?.[1];
    assert.notEqual(versionA, versionB);
    assert.notEqual(hashA, hashB);
    assert.equal(snapB.looks.female_10s[0].image, variantB.image_url);
    assert.equal(buildA, JSON.stringify(snapB.buildId));

    page.events = [];
    await page.navigate(`${BASE_URL}/?remoteLooksManifest=${encodeURIComponent(`${BASE_URL}/missing-latest.json`)}`);
    await waitForApp(page);
    const failureCached = await snapshot(page);
    assert.equal(failureCached.looks.female_10s[0].image, snapB.looks.female_10s[0].image);

    await page.evaluate('localStorage.clear(); true');
    await page.navigate(`${BASE_URL}/?remoteLooksManifest=${encodeURIComponent(`${BASE_URL}/missing-latest.json`)}`);
    await waitForApp(page);
    const failureFallback = await snapshot(page);
    assert.equal(failureFallback.looks.female_10s.some(look => look.image.startsWith('https://storage.googleapis.com/')), false);

    await page.navigate(`${BASE_URL}/?remoteLooksManifest=${encodeURIComponent(STAGING_LATEST_URL)}`);
    await waitForApp(page);
    runPython(['automation/daily_looks/scripts/publish_staging_manifest_variant.py', '--project', PROJECT, '--bucket', BUCKET, '--date', DATE, '--variant', 'invalid']);
    await refresh(page);
    const invalid = await snapshot(page);
    assert.equal(invalid.looks.female_10s[0].image, snapB.looks.female_10s[0].image);

    runPython(['automation/daily_looks/scripts/publish_staging_manifest_variant.py', '--project', PROJECT, '--bucket', BUCKET, '--date', DATE, '--variant', 'a']);
    await refresh(page);
    const rollback = await snapshot(page);
    assert.equal(rollback.looks.female_10s[0].image, snapA.looks.female_10s[0].image);

    await page.navigate(`${BASE_URL}/?remoteLooks=disabled`);
    await waitForApp(page);
    const disabledAfterCache = await snapshot(page);
    assert.equal(disabledAfterCache.looks.female_10s.some(look => look.image.startsWith('https://storage.googleapis.com/')), false);

    const report = {
      BUNDLED_BASELINE: 'PASS',
      STAGING_MANIFEST_URL: STAGING_LATEST_URL,
      REMOTE_MANIFEST_FETCH: enabledManifestRequests > 0 ? 'PASS' : 'FAIL',
      PARTIAL_REMOTE_OVERRIDE: 'PASS',
      MISSING_SEGMENT_BUNDLED_FALLBACK: 'PASS',
      REMOTE_IMAGES_EXPECTED: 30,
      REMOTE_IMAGES_LOADED: loadedA.filter(item => item.ok).length,
      BROKEN_REMOTE_IMAGES: loadedA.filter(item => !item.ok).length,
      APP_BUILD_ID: snapA.buildId,
      MANIFEST_VERSION_A: versionA,
      MANIFEST_VERSION_B: versionB,
      APP_BINARY_CHANGED_BETWEEN_A_B: buildA !== JSON.stringify(snapB.buildId),
      APK_REINSTALLED_BETWEEN_A_B: false,
      VERSION_CODE_CHANGED: snapA.buildId.androidVersionCode !== snapB.buildId.androidVersionCode,
      REMOTE_IMAGE_CHANGED: hashA !== hashB,
      IMAGE_CHANGE_WITHOUT_APP_REBUILD_E2E: versionA !== versionB && hashA !== hashB && buildA === JSON.stringify(snapB.buildId) ? 'PASS' : 'FAIL',
      CACHE_BUSTING_DEVICE_E2E: hashA !== hashB ? 'PASS' : 'FAIL',
      LAST_KNOWN_GOOD_E2E: failureCached.looks.female_10s[0].image === snapB.looks.female_10s[0].image ? 'PASS' : 'FAIL',
      BUNDLED_FALLBACK_E2E: failureFallback.looks.female_10s.some(look => look.image.startsWith('https://storage.googleapis.com/')) ? 'FAIL' : 'PASS',
      REMOTE_FAILURE_APP_SURVIVES_E2E: 'PASS',
      INVALID_MANIFEST_FAIL_CLOSED: invalid.looks.female_10s[0].image === snapB.looks.female_10s[0].image ? 'PASS' : 'FAIL',
      APP_ROLLBACK_E2E: rollback.looks.female_10s[0].image === snapA.looks.female_10s[0].image ? 'PASS' : 'FAIL',
      REMOTE_DISABLE_AFTER_CACHE: disabledAfterCache.looks.female_10s.some(look => look.image.startsWith('https://storage.googleapis.com/')) ? 'FAIL' : 'PASS',
      REMOTE_DISABLED_GCS_REQUEST_COUNT: disabledGcsRequests,
      REMOTE_ENABLED_MANIFEST_REQUEST: enabledManifestRequests > 0,
      PHYSICAL_DEVICE_TEST: 'NOT_RUN',
      DEVICE_MODEL: 'NONE_ADB_DEVICE_NOT_CONNECTED'
    };
    fs.writeFileSync('automation/daily_looks/remote_pipeline/manifests/260910_app_staging_e2e_report.json', `${JSON.stringify(report, null, 2)}\n`);
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
