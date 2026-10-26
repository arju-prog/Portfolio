'use client';

import { useCallback, type CSSProperties } from 'react';
import { usePlay, type TreasureId } from './PlayProvider';
import SafeImg from '@/components/layout/SafeImg';
import * as fxl from '@/lib/fx';
import { sfx } from '@/lib/sfx';

// A half-hidden doubloon for Drake's treasure hunt (Play mode only).
// Click it, or dig near it with the compass — the compass finds it through the PlayProvider registry.
export default function Treasure({ id, style, className = '' }: { id: TreasureId; style?: CSSProperties; className?: string }) {
  const { play, fx, equipped, found, collect, registerTreasure } = usePlay();
  const ref = useCallback((el: HTMLButtonElement | null) => registerTreasure(id, el), [id, registerTreasure]);

  if (!play || found.has(id)) return null;

  return (
    <button
      ref={ref}
      type="button"
      className={`treasure ${className}`}
      style={style}
      aria-label="Hidden treasure"
      onClick={(e) => {
        if (equipped) return; // the equipped power handles clicks
        const r = e.currentTarget.getBoundingClientRect();
        sfx.coins();
        sfx.chime();
        if (fx) fxl.treasure(fx, { x: r.left + r.width / 2, y: r.top + r.height / 2 });
        collect(id);
      }}
    >
      <SafeImg src="/props/gold_coin.png" />
    </button>
  );
}
