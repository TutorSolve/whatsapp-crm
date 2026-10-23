// Notification sound utility replicating WhatsApp Web notification sound behavior:
// 1. Dual-tone pleasant sine chime via native Web Audio API (zero network latency, no missing file assets).
// 2. Strict 1.5s cooldown debounce to prevent overlapping audio screeching when multiple messages arrive in bursts.
// 3. Adaptive volume for 3 cases:
//    - Background/minimized tab: full chime + tab title notification pulse.
//    - Active tab, different conversation: standard chime.
//    - Active tab, same conversation: gentle/subtle chime.
// 4. Safe browser autoplay handling: unlocks on first user interaction, fails silently if unpermitted.
// 5. Sound mute persistence via localStorage.

class NotificationSoundManager {
  private audioCtx: AudioContext | null = null;
  private lastPlayedTime = 0;
  private readonly COOLDOWN_MS = 1500;
  private isMuted = false;
  private originalTitle = '';
  private titleInterval: ReturnType<typeof setInterval> | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      try {
        this.isMuted = localStorage.getItem('crm_notification_sound_muted') === 'true';
      } catch {
        this.isMuted = false;
      }
      this.originalTitle = document.title || 'TutorSolve CRM';

      // Unlock AudioContext on first user interaction (browser autoplay policy)
      const unlock = () => {
        this.initAudioContext();
        window.removeEventListener('click', unlock);
        window.removeEventListener('keydown', unlock);
        window.removeEventListener('touchstart', unlock);
      };
      window.addEventListener('click', unlock, { passive: true });
      window.addEventListener('keydown', unlock, { passive: true });
      window.addEventListener('touchstart', unlock, { passive: true });

      // Reset document title pulse when tab regains focus or visibility
      const resetPulse = () => {
        this.stopTitlePulse();
      };
      window.addEventListener('focus', resetPulse);
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
          this.stopTitlePulse();
        }
      });
    }
  }

  private initAudioContext(): AudioContext | null {
    if (typeof window === 'undefined') return null;
    try {
      if (!this.audioCtx) {
        const AudioCtxClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        if (AudioCtxClass) {
          this.audioCtx = new AudioCtxClass();
        }
      }
      if (this.audioCtx && this.audioCtx.state === 'suspended') {
        this.audioCtx.resume().catch(() => {});
      }
    } catch {
      // AudioContext unavailable in current environment
    }
    return this.audioCtx;
  }

  public isSoundMuted(): boolean {
    return this.isMuted;
  }

  public setSoundMuted(muted: boolean): void {
    this.isMuted = muted;
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('crm_notification_sound_muted', muted ? 'true' : 'false');
      } catch {}
      window.dispatchEvent(new CustomEvent('crm-sound-mute-changed', { detail: { muted } }));
    }
  }

  public play(options?: { isSameConversation?: boolean }): void {
    // 1. NEVER chime if muted
    if (this.isMuted) return;

    // 2. NEVER chime if within cooldown window (1.5 seconds) to prevent burst audio screech
    const now = Date.now();
    if (now - this.lastPlayedTime < this.COOLDOWN_MS) {
      return;
    }
    this.lastPlayedTime = now;

    // 3. Determine tab activity state
    const isBackground = typeof document !== 'undefined' && (document.hidden || !document.hasFocus());
    const isSame = Boolean(options?.isSameConversation);

    if (isBackground) {
      this.startTitlePulse();
    }

    try {
      const ctx = this.initAudioContext();
      if (!ctx) return;

      // Case 1 (background / other tab or window): 0.70 volume (rich, clearly audible across room/speakers)
      // Case 2 (foreground, different chat): 0.50 volume
      // Case 3 (foreground, same chat): 0.25 volume (gentle feedback)
      const baseVolume = isBackground ? 0.70 : (isSame ? 0.25 : 0.50);
      const startTime = ctx.currentTime;

      // Note 1: 784 Hz (G5 note, 140ms duration)
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();
      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(784, startTime);
      gain1.gain.setValueAtTime(baseVolume, startTime);
      gain1.gain.exponentialRampToValueAtTime(0.001, startTime + 0.14);
      osc1.connect(gain1);
      gain1.connect(ctx.destination);
      osc1.start(startTime);
      osc1.stop(startTime + 0.14);

      // Note 2: 1046 Hz (C6 note, starts at 100ms, 400ms duration with pleasant bell resonance)
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(1046, startTime + 0.10);
      gain2.gain.setValueAtTime(Math.min(1.0, baseVolume * 1.15), startTime + 0.10);
      gain2.gain.exponentialRampToValueAtTime(0.001, startTime + 0.42);
      osc2.connect(gain2);
      gain2.connect(ctx.destination);
      osc2.start(startTime + 0.10);
      osc2.stop(startTime + 0.42);
    } catch {
      // Audio playback fails gracefully if browser autoplay policy blocks it
    }
  }

  private startTitlePulse(): void {
    if (typeof document === 'undefined') return;
    this.stopTitlePulse();
    if (!this.originalTitle) {
      this.originalTitle = document.title || 'TutorSolve CRM';
    }
    let showNotification = true;
    document.title = '(1) New Message | TutorSolve CRM';
    this.titleInterval = setInterval(() => {
      document.title = showNotification ? '(1) New Message | TutorSolve CRM' : this.originalTitle;
      showNotification = !showNotification;
    }, 1200);
  }

  private stopTitlePulse(): void {
    if (this.titleInterval) {
      clearInterval(this.titleInterval);
      this.titleInterval = null;
    }
    if (typeof document !== 'undefined' && this.originalTitle) {
      document.title = this.originalTitle;
    }
  }
}

export const notificationSound = new NotificationSoundManager();
