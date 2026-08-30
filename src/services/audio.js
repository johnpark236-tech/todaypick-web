/**
 * TodayPick Original Audio Service (AudioHub)
 * Faithful web implementation of Unity AudioHub / BgmManager / SfxManager
 */

class AudioService {
  constructor() {
    this.bgmAudio = null;
    this.tapAudio = null;
    this.hasBgmStarted = false;
    this.lastTapTime = 0;
    this.retriggerBlockMs = 40; // Unity RetriggerBlockSeconds = 0.04s
    this.bgmVolume = 0.55;       // Unity BgmManager.DefaultVolume = 0.55
    this.sfxVolume = 0.50;       // Unity SfxManager.DefaultVolume = 0.50
    this.isInitialized = false;
  }

  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;

    try {
      // 1. Initialize BGM audio element (supports mp3 and ogg fallback)
      this.bgmAudio = new Audio();
      this.bgmAudio.loop = true;
      this.bgmAudio.volume = this.bgmVolume;
      this.bgmAudio.preload = 'auto';
      
      // Determine format support
      const canPlayOgg = this.bgmAudio.canPlayType('audio/ogg; codecs="vorbis"');
      this.bgmAudio.src = canPlayOgg ? '/audio/bgm_01.ogg' : '/audio/bgm_01.mp3';

      // 2. Initialize SFX audio element
      this.tapAudio = new Audio('/audio/sfx_tap.wav');
      this.tapAudio.volume = this.sfxVolume;
      this.tapAudio.preload = 'auto';

      // 3. Attempt initial autoplay (if policy permits)
      this.tryPlayBgm();

      // 4. Setup one-time user gesture unlock for mobile WebView / browser autoplay policy
      const unlockGesture = () => {
        if (!this.hasBgmStarted) {
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

  tryPlayBgm() {
    if (!this.bgmAudio || this.hasBgmStarted) return;
    // Set flag immediately to prevent duplicate play calls while promise resolves
    this.hasBgmStarted = true;

    const playPromise = this.bgmAudio.play();
    if (playPromise !== undefined) {
      playPromise.catch(() => {
        // Autoplay policy prevented immediate playback; reset flag so next gesture unlocks
        this.hasBgmStarted = false;
      });
    }
  }

  /**
   * Primary UI interaction sound (tap).
   * Plays tap SFX and guarantees BGM is awakened on first interaction.
   */
  tap() {
    const now = performance.now();
    if (now - this.lastTapTime < this.retriggerBlockMs) {
      return; // Debounce fast duplicate bubbling
    }
    this.lastTapTime = now;

    // Wake up BGM on first interaction if not yet playing
    if (!this.hasBgmStarted) {
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

  setBgmVolume(v) {
    this.bgmVolume = Math.max(0, Math.min(1, v));
    if (this.bgmAudio) this.bgmAudio.volume = this.bgmVolume;
  }

  setSfxVolume(v) {
    this.sfxVolume = Math.max(0, Math.min(1, v));
    if (this.tapAudio) this.tapAudio.volume = this.sfxVolume;
  }
}

export const AudioHub = new AudioService();
