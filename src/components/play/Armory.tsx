'use client';

import { useEffect, useRef, useState } from 'react';
import { usePlay } from './PlayProvider';
import SafeImg from '@/components/layout/SafeImg';
import SectionHead from '@/components/layout/SectionHead';
import { weapons } from '@/data/play/arsenal';
import { characters } from '@/data/play/characters';
import { relics } from '@/data/play/relics';
import type { RingEngine } from '@/lib/ring';
import { sfx, signatureSound } from '@/lib/sfx';

// Play-mode side quest: every Blender relic on a draggable 3D ring + a sprite filmstrip.
// The section (and its WebGL context) only exists while Play mode is on.
export default function Armory() {
  const { play } = usePlay();
  return play ? <ArmoryRing /> : null;
}

function ArmoryRing() {
  const { equip, equipped } = usePlay();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engine = useRef<RingEngine | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [ready, setReady] = useState(true);

  useEffect(() => {
    let cancelled = false;
    import('@/lib/ring')
      .then(({ RingEngine }) => {
        if (cancelled || !canvasRef.current) return;
        engine.current = new RingEngine(canvasRef.current, relics.map((r) => r.id), (id) => {
          if (id) sfx.click();
          setSelected(id);
        });
      })
      .catch(() => setReady(false));
    const io = new IntersectionObserver(([entry]) => engine.current?.setPaused(!entry.isIntersecting));
    if (canvasRef.current) io.observe(canvasRef.current);
    return () => {
      cancelled = true;
      io.disconnect();
      engine.current?.dispose();
      engine.current = null;
    };
  }, []);

  useEffect(() => {
    engine.current?.select(selected);
  }, [selected]);

  const relic = relics.find((r) => r.id === selected);
  const owner = relic ? characters.find((c) => c.id === relic.owner) : null;
  const weapon = relic ? weapons.find((w) => w.id === relic.id) : null;

  return (
    <section className="section" id="armory" data-stop>
      <SectionHead chapter="Side quest" title="The Armory" jp="宝物庫" sub="Every relic here was modelled in Blender. Spin the ring, click a relic, and equip a power — then click anywhere on the page." />

      <div className="armory panel">
        <div className="speedlines" aria-hidden="true" />
        <canvas ref={canvasRef} className="armory__canvas" aria-label="3D relic carousel — drag to spin, click a relic" />
        {!ready && <p className="viewer__msg">3D needs WebGL</p>}

        <div className={`armory__card ${relic ? 'is-on' : ''}`} aria-live="polite">
          {relic ? (
            <>
              <p className="armory__owner">{owner ? `${owner.name} · ${owner.franchise}` : 'Extra'}</p>
              <h3>{relic.name}</h3>
              <p className="armory__jp">{relic.jp}</p>
              <p className="armory__lore">{relic.lore}</p>
              <div className="armory__actions">
                {weapon && (
                  <button type="button" className="btn btn--ink btn--sm" onClick={() => equip(equipped === weapon.id ? null : weapon.id)}>
                    {equipped === weapon.id ? 'Unequip' : `Equip · ${weapon.power}`}
                  </button>
                )}
                {owner && (
                  <button type="button" className="btn btn--sm" onClick={() => signatureSound[owner.id]?.()}>♪</button>
                )}
              </div>
            </>
          ) : (
            <p className="armory__hint">← Drag to spin · click a relic →</p>
          )}
        </div>

        <div className="armory__nav">
          <button type="button" className="btn btn--icon" aria-label="Previous relic" onClick={() => engine.current?.step(-1)}>←</button>
          <button type="button" className="btn btn--icon" aria-label="Next relic" onClick={() => engine.current?.step(1)}>→</button>
        </div>
      </div>

      <ul className="filmstrip" aria-label="All relics">
        {relics.map((r) => (
          <li key={r.id}>
            <button
              type="button"
              className={`filmstrip__item ${selected === r.id ? 'is-on' : ''}`}
              onClick={() => setSelected(r.id)}
              title={r.name}
            >
              <SafeImg src={`/props/${r.id}.png`} loading="lazy" />
              <span>{r.name}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
