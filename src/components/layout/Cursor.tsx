'use client';

import { useEffect, useRef, useState } from 'react';

type State = 'default' | 'hover' | 'grab' | 'text';

const HOVER = 'a, button, [role="button"], [role="switch"], [role="radio"], summary, label, select';
const TEXT = 'input, textarea, [contenteditable="true"]';

/*
  Round custom cursor: an ink dot that tracks the pointer exactly, plus a ring that follows with
  a little lag. The ring grows over clickable things, turns dashed over draggable 3D canvases,
  and gets out of the way in text fields (the native caret shows there).

  Only for fine pointers (mouse/trackpad) — touch devices keep their normal behaviour.
  Hidden while a Play-mode weapon is equipped (that power has its own cursor) and while a
  modal <dialog> is open (dialogs sit in the browser's top layer, above any z-index).
*/
export default function Cursor() {
  const [enabled, setEnabled] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const ring = useRef<HTMLDivElement>(null);
  const dot = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mq = window.matchMedia('(hover: hover) and (pointer: fine)');
    const update = () => setEnabled(mq.matches);
    update();
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);

  useEffect(() => {
    if (!enabled || !root.current || !ring.current || !dot.current) return;
    const html = document.documentElement;
    const el = root.current;
    const ringEl = ring.current;
    const dotEl = dot.current;
    const lag = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 1 : 0.22;
    let x = -100;
    let y = -100;
    let rx = x;
    let ry = y;
    let raf = 0;
    let state: State = 'default';

    html.classList.add('has-cursor');
    const place = (node: HTMLElement, px: number, py: number) => {
      node.style.transform = `translate3d(${px}px, ${py}px, 0) translate(-50%, -50%)`;
    };
    const follow = () => {
      rx += (x - rx) * lag;
      ry += (y - ry) * lag;
      place(ringEl, rx, ry);
      raf = Math.abs(x - rx) + Math.abs(y - ry) > 0.2 ? requestAnimationFrame(follow) : 0;
    };
    const setState = (next: State) => {
      if (next !== state) el.dataset.state = state = next;
    };

    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== 'mouse') return;
      x = e.clientX;
      y = e.clientY;
      place(dotEl, x, y);
      el.classList.remove('is-hidden');
      if (!raf) raf = requestAnimationFrame(follow);
      const target = e.target as Element | null;
      if (target?.closest(TEXT)) setState('text');
      else if (target?.closest(HOVER)) setState('hover');
      else if (target?.closest('canvas:not(.fx-layer):not(.intro__canvas), .node')) setState('grab');
      else setState('default');
    };
    const onDown = () => el.classList.add('is-down');
    const onUp = () => el.classList.remove('is-down');
    const onLeave = () => el.classList.add('is-hidden');

    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerdown', onDown);
    window.addEventListener('pointerup', onUp);
    document.documentElement.addEventListener('mouseleave', onLeave);
    return () => {
      cancelAnimationFrame(raf);
      html.classList.remove('has-cursor');
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerdown', onDown);
      window.removeEventListener('pointerup', onUp);
      document.documentElement.removeEventListener('mouseleave', onLeave);
    };
  }, [enabled]);

  if (!enabled) return null;
  return (
    <div ref={root} className="cursor is-hidden" data-state="default" aria-hidden="true">
      <div ref={ring} className="cursor__ring" />
      <div ref={dot} className="cursor__dot" />
    </div>
  );
}
