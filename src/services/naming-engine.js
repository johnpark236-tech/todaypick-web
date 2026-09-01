/**
 * TodayPick Naming Engine
 * vc72 — 코디명 추천 3개 생성 + normalization + 중복 suffix 처리
 *
 * 핵심 원칙:
 * - 추천 3개: funny / emotional / global 각각 다른 결
 * - 옷 metadata(color, style, gender, ageGroup) 활용
 * - 날짜를 이름에 자동으로 넣지 않음 (날짜는 DB metadata에서만)
 * - 안전 네이밍 정책 준수 (욕설/혐오/비하 금지)
 * - MAX_NAME_LENGTH=50
 */

import LEXICON from '../data/naming-lexicon.json';
import { findRegistryByNormalizedName } from './naming-db.js';

export const MAX_NAME_LENGTH = 50;

// ── 안전 필터 (기본적인 차단 패턴) ─────────────────────────────
const SAFETY_BLOCKLIST = [
  /시발|씨발|씨발|개새끼|미친|꺼져|죽어|닥쳐|존나|ㅅㅂ|ㅆㅂ/i,
];

export function isSafeName(name) {
  return !SAFETY_BLOCKLIST.some(p => p.test(name));
}

// ── normalization ────────────────────────────────────────────────
/**
 * DB 비교용 normalizedName 생성
 * - trim + 중복 공백 제거 + 소문자 + Unicode NFC
 * 원본 baseName은 보존
 */
export function normalizeName(name) {
  return name
    .normalize('NFC')
    .trim()
    .replace(/\s+/g, ' ')
    .toLowerCase();
}

// ── resolvedName: 중복 suffix 처리 ──────────────────────────────
/**
 * DB에서 normalizedBaseName 기반으로 중복 조회 후
 * 충돌 없는 resolvedName 반환
 *
 * 규칙:
 *   baseName        → 충돌 없으면 그대로
 *   baseName (1)    → 1번 충돌
 *   baseName (2)    → 2번 충돌
 *
 * @param {string} baseName  사용자 확정 이름 (원본)
 * @returns {Promise<{baseName:string, resolvedName:string, normalizedName:string}>}
 */
export async function resolveShareName(baseName) {
  const normalizedBase = normalizeName(baseName);

  // DB에서 이 base와 suffix 패턴 모두 조회
  const existingEntries = await findRegistryByNormalizedName(normalizedBase);

  // 이미 사용된 normalizedName 집합 구성
  const usedNormalized = new Set(existingEntries.map(e => e.normalizedName));

  // baseName 자체가 충돌 없으면 사용
  if (!usedNormalized.has(normalizedBase)) {
    return {
      baseName,
      resolvedName:   baseName,
      normalizedName: normalizedBase,
    };
  }

  // suffix (N) 순서대로 탐색
  let n = 1;
  while (n <= 999) {
    const candidate      = `${baseName} (${n})`;
    const normalizedCand = normalizeName(candidate);
    if (!usedNormalized.has(normalizedCand)) {
      return {
        baseName,
        resolvedName:   candidate,
        normalizedName: normalizedCand,
      };
    }
    n++;
  }

  // fallback (사실상 발생 불가)
  return {
    baseName,
    resolvedName:   baseName,
    normalizedName: normalizedBase,
  };
}

// ── 랜덤 픽 (같은 type 내에서) ──────────────────────────────────
function pickRandom(arr) {
  if (!arr || arr.length === 0) return null;
  return arr[Math.floor(Math.random() * arr.length)];
}

// ── outfit metadata → color/style 힌트 추출 ─────────────────────
function extractHints(outfit) {
  const title  = (outfit?.title || '').toLowerCase();
  const id     = (outfit?.id    || '').toLowerCase();

  // 색상 힌트
  const colors = Object.keys(LEXICON.colorMap);
  const detectedColor = colors.find(c => title.includes(c));

  // 스타일 힌트
  const styles = Object.keys(LEXICON.styleMap);
  const detectedStyle = styles.find(s => title.includes(s));

  return { detectedColor, detectedStyle };
}

// ── genderAge 정규화 ─────────────────────────────────────────────
function normalizeGroupKey(currentMode) {
  if (!currentMode) return null;
  const m = currentMode.match(/^(female|male)_(\d+)s?$/i);
  if (!m) return null;
  return `${m[1].toLowerCase()}_${m[2]}s`;
}

// ── 추천 3개 생성 ────────────────────────────────────────────────
/**
 * @param {object} outfit     현재 outfit 객체
 * @param {string} currentMode  'female_20s' 형식
 * @returns {Array<{text:string, type:string}>}  3개 추천 배열
 */
export function generateNamingRecommendations(outfit, currentMode) {
  const { detectedColor, detectedStyle } = extractHints(outfit);
  const groupKey = normalizeGroupKey(currentMode);

  // genderAgeMap에서 type 우선순위 결정 (0=highest)
  const groupPref = LEXICON.genderAgeMap[groupKey] || { funny: 0, emotional: 1, global: 2 };
  const sortedTypes = Object.entries(groupPref)
    .sort((a, b) => a[1] - b[1])
    .map(([type]) => type);  // ['funny','emotional','global'] 순서

  const TYPES = ['funny', 'emotional', 'global'];
  const results = [];
  const usedTexts = new Set();

  for (const type of TYPES) {
    let candidate = null;

    // 1순위: colorMap 힌트
    if (detectedColor && LEXICON.colorMap[detectedColor]?.[type]) {
      candidate = LEXICON.colorMap[detectedColor][type];
    }

    // 2순위: styleMap 힌트
    if (!candidate && detectedStyle && LEXICON.styleMap[detectedStyle]?.[type]) {
      candidate = LEXICON.styleMap[detectedStyle][type];
    }

    // 3순위: 랜덤 (중복 방지)
    if (!candidate || usedTexts.has(candidate)) {
      const pool = (LEXICON.templates[type] || []).filter(t => !usedTexts.has(t));
      candidate = pickRandom(pool) || pickRandom(LEXICON.templates[type]) || `오늘의 코디 Pick`;
    }

    // 안전 필터
    if (!isSafeName(candidate)) {
      candidate = pickRandom(LEXICON.templates.funny) || '오늘의 코디 Pick';
    }

    usedTexts.add(candidate);
    results.push({ text: candidate, type });
  }

  // genderAge 우선순위 순으로 reorder: sortedTypes 순서로 재배열
  const reordered = sortedTypes.map(type => results.find(r => r.type === type)).filter(Boolean);

  // 혹시 3개 미만이면 기본값으로 채우기
  while (reordered.length < 3) {
    reordered.push({ text: '오늘의 코디 Pick', type: 'funny' });
  }

  return reordered.slice(0, 3);
}

// ── 사용자 입력 검증 ─────────────────────────────────────────────
/**
 * 빈 값 / 너무 긴 값 검증
 * @param {string} input
 * @param {string} fallback  빈 경우 fallback
 * @returns {string}  확정 baseName
 */
export function validateUserInput(input, fallback) {
  const trimmed = (input || '').trim();
  if (!trimmed) return fallback;
  if (trimmed.length > MAX_NAME_LENGTH) return trimmed.slice(0, MAX_NAME_LENGTH).trim();
  return trimmed;
}

// ── shareId 생성 ─────────────────────────────────────────────────
export function generateShareId() {
  const ts   = Date.now().toString(36).toUpperCase();
  const rand = Math.random().toString(36).slice(2, 6).toUpperCase();
  return `SHARE_${ts}_${rand}`;
}
