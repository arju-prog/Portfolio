// Play-mode navigation "journeys": each scroll is carried by an anime/game interaction.
// The scroll itself starts immediately and always yields to user input (see motion.ts);
// the animation simply rides along with it.
import * as fxl from './fx';
import { anchorTop, nextStop, prefersReducedMotion, tweenScroll } from './motion';
import { sfx } from './sfx';

let riding = false;

/** Wukong slides down (dir 1) / climbs up (dir -1) his staff to the next stop. */
export async function wukongRide(fx: fxl.FxLayer, dir: 1 | -1) {
  if (riding) return;
  const target = nextStop(dir);
  const distance = Math.abs(target - window.scrollY);
  if (distance < 4) return;
  if (prefersReducedMotion()) return void tweenScroll(target);
  riding = true;
  const duration = Math.max(750, Math.min(1400, distance * 0.55));
  fxl.wukongRide(fx, dir, duration);
  sfx.whoosh(0.3);
  sfx.slide(duration / 1000);
  const completed = await tweenScroll(target, duration);
  if (completed) {
    if (dir > 0) {
      sfx.thump();
      sfx.gong();
    } else {
      sfx.pop();
    }
  }
  riding = false;
}

/** Luffy's arm grabs the page while it scrolls to an anchor. */
export function luffyGoTo(fx: fxl.FxLayer, hash: string, from: fxl.Pt) {
  const target = anchorTop(hash);
  if (target === null) return;
  history.pushState(null, '', hash);
  const duration = Math.max(600, Math.min(1100, Math.abs(target - window.scrollY) * 0.35));
  if (!prefersReducedMotion()) {
    fxl.armGrab(fx, from, duration);
    sfx.boing();
  }
  void tweenScroll(target, duration);
}

/** Kratos throws the Leviathan Axe; the page rides to the top and the axe returns. */
export function kratosToTop(fx: fxl.FxLayer, home: fxl.Pt, onCaught: () => void) {
  if (prefersReducedMotion()) {
    onCaught();
    return void tweenScroll(0);
  }
  const flight = Math.max(600, Math.min(1000, window.scrollY * 0.25));
  fxl.axeBoomerang(fx, home, flight, () => {
    sfx.thump();
    onCaught();
  });
  sfx.whoosh(0.45);
  setTimeout(sfx.ice, 480);
  void tweenScroll(0, 500 + flight);
}

/** Ezio's Leap of Faith: eagle cry, a swooping eagle and a quick dive back to the top. */
export function leapOfFaith(fx: fxl.FxLayer, onFlash: (on: boolean) => void) {
  sfx.eagle();
  if (prefersReducedMotion()) return void tweenScroll(0);
  fxl.eagleSwoop(fx);
  onFlash(true);
  setTimeout(() => onFlash(false), 1000);
  setTimeout(() => sfx.whoosh(0.5), 200);
  void tweenScroll(0, 650);
}
