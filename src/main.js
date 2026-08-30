import './style.css';
import { Capacitor } from '@capacitor/core';
import { App } from '@capacitor/app';
import { OutfitManager } from './data/outfits.js';
import { CoupangService } from './services/coupang.js';
import { StorageService } from './services/storage.js';
import { AudioHub } from './services/audio.js';

// Application state
const state = {
  config: null,
  currentMode: 'female', // 'female' | 'male'
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
  mainImg: document.getElementById('main-character-img'),
  outfitTitle: document.getElementById('lbl-outfit-title'),
  outfitPrice: document.getElementById('lbl-outfit-price'),
  thumbCarousel: document.getElementById('thumb-carousel'),
  btnSave: document.getElementById('btn-save-outfit'),
  btnRandom: document.getElementById('btn-random-pick'),
  btnTogglePrice: document.getElementById('btn-toggle-price'),
  priceSheetBackdrop: document.getElementById('price-sheet-backdrop'),
  priceSheetPanel: document.getElementById('price-sheet-panel'),
  btnCloseSheet: document.getElementById('btn-close-sheet'),
  sheetOutfitName: document.getElementById('sheet-outfit-name'),
  sheetItemsList: document.getElementById('sheet-items-list'),
  sheetTotalPrice: document.getElementById('sheet-total-price'),
  btnBuyFullOutfit: document.getElementById('btn-buy-full-outfit'),
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
  valScale: document.getElementById('val-scale'),
  valOffsetY: document.getElementById('val-offset-y'),
  valGap: document.getElementById('val-gap'),
  btnResetSettings: document.getElementById('btn-reset-settings'),
  btnSaveSettings: document.getElementById('btn-save-settings'),
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

  dom.outfitTitle.textContent = outfit.title;
  dom.outfitPrice.textContent = `${Number(outfit.totalPrice || 0).toLocaleString('ko-KR')}원`;

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
      <span class="thumb-label">${String(index + 1).padStart(2, '0')}</span>
    `;

    card.addEventListener('click', () => {
      AudioHub.tap();
      renderOutfit(look);
    });

    dom.thumbCarousel.appendChild(card);
  });
}

// Switch Character Mode
function switchMode(mode) {
  if (state.currentMode === mode && state.currentOutfit) return;
  state.currentMode = mode;

  dom.modeTabs.forEach(t => {
    t.classList.toggle('active', t.dataset.mode === mode);
  });

  populateThumbnails(mode);
  const firstLook = outfitManager.getOutfit(mode);
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

  // Setup Event Listeners
  setupEventListeners();
}

function setupEventListeners() {
  // Mode Tabs
  dom.modeTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      AudioHub.tap();
      switchMode(tab.dataset.mode);
    });
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

  // Full Outfit Coupang deeplink
  dom.btnBuyFullOutfit.addEventListener('click', async () => {
    if (!state.currentOutfit) return;
    AudioHub.tap();
    const primaryItem = state.currentOutfit.items[0];
    const kw = primaryItem?.searchKeyword || primaryItem?.name || state.currentOutfit.title;
    const searchUrl = `https://www.coupang.com/np/search?component=&q=${encodeURIComponent(kw)}`;
    showToast(`쿠팡 '${kw}' 검색 이동 중...`);
    await coupangService.openInCoupang(searchUrl);
  });

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

  // Save Settings
  dom.btnSaveSettings.addEventListener('click', () => {
    const s = parseFloat(dom.sliderScale.value);
    const o = parseInt(dom.sliderOffsetY.value);
    const g = parseInt(dom.sliderGap.value);
    StorageService.saveUiConfig({
      mainCharacterScale: s,
      mainCharacterOffsetY: o,
      thumbnailGap: g
    });
    showToast('설정이 브라우저에 저장되었습니다.');
  });

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

  // Capacitor Native Android Back Button Listener
  if (Capacitor.isNativePlatform()) {
    App.addListener('backButton', () => {
      handleBackButton();
    });
  }

  // Browser / Testing Support (Escape key triggers back navigation)
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') handleBackButton();
  });

  // Global test hook for automated verification
  window.testBackNav = handleBackButton;
}

// Start app
initApp();
