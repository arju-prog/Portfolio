// Opening sequence: the cast drops in one by one, dances to a beat (each with a signature move),
// poses to present the site, then jumps out of frame. Figures are static meshes, so all motion is
// procedural (hops, squash & stretch, spins, flips). Cel-shaded with ink outlines to match the manga page.
// Client-only — loaded lazily by <Intro />, disposed as soon as it finishes.
import * as THREE from 'three';
import { OutlineEffect } from 'three/addons/effects/OutlineEffect.js';
import type { CastMember, Move } from '@/data/play/intro';
import { loadGLB, variantOf } from './viewer';

export type IntroEvent =
  | { type: 'progress'; loaded: number; total: number }
  | { type: 'start' }
  | { type: 'land'; index: number; at: { x: number; y: number } }
  | { type: 'beat'; n: number }
  | { type: 'signature'; index: number; at: { x: number; y: number } }
  | { type: 'shake' }
  | { type: 'pose'; at: { x: number; y: number } }
  | { type: 'exit' }
  | { type: 'done' };

// timeline (seconds)
const ENTER_START = 0.35;
const ENTER_GAP = 0.22;
const FALL = 0.45;
const BEAT = 0.5; // 120 bpm
const DANCE_BEATS = 10;
// Signature moves ripple left → right: character i starts on beat SIG_START + i·SIG_STAGGER, lasting SIG_LEN beats
const SIG_START = 1.5;
const SIG_STAGGER = 0.6;
const SIG_LEN = 1.6;
const GROUP_SPIN_BEAT = 8;
const POSE = 1.3;
const EXIT = 0.9;
const LOAD_TIMEOUT = 7000;

const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);
const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const clamp01 = (t: number) => Math.max(0, Math.min(1, t));

type Actor = {
  member: CastMember;
  index: number;
  holder: THREE.Group; // position on stage
  pivot: THREE.Group; // rotates around the figure's centre (y = 1)
  home: THREE.Vector3;
  landed: boolean;
  signed: boolean;
};

export class IntroEngine {
  private renderer: THREE.WebGLRenderer;
  private outline: OutlineEffect | null;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(32, 1, 0.1, 200);
  private actors: Actor[] = [];
  private raf = 0;
  private t = 0;
  private last = 0;
  private started = false;
  private beatsSent = -1;
  private posed = false;
  private exited = false;
  private finished = false;
  private shake = 0;
  private camBase = new THREE.Vector3();
  private lookAt = new THREE.Vector3(0, 1.1, 0);
  private danceStart = 0;
  private poseStart = 0;
  private exitStart = 0;
  private resizeObserver: ResizeObserver;

  constructor(
    private canvas: HTMLCanvasElement,
    private cast: CastMember[],
    private emit: (e: IntroEvent) => void,
  ) {
    const small = Math.min(window.innerWidth, window.innerHeight) < 700;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, small ? 1.25 : 1.75));
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.shadowMap.enabled = true;
    // ink outlines double the geometry cost — skip them on phones
    this.outline = small ? null : new OutlineEffect(this.renderer, { defaultThickness: 0.005, defaultColor: [0, 0, 0] });

    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8a8a, 1.7));
    const key = new THREE.DirectionalLight(0xffffff, 2.2);
    key.position.set(-4, 8, 6);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    Object.assign(key.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8 });
    this.scene.add(key);
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.ShadowMaterial({ opacity: 0.16 }));
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    this.scene.add(floor);

    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas.parentElement ?? canvas);
    this.resize();
    void this.load();
  }

  /** Jump to the exit (skip button). */
  skip() {
    if (!this.started) {
      this.finish();
      return;
    }
    if (this.t < this.exitStart) this.t = this.exitStart;
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.resizeObserver.disconnect();
    this.scene.traverse((o) => {
      if (o instanceof THREE.Mesh) o.geometry.dispose();
    });
    this.renderer.dispose();
  }

  // ── setup ──

  private async load() {
    let loaded = 0;
    const total = this.cast.length;
    this.emit({ type: 'progress', loaded, total });
    const timeout = new Promise<null>((r) => setTimeout(() => r(null), LOAD_TIMEOUT));
    const models = await Promise.all(
      this.cast.map((m) =>
        Promise.race([loadGLB(`/models/${m.id}.glb`), timeout])
          .catch(() => null)
          .then((model) => {
            this.emit({ type: 'progress', loaded: ++loaded, total });
            return model;
          }),
      ),
    );
    if (this.finished) return;
    const present = this.cast.map((m, i) => ({ m, model: models[i] })).filter((x) => x.model) as {
      m: CastMember;
      model: THREE.Object3D;
    }[];
    if (present.length === 0) {
      this.finish(); // nothing to show (offline / models not built) — go straight to the site
      return;
    }
    this.layout(present);
    this.danceStart = ENTER_START + present.length * ENTER_GAP + FALL + 0.25;
    this.poseStart = this.danceStart + DANCE_BEATS * BEAT;
    this.exitStart = this.poseStart + POSE;
    this.started = true;
    this.emit({ type: 'start' });
    this.last = performance.now();
    this.raf = requestAnimationFrame(this.frame);
  }

  private layout(present: { m: CastMember; model: THREE.Object3D }[]) {
    const n = present.length;
    const portrait = this.camera.aspect < 0.9;
    const perRow = portrait ? Math.ceil(n / 2) : n;
    const spacing = portrait ? 1.45 : 1.5;
    present.forEach(({ m, model }, i) => {
      model.traverse((o) => {
        if (o instanceof THREE.Mesh) {
          o.castShadow = true;
          const mat = o.material as THREE.Material | THREE.Material[];
          o.material = Array.isArray(mat) ? mat.map((x) => variantOf(x, 'anime')) : variantOf(mat, 'anime');
        }
      });
      const row = Math.floor(i / perRow);
      const col = i % perRow;
      const inRow = Math.min(perRow, n - row * perRow);
      // back row sits half a slot over so every figure shows between the ones in front
      const x = (col - (inRow - 1) / 2) * spacing + (row === 1 ? spacing / 2 : 0);
      const z = -Math.abs(col - (inRow - 1) / 2) * 0.28 - row * 2.1; // gentle arc; back row behind
      const holder = new THREE.Group();
      const pivot = new THREE.Group();
      pivot.position.y = 1; // rotate around the figure's middle
      model.position.y = -1;
      // face slightly toward the centre of the stage
      holder.rotation.y = -x * 0.06;
      pivot.add(model);
      holder.add(pivot);
      holder.position.set(x, 0, z);
      holder.visible = false;
      this.scene.add(holder);
      this.actors.push({ member: m, index: i, holder, pivot, home: holder.position.clone(), landed: false, signed: false });
    });
    // frame the line-up
    const halfW = ((perRow - 1) / 2) * spacing + 1.1;
    const halfFovV = (this.camera.fov * Math.PI) / 360;
    const distW = halfW / (Math.tan(halfFovV) * this.camera.aspect);
    const distH = (portrait ? 2.6 : 1.8) / Math.tan(halfFovV);
    const dist = Math.max(distW, distH) + (portrait ? 2 : 0);
    this.camBase.set(0, portrait ? 6.2 : 2.6, dist);
    this.lookAt.set(0, portrait ? 0.9 : 2.0, portrait ? -1.2 : 0);
    this.camera.position.copy(this.camBase);
  }

  private resize() {
    const parent = this.canvas.parentElement ?? this.canvas;
    const w = parent.clientWidth;
    const h = parent.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  private toScreen(v: THREE.Vector3) {
    const p = v.clone().project(this.camera);
    const r = this.canvas.getBoundingClientRect();
    return { x: r.left + ((p.x + 1) / 2) * r.width, y: r.top + ((1 - p.y) / 2) * r.height };
  }

  private headOf(a: Actor) {
    return this.toScreen(a.holder.position.clone().add(new THREE.Vector3(0, 2.2, 0)));
  }

  private finish() {
    if (this.finished) return;
    this.finished = true;
    this.emit({ type: 'done' });
  }

  // ── animation ──

  private frame = (now: number) => {
    this.raf = requestAnimationFrame(this.frame);
    const dt = Math.min((now - this.last) / 1000, 0.05);
    this.last = now;
    this.t += dt;
    const t = this.t;

    // beats
    if (t >= this.danceStart && t < this.poseStart) {
      const n = Math.floor((t - this.danceStart) / BEAT);
      if (n !== this.beatsSent) {
        this.beatsSent = n;
        this.emit({ type: 'beat', n });
      }
    }
    if (!this.posed && t >= this.poseStart) {
      this.posed = true;
      this.emit({ type: 'pose', at: this.toScreen(new THREE.Vector3(0, 2.6, 0)) });
    }
    if (!this.exited && t >= this.exitStart) {
      this.exited = true;
      this.emit({ type: 'exit' });
    }
    if (t >= this.exitStart + EXIT + 0.15) {
      this.finish();
      cancelAnimationFrame(this.raf);
      return;
    }

    for (const a of this.actors) this.animate(a, t);

    // camera: gentle dolly-in, push during the pose, shake on impacts
    const push = easeInOut(clamp01((t - this.poseStart) / POSE)) * 0.12;
    this.shake *= Math.exp(-dt * 9);
    this.camera.position.set(
      this.camBase.x + Math.sin(t * 0.6) * 0.25 + (Math.random() - 0.5) * this.shake,
      this.camBase.y + (Math.random() - 0.5) * this.shake,
      this.camBase.z * (1 - push) + Math.cos(t * 0.6) * 0.2,
    );
    this.camera.lookAt(this.lookAt);

    if (this.outline) this.outline.render(this.scene, this.camera);
    else this.renderer.render(this.scene, this.camera);
  };

  private animate(a: Actor, t: number) {
    const { holder, pivot, home } = a;
    let y = 0;
    let rx = 0;
    let ry = 0;
    let rz = 0;
    let sx = 1;
    let sy = 1;

    // 1 — drop in with a spin, squash on landing
    const enter = ENTER_START + a.index * ENTER_GAP;
    if (t < enter) {
      holder.visible = false;
      return;
    }
    holder.visible = true;
    const k = (t - enter) / FALL;
    if (k < 1) {
      y = 7 * (1 - k * k);
      ry = (1 - k) * Math.PI * 2;
    } else {
      if (!a.landed) {
        a.landed = true;
        this.emit({ type: 'land', index: a.index, at: this.headOf(a) });
      }
      const u = clamp01((t - enter - FALL) / 0.22);
      if (u < 1) {
        const s = Math.sin(u * Math.PI) * 0.22;
        sy = 1 - s;
        sx = 1 + s * 0.6;
      }
    }

    // 2 — dance: bounce + sway on the beat, signature move on beats 4–6, a group spin on beat 7
    if (t >= this.danceStart && t < this.exitStart) {
      const b = (t - this.danceStart) / BEAT;
      const fade = clamp01((this.poseStart + 0.4 - t) / 0.4); // calm down into the pose
      const side = a.index % 2 ? 1 : -1;
      y += Math.abs(Math.sin(Math.PI * b)) * 0.22 * fade;
      rz += Math.sin(Math.PI * b) * 0.11 * side * fade;
      ry += Math.sin((Math.PI * b) / 2) * 0.35 * fade;
      sy *= 1 - Math.max(0, Math.cos(Math.PI * b * 2)) * 0.04 * fade;

      const su = (b - SIG_START - a.index * SIG_STAGGER) / SIG_LEN;
      if (su > 0 && su < 1) {
        if (!a.signed) {
          a.signed = true;
          this.emit({ type: 'signature', index: a.index, at: this.headOf(a) });
        }
        const m = this.move(a.member.move, su);
        y += m.y;
        rx += m.rx;
        ry += m.ry;
        rz += m.rz;
        sx *= m.sx;
        sy *= m.sy;
      }
      const spin = (b - GROUP_SPIN_BEAT - a.index * 0.05) / 0.9;
      if (spin > 0 && spin < 1) ry += easeInOut(spin) * Math.PI * 2;
    }

    // 3 — pose: face the camera, lean in
    if (t >= this.poseStart && t < this.exitStart) {
      const p = easeOut(clamp01((t - this.poseStart) / 0.4));
      rx += -0.12 * p;
      y += Math.sin(clamp01((t - this.poseStart) / 0.5) * Math.PI) * 0.4;
    }

    // 4 — exit: everyone leaps up and out of frame, staggered from the centre outwards
    if (t >= this.exitStart) {
      const order = Math.abs(a.index - (this.actors.length - 1) / 2);
      const e = clamp01((t - this.exitStart - order * 0.06) / 0.6);
      y += e * e * 12;
      ry += e * 5;
      sy *= 1 + e * 0.3;
      sx *= 1 - e * 0.2;
    }

    holder.position.set(home.x, home.y + y, home.z);
    pivot.rotation.set(rx, ry, rz);
    pivot.scale.set(sx, sy, sx);
  }

  /** Signature move, u ∈ (0, 1). */
  private move(kind: Move, u: number) {
    const arc = Math.sin(u * Math.PI);
    const out = { y: 0, rx: 0, ry: 0, rz: 0, sx: 1, sy: 1 };
    switch (kind) {
      case 'stretch': // Luffy: rubbery stretch up and boing back
        out.sy = 1 + arc * 0.55 * (1 + Math.sin(u * Math.PI * 6) * 0.15);
        out.sx = 1 - arc * 0.18;
        break;
      case 'spin': // Naruto: fast double spin
        out.ry = easeInOut(u) * Math.PI * 4;
        out.y = arc * 0.3;
        break;
      case 'leap': // Deku: big jump
        out.y = arc * 2.2;
        out.sy = 1 + arc * 0.15;
        break;
      case 'slash': // Asta: swing the sword back and forth
        out.ry = Math.sin(u * Math.PI * 2) * 1.1;
        out.rz = arc * 0.15;
        break;
      case 'flip': // Wukong: backflip
        out.y = arc * 1.6;
        out.rx = -easeInOut(u) * Math.PI * 2;
        break;
      case 'stomp': // Kratos: rise and slam
        out.y = u < 0.6 ? Math.sin((u / 0.6) * Math.PI * 0.5) * 0.9 : 0.9 * (1 - (u - 0.6) / 0.4) ** 2;
        if (u > 0.6 && u < 0.7) this.shake = 0.35;
        if (u > 0.6 && u < 0.64) this.emit({ type: 'shake' });
        out.sy = u > 0.6 && u < 0.75 ? 0.85 : 1;
        out.sx = u > 0.6 && u < 0.75 ? 1.12 : 1;
        break;
      case 'dive': // Ezio: forward dive roll
        out.y = arc * 0.9;
        out.rx = easeInOut(u) * Math.PI * 2;
        break;
      case 'wave': // Drake: side-to-side shimmy
        out.rz = Math.sin(u * Math.PI * 4) * 0.25;
        out.y = arc * 0.4;
        break;
    }
    return out;
  }
}
