'use client';

import { useEffect, useRef, useState } from 'react';
import { usePlay } from './PlayProvider';
import SafeImg from '@/components/layout/SafeImg';
import * as fxl from '@/lib/fx';
import { kratosToTop, leapOfFaith, luffyGoTo, wukongRide } from '@/lib/journeys';
import { isTyping, prefersReducedMotion } from '@/lib/motion';
import { sfx } from '@/lib/sfx';

/*
  Play-mode navigation interactions. Native scrolling keys (arrows, Space, PageUp/Down,
  Home/End) are never intercepted — only these letter shortcuts:
    J / K      Wukong rides down / climbs up his staff to the next section
    L          Ezio's Leap of Faith back to the top
    hold E     Eagle Vision
  plus: nav links (Luffy's arm), the axe button (Kratos), kunai scroll progress,
  Shadow Clones on experience entries, and Asta's slash over chapter titles.
*/
export default function Interactions() {
  const { fx } = usePlay();
  const [scrolled, setScrolled] = useState(false);
  const [axeHome, setAxeHome] = useState(true);
  const [leap, setLeap] = useState(false);
  const kunaiRef = useRef<HTMLDivElement>(null);
  const axeRef = useRef<HTMLButtonElement>(null);

  // keyboard shortcuts
  useEffect(() => {
    if (!fx) return;
    let eagle: ReturnType<typeof fxl.eagleVision> | null = null;
    const onDown = (e: KeyboardEvent) => {
      if (isTyping(e) || e.metaKey || e.ctrlKey || e.altKey || e.repeat) return;
      const key = e.key.toLowerCase();
      if (key === 'j') void wukongRide(fx, 1);
      else if (key === 'k') void wukongRide(fx, -1);
      else if (key === 'l') leapOfFaith(fx, setLeap);
      else if (key === 'e' && !eagle) {
        sfx.whoosh(0.5);
        eagle = fxl.eagleVision(fx, () => null);
      }
    };
    const onUp = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'e' && eagle) {
        eagle.stop();
        eagle = null;
      }
    };
    window.addEventListener('keydown', onDown);
    window.addEventListener('keyup', onUp);
    return () => {
      window.removeEventListener('keydown', onDown);
      window.removeEventListener('keyup', onUp);
      eagle?.stop();
    };
  }, [fx]);

  // Luffy's arm on in-page nav links (the scroll starts immediately; the arm rides along)
  useEffect(() => {
    if (!fx) return;
    const onClick = (e: MouseEvent) => {
      const link = (e.target as Element).closest<HTMLAnchorElement>('a[data-nav]');
      if (!link || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
      e.preventDefault();
      const r = link.getBoundingClientRect();
      luffyGoTo(fx, link.getAttribute('href')!, { x: r.left + r.width / 2, y: r.bottom });
    };
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, [fx]);

  // kunai scroll progress + floating buttons after the hero
  useEffect(() => {
    let raf = 0;
    const update = () => {
      raf = 0;
      const max = document.documentElement.scrollHeight - window.innerHeight;
      kunaiRef.current?.style.setProperty('--p', String(max > 0 ? window.scrollY / max : 0));
      setScrolled(window.scrollY > window.innerHeight * 0.6);
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    update();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

  // Decorations triggered as content scrolls into view (purely visual, silent, never hide content):
  // Asta's slash across chapter titles, and a Shadow Clone greeting each experience entry.
  useEffect(() => {
    if (!fx || prefersReducedMotion()) return;
    const io = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        io.unobserve(entry.target);
        const el = entry.target as HTMLElement;
        if (el.matches('.sec-head')) {
          const title = el.querySelector('h2');
          if (title) fxl.headingSlash(fx, title.getBoundingClientRect());
        } else {
          const r = el.getBoundingClientRect();
          // only greet entries that are actually on screen, and keep the clone below the nav
          if (r.top < 60 || r.top > window.innerHeight - 80) continue;
          fxl.clonePop(fx, { x: Math.min(window.innerWidth - 70, r.right - 40), y: r.top + 50 });
        }
      }
    }, { threshold: 0.5 });
    document.querySelectorAll('.sec-head, [data-clone]').forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [fx]);

  function throwAxe() {
    const r = axeRef.current?.getBoundingClientRect();
    if (!r || !axeHome || !fx) return;
    setAxeHome(false);
    kratosToTop(fx, { x: r.left + r.width / 2, y: r.top + r.height / 2 }, () => setAxeHome(true));
  }

  return (
    <>
      <div ref={kunaiRef} className="kunai-track" aria-hidden="true">
        <SafeImg className="kunai-track__kunai" src="/props/kunai.png" />
      </div>

      <div className={`journey ${scrolled ? 'is-scrolled' : ''}`}>
        <button
          type="button"
          className="journey__btn"
          onClick={() => fx && void wukongRide(fx, 1)}
          aria-label="Ride down to the next section with Wukong (J)"
          title="Ride down with Wukong — J"
        >
          <SafeImg src="/props/golden_headband.png" />
          <span aria-hidden="true">J</span>
        </button>
        <button
          ref={axeRef}
          type="button"
          className={`journey__btn ${axeHome ? '' : 'is-thrown'}`}
          onClick={throwAxe}
          aria-label="Back to top — Kratos throws the Leviathan Axe"
          title="Back to top (L = Leap of Faith)"
        >
          <SafeImg src="/props/leviathan_axe.png" />
          <span aria-hidden="true">↑</span>
        </button>
      </div>

      <div className={`leap-flash ${leap ? 'is-on' : ''}`} aria-hidden="true" />
    </>
  );
}
