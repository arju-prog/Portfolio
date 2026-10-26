'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import Arsenal from './Arsenal';
import Interactions from './Interactions';
import TreasureReward from './TreasureReward';
import type { WeaponId } from '@/data/play/arsenal';
import { FxLayer, type Pt } from '@/lib/fx';
import { sfx } from '@/lib/sfx';

/*
  The anime/game layer, opt-in. With Play mode off (the default) none of it renders:
  no key bindings, no effects canvas, no sounds, no floating widgets.

  Everything play-related flows through this context — components never query the DOM
  for each other or talk through window events.
*/

export const TREASURES = ['t-hero', 't-work', 't-projects', 't-skills', 't-contact'] as const;
export type TreasureId = (typeof TREASURES)[number];

type PlayCtx = {
  play: boolean;
  setPlay: (on: boolean) => void;
  fx: FxLayer | null;
  equipped: WeaponId | null;
  equip: (id: WeaponId | null) => void;
  muted: boolean;
  setMuted: (muted: boolean) => void;
  found: ReadonlySet<TreasureId>;
  collect: (id: TreasureId) => void;
  /** Treasures register their element so the compass can point at and dig for them. */
  registerTreasure: (id: TreasureId, el: HTMLElement | null) => void;
  /** Nearest unfound treasure to a viewport point (for the compass). */
  nearestTreasure: (p: Pt) => { id: TreasureId; at: Pt; distance: number } | null;
};

const PlayContext = createContext<PlayCtx | null>(null);

export function usePlay() {
  const ctx = useContext(PlayContext);
  if (!ctx) throw new Error('usePlay must be used inside <PlayProvider>');
  return ctx;
}

const PLAY_KEY = 'pf-play';
const TREASURE_KEY = 'pf-treasure';

export default function PlayProvider({ children }: { children: ReactNode }) {
  const [play, setPlayState] = useState(false);
  const [equipped, setEquipped] = useState<WeaponId | null>(null);
  const [muted, setMutedState] = useState(false);
  const [found, setFound] = useState<Set<TreasureId>>(new Set());
  const [fx, setFx] = useState<FxLayer | null>(null);
  const treasureEls = useRef(new Map<TreasureId, HTMLElement>());

  // restore persisted preferences
  useEffect(() => {
    setMutedState(sfx.muted);
    try {
      setPlayState(localStorage.getItem(PLAY_KEY) === '1');
      const saved = JSON.parse(sessionStorage.getItem(TREASURE_KEY) ?? '[]') as TreasureId[];
      setFound(new Set(saved.filter((t) => TREASURES.includes(t))));
    } catch {}
  }, []);

  // one effects canvas, created only while Play mode is on
  const canvasRef = useCallback((canvas: HTMLCanvasElement | null) => {
    setFx((prev) => {
      prev?.dispose();
      return canvas ? new FxLayer(canvas) : null;
    });
  }, []);

  // reflect state on <html> for the few document-level styles (cursor, play-only UI)
  useEffect(() => {
    const html = document.documentElement;
    html.dataset.play = play ? 'on' : 'off';
    if (equipped) html.dataset.weapon = equipped;
    else delete html.dataset.weapon;
  }, [play, equipped]);

  const setPlay = useCallback((on: boolean) => {
    setPlayState(on);
    if (!on) setEquipped(null);
    try {
      localStorage.setItem(PLAY_KEY, on ? '1' : '0');
    } catch {}
    if (on) sfx.equip();
  }, []);

  const equip = useCallback((id: WeaponId | null) => {
    setEquipped(id);
    if (id) sfx.equip();
  }, []);

  const setMuted = useCallback((value: boolean) => {
    sfx.setMuted(value);
    setMutedState(value);
  }, []);

  const collect = useCallback((id: TreasureId) => {
    setFound((prev) => {
      if (prev.has(id)) return prev;
      const next = new Set(prev).add(id);
      try {
        sessionStorage.setItem(TREASURE_KEY, JSON.stringify([...next]));
      } catch {}
      return next;
    });
  }, []);

  const registerTreasure = useCallback((id: TreasureId, el: HTMLElement | null) => {
    if (el) treasureEls.current.set(id, el);
    else treasureEls.current.delete(id);
  }, []);

  const nearestTreasure = useCallback(
    (p: Pt) => {
      let best: { id: TreasureId; at: Pt; distance: number } | null = null;
      for (const [id, el] of treasureEls.current) {
        if (found.has(id)) continue;
        const r = el.getBoundingClientRect();
        const at = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
        const distance = Math.hypot(at.x - p.x, at.y - p.y);
        if (!best || distance < best.distance) best = { id, at, distance };
      }
      return best;
    },
    [found],
  );

  const value = useMemo<PlayCtx>(
    () => ({ play, setPlay, fx, equipped, equip, muted, setMuted, found, collect, registerTreasure, nearestTreasure }),
    [play, setPlay, fx, equipped, equip, muted, setMuted, found, collect, registerTreasure, nearestTreasure],
  );

  return (
    <PlayContext.Provider value={value}>
      {children}
      {play && (
        <>
          <canvas ref={canvasRef} className="fx-layer" aria-hidden="true" />
          {fx && <Interactions />}
          {fx && <Arsenal />}
          <TreasureReward />
        </>
      )}
    </PlayContext.Provider>
  );
}
