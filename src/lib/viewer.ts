// Interactive figure viewer: loads a Blender-exported GLB onto a display base and renders it
// in one of three looks — 'real' (PBR + reflections + soft shadows), 'anime' (cel-shaded with
// ink outlines) or 'manga' (black & white screentone-style toon with ink outlines).
// Client-only — loaded lazily by <FigureViewer />.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { OutlineEffect } from 'three/addons/effects/OutlineEffect.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

export type ViewerMode = 'real' | 'anime' | 'manga';
export type ViewerStatus = 'loading' | 'ready' | 'error';

export type ViewerOptions = {
  controls: boolean; // drag to orbit
  zoom: boolean;
  autoRotate: boolean;
  onStatus?: (status: ViewerStatus) => void;
};

const TARGET = new THREE.Vector3(0, 0.95, 0);

// ── Shared loading + material variants ─────────────────────────────────

let loader: GLTFLoader | null = null;
const cache = new Map<string, Promise<THREE.Object3D>>();

/** Loads (and caches) a Draco-compressed GLB; every call returns a fresh clone. */
export function loadGLB(url: string) {
  if (!loader) {
    const draco = new DRACOLoader().setDecoderPath('/draco/');
    loader = new GLTFLoader().setDRACOLoader(draco);
  }
  let pending = cache.get(url);
  if (!pending) {
    pending = loader.loadAsync(url).then((gltf) => gltf.scene);
    pending.catch(() => cache.delete(url));
    cache.set(url, pending);
  }
  return pending.then((scene) => scene.clone(true));
}

/** Scale a loaded model so its largest side is `size`, centred on the base with its bottom at y = 0. */
function fitToBase(model: THREE.Object3D, size: number) {
  const box = new THREE.Box3().setFromObject(model);
  const dims = box.getSize(new THREE.Vector3());
  const k = size / Math.max(dims.x, dims.y, dims.z);
  model.scale.setScalar(k);
  box.setFromObject(model);
  const centre = box.getCenter(new THREE.Vector3());
  model.position.set(-centre.x, -box.min.y, -centre.z);
  const holder = new THREE.Group();
  holder.add(model);
  return holder;
}

const toonRamp = (() => {
  const tex = new THREE.DataTexture(new Uint8Array([70, 150, 215, 255]), 4, 1, THREE.RedFormat);
  tex.minFilter = tex.magFilter = THREE.NearestFilter;
  tex.needsUpdate = true;
  return tex;
})();

const inkRamp = (() => {
  const tex = new THREE.DataTexture(new Uint8Array([25, 120, 255]), 3, 1, THREE.RedFormat);
  tex.minFilter = tex.magFilter = THREE.NearestFilter;
  tex.needsUpdate = true;
  return tex;
})();

const variants = new WeakMap<THREE.Material, Record<ViewerMode, THREE.Material>>();

export function variantOf(original: THREE.Material, mode: ViewerMode): THREE.Material {
  let set = variants.get(original);
  if (!set) {
    const src = original as THREE.MeshStandardMaterial;
    const color = src.color ?? new THREE.Color(1, 1, 1);
    const emissive = src.emissive ?? new THREE.Color(0, 0, 0);
    const glow = emissive.r + emissive.g + emissive.b > 0.05;
    const anime = new THREE.MeshToonMaterial({
      color,
      gradientMap: toonRamp,
      emissive,
      emissiveIntensity: Math.min(src.emissiveIntensity ?? 1, 1.5),
    });
    // Manga: luminance → three ink tones; glowing parts become pure white.
    const lum = 0.2126 * color.r + 0.7152 * color.g + 0.0722 * color.b;
    const tone = glow ? 1 : lum > 0.35 ? 1 : lum > 0.08 ? 0.62 : 0.16;
    const manga = new THREE.MeshToonMaterial({
      color: new THREE.Color(tone, tone, tone),
      gradientMap: inkRamp,
      emissive: glow ? new THREE.Color(0.6, 0.6, 0.6) : new THREE.Color(0, 0, 0),
    });
    set = { real: original, anime, manga };
    variants.set(original, set);
  }
  return set[mode];
}

// ── Viewer ─────────────────────────────────────────────────────────────

export class FigureViewerEngine {
  private renderer: THREE.WebGLRenderer;
  private outline: OutlineEffect;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(26, 1, 0.1, 100);
  private controls: OrbitControls;
  private timer = new THREE.Timer();
  private stage = new THREE.Group(); // spins / jumps
  private figure: THREE.Object3D | null = null;
  private base: THREE.Mesh;
  private mode: ViewerMode = 'real';
  private raf = 0;
  private paused = false;
  private loadToken = 0;
  private popIn = 1;
  private spinT = -1;
  private jumpT = -1;
  private resizeObserver: ResizeObserver;
  private envTexture: THREE.Texture;

  constructor(private canvas: HTMLCanvasElement, private options: ViewerOptions) {
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    this.renderer = renderer;
    this.outline = new OutlineEffect(renderer, { defaultThickness: 0.0045, defaultColor: [0, 0, 0] });

    const pmrem = new THREE.PMREMGenerator(renderer);
    this.envTexture = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();
    this.scene.environment = this.envTexture;

    this.camera.position.set(2.2, 1.55, 6.6);

    // Lights: key (with soft shadow), rim for a strong silhouette, soft hemisphere fill.
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x6b6b6b, 1.1));
    const key = new THREE.DirectionalLight(0xffffff, 2.6);
    key.position.set(-3, 5, 4);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.camera.left = key.shadow.camera.bottom = -2;
    key.shadow.camera.right = key.shadow.camera.top = 2;
    key.shadow.radius = 6;
    key.shadow.bias = -0.0005;
    this.scene.add(key);
    const rim = new THREE.DirectionalLight(0xffffff, 2.2);
    rim.position.set(2, 3, -5);
    this.scene.add(rim);

    // Display base + contact shadow.
    this.base = new THREE.Mesh(
      new THREE.CylinderGeometry(0.72, 0.78, 0.12, 64),
      new THREE.MeshStandardMaterial({ color: 0x0d0d0d, roughness: 0.22, metalness: 0.35 }),
    );
    this.base.position.y = -0.06;
    this.base.receiveShadow = true;
    this.base.userData.original = this.base.material;
    this.stage.add(this.base);
    const ground = new THREE.Mesh(new THREE.CircleGeometry(2.4, 48), new THREE.ShadowMaterial({ opacity: 0.18 }));
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.121;
    ground.receiveShadow = true;
    this.scene.add(ground);
    this.scene.add(this.stage);

    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.target.copy(TARGET);
    this.controls.enableDamping = true;
    this.controls.enablePan = false;
    this.controls.enableZoom = options.zoom;
    this.controls.enabled = options.controls;
    // OrbitControls sets touch-action: none, which traps page scrolling on phones.
    // Inline viewers (no zoom) let vertical swipes scroll the page; horizontal drags still rotate.
    canvas.style.touchAction = options.zoom ? 'none' : 'pan-y';
    this.controls.minDistance = 3.2;
    this.controls.maxDistance = 10;
    this.controls.minPolarAngle = 0.35;
    this.controls.maxPolarAngle = 1.75;
    this.controls.autoRotate = options.autoRotate;
    this.controls.autoRotateSpeed = 1.6;
    this.controls.update();

    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas.parentElement ?? canvas);
    this.resize();

    this.raf = requestAnimationFrame(this.frame);
  }

  /** Load a GLB (e.g. '/props/evaratus_lab.glb') and stand it on the display base. */
  async show(url: string) {
    const token = ++this.loadToken;
    this.options.onStatus?.('loading');
    try {
      const model = fitToBase(await loadGLB(url), 2.1);
      if (token !== this.loadToken) return;
      model.traverse((obj) => {
        if (obj instanceof THREE.Mesh) {
          obj.castShadow = true;
          obj.userData.original = obj.material;
        }
      });
      if (this.figure) this.stage.remove(this.figure);
      this.figure = model;
      this.stage.add(model);
      this.applyMode();
      this.popIn = 0;
      this.options.onStatus?.('ready');
    } catch (err) {
      if (token !== this.loadToken) return;
      console.warn(`[viewer] could not load ${url}`, err);
      this.options.onStatus?.('error');
    }
  }

  setMode(mode: ViewerMode) {
    this.mode = mode;
    this.applyMode();
  }

  setAutoRotate(on: boolean) {
    this.controls.autoRotate = on;
  }

  setPaused(paused: boolean) {
    this.paused = paused;
  }

  spin() {
    this.spinT = 0;
  }

  jump() {
    this.jumpT = 0;
  }

  resetView() {
    this.camera.position.set(2.2, 1.55, 6.6);
    this.controls.target.copy(TARGET);
    this.controls.update();
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.resizeObserver.disconnect();
    this.controls.dispose();
    this.envTexture.dispose();
    this.renderer.dispose();
  }

  private applyMode() {
    const swap = (obj: THREE.Object3D) => {
      if (obj instanceof THREE.Mesh && obj.userData.original) {
        const originals = obj.userData.original as THREE.Material | THREE.Material[];
        obj.material = Array.isArray(originals)
          ? originals.map((m) => variantOf(m, this.mode))
          : variantOf(originals, this.mode);
      }
    };
    this.stage.traverse(swap);
    this.renderer.toneMapping = this.mode === 'real' ? THREE.ACESFilmicToneMapping : THREE.NoToneMapping;
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

  private frame = (timestamp: number) => {
    this.raf = requestAnimationFrame(this.frame);
    if (this.paused) return;
    this.timer.update(timestamp);
    const dt = Math.min(this.timer.getDelta(), 0.05);
    const t = this.timer.getElapsed();

    // pop-in on model change (ease-out-back)
    this.popIn = Math.min(1, this.popIn + dt * 2.4);
    const p = this.popIn - 1;
    const scale = 1 + 2.2 * p * p * p + 1.2 * p * p;
    this.stage.scale.setScalar(Math.max(0.001, scale));

    // spin: one full turn with ease-in-out
    let spin = 0;
    if (this.spinT >= 0) {
      this.spinT += dt / 0.9;
      const k = Math.min(1, this.spinT);
      spin = (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2) * Math.PI * 2;
      if (this.spinT >= 1) this.spinT = -1;
    }
    // jump: hop with a little squash & stretch
    let hop = 0;
    let squash = 1;
    if (this.jumpT >= 0) {
      this.jumpT += dt / 0.75;
      const k = Math.min(1, this.jumpT);
      hop = Math.sin(k * Math.PI) * 0.55;
      squash = 1 + Math.sin(k * Math.PI * 2) * 0.06;
      if (this.jumpT >= 1) this.jumpT = -1;
    }
    if (this.figure) {
      this.figure.rotation.y = spin;
      this.figure.position.y = hop + Math.sin(t * 1.6) * 0.012; // idle breathing
      this.figure.scale.set(1 / Math.sqrt(squash), squash, 1 / Math.sqrt(squash));
    }

    this.controls.update(dt);
    if (this.mode === 'real') this.renderer.render(this.scene, this.camera);
    else this.outline.render(this.scene, this.camera);
  };
}
