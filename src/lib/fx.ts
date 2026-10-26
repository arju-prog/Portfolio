// Canvas effects layer for the Arsenal powers. Everything is drawn in manga style
// (ink outlines, white flashes) with Blender-rendered prop sprites from /props/<id>.png.

export type Pt = { x: number; y: number };

type Effect = { update(dt: number): boolean; draw(c: CanvasRenderingContext2D): void };

const TAU = Math.PI * 2;
const rand = (a: number, b: number) => a + Math.random() * (b - a);
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);
const clamp01 = (t: number) => Math.max(0, Math.min(1, t));

const reducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// ── sprites ─────────────────────────────────────────────────────────────

const sprites = new Map<string, HTMLImageElement>();

export function sprite(id: string) {
  let img = sprites.get(id);
  if (!img) {
    img = new Image();
    img.src = `/props/${id}.png`;
    sprites.set(id, img);
  }
  return img;
}

function drawSprite(c: CanvasRenderingContext2D, id: string, x: number, y: number, size: number, rot = 0, alpha = 1) {
  const img = sprite(id);
  if (!img.complete || !img.naturalWidth) return;
  c.save();
  c.globalAlpha = alpha;
  c.translate(x, y);
  c.rotate(rot);
  c.drawImage(img, -size / 2, -size / 2, size, size);
  c.restore();
}

// ── page reactions ──────────────────────────────────────────────────────

export function shake(strength = 8, duration = 380) {
  if (reducedMotion()) return;
  const main = document.querySelector('main');
  if (!main) return;
  const frames = Array.from({ length: 7 }, (_, i) => {
    const k = 1 - i / 7;
    return { transform: `translate(${rand(-1, 1) * strength * k}px, ${rand(-1, 1) * strength * k}px)` };
  });
  main.animate([...frames, { transform: 'none' }], { duration, easing: 'ease-out' });
}

const HIT_TARGETS = '.panel, .btn, .bubble, .sec-head h2, .hero__title, .metric, .node, .sticker';

export function hitElement(p: Pt, kind: 'jolt' | 'freeze' | 'spin' = 'jolt') {
  const el = document.elementFromPoint(p.x, p.y)?.closest<HTMLElement>(HIT_TARGETS);
  if (!el) return null;
  if (kind === 'freeze') {
    el.classList.add('is-frozen');
    setTimeout(() => el.classList.remove('is-frozen'), 2600);
  }
  if (!reducedMotion()) {
    const keyframes =
      kind === 'spin'
        ? [{ transform: 'rotate(0)' }, { transform: 'rotate(-6deg) scale(1.04)' }, { transform: 'rotate(3deg)' }, { transform: 'none' }]
        : [{ transform: 'none' }, { transform: 'translate(6px,-4px) rotate(1.5deg)' }, { transform: 'translate(-4px,2px) rotate(-1deg)' }, { transform: 'none' }];
    el.animate(keyframes, { duration: 420, easing: 'ease-out' });
  }
  return el;
}

/** Manga onomatopoeia popping up at a point. */
export function sfxText(p: Pt, text: string, opts: { color?: string; size?: number; tilt?: number } = {}) {
  const el = document.createElement('span');
  el.className = 'fx-text';
  el.textContent = text;
  el.style.left = `${p.x}px`;
  el.style.top = `${p.y}px`;
  el.style.setProperty('--tilt', `${opts.tilt ?? rand(-14, 14)}deg`);
  if (opts.color) el.style.setProperty('--fx-color', opts.color);
  if (opts.size) el.style.fontSize = `${opts.size}px`;
  document.body.appendChild(el);
  el.addEventListener('animationend', () => el.remove(), { once: true });
  setTimeout(() => el.remove(), 2000);
}

// ── layer ───────────────────────────────────────────────────────────────

export class FxLayer {
  private ctx: CanvasRenderingContext2D;
  private effects: Effect[] = [];
  private raf = 0;
  private last = 0;
  private dpr = 1;

  constructor(readonly canvas: HTMLCanvasElement) {
    this.ctx = canvas.getContext('2d')!;
    this.resize();
    window.addEventListener('resize', this.resize);
  }

  get width() {
    return window.innerWidth;
  }

  get height() {
    return window.innerHeight;
  }

  add(effect: Effect) {
    this.effects.push(effect);
    if (!this.raf) {
      this.last = performance.now();
      this.raf = requestAnimationFrame(this.loop);
    }
    return effect;
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    window.removeEventListener('resize', this.resize);
  }

  private resize = () => {
    this.dpr = Math.min(window.devicePixelRatio, 2);
    this.canvas.width = window.innerWidth * this.dpr;
    this.canvas.height = window.innerHeight * this.dpr;
  };

  private loop = (now: number) => {
    const dt = Math.min((now - this.last) / 1000, 0.05);
    this.last = now;
    const c = this.ctx;
    c.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    c.clearRect(0, 0, this.width, this.height);
    // Effects may spawn new effects during update(); collect those separately so none are lost.
    const current = this.effects;
    this.effects = [];
    const kept = current.filter((e) => {
      const alive = e.update(dt);
      if (alive) e.draw(c);
      return alive;
    });
    this.effects = kept.concat(this.effects);
    this.raf = this.effects.length ? requestAnimationFrame(this.loop) : 0;
    if (!this.raf) c.clearRect(0, 0, this.width, this.height);
  };
}

// ── generic building blocks ─────────────────────────────────────────────

type Particle = {
  x: number; y: number; vx: number; vy: number; life: number; max: number;
  size: number; rot: number; vr: number; color: string; kind: 'dot' | 'shard' | 'feather' | 'sprite' | 'flake';
  sprite?: string; gravity: number; drag: number;
};

function particles(list: Partial<Particle>[]): Effect {
  const ps: Particle[] = list.map((p) => ({
    x: 0, y: 0, vx: 0, vy: 0, life: 0, max: 1, size: 4, rot: 0, vr: 0, color: '#0b0b0b',
    kind: 'dot', gravity: 0, drag: 0.98, ...p,
  }));
  return {
    update(dt) {
      for (const p of ps) {
        p.life += dt;
        p.vy += p.gravity * dt;
        p.vx *= p.drag;
        p.vy *= p.drag;
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.rot += p.vr * dt;
        if (p.kind === 'feather') p.x += Math.sin(p.life * 5 + p.size) * 0.8;
      }
      return ps.some((p) => p.life < p.max);
    },
    draw(c) {
      for (const p of ps) {
        if (p.life >= p.max) continue;
        const a = 1 - p.life / p.max;
        c.save();
        c.globalAlpha = a;
        c.translate(p.x, p.y);
        c.rotate(p.rot);
        if (p.kind === 'sprite' && p.sprite) {
          c.restore();
          drawSprite(c, p.sprite, p.x, p.y, p.size, p.rot, a);
          continue;
        }
        c.fillStyle = p.color;
        c.strokeStyle = '#0b0b0b';
        c.lineWidth = 1.5;
        c.beginPath();
        if (p.kind === 'shard') {
          c.moveTo(0, -p.size);
          c.lineTo(p.size * 0.35, 0);
          c.lineTo(0, p.size);
          c.lineTo(-p.size * 0.35, 0);
          c.closePath();
          c.fill();
          c.stroke();
        } else if (p.kind === 'feather') {
          c.ellipse(0, 0, p.size * 0.35, p.size, 0, 0, TAU);
          c.fill();
          c.stroke();
          c.beginPath();
          c.moveTo(0, -p.size);
          c.lineTo(0, p.size * 1.2);
          c.stroke();
        } else if (p.kind === 'flake') {
          for (let i = 0; i < 3; i++) {
            c.rotate(Math.PI / 3);
            c.moveTo(-p.size, 0);
            c.lineTo(p.size, 0);
          }
          c.strokeStyle = p.color;
          c.lineWidth = 2;
          c.stroke();
        } else {
          c.arc(0, 0, p.size, 0, TAU);
          c.fill();
        }
        c.restore();
      }
    },
  };
}

function burst(p: Pt, n: number, opts: Partial<Particle> & { speed?: [number, number]; size?: number; spread?: number; angle?: number }) {
  const { speed = [150, 450], spread = TAU, angle = 0, ...rest } = opts;
  return particles(
    Array.from({ length: reducedMotion() ? Math.ceil(n / 3) : n }, () => {
      const a = angle + rand(-spread / 2, spread / 2);
      const s = rand(speed[0], speed[1]);
      return {
        ...rest,
        x: p.x, y: p.y, vx: Math.cos(a) * s, vy: Math.sin(a) * s,
        max: rand(0.5, 1) * (rest.max ?? 0.8), rot: rand(0, TAU), vr: rand(-8, 8),
        size: (rest.size ?? 5) * rand(0.6, 1.3),
      };
    }),
  );
}

/** Expanding manga shockwave ring: white band with ink edges. */
function ring(p: Pt, maxR: number, dur = 0.5, width = 10, color = '#ffffff'): Effect {
  let t = 0;
  return {
    update(dt) { t += dt / dur; return t < 1; },
    draw(c) {
      const r = maxR * easeOut(t);
      const w = width * (1 - t) + 1;
      c.save();
      c.globalAlpha = 1 - t * 0.8;
      c.lineWidth = w + 4;
      c.strokeStyle = '#0b0b0b';
      c.beginPath();
      c.arc(p.x, p.y, r, 0, TAU);
      c.stroke();
      c.lineWidth = w;
      c.strokeStyle = color;
      c.stroke();
      c.restore();
    },
  };
}

/** Radial speed lines / impact focus lines. */
function focusLines(p: Pt, inner: number, outer: number, dur = 0.35, count = 28, color = '#0b0b0b'): Effect {
  let t = 0;
  const lines = Array.from({ length: count }, () => ({ a: rand(0, TAU), w: rand(1.5, 5), l: rand(0.6, 1) }));
  return {
    update(dt) { t += dt / dur; return t < 1; },
    draw(c) {
      c.save();
      c.globalAlpha = 1 - t;
      c.fillStyle = color;
      for (const ln of lines) {
        const r0 = inner + (outer - inner) * t * 0.4;
        const r1 = r0 + (outer - inner) * ln.l;
        const ca = Math.cos(ln.a);
        const sa = Math.sin(ln.a);
        c.beginPath();
        c.moveTo(p.x + ca * r0 - sa * ln.w * 0.1, p.y + sa * r0 + ca * ln.w * 0.1);
        c.lineTo(p.x + ca * r1 - sa * ln.w, p.y + sa * r1 + ca * ln.w);
        c.lineTo(p.x + ca * r1 + sa * ln.w, p.y + sa * r1 - ca * ln.w);
        c.closePath();
        c.fill();
      }
      c.restore();
    },
  };
}

/** Jagged lightning bolt between two points. */
function bolt(a: Pt, b: Pt, color: string, dur = 0.3, width = 3): Effect {
  let t = 0;
  const segs = 9;
  const pts = Array.from({ length: segs + 1 }, (_, i) => {
    const k = i / segs;
    const jitter = i === 0 || i === segs ? 0 : rand(-1, 1) * 22;
    const nx = -(b.y - a.y);
    const ny = b.x - a.x;
    const len = Math.hypot(nx, ny) || 1;
    return { x: a.x + (b.x - a.x) * k + (nx / len) * jitter, y: a.y + (b.y - a.y) * k + (ny / len) * jitter };
  });
  return {
    update(dt) { t += dt / dur; return t < 1; },
    draw(c) {
      c.save();
      c.globalAlpha = t < 0.2 ? 1 : 1 - (t - 0.2) / 0.8;
      c.lineJoin = 'miter';
      for (const [w, col] of [[width + 4, '#0b0b0b'], [width, color], [1.2, '#ffffff']] as const) {
        c.lineWidth = w;
        c.strokeStyle = col;
        c.beginPath();
        pts.forEach((pt, i) => (i ? c.lineTo(pt.x, pt.y) : c.moveTo(pt.x, pt.y)));
        c.stroke();
      }
      c.restore();
    },
  };
}

/** Comic impact star (white burst with ink outline). */
function impactStar(p: Pt, r: number, dur = 0.3): Effect {
  let t = 0;
  const spikes = 12;
  const radii = Array.from({ length: spikes * 2 }, (_, i) => (i % 2 ? r * rand(0.35, 0.5) : r * rand(0.85, 1.15)));
  return {
    update(dt) { t += dt / dur; return t < 1; },
    draw(c) {
      const s = 0.5 + easeOut(clamp01(t * 3)) * 0.6;
      c.save();
      c.globalAlpha = 1 - clamp01((t - 0.5) * 2);
      c.translate(p.x, p.y);
      c.scale(s, s);
      c.beginPath();
      radii.forEach((rr, i) => {
        const a = (i / radii.length) * TAU;
        if (i) c.lineTo(Math.cos(a) * rr, Math.sin(a) * rr);
        else c.moveTo(Math.cos(a) * rr, Math.sin(a) * rr);
      });
      c.closePath();
      c.fillStyle = '#ffffff';
      c.fill();
      c.lineWidth = 3;
      c.strokeStyle = '#0b0b0b';
      c.stroke();
      c.restore();
    },
  };
}

// ── powers ──────────────────────────────────────────────────────────────

/** Asta — anti-magic ink slash along a drag path (or a diagonal cut). */
export function slash(fx: FxLayer, path: Pt[]) {
  if (path.length < 2) {
    const p = path[0];
    path = [{ x: p.x - 140, y: p.y + 90 }, { x: p.x, y: p.y }, { x: p.x + 140, y: p.y - 90 }];
  }
  let t = 0;
  fx.add({
    update(dt) { t += dt / 0.55; return t < 1; },
    draw(c) {
      const shown = Math.max(2, Math.ceil(path.length * clamp01(t * 4)));
      const pts = path.slice(0, shown);
      const fade = 1 - clamp01((t - 0.35) / 0.65);
      // one tapered brush stroke: offset both sides of the path by a width that swells mid-stroke
      const left: Pt[] = [];
      const right: Pt[] = [];
      pts.forEach((pt, i) => {
        const a = pts[Math.max(0, i - 1)];
        const b = pts[Math.min(pts.length - 1, i + 1)];
        const len = Math.hypot(b.x - a.x, b.y - a.y) || 1;
        const nx = -(b.y - a.y) / len;
        const ny = (b.x - a.x) / len;
        const w = Math.sin((i / (path.length - 1)) * Math.PI) * 13 + 1;
        left.push({ x: pt.x + nx * w, y: pt.y + ny * w });
        right.push({ x: pt.x - nx * w, y: pt.y - ny * w });
      });
      c.save();
      c.globalAlpha = fade;
      c.fillStyle = '#0b0b0b';
      c.beginPath();
      [...left, ...right.reverse()].forEach((pt, i) => (i ? c.lineTo(pt.x, pt.y) : c.moveTo(pt.x, pt.y)));
      c.closePath();
      c.fill();
      c.strokeStyle = '#f6f4ee';
      c.lineWidth = 2;
      c.lineCap = 'round';
      c.lineJoin = 'round';
      c.beginPath();
      pts.forEach((pt, i) => (i ? c.lineTo(pt.x, pt.y) : c.moveTo(pt.x, pt.y)));
      c.stroke();
      c.restore();
    },
  });
  const end = path[path.length - 1];
  const start = path[0];
  const angle = Math.atan2(end.y - start.y, end.x - start.x);
  fx.add(burst(end, 26, { kind: 'shard', color: '#1d1d22', speed: [200, 520], spread: 1.4, angle, size: 9, max: 0.7 }));
  fx.add(burst(end, 14, { kind: 'dot', color: '#0b0b0b', speed: [60, 260], size: 3, max: 0.9, gravity: 200 }));
  // the sword itself sweeps through the arc
  let s = 0;
  fx.add({
    update(dt) { s += dt / 0.3; return s < 1; },
    draw(c) {
      const k = easeOut(s);
      const i = Math.min(path.length - 1, Math.floor(k * (path.length - 1)));
      drawSprite(c, 'demon_slayer_sword', path[i].x, path[i].y, 150, angle + Math.PI / 2 - 0.6 + k * 1.2, 1 - s * 0.6);
    },
  });
  hitElement(end);
  shake(5, 250);
  sfxText(end, 'ズバッ!', { size: 64 });
}

/** Wukong — the Jingu Bang extends from the sky and slams down. */
export function staffSlam(fx: FxLayer, p: Pt) {
  let t = 0;
  let impacted = false;
  fx.add({
    update(dt) {
      t += dt;
      if (!impacted && t > 0.14) {
        impacted = true;
        fx.add(ring(p, 220, 0.6, 14, '#e3a92b'));
        fx.add(ring(p, 130, 0.45, 8));
        fx.add(focusLines(p, 40, 260, 0.4, 32));
        fx.add(burst(p, 30, { kind: 'dot', color: '#b08a5a', speed: [120, 420], size: 4, max: 0.9, gravity: 600, spread: Math.PI, angle: -Math.PI / 2 }));
        fx.add(burst(p, 10, { kind: 'shard', color: '#e3a92b', speed: [200, 480], size: 8, max: 0.6 }));
        shake(14, 450);
        hitElement(p);
        sfxText({ x: p.x + 40, y: p.y - 60 }, 'ドンッ!', { size: 80, color: '#e3a92b' });
      }
      return t < 0.9;
    },
    draw(c) {
      const extend = easeOut(clamp01(t / 0.14));
      const retract = clamp01((t - 0.55) / 0.35);
      const bottom = p.y - retract * (p.y + 200);
      const length = (p.y + 120) * extend;
      const img = sprite('jingu_bang');
      if (!img.complete || !img.naturalWidth) return;
      // the sprite is a vertical staff; stretch it like the real thing
      c.save();
      c.globalAlpha = 1 - retract * 0.5;
      // the staff is a thin vertical strip in the middle of a square sprite — draw it wide
      c.drawImage(img, p.x - 180, bottom - length, 360, length + 20);
      c.restore();
    },
  });
}

/** Naruto — hold to charge a Rasengan, release to blast. Returns a controller. */
export function rasengan(fx: FxLayer, start: Pt) {
  let level = 0;
  let pos = { ...start };
  let charging = true;
  let t = 0;
  fx.add({
    update(dt) {
      t += dt;
      if (charging) level = Math.min(1, level + dt * 0.8);
      return charging;
    },
    draw(c) {
      const r = 14 + level * 46;
      c.save();
      c.translate(pos.x, pos.y);
      // wind shell
      c.strokeStyle = 'rgba(11,11,11,0.75)';
      c.lineWidth = 2;
      for (let i = 0; i < 7; i++) {
        const a = t * (9 + i) + (i * TAU) / 7;
        c.beginPath();
        c.arc(0, 0, r * (0.9 + (i % 3) * 0.12), a, a + 1.4 + level);
        c.stroke();
      }
      const g = c.createRadialGradient(0, 0, r * 0.1, 0, 0, r);
      g.addColorStop(0, '#ffffff');
      g.addColorStop(0.35, '#bfe9ff');
      g.addColorStop(0.75, '#3fa8ff');
      g.addColorStop(1, 'rgba(63,168,255,0)');
      c.fillStyle = g;
      c.beginPath();
      c.arc(0, 0, r, 0, TAU);
      c.fill();
      c.strokeStyle = '#ffffff';
      c.lineWidth = 2.5;
      for (let i = 0; i < 4; i++) {
        const a = -t * 14 + (i * TAU) / 4;
        c.beginPath();
        c.arc(0, 0, r * 0.55, a, a + 1.1);
        c.stroke();
      }
      c.restore();
    },
  });
  return {
    get level() { return level; },
    move(p: Pt) { pos = { ...p }; },
    release() {
      charging = false;
      const power = 0.4 + level;
      fx.add(ring(pos, 160 * power, 0.55, 12, '#bfe9ff'));
      fx.add(ring(pos, 90 * power, 0.4, 6));
      fx.add(focusLines(pos, 30 * power, 240 * power, 0.45, 36));
      fx.add(burst(pos, 40, { kind: 'dot', color: '#3fa8ff', speed: [200, 700 * power], size: 4, max: 0.7 }));
      // spiral streaks
      let s = 0;
      const origin = { ...pos };
      fx.add({
        update(dt) { s += dt / 0.5; return s < 1; },
        draw(c) {
          c.save();
          c.globalAlpha = 1 - s;
          c.strokeStyle = '#0b0b0b';
          c.lineWidth = 3;
          for (let i = 0; i < 5; i++) {
            c.beginPath();
            for (let k = 0; k < 40; k++) {
              const a = (i * TAU) / 5 + k * 0.18 + s * 6;
              const rr = k * 4 * power * (0.5 + s);
              const x = origin.x + Math.cos(a) * rr;
              const y = origin.y + Math.sin(a) * rr;
              if (k) c.lineTo(x, y);
              else c.moveTo(x, y);
            }
            c.stroke();
          }
          c.restore();
        },
      });
      shake(6 + level * 12, 420);
      hitElement(pos, 'spin');
      sfxText({ x: pos.x, y: pos.y - 70 }, '螺旋丸!', { size: 56 + level * 30, color: '#3fa8ff' });
    },
  };
}

/** Deku — Detroit Smash: shockwave, wind and One For All lightning. */
export function smash(fx: FxLayer, p: Pt) {
  fx.add(impactStar(p, 90, 0.35));
  fx.add(ring(p, 260, 0.6, 16));
  fx.add(ring(p, 170, 0.45, 8, '#7cff6b'));
  fx.add(focusLines(p, 60, 420, 0.5, 40));
  for (let i = 0; i < 9; i++) {
    const a = rand(0, TAU);
    const len = rand(90, 230);
    fx.add(bolt(p, { x: p.x + Math.cos(a) * len, y: p.y + Math.sin(a) * len }, '#7cff6b', rand(0.25, 0.45), rand(2, 4)));
  }
  fx.add(burst(p, 18, { kind: 'dot', color: '#7cff6b', speed: [150, 600], size: 3, max: 0.6 }));
  shake(18, 520);
  hitElement(p);
  sfxText({ x: p.x, y: p.y - 90 }, 'SMASH!!', { size: 84, color: '#7cff6b' });
}

/** Luffy — Gum-Gum Pistol: a stretchy arm shoots in from the nearest screen edge. */
export function gumPistol(fx: FxLayer, p: Pt) {
  const fromLeft = p.x > fx.width / 2;
  const base = { x: fromLeft ? -40 : fx.width + 40, y: Math.min(fx.height - 40, p.y + 80) };
  let t = 0;
  let hit = false;
  const wobble = rand(30, 70) * (Math.random() < 0.5 ? -1 : 1);
  fx.add({
    update(dt) {
      t += dt;
      if (!hit && t > 0.13) {
        hit = true;
        fx.add(impactStar(p, 70, 0.3));
        fx.add(focusLines(p, 30, 200, 0.3, 24));
        hitElement(p);
        shake(9, 300);
        sfxText({ x: p.x, y: p.y - 70 }, 'ゴムゴムの…ピストル!', { size: 40, color: '#d01f26' });
      }
      return t < 0.6;
    },
    draw(c) {
      const out = t < 0.13 ? easeOut(t / 0.13) : t < 0.28 ? 1 : 1 - easeOut(clamp01((t - 0.28) / 0.3));
      if (out <= 0.01) return;
      const tip = { x: base.x + (p.x - base.x) * out, y: base.y + (p.y - base.y) * out };
      const mid = {
        x: (base.x + tip.x) / 2,
        y: (base.y + tip.y) / 2 + wobble * Math.sin(t * 30) * (1 - out * 0.5),
      };
      c.save();
      c.lineCap = 'round';
      for (const [w, col] of [[30, '#0b0b0b'], [24, '#f1c49c']] as const) {
        c.lineWidth = w;
        c.strokeStyle = col;
        c.beginPath();
        c.moveTo(base.x, base.y);
        c.quadraticCurveTo(mid.x, mid.y, tip.x, tip.y);
        c.stroke();
      }
      // red sleeve at the shoulder end
      c.fillStyle = '#d01f26';
      c.strokeStyle = '#0b0b0b';
      c.lineWidth = 3;
      c.beginPath();
      c.arc(base.x, base.y, 42, 0, TAU);
      c.fill();
      c.stroke();
      // fist
      c.fillStyle = '#f1c49c';
      c.beginPath();
      c.arc(tip.x, tip.y, 26, 0, TAU);
      c.fill();
      c.stroke();
      c.lineWidth = 2;
      for (let k = -1; k <= 1; k++) {
        c.beginPath();
        c.moveTo(tip.x + (fromLeft ? 10 : -10), tip.y + k * 9);
        c.lineTo(tip.x + (fromLeft ? 22 : -22), tip.y + k * 9);
        c.stroke();
      }
      c.restore();
    },
  });
}

/** Kratos — the Leviathan Axe is thrown, freezes its target, then returns. */
export function axeThrow(fx: FxLayer, p: Pt, onReturn?: () => void) {
  const from = { x: fx.width + 80, y: fx.height + 80 };
  let t = 0;
  let impacted = false;
  const embedAngle = rand(-0.9, -0.4);
  fx.add({
    update(dt) {
      t += dt;
      if (!impacted && t > 0.28) {
        impacted = true;
        fx.add(ring(p, 150, 0.6, 10, '#bfefff'));
        fx.add(burst(p, 22, { kind: 'shard', color: '#d9f6ff', speed: [120, 420], size: 12, max: 0.9 }));
        fx.add(burst(p, 26, { kind: 'flake', color: '#7fd8ff', speed: [40, 200], size: 6, max: 1.6, gravity: 40 }));
        hitElement(p, 'freeze');
        shake(10, 350);
        sfxText({ x: p.x + 50, y: p.y - 70 }, 'ガキン!', { size: 70, color: '#7fd8ff' });
      }
      if (t > 1.55) onReturn?.();
      return t < 1.6;
    },
    draw(c) {
      if (t < 0.28) {
        const k = easeOut(t / 0.28);
        const x = from.x + (p.x - from.x) * k;
        const y = from.y + (p.y - from.y) * k - Math.sin(k * Math.PI) * 120;
        drawSprite(c, 'leviathan_axe', x, y, 150, -t * 40);
      } else if (t < 1.25) {
        // frost glow around the embedded axe
        const g = c.createRadialGradient(p.x, p.y, 10, p.x, p.y, 120);
        g.addColorStop(0, 'rgba(191,239,255,0.55)');
        g.addColorStop(1, 'rgba(191,239,255,0)');
        c.fillStyle = g;
        c.beginPath();
        c.arc(p.x, p.y, 120, 0, TAU);
        c.fill();
        drawSprite(c, 'leviathan_axe', p.x, p.y, 150, embedAngle);
      } else {
        // recall: flies back to the bottom-right, spinning
        const k = easeOut((t - 1.25) / 0.35);
        drawSprite(c, 'leviathan_axe', p.x + (from.x - p.x) * k, p.y + (from.y - p.y) * k, 150, embedAngle + k * 25);
      }
    },
  });
}

/** Ezio — hidden-blade strike with a flurry of white feathers. */
export function bladeStrike(fx: FxLayer, p: Pt) {
  let t = 0;
  fx.add({
    update(dt) { t += dt / 0.25; return t < 1; },
    draw(c) {
      c.save();
      c.globalAlpha = 1 - t;
      c.strokeStyle = '#0b0b0b';
      c.lineWidth = 8 * (1 - t) + 2;
      c.beginPath();
      c.moveTo(p.x - 70, p.y + 50);
      c.lineTo(p.x + 70 * easeOut(t) + 20, p.y - 50 * easeOut(t) - 14);
      c.stroke();
      c.strokeStyle = '#ffffff';
      c.lineWidth = 2;
      c.stroke();
      c.restore();
    },
  });
  fx.add(burst(p, 16, { kind: 'feather', color: '#ffffff', speed: [60, 220], size: 9, max: 1.8, gravity: 50, drag: 0.94 }));
  fx.add(focusLines(p, 20, 120, 0.25, 16));
  hitElement(p);
  sfxText({ x: p.x + 30, y: p.y - 50 }, 'シャキン!', { size: 46 });
}

/** Drake — treasure found: chest pops up and coins shower out. */
export function treasure(fx: FxLayer, p: Pt) {
  let t = 0;
  fx.add({
    update(dt) { t += dt / 1.6; return t < 1; },
    draw(c) {
      const pop = easeOut(clamp01(t * 4));
      drawSprite(c, 'treasure_chest', p.x, p.y - pop * 30, 120 * (0.4 + pop * 0.6), 0, 1 - clamp01((t - 0.75) * 4));
    },
  });
  fx.add(ring(p, 140, 0.5, 8, '#ffd24a'));
  fx.add(focusLines(p, 50, 200, 0.5, 28, '#c8962e'));
  fx.add(particles(Array.from({ length: reducedMotion() ? 8 : 24 }, () => ({
    kind: 'sprite' as const, sprite: 'gold_coin', x: p.x, y: p.y - 20,
    vx: rand(-260, 260), vy: rand(-720, -360), gravity: 1300, drag: 0.995,
    size: rand(26, 40), rot: rand(0, TAU), vr: rand(-10, 10), max: rand(1.1, 1.6),
  }))));
  sfxText({ x: p.x, y: p.y - 110 }, 'お宝!', { size: 72, color: '#ffd24a' });
}

/** Drake — dig in the wrong place. */
export function dig(fx: FxLayer, p: Pt) {
  fx.add(burst(p, 14, { kind: 'dot', color: '#8a6a45', speed: [80, 260], size: 4, max: 0.7, gravity: 700, spread: Math.PI, angle: -Math.PI / 2 }));
  sfxText({ x: p.x, y: p.y - 30 }, '?', { size: 40 });
}

/** Ezio — Eagle Vision: page dims (CSS) and every interactive target glows gold.
 *  Also reveals the buried treasure if `treasureAt` returns a viewport point. */
export function eagleVision(fx: FxLayer, treasureAt: () => Pt | null) {
  let on = true;
  let fade = 0;
  let t = 0;
  document.documentElement.classList.add('eagle-vision');
  const targets = [...document.querySelectorAll<HTMLElement>('a, button, .node, .sticker, .relic-chip')].filter(
    (el) => !el.closest('.arsenal'),
  );
  fx.add({
    update(dt) {
      t += dt;
      fade = on ? Math.min(1, fade + dt * 5) : Math.max(0, fade - dt * 4);
      return on || fade > 0;
    },
    draw(c) {
      c.save();
      c.globalAlpha = fade;
      c.shadowColor = '#ffcc33';
      c.shadowBlur = 14;
      c.strokeStyle = '#ffcc33';
      c.lineWidth = 2.5;
      for (const el of targets) {
        const r = el.getBoundingClientRect();
        if (r.bottom < 0 || r.top > fx.height || r.width === 0) continue;
        c.strokeRect(r.left - 3, r.top - 3, r.width + 6, r.height + 6);
      }
      const spot = treasureAt();
      if (spot) {
        const pulse = 1 + Math.sin(t * 6) * 0.15;
        c.lineWidth = 6;
        c.strokeStyle = '#ffcc33';
        c.beginPath();
        c.moveTo(spot.x - 22 * pulse, spot.y - 22 * pulse);
        c.lineTo(spot.x + 22 * pulse, spot.y + 22 * pulse);
        c.moveTo(spot.x + 22 * pulse, spot.y - 22 * pulse);
        c.lineTo(spot.x - 22 * pulse, spot.y + 22 * pulse);
        c.stroke();
      }
      c.restore();
    },
  });
  return {
    stop() {
      on = false;
      document.documentElement.classList.remove('eagle-vision');
    },
  };
}

/** Small pop when you click a sticker. */
export function stickerPop(fx: FxLayer, p: Pt, id: string) {
  fx.add(impactStar(p, 40, 0.3));
  fx.add(particles(Array.from({ length: 6 }, () => ({
    kind: 'sprite' as const, sprite: id, x: p.x, y: p.y, vx: rand(-200, 200), vy: rand(-420, -200),
    gravity: 900, size: rand(22, 34), rot: rand(0, TAU), vr: rand(-6, 6), max: 1,
  }))));
}

// ── navigation interactions ─────────────────────────────────────────────

/** Wukong rides his staff like a rope: dir 1 slides down and lands, dir -1 climbs up. */
export function wukongRide(fx: FxLayer, dir: 1 | -1, duration: number) {
  const x = Math.max(70, fx.width - 92);
  const top = 70;
  const bottom = fx.height - 150;
  let t = 0;
  let landed = false;
  const total = duration / 1000 + (dir > 0 ? 0.75 : 0.35);
  fx.add({
    update(dt) {
      t += dt;
      const k = t / (duration / 1000);
      if (dir > 0 && !landed && k >= 1) {
        landed = true;
        const feet = { x, y: bottom + 70 };
        fx.add(ring(feet, 120, 0.5, 8, '#e3a92b'));
        fx.add(burst(feet, 22, { kind: 'dot', color: '#b08a5a', speed: [120, 360], size: 4, max: 0.8, gravity: 600, spread: Math.PI, angle: -Math.PI / 2 }));
        fx.add(focusLines(feet, 30, 170, 0.35, 20));
        sfxText({ x: x - 110, y: bottom }, 'ドンッ!', { size: 64, color: '#e3a92b' });
      }
      return t < total;
    },
    draw(c) {
      const k = clamp01(t / (duration / 1000));
      const extend = easeOut(clamp01(t / 0.18));
      const retract = clamp01((t - duration / 1000 - 0.15) / 0.35);
      // the Jingu Bang stretched into a long pole
      const staff = sprite('jingu_bang');
      if (staff.complete && staff.naturalWidth) {
        const height = (fx.height + 80) * extend * (1 - retract);
        const y0 = dir > 0 ? -40 : fx.height + 40 - height;
        c.save();
        c.globalAlpha = 1 - retract * 0.6;
        c.drawImage(staff, x - 150, y0, 300, height);
        c.restore();
      }
      if (dir > 0 && k >= 1) {
        const settle = clamp01((t - duration / 1000) / 0.2);
        drawSprite(c, 'wukong_land', x - 10, bottom + 10 + (1 - easeOut(settle)) * -30, 150, 0, 1 - clamp01((t - total + 0.25) / 0.25));
        return;
      }
      const eased = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      const y = dir > 0 ? top + (bottom - top) * eased : bottom - (bottom - top) * eased;
      const sway = Math.sin(t * (dir > 0 ? 18 : 10)) * (dir > 0 ? 2 : 5);
      drawSprite(c, 'wukong_slide', x + sway, y, 150, dir > 0 ? 0 : Math.sin(t * 10) * 0.06, dir < 0 ? 1 - clamp01((k - 0.85) / 0.15) : 1);
      // speed lines streaming behind him
      if (dir > 0 && k > 0.05 && k < 0.95) {
        c.save();
        c.strokeStyle = 'rgba(11,11,11,0.55)';
        c.lineWidth = 2;
        for (let i = 0; i < 5; i++) {
          const ox = x - 60 + i * 30;
          c.beginPath();
          c.moveTo(ox, y - 90 - i * 12);
          c.lineTo(ox, y - 200 - i * 18);
          c.stroke();
        }
        c.restore();
      }
    },
  });
}

/** Luffy's arm shoots from a nav link to the bottom edge, "grabs" the page, then snaps back. */
export function armGrab(fx: FxLayer, from: Pt, holdMs: number) {
  const to = { x: from.x + rand(-40, 40), y: fx.height - 30 };
  let t = 0;
  let grabbed = false;
  const hold = holdMs / 1000;
  fx.add({
    update(dt) {
      t += dt;
      if (!grabbed && t > 0.16) {
        grabbed = true;
        fx.add(impactStar(to, 60, 0.3));
        sfxText({ x: to.x, y: to.y - 80 }, 'ゴムゴム!', { size: 44, color: '#d01f26' });
      }
      return t < 0.16 + hold + 0.3;
    },
    draw(c) {
      const out = t < 0.16 ? easeOut(t / 0.16) : t < 0.16 + hold ? 1 : 1 - easeOut(clamp01((t - 0.16 - hold) / 0.3));
      if (out <= 0.01) return;
      const tip = { x: from.x + (to.x - from.x) * out, y: from.y + (to.y - from.y) * out };
      const wobble = Math.sin(t * 28) * 24 * (1 - out * 0.6);
      c.save();
      c.lineCap = 'round';
      for (const [w, col] of [[26, '#0b0b0b'], [20, '#f1c49c']] as const) {
        c.lineWidth = w;
        c.strokeStyle = col;
        c.beginPath();
        c.moveTo(from.x, from.y);
        c.quadraticCurveTo((from.x + tip.x) / 2 + wobble, (from.y + tip.y) / 2, tip.x, tip.y);
        c.stroke();
      }
      c.fillStyle = '#d01f26';
      c.strokeStyle = '#0b0b0b';
      c.lineWidth = 3;
      c.beginPath();
      c.arc(from.x, from.y, 16, 0, TAU);
      c.fill();
      c.stroke();
      c.fillStyle = '#f1c49c';
      c.beginPath();
      c.arc(tip.x, tip.y, 22, 0, TAU);
      c.fill();
      c.stroke();
      c.restore();
    },
  });
}

/** Kratos' back-to-top: the axe flies up, waits while the page scrolls, then returns to `home`. */
export function axeBoomerang(fx: FxLayer, home: Pt, flightMs: number, onCaught: () => void) {
  const away = { x: fx.width * 0.55, y: -140 };
  const THROW = 0.5;
  const RETURN = 0.5;
  const flight = flightMs / 1000;
  let t = 0;
  let caught = false;
  // curved path: bulge sideways so the throw and the return read as arcs
  const along = (a: Pt, b: Pt, k: number, bulge: number) => ({
    x: a.x + (b.x - a.x) * k - Math.sin(k * Math.PI) * bulge,
    y: a.y + (b.y - a.y) * k,
  });
  fx.add({
    update(dt) {
      t += dt;
      if (!caught && t > THROW + flight + RETURN) {
        caught = true;
        fx.add(burst(home, 16, { kind: 'flake', color: '#7fd8ff', speed: [40, 160], size: 6, max: 1.2 }));
        fx.add(ring(home, 60, 0.35, 6, '#bfefff'));
        onCaught();
      }
      return t < THROW + flight + RETURN + 0.05;
    },
    draw(c) {
      if (t < THROW) {
        const k = t / THROW;
        const p = along(home, away, k * k * (3 - 2 * k), 160);
        drawSprite(c, 'leviathan_axe', p.x, p.y, 130, -t * 22);
        fx.add(burst(p, 1, { kind: 'flake', color: '#7fd8ff', speed: [10, 40], size: 5, max: 0.6 }));
      } else if (t > THROW + flight) {
        const k = easeOut(clamp01((t - THROW - flight) / RETURN));
        const p = along(away, home, k, -160);
        drawSprite(c, 'leviathan_axe', p.x, p.y, 130, t * 22);
        c.save();
        c.strokeStyle = 'rgba(127,216,255,0.6)';
        c.lineWidth = 4;
        c.beginPath();
        for (let i = 0; i <= 12; i++) {
          const q = along(away, home, (k * i) / 12, -160);
          if (i) c.lineTo(q.x, q.y);
          else c.moveTo(q.x, q.y);
        }
        c.stroke();
        c.restore();
      }
    },
  });
}

/** Ezio's Leap of Faith: an eagle swoops across the screen. */
export function eagleSwoop(fx: FxLayer) {
  let t = 0;
  fx.add({
    update(dt) { t += dt / 0.9; return t < 1; },
    draw(c) {
      const k = easeOut(t);
      const x = fx.width + 100 - (fx.width + 300) * k;
      const y = 80 + Math.sin(k * Math.PI) * fx.height * 0.35;
      drawSprite(c, 'eagle', x, y, 200, -0.3 + k * 0.5, 1 - clamp01((t - 0.8) * 5));
    },
  });
  fx.add(burst({ x: fx.width * 0.5, y: fx.height * 0.35 }, 18, { kind: 'feather', color: '#ffffff', speed: [60, 240], size: 9, max: 1.8, gravity: 40, drag: 0.94 }));
}

/** Naruto's Shadow Clone pops out of smoke at a point, waves, then vanishes. */
export function clonePop(fx: FxLayer, p: Pt) {
  let t = 0;
  fx.add({
    update(dt) { t += dt; return t < 2.1; },
    draw(c) {
      const inK = easeOut(clamp01(t / 0.25));
      const outK = clamp01((t - 1.6) / 0.25);
      const bob = Math.sin(t * 8) * 3;
      if (t < 0.45) drawSprite(c, 'smoke_puff', p.x, p.y, 120 * (0.5 + inK * 0.8), 0, 1 - clamp01((t - 0.25) / 0.2));
      if (t > 0.12 && t < 1.85) drawSprite(c, 'naruto_clone', p.x, p.y + bob, 120 * (0.6 + inK * 0.4), 0, 1 - outK);
      if (t > 1.6) drawSprite(c, 'smoke_puff', p.x, p.y, 110 * (0.6 + outK * 0.6), 0, 1 - clamp01((t - 1.85) / 0.25));
    },
  });
}

/** Asta's slash across a heading as a section is revealed. */
export function headingSlash(fx: FxLayer, rect: DOMRect) {
  const a = { x: rect.left - 30, y: rect.bottom + 10 };
  const b = { x: rect.left + Math.min(rect.width, 700) + 30, y: rect.top - 10 };
  const path = Array.from({ length: 12 }, (_, i) => ({ x: a.x + ((b.x - a.x) * i) / 11, y: a.y + ((b.y - a.y) * i) / 11 }));
  let t = 0;
  fx.add({
    update(dt) { t += dt / 0.5; return t < 1; },
    draw(c) {
      const shown = Math.max(2, Math.ceil(path.length * clamp01(t * 3)));
      c.save();
      c.globalAlpha = 1 - clamp01((t - 0.4) / 0.6);
      c.strokeStyle = '#0b0b0b';
      c.lineCap = 'round';
      c.lineWidth = 6;
      c.beginPath();
      path.slice(0, shown).forEach((pt, i) => (i ? c.lineTo(pt.x, pt.y) : c.moveTo(pt.x, pt.y)));
      c.stroke();
      c.strokeStyle = '#f6f4ee';
      c.lineWidth = 1.5;
      c.stroke();
      c.restore();
      if (t < 0.45) drawSprite(c, 'demon_slayer_sword', path[shown - 1].x, path[shown - 1].y, 110, Math.atan2(b.y - a.y, b.x - a.x) + Math.PI / 2 - 0.4, 1 - t * 2);
    },
  });
  fx.add(burst(b, 10, { kind: 'shard', color: '#1d1d22', speed: [120, 320], spread: 1.2, angle: Math.atan2(b.y - a.y, b.x - a.x), size: 7, max: 0.6 }));
}

