/**
 * TodayPick Drive Sync GAS
 *
 * 역할:
 *   1. TodayPick_user_config/{YYMMDD}/{segment}/ 에서 새 업로드 감지
 *      → publish_requests/ JSON 커밋 + publish_queue/ JSON 커밋 (push 트리거)
 *   2. 00_MAIN_IMAGES/{MM}/{gender}/{age}/ 에서 파일 삭제 감지
 *      → todaypick-drive-delete-sync 워크플로 dispatch
 *
 * 설정:
 *   Script Properties (파일 > 프로젝트 속성 > 스크립트 속성):
 *     GITHUB_PAT         — GitHub Fine-grained PAT (contents:write, actions:write)
 *     GITHUB_OWNER       — johnpark236-tech
 *     GITHUB_REPO        — todaypick-web
 *     USER_CONFIG_ROOT_ID — TodayPick_user_config 폴더 ID
 *     MAIN_IMAGES_ROOT_ID — 00_MAIN_IMAGES 폴더 ID
 *
 *   Script Properties (자동 기록, 직접 수정 불요):
 *     SUBMITTED_SETS     — 이미 제출한 {date}/{segment} 목록 (JSON)
 *     MAIN_IMAGE_STATE   — 00_MAIN_IMAGES 파일 현황 스냅샷 (JSON)
 */

// ── 설정 읽기 ──────────────────────────────────────────────────────────────────
function getProps() {
  const p = PropertiesService.getScriptProperties();
  return {
    pat: p.getProperty('GITHUB_PAT'),
    owner: p.getProperty('GITHUB_OWNER') || 'johnpark236-tech',
    repo: p.getProperty('GITHUB_REPO') || 'todaypick-web',
    userConfigRootId: p.getProperty('USER_CONFIG_ROOT_ID'),
    mainImagesRootId: p.getProperty('MAIN_IMAGES_ROOT_ID'),
  };
}

// ── 계절 판별 ──────────────────────────────────────────────────────────────────
function seasonOf(yymmdd) {
  const month = parseInt(yymmdd.substring(2, 4), 10);
  if ([12, 1, 2].includes(month)) return 'winter';
  if ([3, 4, 5].includes(month)) return 'spring';
  if ([6, 7, 8].includes(month)) return 'summer';
  return 'autumn';
}

// ── Drive 헬퍼 ─────────────────────────────────────────────────────────────────
function listFolders(parentId) {
  const q = `'${parentId}' in parents and trashed = false and mimeType = 'application/vnd.google-apps.folder'`;
  const res = Drive.Files.list({ q, fields: 'files(id,name)', pageSize: 100 });
  return (res.files || []);
}

function listFiles(parentId) {
  const q = `'${parentId}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'`;
  const res = Drive.Files.list({ q, fields: 'files(id,name,mimeType)', pageSize: 200 });
  return (res.files || []);
}

function readJsonFile(fileId) {
  const content = DriveApp.getFileById(fileId).getBlob().getDataAsString('utf-8');
  return JSON.parse(content);
}

function findFileInFolder(folderId, fileName) {
  const q = `'${folderId}' in parents and trashed = false and name = '${fileName}'`;
  const res = Drive.Files.list({ q, fields: 'files(id,name)', pageSize: 5 });
  const files = res.files || [];
  return files.length > 0 ? files[0] : null;
}

// ── GitHub API ─────────────────────────────────────────────────────────────────
function githubRequest(method, path, body) {
  const { pat, owner, repo } = getProps();
  const url = `https://api.github.com/repos/${owner}/${repo}${path}`;
  const options = {
    method,
    headers: {
      Authorization: `Bearer ${pat}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'Content-Type': 'application/json',
    },
    muteHttpExceptions: true,
  };
  if (body) options.payload = JSON.stringify(body);
  return UrlFetchApp.fetch(url, options);
}

function getFileSha(filePath) {
  const resp = githubRequest('GET', `/contents/${filePath}`);
  if (resp.getResponseCode() === 404) return null;
  return JSON.parse(resp.getContentText()).sha || null;
}

function commitFile(filePath, content, message, sha) {
  const body = {
    message,
    content: Utilities.base64Encode(content, Utilities.Charset.UTF_8),
    branch: 'master',
  };
  if (sha) body.sha = sha;
  const resp = githubRequest('PUT', `/contents/${filePath}`, body);
  const code = resp.getResponseCode();
  if (code !== 200 && code !== 201) {
    throw new Error(`commitFile ${filePath} failed: ${code} ${resp.getContentText().substring(0, 200)}`);
  }
  return JSON.parse(resp.getContentText());
}

function dispatchWorkflow(workflowFile, inputs) {
  const resp = githubRequest('POST', `/actions/workflows/${workflowFile}/dispatches`, {
    ref: 'master',
    inputs,
  });
  const code = resp.getResponseCode();
  if (code !== 204) {
    throw new Error(`dispatch ${workflowFile} failed: ${code} ${resp.getContentText().substring(0, 200)}`);
  }
}

// ── Script Properties 헬퍼 ────────────────────────────────────────────────────
function getSubmittedSets() {
  const raw = PropertiesService.getScriptProperties().getProperty('SUBMITTED_SETS');
  return raw ? JSON.parse(raw) : {};
}

function markSubmitted(key) {
  const sets = getSubmittedSets();
  sets[key] = new Date().toISOString();
  PropertiesService.getScriptProperties().setProperty('SUBMITTED_SETS', JSON.stringify(sets));
}

function getMainImageState() {
  const raw = PropertiesService.getScriptProperties().getProperty('MAIN_IMAGE_STATE');
  return raw ? JSON.parse(raw) : {};
}

function saveMainImageState(state) {
  PropertiesService.getScriptProperties().setProperty('MAIN_IMAGE_STATE', JSON.stringify(state));
}

// ── 업로드 감지 ────────────────────────────────────────────────────────────────
function checkNewUploads() {
  const { userConfigRootId } = getProps();
  if (!userConfigRootId) { Logger.log('USER_CONFIG_ROOT_ID not set'); return; }

  const submitted = getSubmittedSets();
  const dateFolders = listFolders(userConfigRootId);

  for (const dateFolder of dateFolders) {
    // 날짜 폴더 이름 검증 (YYMMDD)
    if (!/^\d{6}$/.test(dateFolder.name)) continue;
    const dateStr = dateFolder.name;

    const segmentFolders = listFolders(dateFolder.id);
    for (const segFolder of segmentFolders) {
      // 세그먼트 이름 검증 (f_10 ~ m_60)
      if (!/^[fm]_(10|20|30|40|50|60)$/.test(segFolder.name)) continue;
      const segment = segFolder.name;
      const key = `${dateStr}/${segment}`;

      if (submitted[key]) continue; // 이미 제출됨

      // manifest.json 확인
      const manifestFile = findFileInFolder(segFolder.id, 'manifest.json');
      if (!manifestFile) continue;

      let manifest;
      try {
        manifest = readJsonFile(manifestFile.id);
      } catch (e) {
        Logger.log(`manifest.json read error ${key}: ${e}`);
        continue;
      }

      // upload_complete 확인
      if (!manifest.upload_complete) continue;
      if (manifest.expected_image_count !== 10) continue;

      // metadata.json 확인
      const metadataFile = findFileInFolder(segFolder.id, 'metadata.json');
      if (!metadataFile) continue;

      Logger.log(`New upload detected: ${key}`);

      try {
        submitPublishRequest(dateStr, segment, segFolder.id, manifestFile.id, metadataFile.id, manifest);
        markSubmitted(key);
        Logger.log(`Submitted: ${key}`);
      } catch (e) {
        Logger.log(`Submit failed ${key}: ${e}`);
      }
    }
  }
}

function submitPublishRequest(dateStr, segment, folderId, manifestFileId, metadataFileId, manifest) {
  const timestamp = new Date().toISOString().replace(/[^0-9]/g, '').substring(0, 14);
  // manifest.json의 request_id가 있으면 그대로 사용 (ChatGPT가 생성한 경우)
  // 없으면 GAS가 새로 생성
  const requestId = manifest.request_id || `tp_${dateStr}_${segment.replace('_', '')}_auto_${timestamp}`;

  // 1. publish_requests JSON 생성
  const requestPath = `publish_requests/${requestId}.json`;
  const requestPayload = JSON.stringify({
    schema_version: 1,
    request_id: requestId,
    date_folder: dateStr,
    segment: segment,
    drive_folder_id: folderId,
    manifest_file_id: manifestFileId,
    metadata_file_id: metadataFileId,
    expected_image_count: 10,
    source: 'gas_auto',
  }, null, 2);

  const existingSha = getFileSha(requestPath);
  commitFile(requestPath, requestPayload,
    `auto: publish request ${requestId}`, existingSha);

  // 2. publish_queue JSON 생성 (push 트리거)
  const queuePath = `publish_queue/auto_${timestamp}.json`;
  const queuePayload = JSON.stringify({
    request_path: requestPath,
    submitted_at: new Date().toISOString(),
    source: 'gas_auto',
  }, null, 2);

  const queueSha = getFileSha(queuePath);
  commitFile(queuePath, queuePayload,
    `auto: queue ${requestId}`, queueSha);

  Logger.log(`Committed: ${requestPath} + ${queuePath}`);
}

// ── 삭제 감지 ──────────────────────────────────────────────────────────────────
/**
 * 00_MAIN_IMAGES/{MM}/{female|male}/{age}/ 구조를 스캔합니다.
 * 파일명 규칙: {look_id}.webp (e.g., autumn_female_50_260923_01.webp)
 * GAS 등록 성공 후 해당 파일들이 위 경로에 복사되어 있어야 감지됩니다.
 */
function checkDeletions() {
  const { mainImagesRootId } = getProps();
  if (!mainImagesRootId) { Logger.log('MAIN_IMAGES_ROOT_ID not set'); return; }

  const prevState = getMainImageState();
  const currentState = {};

  const monthFolders = listFolders(mainImagesRootId);
  for (const monthFolder of monthFolders) {
    if (!/^\d{2}$/.test(monthFolder.name)) continue;

    const genderFolders = listFolders(monthFolder.id);
    for (const genderFolder of genderFolders) {
      if (!['female', 'male'].includes(genderFolder.name)) continue;

      const ageFolders = listFolders(genderFolder.id);
      for (const ageFolder of ageFolders) {
        if (!/^\d{2}$/.test(ageFolder.name)) continue;

        const pathKey = `${monthFolder.name}/${genderFolder.name}/${ageFolder.name}`;
        const files = listFiles(ageFolder.id);
        const fileMap = {};
        for (const f of files) {
          // 파일명에서 look_id 추출 (확장자 제거)
          const lookId = f.name.replace(/\.[^.]+$/, '');
          fileMap[f.id] = lookId;
        }
        currentState[pathKey] = fileMap;
      }
    }
  }

  // 삭제된 파일 감지
  const deletionGroups = {}; // key: "season/segment", value: [look_ids]

  for (const pathKey of Object.keys(prevState)) {
    const prev = prevState[pathKey];
    const curr = currentState[pathKey] || {};

    for (const fileId of Object.keys(prev)) {
      if (!curr[fileId]) {
        // 삭제됨
        const lookId = prev[fileId];
        const [month, gender, age] = pathKey.split('/');
        const monthNum = parseInt(month, 10);
        const season = seasonOf(`00${month}01`);
        const segment = `${gender}_${age}`;
        const groupKey = `${season}/${segment}`;
        if (!deletionGroups[groupKey]) deletionGroups[groupKey] = [];
        deletionGroups[groupKey].push(lookId);
        Logger.log(`Deletion detected: ${lookId} (${groupKey})`);
      }
    }
  }

  // 삭제 워크플로 디스패치
  for (const [groupKey, lookIds] of Object.entries(deletionGroups)) {
    const [season, segment] = groupKey.split('/');
    try {
      dispatchWorkflow('todaypick-drive-delete-sync.yml', {
        look_ids: JSON.stringify(lookIds),
        season,
        segment,
        dry_run: 'false',
      });
      Logger.log(`Delete dispatched: ${groupKey} — ${JSON.stringify(lookIds)}`);
    } catch (e) {
      Logger.log(`Delete dispatch failed ${groupKey}: ${e}`);
    }
  }

  saveMainImageState(currentState);
}

// ── 메인 폴링 함수 (트리거에 등록) ────────────────────────────────────────────
function pollDriveChanges() {
  Logger.log('=== TodayPick Drive Sync Poll START ===');
  try {
    checkNewUploads();
  } catch (e) {
    Logger.log(`checkNewUploads error: ${e}`);
  }
  try {
    checkDeletions();
  } catch (e) {
    Logger.log(`checkDeletions error: ${e}`);
  }
  Logger.log('=== TodayPick Drive Sync Poll END ===');
}

// ── GCS → 00_MAIN_IMAGES 일회성 동기화 ────────────────────────────────────────
/**
 * GCS 카탈로그의 모든 룩을 00_MAIN_IMAGES/{MM}/{gender}/{age}/{look_id}.webp 로 복사.
 * 최초 1회 수동 실행. 이미 존재하는 파일은 건너뜀.
 *
 * look_id 패턴: {season}_{gender}_{age}_{YYMMDD}_{nn}
 * 예: autumn_female_50_260923_01 → 09/female/50/autumn_female_50_260923_01.webp
 */
function syncGcsToMainImages() {
  const { mainImagesRootId } = getProps();
  if (!mainImagesRootId) { Logger.log('MAIN_IMAGES_ROOT_ID not set'); return; }

  const bucket = 'todaypick-daily-looks-363284724091';
  const seasons = ['autumn', 'spring', 'summer', 'winter'];
  const genders = ['female', 'male'];
  const ages = ['10', '20', '30', '40', '50', '60'];

  let total = 0, skipped = 0, uploaded = 0, failed = 0;

  for (const season of seasons) {
    for (const gender of genders) {
      for (const age of ages) {
        const segment = `${gender}_${age}`;
        const catalogUrl = `https://storage.googleapis.com/${bucket}/production/${season}/${segment}.json`;

        let catalog;
        try {
          const resp = UrlFetchApp.fetch(catalogUrl, { muteHttpExceptions: true });
          if (resp.getResponseCode() !== 200) continue;
          catalog = JSON.parse(resp.getContentText());
        } catch (e) {
          Logger.log(`Catalog fetch error ${season}/${segment}: ${e}`);
          continue;
        }

        const looks = catalog.looks || [];
        if (looks.length === 0) continue;
        Logger.log(`Syncing ${season}/${segment}: ${looks.length} looks`);

        for (const look of looks) {
          total++;
          const lookId = look.id;
          if (!lookId || !look.url) { failed++; continue; }

          // look_id에서 월 추출: autumn_female_50_260923_01 → 260923 → 09
          const parts = lookId.split('_');
          // parts: [season, gender, age, YYMMDD, nn] or [season, gender(two parts), age, YYMMDD, nn]
          // gender could be 'female' or 'male' (single word), age is 2-digit number
          const dateStr = parts.find(p => /^\d{6}$/.test(p));
          if (!dateStr) { Logger.log(`Cannot parse date from ${lookId}`); failed++; continue; }
          const month = dateStr.substring(2, 4); // "260923" → "09"

          // 폴더 경로: 00_MAIN_IMAGES/{month}/{gender}/{age}/
          const monthFolder = getOrCreateFolder(mainImagesRootId, month);
          const genderFolder = getOrCreateFolder(monthFolder, gender);
          const ageFolder = getOrCreateFolder(genderFolder, age);

          const fileName = `${lookId}.webp`;

          // 이미 존재하면 skip
          const existing = findFileInFolder(ageFolder, fileName);
          if (existing) { skipped++; continue; }

          // GCS에서 이미지 다운로드 후 Drive에 업로드
          try {
            const imgResp = UrlFetchApp.fetch(look.url, { muteHttpExceptions: true });
            if (imgResp.getResponseCode() !== 200) {
              Logger.log(`Image fetch failed ${lookId}: ${imgResp.getResponseCode()}`);
              failed++;
              continue;
            }
            const blob = imgResp.getBlob().setName(fileName).setContentType('image/webp');
            DriveApp.getFolderById(ageFolder).createFile(blob);
            uploaded++;
            Logger.log(`Uploaded: ${fileName}`);
          } catch (e) {
            Logger.log(`Upload error ${lookId}: ${e}`);
            failed++;
          }

          Utilities.sleep(200); // Drive API 레이트 리밋 방지
        }
      }
    }
  }

  Logger.log(`=== syncGcsToMainImages DONE ===`);
  Logger.log(`Total: ${total}, Uploaded: ${uploaded}, Skipped: ${skipped}, Failed: ${failed}`);
}

function getOrCreateFolder(parentId, name) {
  const q = `'${parentId}' in parents and trashed = false and mimeType = 'application/vnd.google-apps.folder' and name = '${name}'`;
  const res = Drive.Files.list({ q, fields: 'files(id)', pageSize: 5 });
  const files = (res.files || []);
  if (files.length > 0) return files[0].id;
  const meta = {
    name,
    mimeType: 'application/vnd.google-apps.folder',
    parents: [parentId],
  };
  const created = Drive.Files.create(meta, null, { fields: 'id', supportsAllDrives: true });
  return created.id;
}

// ── 트리거 설정 (최초 1회 실행) ───────────────────────────────────────────────
function installTrigger() {
  // 기존 트리거 제거
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'pollDriveChanges') {
      ScriptApp.deleteTrigger(t);
    }
  });
  // 1분마다 실행 (테스트용; 운영시 everyMinutes(5) 으로 변경)
  ScriptApp.newTrigger('pollDriveChanges')
    .timeBased()
    .everyMinutes(1)
    .create();
  Logger.log('Trigger installed: pollDriveChanges every 1 minute');
}

function removeTrigger() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'pollDriveChanges') {
      ScriptApp.deleteTrigger(t);
      Logger.log('Trigger removed');
    }
  });
}
