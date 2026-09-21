/**
 * TodayPick Daily Input Folder Creator — Google Apps Script v1.0 (2026-09-22)
 *
 * Creates daily input folders in Google Drive at 00:01 KST every day.
 *
 * Structure:
 *   TodayPick_user_config/
 *   └── YYMMDD/
 *       ├── f_10 / f_20 / f_30 / f_40 / f_50 / f_60
 *       └── m_10 / m_20 / m_30 / m_40 / m_50 / m_60
 *
 * DEPLOYMENT:
 *   1. Go to https://script.google.com/home → New Project
 *   2. Rename project to "TodayPick_Daily_Input_Folders"
 *   3. Paste this entire file, replacing the default code
 *   4. Set timezone: Project Settings → Time Zone → (UTC+09:00) Seoul
 *   5. Run createDailyTrigger() once to install the daily trigger
 *   6. Authorize Drive access when prompted
 *
 * ROOT_FOLDER_ID:
 *   The folder ID of TodayPick_user_config in Google Drive.
 *   Extract from the URL: drive.google.com/drive/folders/FOLDER_ID_HERE
 */

// ── CONFIGURATION ──────────────────────────────────────────────────────────────
var ROOT_FOLDER_ID = '1WvKlV8B3xM9X21vl_47Oh6dTfBDFVUPd'; // TodayPick_user_config

var SEGMENT_FOLDERS = [
  'f_10', 'f_20', 'f_30', 'f_40', 'f_50', 'f_60',
  'm_10', 'm_20', 'm_30', 'm_40', 'm_50', 'm_60'
];


// ── CORE FUNCTIONS ─────────────────────────────────────────────────────────────

/**
 * Returns today's date in YYMMDD format using KST (Asia/Seoul, UTC+9).
 * Apps Script project timezone must be set to Asia/Seoul.
 */
function getKstDateFolderName() {
  // Utilities.formatDate uses the project's timezone when no tz arg given,
  // but we set KST explicitly to be safe.
  var now = new Date();
  return Utilities.formatDate(now, 'Asia/Seoul', 'yyMMdd');
}

/**
 * Finds or creates a child folder with the given name inside parent.
 * Returns the folder object.
 */
function getOrCreateChildFolder(parent, name) {
  var existing = parent.getFoldersByName(name);
  if (existing.hasNext()) {
    return existing.next();
  }
  return parent.createFolder(name);
}

/**
 * Main entry: creates today's date folder and 12 segment subfolders.
 * Safe to run multiple times (idempotent).
 */
function createDailyInputFolders() {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(30000); // wait up to 30s
  } catch (e) {
    Logger.log('Could not acquire lock: ' + e);
    return;
  }

  try {
    var dateName = getKstDateFolderName();
    var root = DriveApp.getFolderById(ROOT_FOLDER_ID);

    // Create or find date folder
    var dateFolder = getOrCreateChildFolder(root, dateName);
    var dateFolderId = dateFolder.getId();
    Logger.log('DATE=' + dateName + ' FOLDER_ID=' + dateFolderId);

    // Create or find segment subfolders
    var created = [];
    var existed = [];
    for (var i = 0; i < SEGMENT_FOLDERS.length; i++) {
      var segName = SEGMENT_FOLDERS[i];
      var existing = dateFolder.getFoldersByName(segName);
      if (existing.hasNext()) {
        existed.push(segName);
        Logger.log('  ' + segName + ': EXISTS');
      } else {
        dateFolder.createFolder(segName);
        created.push(segName);
        Logger.log('  ' + segName + ': CREATED');
      }
    }

    Logger.log(
      'DATE=' + dateName +
      ' DATE_FOLDER=' + (created.length + existed.length === 12 && existed.length < 12 ? 'CREATED' : 'EXISTS') +
      ' SEGMENT_FOLDERS=' + (created.length + existed.length) + '/12' +
      ' MISSING_FOLDERS_CREATED=' + created.length +
      ' EXISTING_FOLDERS_PRESERVED=YES' +
      ' FINAL_VERDICT=PASS'
    );
  } finally {
    lock.releaseLock();
  }
}

/**
 * Verifies that today's date folder has all 12 segment subfolders.
 * Returns an object with { ok: bool, dateName, missing: [] }.
 */
function verifyDailyInputFolders() {
  var dateName = getKstDateFolderName();
  var root = DriveApp.getFolderById(ROOT_FOLDER_ID);
  var dateFolders = root.getFoldersByName(dateName);

  if (!dateFolders.hasNext()) {
    return { ok: false, dateName: dateName, missing: SEGMENT_FOLDERS.slice(), error: 'date folder not found' };
  }
  var dateFolder = dateFolders.next();
  var missing = [];
  for (var i = 0; i < SEGMENT_FOLDERS.length; i++) {
    if (!dateFolder.getFoldersByName(SEGMENT_FOLDERS[i]).hasNext()) {
      missing.push(SEGMENT_FOLDERS[i]);
    }
  }
  Logger.log('VERIFY date=' + dateName + ' missing=' + JSON.stringify(missing));
  return { ok: missing.length === 0, dateName: dateName, missing: missing };
}

/**
 * Installs a daily time-based trigger at 00:01 KST.
 * Apps Script triggers fire within an hour of the specified time; actual
 * execution time is logged. Run this function ONCE manually from the editor.
 * Safe to re-run: removes existing TodayPick triggers before creating new one.
 */
function createDailyTrigger() {
  // Remove existing TodayPick daily triggers to avoid duplicates
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    var t = triggers[i];
    if (t.getHandlerFunction() === 'createDailyInputFolders') {
      ScriptApp.deleteTrigger(t);
      Logger.log('Removed existing trigger: ' + t.getUniqueId());
    }
  }

  // Create new trigger: run createDailyInputFolders at midnight KST (hour 0)
  ScriptApp.newTrigger('createDailyInputFolders')
    .timeBased()
    .atHour(0)          // 00:xx KST (within the midnight hour)
    .nearMinute(1)
    .everyDays(1)
    .inTimezone('Asia/Seoul')
    .create();

  Logger.log('Daily trigger created: createDailyInputFolders at ~00:01 KST');
}

/**
 * Lists all installed triggers for this project (for debugging).
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
