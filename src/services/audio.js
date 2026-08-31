/**
 * TodayPick Audio Service (AudioHub) - vc54
 * - Local Bundled 5-Track BGM Sequential Playlist (HTML5 Audio Engine)
 * - Single HTMLAudioElement instance for seamless local playback
 * - Zero remote download / zero external network dependency
 * - User BGM ON/OFF & Volume controls with persistence
 * - Independent SFX volume & ON/OFF controls with persistence
 * - Mobile lifecycle aware (pause on background, resume on foreground)
 * - Now Playing title broadcast & Rainbow CSS Equalizer support
 */

const BGM_TRACKS = [
  {
    title: 'The Perfect Fit',
    src: '/audio/The_Perfect_Fit.mp3'
  },
  {
    title: 'Ice Cubes in the Sun',
    src: '/audio/Ice_Cubes_in_the_Sun.mp3'
  },
  {
    title: 'Seven AM Sharp',
    src: '/audio/Seven_AM_Sharp.mp3'
  },
  {
    title: 'Sunday Hanger',
    src: '/audio/Sunday_Hanger.mp3'
  },
  {
    title: 'Morning Palette',
    src: '/audio/Morning_Palette.mp3'
  }
];

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

    const savedBgmEnabled = localStorage.getItem(BGM_ENABLED_KEY);
    this.isBgmEnabled = savedBgmEnabled !== 'false';

    const savedSfxEnabled = localStorage.getItem(SFX_ENABLED_KEY);
    this.isSfxEnabled = savedSfxEnabled !== 'false';

    const savedBgmVol = localStorage.getItem(BGM_VOLUME_KEY);
    this.bgmVolume = savedBgmVol !== null ? parseFloat(savedBgmVol) : 0.55;

    const savedSfxVol = localStorage.getItem(SFX_VOLUME_KEY);
    this.sfxVolume = savedSfxVol !== null ? parseFloat(savedSfxVol) : 0.35;

    this.bgmTracks = BGM_TRACKS;
    this.currentTrackIndex = 0;
    this.isInitialized = false;
    this.trackChangeListeners = [];
  }

  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;

    try {
      this.bgmAudio = new Audio();
      this.bgmAudio.loop = false;
      this.bgmAudio.volume = this.bgmVolume;
      this.bgmAudio.preload = 'auto';

      this.currentTrackIndex = 0;
      this.loadTrack(this.currentTrackIndex);

      this.bgmAudio.addEventListener('ended', () => {
        console.log('[AudioHub] Track completed. Advancing to next track.');
        this.nextTrack();
      });

      this.bgmAudio.addEventListener('error', (e) => {
        console.warn('[AudioHub] Track playback error on index', this.currentTrackIndex, e);
        setTimeout(() => this.nextTrack(), 1000);
      });

      this.tapAudio = new Audio('/audio/sfx_tap.wav');
      this.tapAudio.volume = this.sfxVolume;
      this.tapAudio.muted = !this.isSfxEnabled || this.sfxVolume <= 0;
      this.tapAudio.preload = 'auto';

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

  loadTrack(index) {
    if (!this.bgmAudio || !this.bgmTracks.length) return;
    this.currentTrackIndex = ((index % this.bgmTracks.length) + this.bgmTracks.length) % this.bgmTracks.length;
    const track = this.bgmTracks[this.currentTrackIndex];
    this.bgmAudio.src = track.src;
    this.bgmAudio.volume = this.bgmVolume;
    this.notifyTrackChange(track.title);
  }

  nextTrack() {
    if (!this.bgmTracks.length) return;
    this.currentTrackIndex = (this.currentTrackIndex + 1) % this.bgmTracks.length;
    this.loadTrack(this.currentTrackIndex);

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
    if (this.bgmTracks[this.currentTrackIndex]) {
      callback(this.bgmTracks[this.currentTrackIndex].title);
    }
  }

  setEqualizerElements() {
    // Decoupled: Equalizer is handled entirely via Rainbow CSS Animation.
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
    localStorage.setItem(BGM_ENABLED_KEY, String(this.isBgmEnabled));

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

    this.wasBgmPlayingBeforeBackground = Boolean(this.bgmAudio && !this.bgmAudio.paused);
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
    localStorage.setItem(BGM_VOLUME_KEY, String(this.bgmVolume));
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
