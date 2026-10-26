// Scroll helpers shared by the navigation interactions.
//
// Animated scrolls never fight the user: any wheel, touch, pointer or key input
// cancels an in-flight tween immediately and leaves the page where the user put it.

const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const INTERRUPTS = ['wheel', 'touchstart', 'pointerdown', 'keydown'] as const;
const NAV_OFFSET = 72; // fixed nav height

export const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

let active: { cancel: () => void } | null = null;

/** Scroll to `top` over `duration` ms. Resolves true if it finished, false if the user interrupted. */
export function tweenScroll(top: number, duration = 800): Promise<boolean> {
  active?.cancel();
  const max = document.documentElement.scrollHeight - window.innerHeight;
  const to = Math.max(0, Math.min(max, top));
  const from = window.scrollY;
  if (prefersReducedMotion() || Math.abs(to - from) < 2) {
    window.scrollTo({ top: to, behavior: 'instant' });
    return Promise.resolve(true);
  }
  return new Promise((resolve) => {
    let raf = 0;
    const start = performance.now();
    const finish = (completed: boolean) => {
      cancelAnimationFrame(raf);
      INTERRUPTS.forEach((type) => window.removeEventListener(type, interrupt, true));
      active = null;
      resolve(completed);
    };
    const interrupt = () => finish(false);
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      window.scrollTo({ top: from + (to - from) * easeInOut(t), behavior: 'instant' });
      if (t < 1) raf = requestAnimationFrame(step);
      else finish(true);
    };
    INTERRUPTS.forEach((type) => window.addEventListener(type, interrupt, { capture: true, passive: true }));
    active = { cancel: () => finish(false) };
    raf = requestAnimationFrame(step);
  });
}

/** Document-y of every scroll stop (elements marked data-stop), in page order. */
export function scrollStops() {
  return [...document.querySelectorAll<HTMLElement>('[data-stop]')].map(
    (el) => el.getBoundingClientRect().top + window.scrollY - NAV_OFFSET,
  );
}

/** Next stop below (dir 1) or above (dir -1) the current scroll position. */
export function nextStop(dir: 1 | -1) {
  const stops = scrollStops();
  const y = window.scrollY;
  if (dir > 0) return stops.find((s) => s > y + 8) ?? document.documentElement.scrollHeight;
  return [...stops].reverse().find((s) => s < y - 8) ?? 0;
}

/** Document-y for an in-page anchor like '#about'. */
export function anchorTop(hash: string) {
  if (hash === '#top') return 0;
  const el = document.getElementById(hash.slice(1));
  return el ? el.getBoundingClientRect().top + window.scrollY - NAV_OFFSET : null;
}

export const isTyping = (e: KeyboardEvent) =>
  (e.target as HTMLElement | null)?.closest('input, textarea, select, [contenteditable="true"], [role="tablist"]') !== null;
