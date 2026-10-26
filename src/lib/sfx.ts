// Synthesised sound effects (Web Audio) — no audio files, nothing copyrighted.
// Every effect is built from oscillators and filtered noise.

const STORAGE_KEY = 'pf-muted';
let ctx: AudioContext | null = null;
let master: GainNode | null = null;
let noise: AudioBuffer | null = null;
let muted = false;

try {
  muted = typeof window !== 'undefined' && localStorage.getItem(STORAGE_KEY) === '1';
} catch {}

function audio() {
  if (muted || typeof window === 'undefined') return null;
  try {
    if (!ctx) {
      ctx = new AudioContext();
      master = ctx.createGain();
      master.gain.value = 0.55;
      const limiter = ctx.createDynamicsCompressor();
      master.connect(limiter).connect(ctx.destination);
      noise = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
      const data = noise.getChannelData(0);
      for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
    }
    if (ctx.state === 'suspended') void ctx.resume();
    return ctx;
  } catch {
    return null;
  }
}

/**
 * Try to start audio. Browsers keep audio suspended until the visitor interacts with the page,
 * so this resolves true only if sound can actually play right now. Call it again from inside a
 * click / key handler to unlock it.
 */
export function unlockAudio(): Promise<boolean> {
  const ac = audio();
  if (!ac) return Promise.resolve(false);
  if (ac.state === 'running') return Promise.resolve(true);
  return Promise.race([
    ac.resume().then(() => ac.state === 'running').catch(() => false),
    new Promise<boolean>((r) => setTimeout(() => r(ac.state === 'running'), 250)),
  ]);
}

// ── building blocks ──

function env(ac: AudioContext, peak: number, attack: number, decay: number, at = ac.currentTime) {
  const g = ac.createGain();
  g.gain.setValueAtTime(0.0001, at);
  g.gain.exponentialRampToValueAtTime(peak, at + attack);
  g.gain.exponentialRampToValueAtTime(0.0001, at + attack + decay);
  g.connect(master!);
  return g;
}

function tone(type: OscillatorType, from: number, to: number, dur: number, peak: number, delay = 0) {
  const ac = audio();
  if (!ac) return;
  const t = ac.currentTime + delay;
  const osc = ac.createOscillator();
  osc.type = type;
  osc.frequency.setValueAtTime(from, t);
  osc.frequency.exponentialRampToValueAtTime(Math.max(1, to), t + dur);
  osc.connect(env(ac, peak, 0.005, dur, t));
  osc.start(t);
  osc.stop(t + dur + 0.05);
}

function hiss(filter: BiquadFilterType, from: number, to: number, dur: number, peak: number, q = 1, delay = 0) {
  const ac = audio();
  if (!ac || !noise) return;
  const t = ac.currentTime + delay;
  const src = ac.createBufferSource();
  src.buffer = noise;
  src.loop = true;
  const f = ac.createBiquadFilter();
  f.type = filter;
  f.Q.value = q;
  f.frequency.setValueAtTime(from, t);
  f.frequency.exponentialRampToValueAtTime(Math.max(20, to), t + dur);
  src.connect(f).connect(env(ac, peak, 0.01, dur, t));
  src.start(t, Math.random());
  src.stop(t + dur + 0.05);
}

// ── effects ──

export const sfx = {
  get muted() {
    return muted;
  },
  setMuted(value: boolean) {
    muted = value;
    try {
      localStorage.setItem(STORAGE_KEY, value ? '1' : '0');
    } catch {}
    if (value) void ctx?.suspend();
  },

  click: () => tone('triangle', 900, 1400, 0.05, 0.08),
  equip: () => {
    tone('triangle', 520, 780, 0.09, 0.12);
    tone('triangle', 780, 1170, 0.12, 0.1, 0.07);
  },

  /** Sword swing: filtered noise sweep. */
  whoosh: (dur = 0.28) => hiss('bandpass', 500, 3200, dur, 0.5, 1.4),
  /** Metal impact: inharmonic partials + tick. */
  clang: () => {
    [523, 1307, 2171, 3420].forEach((f, i) => tone(i % 2 ? 'square' : 'triangle', f, f * 0.98, 0.6 - i * 0.1, 0.09));
    hiss('highpass', 4000, 2000, 0.06, 0.4);
  },
  /** Body-blow thump. */
  thump: () => {
    tone('sine', 140, 40, 0.28, 0.9);
    hiss('lowpass', 900, 200, 0.12, 0.4);
  },
  /** Heavy impact: sub drop + rumble. */
  boom: () => {
    tone('sine', 90, 28, 0.9, 1);
    hiss('lowpass', 600, 60, 1.0, 0.8);
  },
  /** Rubber stretch (Gum-Gum). */
  boing: () => {
    const ac = audio();
    if (!ac) return;
    const t = ac.currentTime;
    const osc = ac.createOscillator();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(160, t);
    osc.frequency.exponentialRampToValueAtTime(620, t + 0.16);
    osc.frequency.exponentialRampToValueAtTime(130, t + 0.42);
    const vib = ac.createOscillator();
    const vibGain = ac.createGain();
    vib.frequency.value = 18;
    vibGain.gain.value = 25;
    vib.connect(vibGain).connect(osc.frequency);
    osc.connect(env(ac, 0.35, 0.01, 0.45, t));
    osc.start(t);
    vib.start(t);
    osc.stop(t + 0.5);
    vib.stop(t + 0.5);
  },
  /** Electric crackle (One For All). */
  crackle: (dur = 0.6) => {
    for (let i = 0; i < 26; i++) {
      const d = Math.random() * dur;
      hiss('highpass', 2500 + Math.random() * 3000, 1800, 0.025 + Math.random() * 0.03, 0.35 + Math.random() * 0.3, 0.7, d);
    }
    tone('sawtooth', 60, 55, dur, 0.06);
  },
  /** Temple gong (Wukong). */
  gong: () => {
    [1, 2.76, 5.4, 8.93].forEach((p, i) => tone('sine', 96 * p, 96 * p * 0.985, 2.6 - i * 0.5, 0.28 / (i + 1)));
    hiss('lowpass', 1200, 200, 0.4, 0.3);
  },
  /** Ice crack + crystal tinkles (Leviathan Axe). */
  ice: () => {
    hiss('highpass', 3000, 6000, 0.12, 0.6, 2);
    hiss('bandpass', 1800, 900, 0.25, 0.4, 3);
    for (let i = 0; i < 9; i++) tone('sine', 2400 + Math.random() * 2600, 2300, 0.3 + Math.random() * 0.4, 0.05, 0.05 + Math.random() * 0.4);
  },
  /** Blade unsheathe (Hidden Blade). */
  schwing: () => {
    hiss('highpass', 2000, 7000, 0.18, 0.45, 2);
    tone('sine', 3200, 4600, 0.35, 0.06, 0.04);
    tone('sine', 5300, 5600, 0.3, 0.03, 0.06);
  },
  /** Coin shower (treasure). */
  coins: () => {
    for (let i = 0; i < 16; i++) tone('triangle', 1800 + Math.random() * 1600, 1700, 0.12 + Math.random() * 0.1, 0.07, Math.random() * 0.8);
  },
  /** Bright success arpeggio. */
  chime: () => [523.25, 659.25, 783.99, 1046.5].forEach((f, i) => tone('sine', f, f, 0.6, 0.12, i * 0.08)),
  /** Shovel / miss. */
  dig: () => hiss('lowpass', 500, 120, 0.18, 0.5),
  /** Short spiral burst (Rasengan release). */
  burst: () => {
    hiss('bandpass', 400, 4000, 0.45, 0.7, 0.8);
    tone('sawtooth', 220, 1200, 0.3, 0.08);
    tone('sine', 120, 40, 0.6, 0.8);
  },

  /** Eagle cry (Leap of Faith): two descending screeches. */
  eagle: () => {
    [0, 0.32].forEach((d, i) => {
      tone('sawtooth', 2600 - i * 300, 1500 - i * 200, 0.38, 0.05, d);
      tone('square', 3100 - i * 300, 1900, 0.3, 0.02, d + 0.02);
      hiss('bandpass', 4200, 2200, 0.35, 0.18, 6, d);
    });
  },
  /** Smoke poof (Shadow Clone). */
  poof: () => {
    hiss('lowpass', 2400, 300, 0.35, 0.5);
    tone('sine', 520, 180, 0.18, 0.12);
  },
  /** Hands sliding down the staff. */
  slide: (dur = 0.8) => hiss('bandpass', 1800, 900, dur, 0.22, 2.5),
  /** Short pop. */
  pop: () => tone('sine', 700, 1500, 0.08, 0.12),
  /** Soft hover blip for items. */
  hover: () => tone('triangle', 1600, 2100, 0.05, 0.035),

  /** Rising whir while charging; returns a controller. */
  charge() {
    const ac = audio();
    if (!ac || !noise) return { set: (_level: number) => {}, stop: () => {} };
    const t = ac.currentTime;
    const out = ac.createGain();
    out.gain.setValueAtTime(0.0001, t);
    out.gain.exponentialRampToValueAtTime(0.25, t + 0.15);
    out.connect(master!);
    const oscA = ac.createOscillator();
    const oscB = ac.createOscillator();
    oscA.type = oscB.type = 'sawtooth';
    oscA.frequency.value = 110;
    oscB.frequency.value = 113;
    const src = ac.createBufferSource();
    src.buffer = noise;
    src.loop = true;
    const band = ac.createBiquadFilter();
    band.type = 'bandpass';
    band.Q.value = 3;
    band.frequency.value = 600;
    const lfo = ac.createOscillator();
    const lfoGain = ac.createGain();
    lfo.frequency.value = 9;
    lfoGain.gain.value = 250;
    lfo.connect(lfoGain).connect(band.frequency);
    const oscGain = ac.createGain();
    oscGain.gain.value = 0.12;
    oscA.connect(oscGain);
    oscB.connect(oscGain);
    oscGain.connect(out);
    src.connect(band).connect(out);
    [oscA, oscB, src, lfo].forEach((n) => n.start(t));
    return {
      set(level: number) {
        const now = ac.currentTime;
        oscA.frequency.setTargetAtTime(110 + level * 330, now, 0.05);
        oscB.frequency.setTargetAtTime(113 + level * 345, now, 0.05);
        band.frequency.setTargetAtTime(600 + level * 2600, now, 0.05);
        lfo.frequency.setTargetAtTime(9 + level * 20, now, 0.05);
      },
      stop() {
        const now = ac.currentTime;
        out.gain.cancelScheduledValues(now);
        out.gain.setTargetAtTime(0.0001, now, 0.04);
        [oscA, oscB, src, lfo].forEach((n) => n.stop(now + 0.3));
      },
    };
  },
};

/** Signature sound per character (played when you open their figure). */
export const signatureSound: Record<string, () => void> = {
  luffy: () => { sfx.boing(); setTimeout(sfx.thump, 260); },
  naruto: () => { const c = sfx.charge(); c.set(0.6); setTimeout(() => { c.stop(); sfx.burst(); }, 500); },
  deku: () => { sfx.crackle(0.5); setTimeout(sfx.boom, 300); },
  asta: () => { sfx.whoosh(); setTimeout(sfx.clang, 180); },
  wukong: sfx.gong,
  kratos: () => { sfx.whoosh(0.35); setTimeout(sfx.ice, 250); },
  ezio: sfx.schwing,
  drake: sfx.chime,
};
