'use client';

import { useEffect, useRef, useState } from 'react';
import { TREASURES, usePlay } from './PlayProvider';
import SafeImg from '@/components/layout/SafeImg';
import { profile } from '@/data/profile';
import { sfx } from '@/lib/sfx';

// Treasure counter + the reward panel once every doubloon is found.
export default function TreasureReward() {
  const { found } = usePlay();
  const [open, setOpen] = useState(false);
  const announced = useRef(false);
  const all = found.size === TREASURES.length;

  useEffect(() => {
    if (all && !announced.current) {
      announced.current = true;
      setOpen(true);
      sfx.chime();
      setTimeout(sfx.coins, 200);
    }
  }, [all]);

  if (found.size === 0) return null;

  return (
    <>
      <p className="treasure-count" aria-live="polite">
        <SafeImg src="/props/gold_coin.png" />
        <span>{found.size} / {TREASURES.length}</span>
      </p>
      {open && (
        <div className="reward panel" role="dialog" aria-label="Treasure found">
          <SafeImg className="reward__chest" src="/props/treasure_chest.png" />
          <p className="reward__label">Sic Parvis Magna</p>
          <h3>All treasure found!</h3>
          <p>You followed the compass to the end. Your reward: the collector’s-edition résumé.</p>
          <div className="actions">
            <a className="btn btn--ink" href={profile.resumeUrl} download>Claim résumé</a>
            <button type="button" className="btn" onClick={() => setOpen(false)}>Close</button>
          </div>
        </div>
      )}
    </>
  );
}
