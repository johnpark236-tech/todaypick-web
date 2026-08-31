/**
 * TodayPick Audio Service (AudioHub) - vc51
 * Android uses native MediaPlayer after downloading remote Drive MP3s to app cache.
 * Browser keeps the existing HTMLAudioElement fallback for local development.
 */

import { Capacitor, registerPlugin } from '@capacitor/core';
import { BGM_PLAYLIST } from '../data/bgmManifest.js';

const TodayPickAudio = registerPlugin('TodayPickAudio');
const CACHE_NAME = 'todaypick_bgm_cache_v1';
const SFX_ENABLED_KEY = 'todaypick_sfx_enabled';
const BGM_ENABLED_KEY = 'todaypick_bgm_enabled';
const BGM_VOLUME_KEY = 'todaypick_bgm_volume';
const SFX_VOLUME_KEY = 'todaypick_sfx_volume';

class AudioService {
  constructor() {
    this.bgmAudio = null;
    this.tapAudio = null;
    this.hasBgmStarted = false;
    this.isAppActive = true;
    this.wasBgmPlayingBeforeBackground = false;
    this.lastTapTime = 0;
    this.retriggerBlockMs = 40;
    this.nativeAudioReady = false;
    this.isNativeAndroid = Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android';

    const savedBgmEnabled = localStorage.getItem(BGM_ENABLED_KEY);
    this.isBgmEnabled = savedBgmEnabled !== 'false';

    const savedSfxEnabled = localStorage.getItem(SFX_ENABLED_KEY);
    this.isSfxEnabled = savedSfxEnabled !== 'false';

    const savedBgmVol = localStorage.getItem(BGM_VOLUME_KEY);
    this.bgmVolume = savedBgmVol !== null ? parseFloat(savedBgmVol) : 0.55;

    const savedSfxVol = localStorage.getItem(SFX_VOLUME_KEY);
    this.sfxVolume = savedSfxVol !== null ? parseFloat(savedSfxVol) : 0.35;

    this.playlist = BGM_PLAYLIST || [];
    this.currentTrackIndex = 0;
    this.isInitialized = false;

    this.blobUrlMap = new Map();
    this.downloadingSet = new Set();
    this.trackChangeListeners = [];
  }

  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;

    try {
      this.tapAudio = new Audio('/audio/sfx_tap.wav');
      this.tapAudio.volume = this.sfxVolume;
      this.tapAudio.muted = !this.isSfxEnabled || this.sfxVolume <= 0;
      this.tapAudio.preload = 'auto';

      if (this.isNativeAndroid) {
        this.configureNativeAudio();
      } else {
        this.initWebBgm();
      }

      const unlockGesture = () => {
        if (this.isBgmEnabled && !this.hasBgmStarted && this.isAppActive) {
          this.tryPlayBgm();
        }
      };

      window.addEventListener('pointerdown', unlockGesture, { passive: true });
      window.addEventListener('touchstart', unlockGesture, { passive: true });
      window.addEventListener('keydown', unlockGesture, { passive: true });

      if (this.isBgmEnabled) {
        this.tryPlayBgm();
      }
    } catch (err) {
      console.warn('[AudioHub] Audio initialization note:', err.message);
    }
  }

  initWebBgm() {
    this.bgmAudio = new Audio();
    this.bgmAudio.loop = false;
    this.bgmAudio.volume = this.bgmVolume;
    this.bgmAudio.preload = 'auto';

    this.bgmAudio.addEventListener('ended', () => {
      console.log('[AudioHub] Track completed. Advancing to next track.');
      this.nextTrack();
    });

    this.bgmAudio.addEventListener('error', (e) => {
      console.warn('[AudioHub] Playback error on track', this.currentTrackIndex, e);
      setTimeout(() => this.nextTrack(), 1000);
    });

    if (this.playlist.length > 0) {
      this.applyCurrentTrack();
    }
  }

  async configureNativeAudio() {
    try {
      const res = await TodayPickAudio.configure({
        enabled: this.isBgmEnabled,
        volume: this.bgmVolume,
        tracks: this.playlist
      });
      this.nativeAudioReady = true;
      console.log('[AudioHub] Native Android audio configured:', res);
      this.notifyTrackChange(this.playlist[this.currentTrackIndex]?.title || '');
    } catch (err) {
      this.nativeAudioReady = false;
      console.warn('[AudioHub] Native audio configure failed; using web fallback:', err.message);
      this.initWebBgm();
    }
  }

  async resolveTrackUrl(track) {
    if (!track) return null;
    if (this.blobUrlMap.has(track.id)) return this.blobUrlMap.get(track.id);

    try {
      if ('caches' in window) {
        const cache = await caches.open(CACHE_NAME);
        const cachedResp = await cache.match(track.url);
        if (cachedResp) {
          const blob = await cachedResp.blob();
          if (blob && blob.size > 10000) {
            const blobUrl = URL.createObjectURL(blob);
            this.blobUrlMap.set(track.id, blobUrl);
            console.log(`[AudioHub] Loaded ${track.fileName} from app cache (${blob.size} bytes)`);
            return blobUrl;
          }
        }

        if (!this.downloadingSet.has(track.id)) {
          this.downloadingSet.add(track.id);
          fetch(track.url, { mode: 'cors' })
            .then(async (resp) => {
              if (resp.ok) {
                const clone = resp.clone();
                const blob = await resp.blob();
                if (blob && blob.size > 10000) {
                  await cache.put(track.url, clone);
                  const blobUrl = URL.createObjectURL(blob);
                  this.blobUrlMap.set(track.id, blobUrl);
                  console.log(`[AudioHub] Downloaded and cached ${track.fileName} (${blob.size} bytes)`);
                  if (this.playlist[this.currentTrackIndex]?.id === track.id && this.bgmAudio && !this.bgmAudio.src) {
                    this.bgmAudio.src = blobUrl;
                    if (this.isBgmEnabled && this.isAppActive) this.bgmAudio.play().catch(() => {});
                  }
                }
              }
            })
            .catch((err) => {
              console.warn(`[AudioHub] Background cache fetch note for ${track.fileName}:`, err.message);
            })
            .finally(() => {
              this.downloadingSet.delete(track.id);
            });
        }
      }
    } catch (e) {
      console.warn('[AudioHub] Cache storage note:', e.message);
    }

    return track.url;
  }

  async applyCurrentTrack() {
    const track = this.playlist[this.currentTrackIndex];
    if (!track) return;
    this.notifyTrackChange(track.title);
    if (this.isNativeAndroid && this.nativeAudioReady) return;
    if (!this.bgmAudio) return;

    const playUrl = await this.resolveTrackUrl(track);
    if (playUrl) this.bgmAudio.src = playUrl;
  }

  async nextTrack() {
    if (!this.playlist.length) return;
    this.currentTrackIndex = (this.currentTrackIndex + 1) % this.playlist.length;
    await this.applyCurrentTrack();

    if (this.isNativeAndroid && this.nativeAudioReady) {
      try {
        await TodayPickAudio.playTrack({ index: this.currentTrackIndex });
        this.hasBgmStarted = true;
      } catch (err) {
        this.hasBgmStarted = false;
        console.warn('[AudioHub] Native next track failed:', err.message);
      }
      return;
    }

    if (this.isBgmEnabled && this.isAppActive && this.bgmAudio) {
      this.bgmAudio.currentTime = 0;
      const p = this.bgmAudio.play();
      if (p !== undefined) {
        p.then(() => { this.hasBgmStarted = true; }).catch((err) => {
          console.log('[AudioHub] Playback deferred:', err.message);
          this.hasBgmStarted = false;
        });
      }
    }
  }

  notifyTrackChange(title) {
    this.trackChangeListeners.forEach(cb => {
      try { cb(title); } catch {}
    });
  }

  onTrackChange(callback) {
    this.trackChangeListeners.push(callback);
    if (this.playlist[this.currentTrackIndex]) callback(this.playlist[this.currentTrackIndex].title);
  }

  setEqualizerElements() {
    // Decoupled: Equalizer is handled entirely via Rainbow CSS Animation.
  }

  async tryPlayBgm() {
    if (!this.isAppActive || !this.isBgmEnabled) return;

    if (this.isNativeAndroid && this.nativeAudioReady) {
      try {
        await TodayPickAudio.playTrack({ index: this.currentTrackIndex });
        this.hasBgmStarted = true;
      } catch (err) {
        this.hasBgmStarted = false;
        console.log('[AudioHub] Native playback awaiting retry:', err.message);
      }
      return;
    }

    if (!this.bgmAudio) return;
    const p = this.bgmAudio.play();
    if (p !== undefined) {
      p.then(() => { this.hasBgmStarted = true; }).catch((err) => {
        this.hasBgmStarted = false;
        console.log('[AudioHub] Playback awaiting user touch:', err.message);
      });
    }
  }

  toggleBgm() {
    this.isBgmEnabled = !this.isBgmEnabled;
    localStorage.setItem(BGM_ENABLED_KEY, String(this.isBgmEnabled));

    if (this.isNativeAndroid && this.nativeAudioReady) {
      if (this.isBgmEnabled) this.tryPlayBgm();
      else TodayPickAudio.pauseBgm().catch(() => {});
      return this.isBgmEnabled;
    }

    if (this.isBgmEnabled) {
      if (this.isAppActive && this.bgmAudio) {
        this.bgmAudio.play().then(() => { this.hasBgmStarted = true; }).catch(() => {
          this.hasBgmStarted = false;
        });
      }
    } else if (this.bgmAudio && !this.bgmAudio.paused) {
      this.bgmAudio.pause();
    }
    return this.isBgmEnabled;
  }

  getIsBgmEnabled() {
    return this.isBgmEnabled;
  }

  tap() {
    if (!this.isAppActive) return;

    const now = performance.now();
    if (now - this.lastTapTime < this.retriggerBlockMs) return;
    this.lastTapTime = now;

    if (this.isBgmEnabled && !this.hasBgmStarted) {
      this.tryPlayBgm();
    }

    if (!this.isSfxEnabled || this.sfxVolume <= 0) {
      console.log('[AudioHub] SFX_PLAY_SKIPPED_WHEN_OFF');
      return;
    }

    try {
      if (this.tapAudio) {
        this.tapAudio.muted = false;
        this.tapAudio.volume = this.sfxVolume;
        this.tapAudio.currentTime = 0;
        const p = this.tapAudio.play();
        if (p !== undefined) p.catch(() => {});
      }
    } catch {}
  }

  onBackground() {
    if (!this.isAppActive) return;
    this.isAppActive = false;

    if (this.isNativeAndroid && this.nativeAudioReady) {
      this.wasBgmPlayingBeforeBackground = this.isBgmEnabled && this.hasBgmStarted;
      TodayPickAudio.pauseBgm().catch(() => {});
    } else {
      this.wasBgmPlayingBeforeBackground = Boolean(this.bgmAudio && !this.bgmAudio.paused);
      if (this.bgmAudio && !this.bgmAudio.paused) this.bgmAudio.pause();
    }

    if (this.tapAudio) {
      this.tapAudio.pause();
      this.tapAudio.currentTime = 0;
    }
  }

  onForeground() {
    if (this.isAppActive) return;
    this.isAppActive = true;
    if (this.isBgmEnabled && this.wasBgmPlayingBeforeBackground) this.tryPlayBgm();
  }

  setBgmVolume(v) {
    this.bgmVolume = Math.max(0, Math.min(1, v));
    localStorage.setItem(BGM_VOLUME_KEY, String(this.bgmVolume));
    if (this.isNativeAndroid && this.nativeAudioReady) {
      TodayPickAudio.setBgmVolume({ volume: this.bgmVolume }).catch(() => {});
    }
    if (this.bgmAudio) this.bgmAudio.volume = this.bgmVolume;
  }

  getBgmVolume() {
    return this.bgmVolume;
  }

  setSfxEnabled(enabled) {
    this.isSfxEnabled = Boolean(enabled);
    localStorage.setItem(SFX_ENABLED_KEY, String(this.isSfxEnabled));
    if (this.tapAudio) this.tapAudio.muted = !this.isSfxEnabled || this.sfxVolume <= 0;
  }

  getIsSfxEnabled() {
    return this.isSfxEnabled;
  }

  setSfxVolume(v) {
    this.sfxVolume = Math.max(0, Math.min(1, v));
    localStorage.setItem(SFX_VOLUME_KEY, String(this.sfxVolume));
    if (this.tapAudio) {
      this.tapAudio.volume = this.sfxVolume;
      this.tapAudio.muted = !this.isSfxEnabled || this.sfxVolume <= 0;
    }
  }

  getSfxVolume() {
    return this.sfxVolume;
  }
}

export const AudioHub = new AudioService();
