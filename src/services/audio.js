/**
 * TodayPick Audio Service (AudioHub)
 * - Dual BGM Sequential Playlist (Track 1 -> Track 2 -> Track 1...)
 * - Simultaneous playback strictly prevented (Single BGM Audio instance)
 * - User BGM ON/OFF toggle with persistence (todaypick_bgm_enabled)
 * - Independent BGM / SFX volume controls with persistence
 * - Mobile/Web lifecycle aware (pause on background, resume on foreground)
 */

class AudioService {
  constructor() {
    this.bgmAudio = null;
    this.tapAudio = null;
    this.hasBgmStarted = false;
    this.isAppActive = true;
    this.wasBgmPlayingBeforeBackground = false;
    this.lastTapTime = 0;
    this.retriggerBlockMs = 40; // Unity RetriggerBlockSeconds = 0.04s

    // Load persisted settings or defaults
    const savedBgmEnabled = localStorage.getItem('todaypick_bgm_enabled');
    this.isBgmEnabled = savedBgmEnabled !== 'false'; // default: true

    const savedBgmVol = localStorage.getItem('todaypick_bgm_volume');
    this.bgmVolume = savedBgmVol !== null ? parseFloat(savedBgmVol) : 0.55;

    const savedSfxVol = localStorage.getItem('todaypick_sfx_volume');
    this.sfxVolume = savedSfxVol !== null ? parseFloat(savedSfxVol) : 0.50;

    // Dual BGM Playlist
    this.bgmTracks = [];
    this.currentTrackIndex = 0;
    this.isInitialized = false;
  }

  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;

    try {
      // 1. Configure BGM tracks
      this.bgmAudio = new Audio();
      const canPlayOgg = this.bgmAudio.canPlayType('audio/ogg; codecs="vorbis"');
      const track1 = canPlayOgg ? '/audio/bgm_01.ogg' : '/audio/bgm_01.mp3';
      const track2 = '/audio/Morning_Palette.mp3';
      this.bgmTracks = [track1, track2];
      this.currentTrackIndex = 0;

      this.bgmAudio.src = this.bgmTracks[0];
      this.bgmAudio.loop = false; // Sequential playlist, not single track loop
      this.bgmAudio.volume = this.bgmVolume;
      this.bgmAudio.preload = 'auto';

      // Track Ended Event -> Advance to next track sequentially
      this.bgmAudio.addEventListener('ended', () => {
        this.nextTrack();
      });

      // 2. Initialize SFX audio element
      this.tapAudio = new Audio('/audio/sfx_tap.wav');
      this.tapAudio.volume = this.sfxVolume;
      this.tapAudio.preload = 'auto';

      // 3. Attempt initial autoplay if enabled
      if (this.isBgmEnabled) {
        this.tryPlayBgm();
      }

      // 4. One-time user gesture unlock for mobile WebView autoplay policy
      const unlockGesture = () => {
        if (!this.hasBgmStarted && this.isAppActive && this.isBgmEnabled) {
          this.tryPlayBgm();
        }
        window.removeEventListener('pointerdown', unlockGesture, true);
        window.removeEventListener('keydown', unlockGesture, true);
      };

      window.addEventListener('pointerdown', unlockGesture, true);
      window.addEventListener('keydown', unlockGesture, true);
    } catch (err) {
      console.warn('[AudioHub] Audio initialization note:', err.message);
    }
  }

  nextTrack() {
    if (!this.bgmAudio || !this.bgmTracks.length) return;
    this.currentTrackIndex = (this.currentTrackIndex + 1) % this.bgmTracks.length;
    this.bgmAudio.src = this.bgmTracks[this.currentTrackIndex];
    this.bgmAudio.currentTime = 0;

    if (this.isBgmEnabled && this.isAppActive) {
      const p = this.bgmAudio.play();
      if (p !== undefined) {
        p.catch(() => {});
      }
    }
  }

  tryPlayBgm() {
    if (!this.bgmAudio || this.hasBgmStarted || !this.isAppActive || !this.isBgmEnabled) return;
    this.hasBgmStarted = true;

    const playPromise = this.bgmAudio.play();
    if (playPromise !== undefined) {
      playPromise.catch(() => {
        this.hasBgmStarted = false;
      });
    }
  }

  /**
   * Toggle BGM ON/OFF.
   * Preserves current track and playback position on pause.
   */
  toggleBgm() {
    this.isBgmEnabled = !this.isBgmEnabled;
    localStorage.setItem('todaypick_bgm_enabled', String(this.isBgmEnabled));

    if (this.isBgmEnabled) {
      this.hasBgmStarted = true;
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

  /**
   * Primary UI interaction sound (tap).
   */
  tap() {
    if (!this.isAppActive) return;

    const now = performance.now();
    if (now - this.lastTapTime < this.retriggerBlockMs) {
      return;
    }
    this.lastTapTime = now;

    // Wake up BGM on first interaction if enabled and not yet playing
    if (this.isBgmEnabled && !this.hasBgmStarted) {
      this.tryPlayBgm();
    }

    // Play Touch SFX
    try {
      if (this.tapAudio) {
        this.tapAudio.currentTime = 0;
        const p = this.tapAudio.play();
        if (p !== undefined) {
          p.catch(() => {});
        }
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

    // Resume BGM ONLY if user has BGM enabled AND it was playing before background
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
