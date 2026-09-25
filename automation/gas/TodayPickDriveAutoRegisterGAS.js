/**
 * TodayPick Drive Auto-Register — Google Apps Script v1.0 (2026-09-25)
 *
 * Polls TodayPick_user_config every 1 minute. When a new YYMMDD folder
 * is detected with ≥10 images in any non-teen segment (f_20…f_60, m_20…m_60),
 * triggers GitHub Actions workflow: todaypick-drive-image-register.yml
 *
 * DEPLOYMENT:
 *   1. Go to https://script.google.com/home → New Project
 *   2. Rename project to "TodayPick_Drive_Auto_Register"
 *   3. Paste this entire file, replacing the default code
 *   4. Set timezone: Project Settings → Time Zone → (UTC+09:00) Seoul
 *   5. Add Script Properties (Project Settings → Script Properties):
 *        GH_TOKEN      = <GitHub Personal Access Token with workflow scope>
 *        GH_REPO       = todaypick-web   (or owner/repo if not johnpark236)
 *        GH_OWNER      = johnpark236
 *   6. Run installMinuteTrigger() once to install the 1-minute trigger
 *   7. Authorize Drive access when prompted
 *
 * SECURITY: GH_TOKEN is stored in Script Properties (encrypted at rest by Google).
 *   Never paste tokens in the script body.
 *
 * ROOT_FOLDER_ID: TodayPick_user_config
 */

// ── CONFIGURATION ──────────────────────────────────────────────────────────────
var ROOT_FOLDER_ID   = '1WvKlV8B3xM9X21vl_47Oh6dTfBDFVUPd';  // TodayPick_user_config
var WORKFLOW_FILE    = 'todaypick-drive-image-register.yml';
var GH_BRANCH        = 'master';
var REQUIRED_IMAGES  = 10;         // minimum images per segment to trigger
var REQUIRED_META_FILES = ['metadata.json', 'manifest.json']; // both must be present

// Segments that have been removed from the app; never trigger registration for these.
var EXCLUDED_SEGMENTS = ['f_10', 'm_10'];

// All valid segment folder names (excluding teens).
var ACTIVE_SEGMENTS = [
  'f_20', 'f_30', 'f_40', 'f_50', 'f_60',
  'm_20', 'm_30', 'm_40', 'm_50', 'm_60'
];

// Script Properties keys
var PROP_PROCESSED_DATES = 'PROCESSED_DATES_V1';   // JSON: { "YYMMDD": "ISO timestamp" }
var PROP_LAST_SCAN       = 'LAST_SCAN_ISO';

var DATE_FOLDER_RE = /^[0-9]{6}$/;
var IMAGE_MIME_TYPES = {
  'image/jpeg': true,
  'image/png':  true,
  'image/webp': true
};


// ── MAIN POLL FUNCTION (called by trigger) ─────────────────────────────────────

/**
 * Scans Drive for new YYMMDD folders with ready images, dispatches GitHub Actions.
 * This is the function installed as the 1-minute trigger.
 */
function pollAndRegister() {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(10000);
  } catch (e) {
    Logger.log('SKIP: Could not acquire lock (previous run still active)');
    return;
  }

  try {
    var props    = PropertiesService.getScriptProperties();
    var processed = loadProcessed(props);
    var root      = DriveApp.getFolderById(ROOT_FOLDER_ID);

    // List all YYMMDD date folders in root
    var dateFolders = [];
    var iter = root.getFolders();
    while (iter.hasNext()) {
      var f = iter.next();
      var n = f.getName();
      if (DATE_FOLDER_RE.test(n)) {
        dateFolders.push({ folder: f, name: n });
      }
    }

    // Sort newest-first so we process today's uploads promptly
    dateFolders.sort(function(a, b) { return b.name.localeCompare(a.name); });

    var scanned = 0;
    var triggered = 0;
    var kstNow = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyMMdd');

    for (var i = 0; i < dateFolders.length; i++) {
      var dateName   = dateFolders[i].name;
      var dateFolder = dateFolders[i].folder;
      scanned++;

      // Skip already-processed dates
      if (processed[dateName]) {
        Logger.log('SKIP: ' + dateName + ' (already processed at ' + processed[dateName] + ')');
        continue;
      }

      // Detect ready segments
      var readySegments = detectReadySegments(dateFolder, dateName);

      if (readySegments.length === 0) {
        Logger.log('WAIT: ' + dateName + ' — no segment has ' + REQUIRED_IMAGES + '+ images yet');
        continue;
      }

      // Dispatch GitHub Actions
      Logger.log('TRIGGER: ' + dateName + ' segments=' + readySegments.join(','));
      var ok = dispatchWorkflow(dateName, props);
      if (ok) {
        processed[dateName] = new Date().toISOString();
        saveProcessed(props, processed);
        triggered++;
        Logger.log('DISPATCHED: ' + dateName + ' → workflow queued');
      } else {
        Logger.log('ERROR: dispatch failed for ' + dateName + ' — will retry next poll');
      }
    }

    props.setProperty(PROP_LAST_SCAN, new Date().toISOString());
    Logger.log('POLL DONE: scanned=' + scanned + ' triggered=' + triggered);
  } finally {
    lock.releaseLock();
  }
}


// ── HELPERS ────────────────────────────────────────────────────────────────────

/**
 * Returns list of segment names inside dateFolder that have ≥ REQUIRED_IMAGES images
 * AND both metadata.json + manifest.json present.
 * Excludes teen segments.
 */
function detectReadySegments(dateFolder, dateName) {
  var ready = [];
  for (var i = 0; i < ACTIVE_SEGMENTS.length; i++) {
    var segName = ACTIVE_SEGMENTS[i];
    var segIter = dateFolder.getFoldersByName(segName);
    if (!segIter.hasNext()) continue;
    var segFolder = segIter.next();

    var count = countImages(segFolder);
    var missingMeta = checkRequiredMetaFiles(segFolder);

    if (missingMeta.length > 0) {
      Logger.log('  ' + dateName + '/' + segName + ': images=' + count
        + ' WAIT — missing meta files: ' + missingMeta.join(', '));
      continue;
    }

    Logger.log('  ' + dateName + '/' + segName + ': images=' + count
      + ' meta=OK (metadata.json + manifest.json)');

    if (count >= REQUIRED_IMAGES) {
      ready.push(segName);
    } else {
      Logger.log('  ' + dateName + '/' + segName + ': WAIT — only ' + count + '/' + REQUIRED_IMAGES + ' images');
    }
  }
  return ready;
}

/**
 * Counts image files in a folder (non-recursive).
 */
function countImages(folder) {
  var count = 0;
  var fileIter = folder.getFiles();
  while (fileIter.hasNext()) {
    var file = fileIter.next();
    if (IMAGE_MIME_TYPES[file.getMimeType()]) {
      count++;
    }
  }
  return count;
}

/**
 * Checks that all REQUIRED_META_FILES exist in the folder.
 * Returns an array of missing filenames (empty = all present).
 */
function checkRequiredMetaFiles(folder) {
  var missing = [];
  for (var i = 0; i < REQUIRED_META_FILES.length; i++) {
    var name = REQUIRED_META_FILES[i];
    var iter = folder.getFilesByName(name);
    if (!iter.hasNext()) {
      missing.push(name);
    }
  }
  return missing;
}

/**
 * Dispatches the GitHub Actions workflow via REST API.
 * Returns true on success (HTTP 204), false on error.
 */
function dispatchWorkflow(dateYymmdd, props) {
  var token = props.getProperty('GH_TOKEN');
  var owner = props.getProperty('GH_OWNER') || 'johnpark236';
  var repo  = props.getProperty('GH_REPO')  || 'todaypick-web';

  if (!token) {
    Logger.log('ERROR: GH_TOKEN not set in Script Properties');
    return false;
  }

  var url = 'https://api.github.com/repos/' + owner + '/' + repo
            + '/actions/workflows/' + WORKFLOW_FILE + '/dispatches';

  var payload = JSON.stringify({
    ref: GH_BRANCH,
    inputs: {
      date_yymmdd: dateYymmdd,
      dry_run: 'false'
    }
  });

  var options = {
    method:             'post',
    contentType:        'application/json',
    payload:            payload,
    headers: {
      'Authorization':        'Bearer ' + token,
      'Accept':               'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28'
    },
    muteHttpExceptions: true
  };

  try {
    var response = UrlFetchApp.fetch(url, options);
    var code     = response.getResponseCode();
    if (code === 204) {
      return true;
    }
    Logger.log('ERROR: GitHub API returned HTTP ' + code + ': ' + response.getContentText().slice(0, 500));
    return false;
  } catch (e) {
    Logger.log('ERROR: GitHub API fetch failed: ' + e);
    return false;
  }
}

/**
 * Loads the processed-dates map from Script Properties.
 */
function loadProcessed(props) {
  try {
    var raw = props.getProperty(PROP_PROCESSED_DATES);
    return raw ? JSON.parse(raw) : {};
  } catch (e) {
    return {};
  }
}

/**
 * Saves the processed-dates map to Script Properties.
 */
function saveProcessed(props, map) {
  props.setProperty(PROP_PROCESSED_DATES, JSON.stringify(map));
}


// ── TRIGGER MANAGEMENT ─────────────────────────────────────────────────────────

/**
 * Installs a 1-minute time-based trigger for pollAndRegister.
 * Safe to re-run: removes existing triggers first to avoid duplicates.
 * Run this function ONCE manually from the Apps Script editor.
 */
function installMinuteTrigger() {
  removePollTriggers();
  ScriptApp.newTrigger('pollAndRegister')
    .timeBased()
    .everyMinutes(5)
    .create();
  Logger.log('5-minute trigger installed for pollAndRegister (Gmail free account quota-safe)');
}

/**
 * Removes all existing pollAndRegister triggers.
 */
function removePollTriggers() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'pollAndRegister') {
      ScriptApp.deleteTrigger(triggers[i]);
      Logger.log('Removed trigger: ' + triggers[i].getUniqueId());
    }
  }
}

/**
 * Lists all installed triggers (for debugging).
 */
function listTriggers() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    var t = triggers[i];
    Logger.log(
      'trigger[' + i + ']: handler=' + t.getHandlerFunction() +
      ' type=' + t.getEventType() +
      ' id=' + t.getUniqueId()
    );
  }
}

/**
 * Shows processed dates and last scan time (for debugging).
 */
function showStatus() {
  var props = PropertiesService.getScriptProperties();
  var processed = loadProcessed(props);
  var lastScan  = props.getProperty(PROP_LAST_SCAN) || '(never)';
  Logger.log('Last scan: ' + lastScan);
  Logger.log('Processed dates: ' + JSON.stringify(processed, null, 2));
}

/**
 * Clears processed-dates cache so dates will be re-evaluated on next poll.
 * USE WITH CAUTION — will re-trigger registration for any date with images.
 */
function clearProcessedCache() {
  var props = PropertiesService.getScriptProperties();
  props.deleteProperty(PROP_PROCESSED_DATES);
  Logger.log('Processed dates cache cleared');
}

/**
 * Manually triggers registration for a specific date (for testing/recovery).
 * Set testDate to the YYMMDD you want to re-register.
 */
function manualTriggerDate() {
  var testDate = '260925';  // ← change to desired YYMMDD before running
  var props = PropertiesService.getScriptProperties();
  var ok = dispatchWorkflow(testDate, props);
  Logger.log(ok ? 'Dispatch OK for ' + testDate : 'Dispatch FAILED for ' + testDate);
}
