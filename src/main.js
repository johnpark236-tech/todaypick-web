import './style.css';
import { Capacitor } from '@capacitor/core';
import { App } from '@capacitor/app';
import { Share } from '@capacitor/share';
import { OutfitManager } from './data/outfits.js';
import { CoupangService } from './services/coupang.js';
import { StorageService } from './services/storage.js';
import { AudioHub } from './services/audio.js';

// 12 Demographic groups ordered sequentially for vertical swipe navigation
const ALL_GROUPS = [
  'female_10s', 'female_20s', 'female_30s', 'female_40s', 'female_50s', 'female_60s',
  'male_10s', 'male_20s', 'male_30s', 'male_40s', 'male_50s', 'male_60s'
];

// Application state
const state = {
  config: null,
  currentMode: 'female_20s', // 12 cohorts: female_10s~60s, male_10s~60s
  currentOutfit: null,
  activeView: 'view-home',
  isPriceSheetOpen: false,
  isExitDialogOpen: false
};

const outfitManager = new OutfitManager();
let coupangService = null;

// DOM Elements
const dom = {
  greeting: document.getElementById('lbl-greeting'),
  modeTabs: document.querySelectorAll('.mode-tab'),
  btnModeFemale: document.getElementById('btn-mode-female'),
  btnModeMale: document.getElementById('btn-mode-male'),
  dropdownFemale: document.getElementById('dropdown-female'),
  dropdownMale: document.getElementById('dropdown-male'),
  lblFemaleAge: document.getElementById('lbl-female-age'),
  lblMaleAge: document.getElementById('lbl-male-age'),
  dropdownItems: document.querySelectorAll('.dropdown-item'),
  characterDisplay: document.querySelector('.character-display'),
  mainImg: document.getElementById('main-character-img'),
  thumbCarousel: document.getElementById('thumb-carousel'),
  btnSave: document.getElementById('btn-save-outfit'),
  btnShare: document.getElementById('btn-share-outfit'),
  btnRandom: document.getElementById('btn-random-pick'),
  btnTogglePrice: document.getElementById('btn-toggle-price'),
  btnToggleBgm: document.getElementById('btn-toggle-bgm'),
  priceSheetBackdrop: document.getElementById('price-sheet-backdrop'),
  priceSheetPanel: document.getElementById('price-sheet-panel'),
  btnCloseSheet: document.getElementById('btn-close-sheet'),
  sheetOutfitName: document.getElementById('sheet-outfit-name'),
  sheetItemsList: document.getElementById('sheet-items-list'),
  sheetTotalPrice: document.getElementById('sheet-total-price'),
  navItems: document.querySelectorAll('.nav-item'),
  views: document.querySelectorAll('.view-section'),
  searchInput: document.getElementById('search-input'),
  btnDoSearch: document.getElementById('btn-do-search'),
  searchResults: document.getElementById('search-results'),
  searchChips: document.querySelectorAll('.chip-btn'),
  savedGrid: document.getElementById('saved-looks-grid'),
  sliderScale: document.getElementById('slider-scale'),
  sliderOffsetY: document.getElementById('slider-offset-y'),
  sliderGap: document.getElementById('slider-gap'),
  sliderBgmVol: document.getElementById('slider-bgm-volume'),
  valBgmVol: document.getElementById('val-bgm-volume'),
  sliderSfxVol: document.getElementById('slider-sfx-volume'),
  valSfxVol: document.getElementById('val-sfx-volume'),
  valScale: document.getElementById('val-scale'),
  valOffsetY: document.getElementById('val-offset-y'),
  valGap: document.getElementById('val-gap'),
  btnResetSettings: document.getElementById('btn-reset-settings'),
  btnSaveSettings: document.getElementById('btn-save-settings'),
  btnDownloadBackup: document.getElementById('btn-download-backup'),
  lblWorkerStatus: document.getElementById('lbl-worker-status'),
  toast: document.getElementById('toast'),
  exitDialogBackdrop: document.getElementById('exit-dialog-backdrop'),
  btnExitCancel: document.getElementById('btn-exit-cancel'),
  btnExitConfirm: document.getElementById('btn-exit-confirm')
};

// Toast notification
function showToast(msg) {
  dom.toast.textContent = msg;
  dom.toast.classList.add('show');
  setTimeout(() => dom.toast.classList.remove('show'), 2200);
}

// Greeting helper
function updateGreeting() {
  const hour = new Date().getHours();
  let text = '좋은 하루예요';
  if (hour >= 6 && hour < 12) text = '좋은 아침이에요';
  else if (hour >= 12 && hour < 18) text = '좋은 오후예요';
  else if (hour >= 18 && hour < 22) text = '좋은 저녁이에요';
  else text = '편안한 밤 되세요';
  dom.greeting.textContent = text;
}

// Apply CSS variables from settings
function applyUiSettings(scale, offsetY, gap) {
  document.documentElement.style.setProperty('--character-scale', scale);
  document.documentElement.style.setProperty('--character-offset-y', `${offsetY}px`);
  document.documentElement.style.setProperty('--thumbnail-gap', `${gap}px`);
}

// Render Outfit in Home stage
function renderOutfit(outfit) {
  if (!outfit) return;
  state.currentOutfit = outfit;

  dom.mainImg.style.opacity = '0';
  setTimeout(() => {
    dom.mainImg.src = outfit.image;
    dom.mainImg.alt = outfit.title;
    dom.mainImg.style.opacity = '1';
  }, 80);

  // Update Save button state
  const isSaved = StorageService.isSaved(outfit.id, outfit.mode);
  dom.btnSave.classList.toggle('saved', isSaved);

  // Update Carousel active selection
  const cards = dom.thumbCarousel.querySelectorAll('.thumb-card');
  cards.forEach(c => {
    const isCur = c.dataset.id === outfit.id;
    c.classList.toggle('selected', isCur);
    if (isCur) {
      c.scrollIntoView({ behavior: 'smooth', inline: 'nearest', block: 'nearest' });
    }
  });
}

// Populate Thumbnails Carousel
function populateThumbnails(mode) {
  const looks = outfitManager.getLooks(mode);
  dom.thumbCarousel.innerHTML = '';

  looks.forEach((look, index) => {
    const card = document.createElement('article');
    card.className = 'thumb-card';
    card.dataset.id = look.id;
    if (state.currentOutfit && state.currentOutfit.id === look.id) {
      card.classList.add('selected');
    }

    card.innerHTML = `
      <img class="thumb-img" src="${look.thumbnail}" alt="${look.title}" loading="lazy" />
    `;

    card.addEventListener('click', () => {
      AudioHub.tap();
      renderOutfit(look);
    });

    dom.thumbCarousel.appendChild(card);
  });
}

// Close all open dropdown menus
function closeDropdowns() {
  if (dom.dropdownFemale) dom.dropdownFemale.classList.remove('open');
  if (dom.dropdownMale) dom.dropdownMale.classList.remove('open');
}

// Switch Character Mode across 12 Demographic Groups
function switchMode(groupKey) {
  // Alias backward compatibility: 'female' -> 'female_20s', 'male' -> 'male_20s'
  if (groupKey === 'female') groupKey = 'female_20s';
  if (groupKey === 'male') groupKey = 'male_20s';

  state.currentMode = groupKey;

  const isFemale = groupKey.startsWith('female');
  const gender = isFemale ? 'female' : 'male';
  const ageLabel = groupKey.replace(`${gender}_`, '').replace('s', '대');

  // Update tabs active state
  if (dom.btnModeFemale) dom.btnModeFemale.classList.toggle('active', isFemale);
  if (dom.btnModeMale) dom.btnModeMale.classList.toggle('active', !isFemale);

  // Update tab sub label
  if (isFemale && dom.lblFemaleAge) dom.lblFemaleAge.textContent = ageLabel;
  if (!isFemale && dom.lblMaleAge) dom.lblMaleAge.textContent = ageLabel;

  // Update dropdown item highlights
  if (dom.dropdownItems) {
    dom.dropdownItems.forEach(item => {
      item.classList.toggle('active', item.dataset.group === groupKey);
    });
  }

  // Close dropdowns
  closeDropdowns();

  // Populate thumbnails and render first look of the group
  populateThumbnails(groupKey);
  const firstLook = outfitManager.getOutfit(groupKey);
  renderOutfit(firstLook);
}

// Open / Close Price Sheet
function setPriceSheet(isOpen) {
  state.isPriceSheetOpen = isOpen;
  dom.priceSheetBackdrop.classList.toggle('open', isOpen);
  dom.priceSheetPanel.classList.toggle('open', isOpen);

  if (isOpen && state.currentOutfit) {
    dom.sheetOutfitName.textContent = state.currentOutfit.title;
    dom.sheetTotalPrice.textContent = `${Number(state.currentOutfit.totalPrice).toLocaleString('ko-KR')}원`;

    dom.sheetItemsList.innerHTML = state.currentOutfit.items.map(item => `
      <div class="item-row">
        <span class="item-slot-badge">${item.slot}</span>
        <div class="item-info">
          <span class="item-name">${item.name}</span>
          <span class="item-price">${Number(item.price).toLocaleString('ko-KR')}원</span>
        </div>
        <button class="item-btn-coupang" data-keyword="${item.searchKeyword}" data-name="${item.name}">
          쿠팡보기
        </button>
      </div>
    `).join('');

    // Attach click handlers to "쿠팡보기"
    dom.sheetItemsList.querySelectorAll('.item-btn-coupang').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        AudioHub.tap();
        const kw = e.currentTarget.dataset.keyword || e.currentTarget.dataset.name;
        const searchUrl = `https://www.coupang.com/np/search?component=&q=${encodeURIComponent(kw)}`;
        showToast(`쿠팡 '${kw}' 검색 중...`);
        await coupangService.openInCoupang(searchUrl);
      });
    });
  }
}

// Open / Close Exit Confirmation Dialog (One Dialog Only)
function setExitDialog(isOpen) {
  if (state.isExitDialogOpen === isOpen) return; // Prevent duplicate transitions
  state.isExitDialogOpen = isOpen;
  if (!dom.exitDialogBackdrop) return;
  dom.exitDialogBackdrop.classList.toggle('open', isOpen);
}

// Android Back Navigation Handler with Strict Priority Hierarchy
function handleBackButton() {
  // Priority 1: Exit Confirmation Dialog is open -> Close dialog (Cancel exit)
  if (state.isExitDialogOpen) {
    setExitDialog(false);
    return;
  }

  // Priority 2: Price Sheet Modal is open -> Close Price Sheet only (Do not exit)
  if (state.isPriceSheetOpen) {
    setPriceSheet(false);
    return;
  }

  // Priority 3: Subroute / Subview active -> Return to HOME (view-home)
  if (state.activeView !== 'view-home') {
    switchView('view-home');
    return;
  }

  // Priority 4: Complete HOME root state -> Show Exit Confirmation Dialog
  setExitDialog(true);
}

// Switch Active View
function switchView(targetId) {
  state.activeView = targetId;
  dom.views.forEach(v => {
    v.classList.toggle('active', v.id === targetId);
  });
  dom.navItems.forEach(n => {
    n.classList.toggle('active', n.dataset.target === targetId);
  });

  if (targetId === 'view-saved') {
    renderSavedLooks();
  }
}

// Render Saved Looks
function renderSavedLooks() {
  const saved = StorageService.getSavedLooks();
  if (!saved.length) {
    dom.savedGrid.innerHTML = '<div class="empty-state" style="grid-column: span 2;">저장된 코디가 없습니다.<br>홈 화면에서 마음에 드는 코디를 저장해보세요!</div>';
    return;
  }

  dom.savedGrid.innerHTML = saved.map(item => `
    <div class="saved-card" data-id="${item.id}" data-mode="${item.mode}">
      <button class="saved-btn-remove" data-id="${item.id}" data-mode="${item.mode}">&times;</button>
      <img class="saved-thumb" src="${item.image}" alt="${item.title}" />
      <span class="saved-title">${item.title}</span>
      <span class="saved-price">${Number(item.totalPrice).toLocaleString('ko-KR')}원</span>
      <button class="btn-primary" style="padding: 6px; font-size: 11px;" data-action="view">코디 보기</button>
    </div>
  `).join('');

  dom.savedGrid.querySelectorAll('.saved-btn-remove').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const id = e.currentTarget.dataset.id;
      const mode = e.currentTarget.dataset.mode;
      StorageService.removeLook(id, mode);
      showToast('코디가 삭제되었습니다.');
      renderSavedLooks();
      if (state.currentOutfit && state.currentOutfit.id === id) {
        dom.btnSave.classList.remove('saved');
      }
    });
  });

  dom.savedGrid.querySelectorAll('[data-action="view"]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const card = e.currentTarget.closest('.saved-card');
      const id = card.dataset.id;
      const mode = card.dataset.mode;
      switchView('view-home');
      switchMode(mode);
      const look = outfitManager.getOutfit(mode, id);
      renderOutfit(look);
    });
  });
}

// Coupang Search
async function executeSearch(query) {
  if (!query || !query.trim()) return;
  dom.searchInput.value = query;
  dom.searchResults.innerHTML = '<div class="empty-state">쿠팡 상품을 검색 중입니다...</div>';

  try {
    const res = await coupangService.search(query);
    if (!res.products || !res.products.length) {
      dom.searchResults.innerHTML = '<div class="empty-state">검색 결과가 없습니다. 다른 검색어를 입력해보세요.</div>';
      return;
    }

    dom.searchResults.innerHTML = res.products.map(p => {
      const priceFmt = Number(p.productPrice || 0).toLocaleString('ko-KR');
      const prodUrl = p.canonicalUrl || p.productUrl;
      return `
        <article class="product-card">
          <img class="product-thumb" src="${p.productImage}" alt="${p.productName}" />
          <div class="product-body">
            <h4 class="product-title">${p.productName}</h4>
            <div class="product-bottom-row">
              <span class="product-price-txt">${priceFmt}원</span>
              <button class="product-btn-buy" data-url="${prodUrl}">쿠팡 구매</button>
            </div>
          </div>
        </article>
      `;
    }).join('');

    dom.searchResults.querySelectorAll('.product-btn-buy').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const url = e.currentTarget.dataset.url;
        showToast('쿠팡 제휴 링크로 이동 중...');
        await coupangService.openInCoupang(url);
      });
    });
  } catch (err) {
    dom.searchResults.innerHTML = `<div class="empty-state">검색 실패: ${err.message}</div>`;
  }
}

// Initialize Application
async function initApp() {
  AudioHub.init();
  updateGreeting();

  // Load config.json
  try {
    const cfgRes = await fetch('/config.json');
    state.config = await cfgRes.json();
  } catch {
    state.config = {
      workerUrl: 'https://todaypick-coupang-proxy.johnpark236.workers.dev',
      mainCharacterScale: 1.0,
      mainCharacterOffsetY: 0,
      thumbnailGap: 8,
      defaultMode: 'real'
    };
  }

  coupangService = new CoupangService(state.config.workerUrl);

  // Restore stored UI config if exists
  const storedUi = StorageService.getUiConfig();
  const currentScale = storedUi?.mainCharacterScale ?? state.config.mainCharacterScale ?? 1.0;
  const currentOffset = storedUi?.mainCharacterOffsetY ?? state.config.mainCharacterOffsetY ?? 0;
  const currentGap = storedUi?.thumbnailGap ?? state.config.thumbnailGap ?? 8;

  applyUiSettings(currentScale, currentOffset, currentGap);

  // Sync sliders
  dom.sliderScale.value = currentScale;
  dom.sliderOffsetY.value = currentOffset;
  dom.sliderGap.value = currentGap;
  dom.valScale.textContent = `${currentScale}x`;
  dom.valOffsetY.textContent = `${currentOffset}px`;
  dom.valGap.textContent = `${currentGap}px`;

  // Sync Audio Settings
  const curBgmVol = Math.round(AudioHub.getBgmVolume() * 100);
  const curSfxVol = Math.round(AudioHub.getSfxVolume() * 100);
  if (dom.sliderBgmVol) dom.sliderBgmVol.value = curBgmVol;
  if (dom.valBgmVol) dom.valBgmVol.textContent = `${curBgmVol}%`;
  if (dom.sliderSfxVol) dom.sliderSfxVol.value = curSfxVol;
  if (dom.valSfxVol) dom.valSfxVol.textContent = `${curSfxVol}%`;
  updateBgmButtonUi(AudioHub.getIsBgmEnabled());

  // Start with default mode
  switchMode(state.config.defaultMode || 'female');

  // Check Coupang worker health in background
  coupangService.checkHealth().then(h => {
    if (h.status === 'ok') {
      dom.lblWorkerStatus.innerHTML = '<strong>상태:</strong> 정상 연결됨 (Real Mode)';
      dom.lblWorkerStatus.style.color = '#10B981';
    } else {
      dom.lblWorkerStatus.innerHTML = `<strong>상태:</strong> ${h.status}`;
      dom.lblWorkerStatus.style.color = '#EF4444';
    }
  });

  // Clean legacy Google session keys if any
  try {
    localStorage.removeItem('todaypick_google_session');
    localStorage.removeItem('todaypick_google_account_email');
  } catch {}

  // Setup Event Listeners
  setupEventListeners();
}

function updateBgmButtonUi(isEnabled) {
  if (!dom.btnToggleBgm) return;
  dom.btnToggleBgm.classList.toggle('muted', !isEnabled);
  const iconOn = dom.btnToggleBgm.querySelector('.icon-bgm-on');
  const iconOff = dom.btnToggleBgm.querySelector('.icon-bgm-off');
  if (iconOn && iconOff) {
    iconOn.style.display = isEnabled ? 'block' : 'none';
    iconOff.style.display = isEnabled ? 'none' : 'block';
  }
}

function setupEventListeners() {
  // Female tab click -> Toggle Female dropdown
  if (dom.btnModeFemale) {
    dom.btnModeFemale.addEventListener('click', (e) => {
      e.stopPropagation();
      AudioHub.tap();
      if (!state.currentMode.startsWith('female')) {
        const curAge = dom.lblFemaleAge ? dom.lblFemaleAge.textContent.replace('대', 's') : '20s';
        switchMode(`female_${curAge}`);
      }
      const isOpen = dom.dropdownFemale && dom.dropdownFemale.classList.contains('open');
      closeDropdowns();
      if (!isOpen && dom.dropdownFemale) dom.dropdownFemale.classList.add('open');
    });
  }

  // Male tab click -> Toggle Male dropdown
  if (dom.btnModeMale) {
    dom.btnModeMale.addEventListener('click', (e) => {
      e.stopPropagation();
      AudioHub.tap();
      if (!state.currentMode.startsWith('male')) {
        const curAge = dom.lblMaleAge ? dom.lblMaleAge.textContent.replace('대', 's') : '20s';
        switchMode(`male_${curAge}`);
      }
      const isOpen = dom.dropdownMale && dom.dropdownMale.classList.contains('open');
      closeDropdowns();
      if (!isOpen && dom.dropdownMale) dom.dropdownMale.classList.add('open');
    });
  }

  // Dropdown items click
  if (dom.dropdownItems) {
    dom.dropdownItems.forEach(item => {
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        AudioHub.tap();
        const targetGroup = item.dataset.group;
        if (targetGroup) {
          switchMode(targetGroup);
        }
      });
    });
  }

  // Close dropdown when clicking outside
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.mode-dropdown-container')) {
      closeDropdowns();
    }
  });

  // Save button
  dom.btnSave.addEventListener('click', () => {
    if (!state.currentOutfit) return;
    AudioHub.tap();
    const isNowSaved = StorageService.isSaved(state.currentOutfit.id, state.currentOutfit.mode);
    if (isNowSaved) {
      StorageService.removeLook(state.currentOutfit.id, state.currentOutfit.mode);
      dom.btnSave.classList.remove('saved');
      showToast('저장 목록에서 제거되었습니다.');
    } else {
      StorageService.saveLook(state.currentOutfit);
      dom.btnSave.classList.add('saved');
      showToast('코디가 내 코디에 저장되었습니다!');
    }
  });

  // Share button (Android Native Share / KakaoTalk share support)
  if (dom.btnShare) {
    dom.btnShare.addEventListener('click', async () => {
      AudioHub.tap();
      await shareCurrentOutfit();
    });
  }

  // Random pick button
  dom.btnRandom.addEventListener('click', () => {
    AudioHub.tap();
    const next = outfitManager.getRandom(state.currentMode, state.currentOutfit?.id);
    renderOutfit(next);
    showToast('새로운 추천 코디를 골랐어요!');
  });

  // Price Sheet Toggle
  dom.btnTogglePrice.addEventListener('click', () => {
    AudioHub.tap();
    setPriceSheet(true);
  });
  dom.btnCloseSheet.addEventListener('click', () => {
    AudioHub.tap();
    setPriceSheet(false);
  });
  dom.priceSheetBackdrop.addEventListener('click', (e) => {
    if (e.target === dom.priceSheetBackdrop) {
      AudioHub.tap();
      setPriceSheet(false);
    }
  });

  // BGM Toggle Button (Speaker Icon)
  if (dom.btnToggleBgm) {
    dom.btnToggleBgm.addEventListener('click', () => {
      AudioHub.tap();
      const isEnabled = AudioHub.toggleBgm();
      updateBgmButtonUi(isEnabled);
      showToast(isEnabled ? '배경음을 켰습니다.' : '배경음을 껐습니다.');
    });
  }

  // Audio Volume Sliders (Settings View)
  if (dom.sliderBgmVol) {
    dom.sliderBgmVol.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      if (dom.valBgmVol) dom.valBgmVol.textContent = `${val}%`;
      AudioHub.setBgmVolume(val / 100);
    });
  }
  if (dom.sliderSfxVol) {
    dom.sliderSfxVol.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      if (dom.valSfxVol) dom.valSfxVol.textContent = `${val}%`;
      AudioHub.setSfxVolume(val / 100);
    });
  }

  // Share current outfit via Native Android Share Sheet (KakaoTalk enabled)
  async function shareCurrentOutfit() {
    if (!state.currentOutfit) {
      showToast('공유할 코디가 없습니다.');
      return;
    }
    const outfit = state.currentOutfit;
    const sharePayload = {
      title: 'TodayPick 오늘뭐입지',
      text: `[TodayPick 오늘뭐입지]\n오늘의 추천 코디: ${outfit.title}\nTodayPick에서 스타일링과 최저가 정보를 확인해보세요!`,
      dialogTitle: 'TodayPick 코디 공유'
    };

    // Priority 1: Capacitor Native Share plugin (Android Native Share Sheet with KakaoTalk)
    try {
      await Share.share(sharePayload);
      return;
    } catch (nativeErr) {
      if (nativeErr && (nativeErr.name === 'AbortError' || String(nativeErr).includes('canceled') || String(nativeErr).includes('cancelled'))) {
        return;
      }
      console.warn('[Share] Native share note:', nativeErr);
    }

    // Priority 2: Web Share API fallback (Browser)
    if (navigator.share) {
      try {
        await navigator.share(sharePayload);
        return;
      } catch (webErr) {
        if (webErr && webErr.name === 'AbortError') return;
        console.warn('[Share] Web share note:', webErr);
      }
    }

    // Priority 3: Clipboard fallback (Desktop browser without share API)
    if (navigator.clipboard) {
      try {
        await navigator.clipboard.writeText(`${sharePayload.title}\n${sharePayload.text}`);
        showToast('코디 정보가 클립보드에 복사되었습니다.');
      } catch {}
    }
  }

  // Bottom Navigation
  dom.navItems.forEach(item => {
    item.addEventListener('click', () => {
      AudioHub.tap();
      switchView(item.dataset.target);
    });
  });

  // Search
  dom.btnDoSearch.addEventListener('click', () => {
    AudioHub.tap();
    executeSearch(dom.searchInput.value);
  });
  dom.searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      AudioHub.tap();
      executeSearch(dom.searchInput.value);
    }
  });
  dom.searchChips.forEach(chip => {
    chip.addEventListener('click', () => {
      AudioHub.tap();
      executeSearch(chip.dataset.query);
    });
  });

  // Settings Sliders (Live Update)
  dom.sliderScale.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    dom.valScale.textContent = `${val.toFixed(2)}x`;
    applyUiSettings(val, parseFloat(dom.sliderOffsetY.value), parseInt(dom.sliderGap.value));
  });

  dom.sliderOffsetY.addEventListener('input', (e) => {
    const val = parseInt(e.target.value);
    dom.valOffsetY.textContent = `${val}px`;
    applyUiSettings(parseFloat(dom.sliderScale.value), val, parseInt(dom.sliderGap.value));
  });

  dom.sliderGap.addEventListener('input', (e) => {
    const val = parseInt(e.target.value);
    dom.valGap.textContent = `${val}px`;
    applyUiSettings(parseFloat(dom.sliderScale.value), parseFloat(dom.sliderOffsetY.value), val);
  });

  // Reset Settings
  dom.btnResetSettings.addEventListener('click', () => {
    StorageService.clearUiConfig();
    const s = state.config.mainCharacterScale || 1.0;
    const o = state.config.mainCharacterOffsetY || 0;
    const g = state.config.thumbnailGap || 8;
    dom.sliderScale.value = s;
    dom.sliderOffsetY.value = o;
    dom.sliderGap.value = g;
    dom.valScale.textContent = `${s}x`;
    dom.valOffsetY.textContent = `${o}px`;
    dom.valGap.textContent = `${g}px`;
    applyUiSettings(s, o, g);
    showToast('설정이 기본값으로 복원되었습니다.');
  });

  // Save Settings (Local Phone Storage Only)
  dom.btnSaveSettings.addEventListener('click', () => {
    AudioHub.tap();
    const s = parseFloat(dom.sliderScale.value) || 1.0;
    const o = parseInt(dom.sliderOffsetY.value) || 0;
    const g = parseInt(dom.sliderGap.value) || 4;
    const sliderMode = document.getElementById('slider-mode-button-scale');
    const modeScale = sliderMode ? parseFloat(sliderMode.value) : 2.0;
    const bgmVol = AudioHub.getBgmVolume();
    const sfxVol = AudioHub.getSfxVolume();
    const isBgmOn = AudioHub.getIsBgmEnabled();

    // Local Storage Save & Merge
    StorageService.saveUiConfig({
      mainCharacterScale: s,
      mainCharacterOffsetY: o,
      thumbnailGap: g,
      modeButtonScale: modeScale,
      genderButtonScale: modeScale,
      bgmVolume: bgmVol,
      sfxVolume: sfxVol,
      isBgmEnabled: isBgmOn
    });

    showToast('설정이 휴대폰에 저장되었습니다.');
  });

  // Download Settings Backup (JSON Export)
  if (dom.btnDownloadBackup) {
    dom.btnDownloadBackup.addEventListener('click', async () => {
      AudioHub.tap();
      try {
        const storedUi = StorageService.getUiConfig() || {};
        const now = new Date();
        const pad = (n) => String(n).padStart(2, '0');
        const tsStr = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
        const fileName = `TodayPick-settings-backup-${tsStr}.json`;

        const backupData = {
          app: 'TodayPick',
          backupVersion: 1,
          exportedAt: now.toISOString(),
          settings: {
            mainCharacterScale: storedUi.mainCharacterScale ?? parseFloat(dom.sliderScale.value) ?? 1.0,
            mainCharacterOffsetY: storedUi.mainCharacterOffsetY ?? parseInt(dom.sliderOffsetY.value) ?? 0,
            thumbnailGap: storedUi.thumbnailGap ?? parseInt(dom.sliderGap.value) ?? 4,
            genderButtonScale: storedUi.genderButtonScale ?? storedUi.modeButtonScale ?? 2.0,
            bgmVolume: storedUi.bgmVolume ?? AudioHub.getBgmVolume() ?? 0.55,
            sfxVolume: storedUi.sfxVolume ?? AudioHub.getSfxVolume() ?? 0.50,
            isBgmEnabled: storedUi.isBgmEnabled ?? AudioHub.getIsBgmEnabled() ?? true
          }
        };

        const jsonStr = JSON.stringify(backupData, null, 2);

        // Native Android Share or Browser Download
        if (Capacitor.isNativePlatform()) {
          try {
            await Share.share({
              title: 'TodayPick 설정 백업',
              text: jsonStr,
              dialogTitle: '설정 백업 파일 저장 또는 공유'
            });
            showToast('설정 백업 파일을 저장했습니다.');
            return;
          } catch (shareErr) {
            console.warn('[Backup] Share dialog dismissed or error, falling back to blob:', shareErr);
          }
        }

        // Web Blob Download fallback
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showToast('설정 백업 파일을 저장했습니다.');
      } catch (err) {
        console.error('[Backup] Export error:', err);
        showToast('설정 백업 저장에 실패했습니다.');
      }
    });
  }

  // Exit Confirmation Dialog Handlers
  if (dom.btnExitCancel) {
    dom.btnExitCancel.addEventListener('click', () => {
      AudioHub.tap();
      setExitDialog(false);
    });
  }

  if (dom.btnExitConfirm) {
    dom.btnExitConfirm.addEventListener('click', () => {
      AudioHub.tap();
      setExitDialog(false);
      if (Capacitor.isNativePlatform()) {
        App.exitApp();
      } else {
        showToast('웹 환경에서는 앱을 닫을 수 없습니다.');
      }
    });
  }

  if (dom.exitDialogBackdrop) {
    dom.exitDialogBackdrop.addEventListener('click', (e) => {
      if (e.target === dom.exitDialogBackdrop) setExitDialog(false);
    });
  }

  // Capacitor Native Listeners (Back Button & App Lifecycle)
  if (Capacitor.isNativePlatform()) {
    App.addListener('backButton', () => {
      handleBackButton();
    });

    App.addListener('appStateChange', ({ isActive }) => {
      if (isActive) {
        AudioHub.onForeground();
      } else {
        AudioHub.onBackground();
      }
    });
  }

  // Browser Fallback for Audio Lifecycle (Visibility Change)
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      AudioHub.onBackground();
    } else {
      AudioHub.onForeground();
    }
  });

  // Browser / Testing Support (Escape key triggers back navigation)
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') handleBackButton();
  });

  // Main Character Swipe Gesture Navigation
  setupSwipeNavigation();

  // Global test hook for automated verification
  window.testBackNav = handleBackButton;
}

// Setup Main Character Swipe Navigation
function setupSwipeNavigation() {
  const target = dom.characterDisplay || dom.mainImg;
  if (!target) return;

  let startX = 0;
  let startY = 0;
  let isTracking = false;
  const MIN_SWIPE_DISTANCE = 45; // Minimum px threshold

  const onPointerDown = (clientX, clientY) => {
    if (state.isPriceSheetOpen || state.isExitDialogOpen) return;
    startX = clientX;
    startY = clientY;
    isTracking = true;
  };

  const onPointerUp = (clientX, clientY) => {
    if (!isTracking) return;
    isTracking = false;
    if (state.isPriceSheetOpen || state.isExitDialogOpen) return;

    const deltaX = clientX - startX;
    const deltaY = clientY - startY;
    const absX = Math.abs(deltaX);
    const absY = Math.abs(deltaY);

    // Filter short movements / taps
    if (absX < MIN_SWIPE_DISTANCE && absY < MIN_SWIPE_DISTANCE) {
      return;
    }

    if (absY > absX) {
      // 1. VERTICAL SWIPE (Up or Down) -> Sequential 12 Demographic Group Switching
      const curIdx = ALL_GROUPS.indexOf(state.currentMode);
      const safeIdx = curIdx >= 0 ? curIdx : 1; // Default to female_20s (idx 1)
      let nextIdx;

      if (deltaY < 0) {
        // Swipe Up (위로) -> Next Group
        nextIdx = (safeIdx + 1) % ALL_GROUPS.length;
      } else {
        // Swipe Down (아래로) -> Previous Group
        nextIdx = (safeIdx - 1 + ALL_GROUPS.length) % ALL_GROUPS.length;
      }

      AudioHub.tap();
      switchMode(ALL_GROUPS[nextIdx]);
    } else {
      // 2. HORIZONTAL SWIPE
      const looks = outfitManager.getLooks(state.currentMode);
      if (!looks || !looks.length) return;
      const curIdx = looks.findIndex(l => l.id === state.currentOutfit?.id);
      if (curIdx === -1) return;

      if (deltaX > 0) {
        // SWIPE RIGHT (Left -> Right): PREVIOUS CHARACTER
        if (curIdx > 0) {
          AudioHub.tap();
          renderOutfit(looks[curIdx - 1]);
        }
      } else {
        // SWIPE LEFT (Right -> Left): NEXT CHARACTER
        if (curIdx < looks.length - 1) {
          AudioHub.tap();
          renderOutfit(looks[curIdx + 1]);
        }
      }
    }
  };

  // Touch Events (Mobile)
  target.addEventListener('touchstart', (e) => {
    if (e.touches && e.touches.length === 1) {
      onPointerDown(e.touches[0].clientX, e.touches[0].clientY);
    }
  }, { passive: true });

  target.addEventListener('touchend', (e) => {
    if (e.changedTouches && e.changedTouches.length > 0) {
      onPointerUp(e.changedTouches[0].clientX, e.changedTouches[0].clientY);
    }
  }, { passive: true });

  target.addEventListener('touchcancel', () => {
    isTracking = false;
  }, { passive: true });

  // Pointer Events (Mouse / Automation fallback)
  target.addEventListener('pointerdown', (e) => {
    if (e.pointerType === 'mouse') {
      onPointerDown(e.clientX, e.clientY);
    }
  });

  target.addEventListener('pointerup', (e) => {
    if (e.pointerType === 'mouse') {
      onPointerUp(e.clientX, e.clientY);
    }
  });

  target.addEventListener('pointercancel', () => {
    isTracking = false;
  });

  // Global test hook for programmatic gesture testing
  window.testSwipe = (direction, distance = 60) => {
    let dx = 0, dy = 0;
    if (direction === 'up') dy = -distance;
    else if (direction === 'down') dy = distance;
    else if (direction === 'left') dx = -distance;
    else if (direction === 'right') dx = distance;
    onPointerDown(100, 100);
    onPointerUp(100 + dx, 100 + dy);
  };
}

// Start app
initApp();
