/**
 * TodayPick Audio Service (AudioHub) - vc49
 * - Solves BGM silence root causes:
 *   1. Eliminates Web Audio createMediaElementSource CORS muting trap
 *   2. Native speaker audio playback guaranteed via HTMLAudioElement
 *   3. Touch/gesture autoplay unlock for Android WebView
 *   4. Eliminates confusing 'Silent Mode' UI text
 *   5. Seamless 5-track Google Drive streaming loop
 *   6. Dynamic reactive Equalizer synced to active playback
 *   7. Full Volume and BGM ON/OFF control with persistence
 */

import { BGM_PLAYLIST } from '../data/bgmManifest.js';

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
    this.consecutiveFailures = 0;

    // UI Listeners & Elements
    this.trackChangeListeners = [];
    this.equalizerBars = [];
    this.eqAnimationId = null;

    // AudioContext for system audio timing
    this.audioCtx = null;
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

      // Load initial track
      if (this.playlist.length > 0) {
        this.applyCurrentTrack();
      }

      // Track Ended Event -> Sequential progression
      this.bgmAudio.addEventListener('ended', () => {
        console.log('[AudioHub] Track ended. Advancing to next track.');
        this.nextTrack();
      });

      // Error handler -> gracefully retry or advance
      this.bgmAudio.addEventListener('error', (e) => {
        console.warn('[AudioHub] Track stream notice on index', this.currentTrackIndex, e);
        this.consecutiveFailures++;
        if (this.consecutiveFailures < this.playlist.length) {
          setTimeout(() => this.nextTrack(), 1000);
        } else {
          // Reset failure counter after cycling through once to prevent loop flood
          this.consecutiveFailures = 0;
        }
      });

      // SFX Audio element (touch tap)
      this.tapAudio = new Audio('/audio/sfx_tap.wav');
      this.tapAudio.volume = this.sfxVolume;
      this.tapAudio.preload = 'auto';

      // One-time user gesture unlock for mobile WebView autoplay policy
      const unlockGesture = () => {
        this.unlockAudio();
        if (this.isBgmEnabled && !this.hasBgmStarted && this.isAppActive) {
          this.tryPlayBgm();
        }
      };

      window.addEventListener('pointerdown', unlockGesture, { passive: true });
      window.addEventListener('touchstart', unlockGesture, { passive: true });
      window.addEventListener('keydown', unlockGesture, { passive: true });

      // Start Equalizer animation loop
      this.startEqualizerLoop();

      // Initial attempt to play if enabled
      if (this.isBgmEnabled) {
        this.tryPlayBgm();
      }
    } catch (err) {
      console.warn('[AudioHub] Audio initialization note:', err.message);
    }
  }

  unlockAudio() {
    if (!this.audioCtx) {
      try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
          this.audioCtx = new AudioContext();
        }
      } catch {}
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume().catch(() => {});
    }
  }

  applyCurrentTrack() {
    if (!this.bgmAudio || !this.playlist.length) return;
    const track = this.playlist[this.currentTrackIndex];
    if (!track) return;
    
    this.bgmAudio.src = track.url;
    this.notifyTrackChange(track.title);
  }

  nextTrack() {
    if (!this.playlist.length) return;
    this.currentTrackIndex = (this.currentTrackIndex + 1) % this.playlist.length;
    this.applyCurrentTrack();

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

  setEqualizerElements(elements) {
    this.equalizerBars = Array.from(elements);
  }

  startEqualizerLoop() {
    let lastTime = 0;
    const intervalMs = 50; // ~20fps power-efficient mobile rendering

    const tick = (timestamp) => {
      if (timestamp - lastTime >= intervalMs) {
        lastTime = timestamp;
        this.updateEqualizer();
      }
      this.eqAnimationId = requestAnimationFrame(tick);
    };

    this.eqAnimationId = requestAnimationFrame(tick);
  }

  updateEqualizer() {
    if (!this.equalizerBars || !this.equalizerBars.length) return;

    // Check if BGM is actively outputting sound
    const isPlaying = Boolean(
      this.isBgmEnabled &&
      this.isAppActive &&
      this.bgmAudio &&
      !this.bgmAudio.paused &&
      !this.bgmAudio.ended
    );

    if (!isPlaying) {
      // Idle state: all bars resting at minimum height
      this.equalizerBars.forEach(bar => {
        bar.style.height = '2px';
      });
      return;
    }

    // Dynamic rhythmic visualization reacting to audio playback
    const now = performance.now() / 140;
    const numBars = this.equalizerBars.length;
    
    this.equalizerBars.forEach((bar, idx) => {
      // Combine multiple harmonic frequencies for organic sound wave look
      const wave1 = Math.sin(now * 1.5 + idx * 0.9);
      const wave2 = Math.cos(now * 0.8 + idx * 1.3);
      const wave3 = Math.sin(now * 2.2 + idx * 0.5);
      const norm = Math.max(0, Math.min(1, (wave1 + wave2 + wave3 + 3) / 6));
      
      // Scale from 2px to 24px (2x height)
      const h = Math.max(2, Math.min(24, Math.round(2 + norm * 22)));
      bar.style.height = `${h}px`;
    });
  }

  tryPlayBgm() {
    if (!this.bgmAudio || !this.isAppActive || !this.isBgmEnabled) return;
    this.unlockAudio();

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
      this.unlockAudio();
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

    this.unlockAudio();
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
      this.unlockAudio();
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