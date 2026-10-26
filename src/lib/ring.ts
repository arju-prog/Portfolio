// A ring of Blender models on a rotating 3D carousel, cel-shaded with ink outlines (the Armory).
// Drag to spin (with inertia), hover to lift, click to bring a relic to the front.
import * as THREE from 'three';
import { OutlineEffect } from 'three/addons/effects/OutlineEffect.js';
import { loadGLB, variantOf } from './viewer';

const TAU = Math.PI * 2;

export type RingOptions = { radius?: number; scale?: number };

type Slot = { id: string; angle: number; holder: THREE.Group; spin: number; hover: number; pick: number };

export class RingEngine {
  private renderer: THREE.WebGLRenderer;
  private outline: OutlineEffect;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
  private ring = new THREE.Group();
  private slots: Slot[] = [];
  private raycaster = new THREE.Raycaster();
  private pointer = new THREE.Vector2(9, 9);
  private rotation = 0;
  private velocity = 0;
  private target: number | null = null;
  private selected: string | null = null;
  private hovered: Slot | null = null;
  private dragging = false;
  private dragStartX = 0;
  private lastX = 0;
  private moved = 0;
  private paused = false;
  private raf = 0;
  private timer = new THREE.Timer();
  private resizeObserver: ResizeObserver;

  private radius: number;
  private itemScale: number;

  constructor(
    private canvas: HTMLCanvasElement,
    ids: string[],
    private onSelect: (id: string | null) => void,
    { radius = 3.6, scale = 0.95 }: RingOptions = {},
  ) {
    this.radius = radius;
    this.itemScale = scale;
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    this.renderer = renderer;
    this.outline = new OutlineEffect(renderer, { defaultThickness: 0.006, defaultColor: [0, 0, 0] });

    this.camera.position.set(0, 1.5, 11);
    this.camera.lookAt(0, 0.1, 0);
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x777777, 1.6));
    const key = new THREE.DirectionalLight(0xffffff, 2.2);
    key.position.set(-3, 4, 5);
    this.scene.add(key);
    this.scene.add(this.ring);

    ids.forEach((id, i) => {
      const holder = new THREE.Group();
      const angle = (i / ids.length) * TAU;
      holder.position.set(Math.sin(angle) * radius, 0, Math.cos(angle) * radius);
      holder.userData.id = id;
      this.ring.add(holder);
      const slot: Slot = { id, angle, holder, spin: Math.random() * TAU, hover: 0, pick: 0 };
      this.slots.push(slot);
      loadGLB(`/props/${id}.glb`)
        .then((model) => {
          model.traverse((obj) => {
            if (obj instanceof THREE.Mesh) {
              const m = obj.material as THREE.Material | THREE.Material[];
              obj.material = Array.isArray(m) ? m.map((x) => variantOf(x, 'anime')) : variantOf(m, 'anime');
            }
          });
          model.scale.setScalar(this.itemScale);
          holder.add(model);
        })
        .catch(() => {
          /* prop not built yet — leave the slot empty */
        });
    });

    canvas.addEventListener('pointerdown', this.onDown);
    window.addEventListener('pointermove', this.onMove);
    window.addEventListener('pointerup', this.onUp);
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas.parentElement ?? canvas);
    this.resize();
    this.raf = requestAnimationFrame(this.frame);
  }

  select(id: string | null) {
    this.selected = id;
    const slot = this.slots.find((s) => s.id === id);
    if (slot) {
      // nearest rotation that brings this slot to the front (angle + rotation ≡ 0)
      const desired = -slot.angle;
      const turns = Math.round((this.rotation - desired) / TAU);
      this.target = desired + turns * TAU;
      this.velocity = 0;
    } else {
      this.target = null;
    }
  }

  step(delta: number) {
    const i = this.slots.findIndex((s) => s.id === this.selected);
    const next = this.slots[(Math.max(0, i) + delta + this.slots.length) % this.slots.length];
    this.onSelect(next.id);
  }

  setPaused(paused: boolean) {
    this.paused = paused;
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.resizeObserver.disconnect();
    this.canvas.removeEventListener('pointerdown', this.onDown);
    window.removeEventListener('pointermove', this.onMove);
    window.removeEventListener('pointerup', this.onUp);
    this.renderer.dispose();
  }

  private resize() {
    const parent = this.canvas.parentElement ?? this.canvas;
    const w = parent.clientWidth;
    const h = parent.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    // keep the whole ring in view on narrow screens
    // back off just enough to keep the whole ring (plus a selected, enlarged item) in frame
    const halfFov = Math.tan((this.camera.fov * Math.PI) / 360);
    const needed = (this.radius + 1.1) / (halfFov * this.camera.aspect) + this.radius * 0.5;
    this.camera.position.z = Math.max(this.radius * 2.4, needed);
    this.camera.position.y = this.camera.position.z * 0.3; // look down onto the ring
    this.camera.lookAt(0, 0, 0);
    this.camera.updateProjectionMatrix();
  }

  private setPointer(e: PointerEvent) {
    const r = this.canvas.getBoundingClientRect();
    this.pointer.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    return r;
  }

  private pick(): Slot | null {
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hits = this.raycaster.intersectObjects(this.ring.children, true);
    for (const hit of hits) {
      let o: THREE.Object3D | null = hit.object;
      while (o && !o.userData.id) o = o.parent;
      if (o) return this.slots.find((s) => s.id === o!.userData.id) ?? null;
    }
    return null;
  }

  private onDown = (e: PointerEvent) => {
    this.dragging = true;
    this.dragStartX = this.lastX = e.clientX;
    this.moved = 0;
    this.velocity = 0;
    this.canvas.setPointerCapture?.(e.pointerId);
  };

  private onMove = (e: PointerEvent) => {
    const r = this.setPointer(e);
    const inside = e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom;
    if (!inside && !this.dragging) this.pointer.set(9, 9);
    if (!this.dragging) return;
    const dx = e.clientX - this.lastX;
    this.lastX = e.clientX;
    this.moved = Math.max(this.moved, Math.abs(e.clientX - this.dragStartX));
    this.rotation += dx * 0.006;
    this.velocity = dx * 0.006;
    this.target = null;
  };

  private onUp = (e: PointerEvent) => {
    if (!this.dragging) return;
    this.dragging = false;
    if (this.moved < 6) {
      this.setPointer(e);
      const slot = this.pick();
      this.onSelect(slot ? slot.id : null);
    } else if (this.selected) {
      this.onSelect(null);
    }
  };

  private frame = (timestamp: number) => {
    this.raf = requestAnimationFrame(this.frame);
    if (this.paused) return;
    this.timer.update(timestamp);
    const dt = Math.min(this.timer.getDelta(), 0.05);
    const t = this.timer.getElapsed();

    if (this.target !== null) {
      this.rotation += (this.target - this.rotation) * Math.min(1, dt * 6);
    } else if (!this.dragging) {
      this.rotation += this.velocity;
      this.velocity *= 0.94;
      if (Math.abs(this.velocity) < 0.0005) this.rotation += dt * 0.12; // idle drift
    }
    this.ring.rotation.y = this.rotation;

    this.hovered = this.dragging ? null : this.pick();
    this.canvas.style.cursor = this.dragging ? 'grabbing' : this.hovered ? 'pointer' : 'grab';

    for (const s of this.slots) {
      s.hover += ((this.hovered === s ? 1 : 0) - s.hover) * Math.min(1, dt * 10);
      s.pick += ((this.selected === s.id ? 1 : 0) - s.pick) * Math.min(1, dt * 6);
      s.spin += dt * (0.5 + s.pick * 0.6);
      s.holder.rotation.y = s.spin - this.rotation; // keep each relic turning on its own axis
      s.holder.position.y = Math.sin(t * 1.4 + s.angle * 3) * 0.08 + s.pick * 0.35;
      s.holder.scale.setScalar(1 + s.hover * 0.15 + s.pick * 0.9);
    }
    this.outline.render(this.scene, this.camera);
  };
}
