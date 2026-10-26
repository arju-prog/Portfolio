'use client';

import { useCallback, useEffect, useRef, useState, type MouseEvent } from 'react';
import { cast, welcomeLine } from '@/data/play/intro';
import { profile } from '@/data/profile';
import type { IntroEngine, IntroEvent } from '@/lib/intro';
import { sfx, signatureSound, unlockAudio } from '@/lib/sfx';

/*
  Opening sequence (~8s): the cast drops in, dances, presents the site and leaps away.

  Behaviour rules:
  - Shown once per browser session; `/?intro` replays it. Skipped for prefers-reduced-motion.
    The decision is made by an inline script in <head> before first paint (sets html[data-intro]),
    so the page never flashes before the intro, and the overlay never flashes on later visits.
  - Always skippable: Skip button, Esc / Enter / Space, or a click anywhere.
  - Sound is ON by default. Browsers only allow audio after the visitor interacts, so if it's
    blocked a "Tap for sound" prompt appears: the first click / key unlocks sound and the show
    keeps going (it does not skip). The Sound button turns it off.
  - The page underneath is fully rendered; scrolling unlocks the moment the intro ends.
*/

type Pop = { id: number; text: string; x: number; y: number; color?: string; big?: boolean };

export default function Intro() {
  const [active, setActive] = useState(true);
  const [leaving, setLeaving] = useState(false);
  const [progress, setProgress] = useState(0);
  const [started, setStarted] = useState(false);
  const [landed, setLanded] = useState<number[]>([]);
  const [pops, setPops] = useState<Pop[]>([]);
  const [beat, setBeat] = useState(-1);
  const [title, setTitle] = useState(false);
  const [exiting, setExiting] = useState(false);
  const [sound, setSound] = useState(true);
  const [locked, setLocked] = useState(false); // sound wanted, but the browser is blocking audio
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engine = useRef<IntroEngine | null>(null);
  const soundRef = useRef(true);
  const lockedRef = useRef(false);
  const popId = useRef(0);
  const ended = useRef(false);

  const finish = useCallback(() => {
    if (ended.current) return;
    ended.current = true;
    setLeaving(true);
    try {
      sessionStorage.setItem('pf-intro', '1');
    } catch {}
    setTimeout(() => {
      document.documentElement.dataset.intro = 'seen';
      engine.current?.dispose();
      engine.current = null;
      setActive(false);
      if (new URL(location.href).searchParams.has('intro')) history.replaceState(null, '', location.pathname + location.hash);
    }, 650);
  }, []);

  const pop = useCallback((p: Omit<Pop, 'id'>) => {
    const id = ++popId.current;
    setPops((list) => [...list, { ...p, id }]);
    setTimeout(() => setPops((list) => list.filter((x) => x.id !== id)), 1100);
  }, []);

  useEffect(() => {
    if (document.documentElement.dataset.intro !== 'show') {
      setActive(false);
      return;
    }
    let cancelled = false;

    // Sound on by default (unless the visitor muted the site before) — see if the browser lets us play.
    if (sfx.muted) {
      soundRef.current = false;
      setSound(false);
    } else {
      void unlockAudio().then((ok) => {
        if (cancelled || ok) return;
        lockedRef.current = true;
        setLocked(true);
      });
    }

    const onEvent = (e: IntroEvent) => {
      const s = soundRef.current && !lockedRef.current; // don't poke a blocked AudioContext
      switch (e.type) {
        case 'progress':
          setProgress(e.total ? e.loaded / e.total : 0);
          break;
        case 'start':
          setStarted(true);
          break;
        case 'land':
          setLanded((l) => [...l, e.index]);
          pop({ text: cast[e.index].short, x: e.at.x, y: e.at.y, color: cast[e.index].color });
          if (s) {
            sfx.thump();
            sfx.pop();
          }
          break;
        case 'beat':
          setBeat(e.n);
          if (s) {
            if (e.n % 2 === 0) sfx.thump();
            else sfx.pop();
          }
          break;
        case 'signature':
          // alternate heights so neighbouring sound effects don't collide
          pop({ text: cast[e.index].sfx, x: e.at.x, y: e.at.y - (e.index % 2 ? 80 : 20), color: cast[e.index].color, big: true });
          if (s) signatureSound[cast[e.index].id]?.();
          break;
        case 'shake':
          if (s) sfx.boom();
          break;
        case 'pose':
          setTitle(true);
          if (s) sfx.chime();
          break;
        case 'exit':
          setExiting(true);
          if (s) {
            sfx.whoosh(0.5);
            setTimeout(sfx.gong, 300);
          }
          break;
        case 'done':
          finish();
          break;
      }
    };
    import('@/lib/intro')
      .then(({ IntroEngine }) => {
        if (cancelled || !canvasRef.current) return;
        engine.current = new IntroEngine(canvasRef.current, cast, onEvent);
      })
      .catch(() => finish()); // no WebGL / chunk failed → straight to the site

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        skip();
      } else if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (lockedRef.current) unlock(); // first key press turns the sound on
        else skip();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => {
      cancelled = true;
      window.removeEventListener('keydown', onKey);
      engine.current?.dispose();
      engine.current = null;
    };
    // skip/finish/pop are stable callbacks
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function skip() {
    if (engine.current && !ended.current) {
      engine.current.skip(); // jump to the exit leap, which then finishes
      setTimeout(finish, 1300); // safety net
    } else {
      finish();
    }
  }

  /** Runs inside a click / key handler, which is what browsers require to start audio. */
  function unlock() {
    lockedRef.current = false;
    setLocked(false);
    soundRef.current = true;
    setSound(true);
    if (sfx.muted) sfx.setMuted(false);
    void unlockAudio().then((ok) => ok && sfx.equip());
  }

  function onOverlayClick() {
    if (lockedRef.current) unlock(); // first click = sound on, the show continues
    else skip();
  }

  function toggleSound(e: MouseEvent) {
    e.stopPropagation();
    if (lockedRef.current || !soundRef.current) {
      unlock();
      return;
    }
    soundRef.current = false;
    setSound(false);
  }

  if (!active) return null;

  return (
    <div
      className={`intro ${exiting ? 'is-exiting' : ''} ${leaving ? 'is-leaving' : ''} ${beat >= 0 && beat % 2 === 0 ? 'is-beat' : ''}`}
      role="dialog"
      aria-modal="true"
      aria-label={`Intro animation — ${profile.name}'s portfolio`}
      onClick={onOverlayClick}
    >
      <div className="intro__lines" aria-hidden="true" />
      <div className="intro__tone" aria-hidden="true" />

      <header className="intro__head">
        <p className="intro__presents">{profile.name} presents</p>
        <p className="intro__vol">Vol. 01 · Collector’s cast</p>
      </header>

      <canvas ref={canvasRef} className="intro__canvas" aria-hidden="true" />

      {!started && (
        <div className="intro__loading" aria-live="polite">
          <span>Assembling the cast…</span>
          <span className="intro__bar"><span style={{ width: `${Math.round(progress * 100)}%` }} /></span>
        </div>
      )}

      <ol className="intro__roll" aria-hidden="true">
        {cast.map((c, i) => (
          <li key={c.id} className={landed.includes(i) ? 'is-in' : ''}>{c.short}</li>
        ))}
      </ol>

      {pops.map((p) => (
        <span
          key={p.id}
          className={`intro__pop ${p.big ? 'intro__pop--big' : ''}`}
          style={{ left: p.x, top: p.y, ['--pop' as string]: p.color }}
          aria-hidden="true"
        >
          {p.text}
        </span>
      ))}

      {title && (
        <div className="intro__title">
          <p className="intro__bubble">{welcomeLine}</p>
          <h1>
            {profile.firstName} <span>{profile.lastName}</span>
          </h1>
          <p className="intro__role">{profile.title}</p>
        </div>
      )}

      {locked && (
        <button type="button" className="intro__unmute" onClick={(e) => { e.stopPropagation(); unlock(); }}>
          <span aria-hidden="true">🔊</span> Tap anywhere for sound
        </button>
      )}

      <div className="intro__controls" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="intro__btn" aria-pressed={sound && !locked} onClick={toggleSound}>
          {sound && !locked ? '♪ Sound on' : '♪ Sound off'}
        </button>
        <button type="button" className="intro__btn intro__btn--ink" onClick={skip} autoFocus>
          Skip intro →
        </button>
      </div>

      <div className="intro__wipe" aria-hidden="true" />
    </div>
  );
}
