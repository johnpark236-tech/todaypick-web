/**
 * TodayPick Audio Service (AudioHub) - vc48
 * - Drive Streaming BGM Sequential Playlist (5 Tracks Loop)
 * - Zero MP3 bundle embedding in APK/AAB
 * - Simultaneous playback strictly prevented (Single BGM Audio instance)
 * - Real-time Web Audio API Equalizer analyzer with smooth fallback
 * - Now Playing title broadcast
 * - User BGM ON/OFF & Volume controls with persistence
 * - Mobile lifecycle aware
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

    // Listeners for UI
    this.trackChangeListeners = [];
    this.equalizerBars = [];

    // Web Audio API
    this.audioCtx = null;
    this.analyser = null;
    this.sourceNode = null;
    this.dataArray = null;
    this.isWebAudioConnected = false;
    this.eqAnimationId = null;
  }

  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;

    try {
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
        this.nextTrack();
      });

      // Error handler -> Try next track, avoid infinite loop
      this.bgmAudio.addEventListener('error', (e) => {
        console.warn('[AudioHub] Track load error on index', this.currentTrackIndex, e);
        this.consecutiveFailures++;
        if (this.consecutiveFailures < this.playlist.length) {
          setTimeout(() => this.nextTrack(), 800);
        } else {
          console.warn('[AudioHub] All tracks failed to stream, entering silent mode.');
          this.notifyTrackChange('Silent Mode');
        }
      });

      // SFX Audio element (touch tap)
      this.tapAudio = new Audio('/audio/sfx_tap.wav');
      this.tapAudio.volume = this.sfxVolume;
      this.tapAudio.preload = 'auto';

      // User gesture unlock for Web Audio and mobile autoplay
      const unlockGesture = () => {
        this.ensureAudioContext();
        if (!this.hasBgmStarted && this.isAppActive && this.isBgmEnabled) {
          this.tryPlayBgm();
        }
        window.removeEventListener('pointerdown', unlockGesture, true);
        window.removeEventListener('keydown', unlockGesture, true);
      };

      window.addEventListener('pointerdown', unlockGesture, true);
      window.addEventListener('keydown', unlockGesture, true);

      // Start Equalizer update loop
      this.startEqualizerLoop();

      if (this.isBgmEnabled) {
        this.tryPlayBgm();
      }
    } catch (err) {
      console.warn('[AudioHub] Audio initialization note:', err.message);
    }
  }

  ensureAudioContext() {
    if (!this.audioCtx) {
      try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
          this.audioCtx = new AudioContext();
          this.analyser = this.audioCtx.createAnalyser();
          this.analyser.fftSize = 64;
          this.analyser.smoothingTimeConstant = 0.8;
          this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
          
          if (this.bgmAudio && !this.isWebAudioConnected) {
            try {
              this.sourceNode = this.audioCtx.createMediaElementSource(this.bgmAudio);
              this.sourceNode.connect(this.analyser);
              this.analyser.connect(this.audioCtx.destination);
              this.isWebAudioConnected = true;
            } catch (ce) {
              console.log('[AudioHub] MediaElementSource CORS constraint detected; using adaptive simulation analyzer.');
            }
          }
        }
      } catch (e) {
        console.warn('[AudioHub] AudioContext setup note:', e.message);
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume().catch(() => {});
    }
  }

  applyCurrentTrack() {
    if (!this.bgmAudio || !this.playlist.length) return;
    const track = this.playlist[this.currentTrackIndex];
    this.bgmAudio.src = track.url;
    this.notifyTrackChange(track.title);
  }

  nextTrack() {
    if (!this.playlist.length) return;
    this.currentTrackIndex = (this.currentTrackIndex + 1) % this.playlist.length;
    this.applyCurrentTrack();

    if (this.isBgmEnabled && this.isAppActive && this.bgmAudio) {
      this.bgmAudio.currentTime = 0;
      this.bgmAudio.play().catch(() => {
        this.hasBgmStarted = false;
      });
    }
  }

  notifyTrackChange(title) {
    this.trackChangeListeners.forEach(cb => {
      try { cb(title); } catch {}
    });
  }

  onTrackChange(callback) {
    this.trackChangeListeners.push(callback);
    // Notify current title immediately if ready
    if (this.playlist[this.currentTrackIndex]) {
      callback(this.playlist[this.currentTrackIndex].title);
    }
  }

  setEqualizerElements(elements) {
    this.equalizerBars = Array.from(elements);
  }

  startEqualizerLoop() {
    let lastTime = 0;
    const intervalMs = 50; // ~20fps for power-efficient mobile rendering

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

    const isPlaying = Boolean(
      this.isBgmEnabled &&
      this.isAppActive &&
      this.bgmAudio &&
      !this.bgmAudio.paused &&
      !this.bgmAudio.ended &&
      this.bgmAudio.readyState > 2
    );

    if (!isPlaying) {
      // Idle state: set all bars to minimal height (2px)
      this.equalizerBars.forEach(bar => {
        bar.style.height = '2px';
      });
      return;
    }

    if (this.isWebAudioConnected && this.analyser && this.dataArray) {
      this.analyser.getByteFrequencyData(this.dataArray);
      const step = Math.floor(this.dataArray.length / this.equalizerBars.length) || 1;
      this.equalizerBars.forEach((bar, idx) => {
        const val = this.dataArray[idx * step] || 0;
        const h = Math.max(2, Math.min(12, Math.round((val / 255) * 12)));
        bar.style.height = `${h}px`;
      });
    } else {
      // Adaptive rhythm simulation: reacts when music is actually playing
      const now = performance.now() / 150;
      this.equalizerBars.forEach((bar, idx) => {
        const sine = Math.sin(now + idx * 1.1);
        const h = Math.max(2, Math.min(12, Math.round(4 + sine * 4 + (idx % 3) * 2)));
        bar.style.height = `${h}px`;
      });
    }
  }

  tryPlayBgm() {
    if (!this.bgmAudio || this.hasBgmStarted || !this.isAppActive || !this.isBgmEnabled) return;
    this.hasBgmStarted = true;
    this.ensureAudioContext();

    const p = this.bgmAudio.play();
    if (p !== undefined) {
      p.catch(() => {
        this.hasBgmStarted = false;
      });
    }
  }

  toggleBgm() {
    this.isBgmEnabled = !this.isBgmEnabled;
    localStorage.setItem('todaypick_bgm_enabled', String(this.isBgmEnabled));

    if (this.isBgmEnabled) {
      this.hasBgmStarted = true;
      this.ensureAudioContext();
      if (this.isAppActive && this.bgmAudio) {
        this.bgmAudio.play().catch(() => {
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

    this.ensureAudioContext();
    if (this.isBgmEnabled && !this.hasBgmStarted) {
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
      this.bgmAudio && !this.bgmAudio.paused && this.hasBgmStarted
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
      const p = this.bgmAudio.play();
      if (p !== undefined) {
        p.catch(() => {
          this.hasBgmStarted = false;
        });
      }
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