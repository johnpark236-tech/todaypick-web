/**
 * TodayPick Audio Service (AudioHub) - vc50
 * - Reliable Drive BGM Cache Architecture:
 *   1. Remote Source: Google Drive
 *   2. Download on demand via CacheStorage Blob
 *   3. Zero MP3s embedded in APK/AAB bundle
 *   4. Local Blob URL playback eliminating WebView CORS/Range streaming issues
 *   5. Seamless 5-track loop: The Perfect Fit -> Ice Cubes in the Sun -> Seven AM Sharp -> Sunday Hanger -> Morning Palette
 *   6. Single Audio instance strictly preventing simultaneous duplicates
 *   7. Decoupled from Equalizer (Zero Web Audio Analyser blocking)
 *   8. Full Volume and BGM ON/OFF control with persistence
 */

import { BGM_PLAYLIST } from '../data/bgmManifest.js';

const CACHE_NAME = 'todaypick_bgm_cache_v1';

class AudioService {
  constructor() {
    this.bgmAudio = null;
    this.tapAudio = null;
    this.hasBgmStarted = false;
    this.isAppActive = true;
    this.wasBgmPlayingBeforeBackground = false;
    this.lastTapTime = 0;
    this.retriggerBlockMs = 40;

    // Persisted settings
    const savedBgmEnabled = localStorage.getItem('todaypick_bgm_enabled');
    this.isBgmEnabled = savedBgmEnabled !== 'false';

    const savedBgmVol = localStorage.getItem('todaypick_bgm_volume');
    this.bgmVolume = savedBgmVol !== null ? parseFloat(savedBgmVol) : 0.55;

    const savedSfxVol = localStorage.getItem('todaypick_sfx_volume');
    this.sfxVolume = savedSfxVol !== null ? parseFloat(savedSfxVol) : 0.50;

    // Playlist state
    this.playlist = BGM_PLAYLIST || [];
    this.currentTrackIndex = 0;
    this.isInitialized = false;

    // Blob URL cache in memory
    this.blobUrlMap = new Map();
    this.downloadingSet = new Set();

    // UI Listeners
    this.trackChangeListeners = [];
  }

  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;

    try {
      // 1. Create BGM HTMLAudioElement
      this.bgmAudio = new Audio();
      this.bgmAudio.loop = false;
      this.bgmAudio.volume = this.bgmVolume;
      this.bgmAudio.preload = 'auto';

      // 2. Track Ended Event -> Sequential progression
      this.bgmAudio.addEventListener('ended', () => {
        console.log('[AudioHub] Track completed. Advancing to next track.');
        this.nextTrack();
      });

      // 3. Audio Error Handler -> Fallback to next track
      this.bgmAudio.addEventListener('error', (e) => {
        console.warn('[AudioHub] Playback error on track', this.currentTrackIndex, e);
        setTimeout(() => this.nextTrack(), 1000);
      });

      // 4. SFX Audio element (touch tap)
      this.tapAudio = new Audio('/audio/sfx_tap.wav');
      this.tapAudio.volume = this.sfxVolume;
      this.tapAudio.preload = 'auto';

      // 5. Pre-warm first track cache & apply title
      if (this.playlist.length > 0) {
        this.applyCurrentTrack();
      }

      // 6. User gesture unlock for mobile WebView autoplay policy
      const unlockGesture = () => {
        if (this.isBgmEnabled && !this.hasBgmStarted && this.isAppActive) {
          this.tryPlayBgm();
        }
      };

      window.addEventListener('pointerdown', unlockGesture, { passive: true });
      window.addEventListener('touchstart', unlockGesture, { passive: true });
      window.addEventListener('keydown', unlockGesture, { passive: true });

      // Initial attempt to play if enabled
      if (this.isBgmEnabled) {
        this.tryPlayBgm();
      }
    } catch (err) {
      console.warn('[AudioHub] Audio initialization note:', err.message);
    }
  }

  /**
   * Resolves audio source URL: checks memory blob, then CacheStorage, then downloads.
   */
  async resolveTrackUrl(track) {
    if (!track) return null;

    // Check in-memory object URL
    if (this.blobUrlMap.has(track.id)) {
      return this.blobUrlMap.get(track.id);
    }

    // Try CacheStorage
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

        // Download in background if not already downloading
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
                  // If current track is still waiting for src, apply it
                  if (this.playlist[this.currentTrackIndex]?.id === track.id && this.bgmAudio && !this.bgmAudio.src) {
                    this.bgmAudio.src = blobUrl;
                    if (this.isBgmEnabled && this.isAppActive) {
                      this.bgmAudio.play().catch(() => {});
                    }
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

    // Fallback: direct streaming URL while downloading
    return track.url;
  }

  async applyCurrentTrack() {
    if (!this.bgmAudio || !this.playlist.length) return;
    const track = this.playlist[this.currentTrackIndex];
    if (!track) return;

    this.notifyTrackChange(track.title);

    const playUrl = await this.resolveTrackUrl(track);
    if (playUrl) {
      this.bgmAudio.src = playUrl;
    }
  }

  async nextTrack() {
    if (!this.playlist.length) return;
    this.currentTrackIndex = (this.currentTrackIndex + 1) % this.playlist.length;
    await this.applyCurrentTrack();

    if (this.isBgmEnabled && this.isAppActive && this.bgmAudio) {
      this.bgmAudio.currentTime = 0;
      const p = this.bgmAudio.play();
      if (p !== undefined) {
        p.then(() => {
          this.hasBgmStarted = true;
        }).catch((err) => {
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
    if (this.playlist[this.currentTrackIndex]) {
      callback(this.playlist[this.currentTrackIndex].title);
    }
  }

  setEqualizerElements() {
    // Decoupled: Equalizer is handled entirely via Rainbow CSS Animation
  }

  tryPlayBgm() {
    if (!this.bgmAudio || !this.isAppActive || !this.isBgmEnabled) return;

    const p = this.bgmAudio.play();
    if (p !== undefined) {
      p.then(() => {
        this.hasBgmStarted = true;
      }).catch((err) => {
        this.hasBgmStarted = false;
        console.log('[AudioHub] Playback awaiting user touch:', err.message);
      });
    }
  }

  toggleBgm() {
    this.isBgmEnabled = !this.isBgmEnabled;
    localStorage.setItem('todaypick_bgm_enabled', String(this.isBgmEnabled));

    if (this.isBgmEnabled) {
      if (this.isAppActive && this.bgmAudio) {
        this.bgmAudio.play().then(() => {
          this.hasBgmStarted = true;
        }).catch(() => {
          this.hasBgmStarted = false;
        });
      }
    } else {
      if (this.bgmAudio && !this.bgmAudio.paused) {
        this.bgmAudio.pause();
      }
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

    if (this.isBgmEnabled && (!this.hasBgmStarted || (this.bgmAudio && this.bgmAudio.paused))) {
      this.tryPlayBgm();
    }

    try {
      if (this.tapAudio) {
        this.tapAudio.currentTime = 0;
        const p = this.tapAudio.play();
        if (p !== undefined) p.catch(() => {});
      }
    } catch {}
  }

  onBackground() {
    if (!this.isAppActive) return;
    this.isAppActive = false;

    this.wasBgmPlayingBeforeBackground = Boolean(
      this.bgmAudio && !this.bgmAudio.paused
    );

    if (this.bgmAudio && !this.bgmAudio.paused) {
      this.bgmAudio.pause();
    }

    if (this.tapAudio) {
      this.tapAudio.pause();
      this.tapAudio.currentTime = 0;
    }
  }

  onForeground() {
    if (this.isAppActive) return;
    this.isAppActive = true;

    if (this.isBgmEnabled && this.wasBgmPlayingBeforeBackground && this.bgmAudio) {
      this.bgmAudio.play().then(() => {
        this.hasBgmStarted = true;
      }).catch(() => {
        this.hasBgmStarted = false;
      });
    }
  }

  setBgmVolume(v) {
    this.bgmVolume = Math.max(0, Math.min(1, v));
    localStorage.setItem('todaypick_bgm_volume', String(this.bgmVolume));
    if (this.bgmAudio) this.bgmAudio.volume = this.bgmVolume;
  }

  getBgmVolume() {
    return this.bgmVolume;
  }

  setSfxVolume(v) {
    this.sfxVolume = Math.max(0, Math.min(1, v));
    localStorage.setItem('todaypick_sfx_volume', String(this.sfxVolume));
    if (this.tapAudio) this.tapAudio.volume = this.sfxVolume;
  }

  getSfxVolume() {
    return this.sfxVolume;
  }
}

export const AudioHub = new AudioService();