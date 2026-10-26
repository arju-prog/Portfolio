'use client';

import { useEffect, useRef, useState } from 'react';
import { TREASURES, usePlay } from './PlayProvider';
import { characters } from '@/data/play/characters';
import { weapons, type WeaponId } from '@/data/play/arsenal';
import * as fxl from '@/lib/fx';
import { sfx } from '@/lib/sfx';

type Pt = fxl.Pt;

// The Arsenal: equip an item from the dock → it becomes your cursor and clicks trigger its power.
export default function Arsenal() {
  const { fx, equipped, equip, muted, setMuted, found, collect, nearestTreasure } = usePlay();
  const [dockOpen, setDockOpen] = useState(false);
  const [heat, setHeat] = useState('');
  const cursorRef = useRef<HTMLDivElement>(null);
  const needleRef = useRef<HTMLImageElement>(null);
  const busy = useRef(false); // e.g. axe is out
  const weapon = weapons.find((w) => w.id === equipped) ?? null;

  useEffect(() => {
    weapons.forEach((w) => fxl.sprite(w.id));
    ['jingu_bang', 'gold_coin', 'treasure_chest', 'compass_needle'].forEach(fxl.sprite);
  }, []);

  // ── pointer handling ──
  useEffect(() => {
    if (!equipped || !fx) return;
    const layer = fx;
    let down = false;
    let path: Pt[] = [];
    let charge: ReturnType<typeof fxl.rasengan> | null = null;
    let chargeSound: ReturnType<typeof sfx.charge> | null = null;
    let eagle: ReturnType<typeof fxl.eagleVision> | null = null;
    let holdTimer = 0;

    const ignored = (e: PointerEvent) =>
      (e.target as Element).closest('.arsenal, .nav, dialog, .play-toggle') !== null || e.button !== 0;

    const onMove = (e: PointerEvent) => {
      const p = { x: e.clientX, y: e.clientY };
      if (cursorRef.current) {
        cursorRef.current.style.transform = `translate(${p.x}px, ${p.y}px)`;
        cursorRef.current.dataset.touch = e.pointerType === 'touch' ? 'true' : 'false';
      }
      if (equipped === 'compass' && needleRef.current) {
        const target = nearestTreasure(p);
        if (target) {
          const angle = Math.atan2(target.at.y - p.y, target.at.x - p.x) + Math.PI / 2;
          needleRef.current.style.transform = `translate(-50%, -50%) rotate(${angle}rad)`;
          const d = target.distance;
          setHeat(d < 180 ? 'HOT!' : d < 600 ? 'Warm' : 'Cold');
        } else {
          setHeat('All found!');
        }
      }
      if (!down) return;
      if (equipped === 'demon_slayer_sword') path.push(p);
      if (charge) charge.move(p);
    };

    const onDown = (e: PointerEvent) => {
      if (ignored(e)) return;
      const p = { x: e.clientX, y: e.clientY };
      down = true;
      switch (equipped) {
        case 'golden_headband':
          sfx.whoosh(0.15);
          setTimeout(() => { sfx.boom(); sfx.gong(); }, 140);
          fxl.staffSlam(layer, p);
          break;
        case 'demon_slayer_sword':
          path = [p];
          sfx.whoosh(0.2);
          break;
        case 'kunai':
          charge = fxl.rasengan(layer, p);
          chargeSound = sfx.charge();
          break;
        case 'ofa_glove':
          sfx.crackle(0.5);
          sfx.boom();
          fxl.smash(layer, p);
          break;
        case 'straw_hat':
          sfx.boing();
          setTimeout(sfx.thump, 130);
          fxl.gumPistol(layer, p);
          break;
        case 'leviathan_axe':
          if (busy.current) return;
          busy.current = true;
          cursorRef.current?.classList.add('is-empty');
          sfx.whoosh(0.3);
          setTimeout(sfx.ice, 280);
          setTimeout(() => sfx.whoosh(0.3), 1250);
          fxl.axeThrow(layer, p, () => {
            busy.current = false;
            cursorRef.current?.classList.remove('is-empty');
            sfx.thump();
          });
          break;
        case 'hidden_blade':
          holdTimer = window.setTimeout(() => {
            sfx.whoosh(0.6);
            eagle = fxl.eagleVision(layer, () => null);
          }, 350);
          break;
        case 'compass': {
          const hit = nearestTreasure(p);
          if (hit && hit.distance < 90) {
            sfx.coins();
            sfx.chime();
            fxl.treasure(layer, hit.at);
            collect(hit.id);
          } else {
            sfx.dig();
            fxl.dig(layer, p);
          }
          break;
        }
      }
    };

    const onUp = (e: PointerEvent) => {
      if (!down) return;
      down = false;
      const p = { x: e.clientX, y: e.clientY };
      if (equipped === 'demon_slayer_sword') {
        const trimmed = path.filter((_, i) => i % 2 === 0 || i === path.length - 1);
        fxl.slash(layer, trimmed.length > 3 ? trimmed : [p]);
        sfx.whoosh(0.25);
        setTimeout(sfx.clang, 90);
      }
      if (charge) {
        chargeSound?.stop();
        sfx.burst();
        charge.release();
        charge = null;
      }
      if (equipped === 'hidden_blade') {
        clearTimeout(holdTimer);
        if (eagle) {
          eagle.stop();
          eagle = null;
        } else {
          sfx.schwing();
          fxl.bladeStrike(layer, p);
        }
      }
    };

    // While charging, raise the Rasengan's pitch.
    const meter = window.setInterval(() => charge && chargeSound?.set(charge.level), 50);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') equip(null);
    };

    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerdown', onDown);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerdown', onDown);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onUp);
      window.removeEventListener('keydown', onKey);
      clearInterval(meter);
      clearTimeout(holdTimer);
      chargeSound?.stop();
      eagle?.stop();
    };
  }, [fx, equipped, equip, collect, nearestTreasure]);

  const owner = weapon ? characters.find((c) => c.id === weapon.owner) : null;

  return (
    <>
      <div className="eagle-overlay" aria-hidden="true" />

      {weapon && (
        <div ref={cursorRef} className={`weapon-cursor weapon-cursor--${weapon.id}`} aria-hidden="true">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={`/props/${weapon.id}.png`} alt="" />
          {weapon.id === 'compass' && (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img ref={needleRef} className="weapon-cursor__needle" src="/props/compass_needle.png" alt="" />
              <span className="weapon-cursor__heat">{heat}</span>
            </>
          )}
        </div>
      )}

      <aside className={`arsenal ${dockOpen ? 'is-open' : ''}`} aria-label="Arsenal">
        {dockOpen && (
          <div className="arsenal__panel" role="dialog" aria-label="Choose an item">
            <div className="arsenal__head">
              <strong>Arsenal <small>武器庫</small></strong>
              <button type="button" className="arsenal__mute" aria-pressed={!muted} onClick={() => setMuted(!muted)}>
                Sound {muted ? 'off' : 'on'}
              </button>
            </div>
            <ul className="arsenal__grid">
              {weapons.map((w) => {
                const who = characters.find((c) => c.id === w.owner);
                return (
                  <li key={w.id}>
                    <button
                      type="button"
                      className={`arsenal__item ${equipped === w.id ? 'is-on' : ''}`}
                      aria-pressed={equipped === w.id}
                      onClick={() => equip(equipped === w.id ? null : (w.id as WeaponId))}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={`/props/${w.id}.png`} alt="" loading="lazy" />
                      <span className="arsenal__name">{w.power}</span>
                      <span className="arsenal__owner">{who?.name}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
        <div className="arsenal__bar">
          <button type="button" className="arsenal__toggle" aria-expanded={dockOpen} onClick={() => { sfx.click(); setDockOpen((v) => !v); }}>
            {weapon ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={`/props/${weapon.id}.png`} alt="" />
            ) : (
              <span aria-hidden="true">⚔</span>
            )}
            <span>Arsenal</span>
          </button>
          {weapon && (
            <p className="arsenal__status">
              <strong>{weapon.power}</strong> <small>{owner?.name}</small>
              <span>{weapon.hint}{weapon.id === 'compass' ? ` · found ${found.size}/${TREASURES.length}` : ''}</span>
            </p>
          )}
          {weapon && (
            <button type="button" className="arsenal__off" onClick={() => equip(null)} aria-label="Unequip (Esc)">✕</button>
          )}
        </div>
      </aside>
    </>
  );
}
