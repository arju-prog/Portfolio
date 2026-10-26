'use client';

import { useRef, type CSSProperties, type MouseEvent } from 'react';
import { usePlay } from './PlayProvider';
import SafeImg from '@/components/layout/SafeImg';
import { relics } from '@/data/play/relics';
import * as fxl from '@/lib/fx';
import { sfx } from '@/lib/sfx';

const SOUNDS: Record<string, () => void> = {
  ramen_bowl: sfx.chime,
  devil_fruit: sfx.boing,
  apple_of_eden: sfx.schwing,
  map_scroll: sfx.dig,
  drake_ring: sfx.coins,
  grimoire: sfx.clang,
  guardian_shield: sfx.thump,
  leaf_headband: sfx.whoosh,
};

// A Blender-rendered relic slapped onto the page like a manga sticker (Play mode only).
export default function Sticker({ id, style, className = '' }: { id: string; style?: CSSProperties; className?: string }) {
  const { play, fx, equipped } = usePlay();
  const ref = useRef<HTMLButtonElement>(null);
  const lastHover = useRef(0);
  const relic = relics.find((r) => r.id === id);

  if (!play) return null;

  function onHover() {
    if (performance.now() - lastHover.current < 1000) return;
    lastHover.current = performance.now();
    (SOUNDS[id] ?? sfx.hover)();
  }

  function onClick(e: MouseEvent) {
    if (equipped) return; // the equipped power handles clicks
    (SOUNDS[id] ?? sfx.click)();
    if (fx) fxl.stickerPop(fx, { x: e.clientX, y: e.clientY }, id);
    ref.current?.animate(
      [{ transform: 'rotate(0) scale(1)' }, { transform: 'rotate(-12deg) scale(1.25)' }, { transform: 'rotate(6deg) scale(0.95)' }, { transform: 'none' }],
      { duration: 500, easing: 'ease-out' },
    );
  }

  return (
    <button ref={ref} type="button" className={`sticker ${className}`} style={style} onClick={onClick} onPointerEnter={onHover} title={relic?.name} aria-label={relic?.name ?? id}>
      <SafeImg src={`/props/${id}.png`} loading="lazy" />
    </button>
  );
}
