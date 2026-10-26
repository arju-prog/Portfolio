'use client';

import { useState } from 'react';
import { usePlay } from './PlayProvider';

// The opt-in switch for the anime/game layer, plus a one-line cheat sheet when it turns on.
export default function PlayToggle() {
  const { play, setPlay } = usePlay();
  const [hint, setHint] = useState(false);

  return (
    <div className="play-toggle">
      <button
        type="button"
        role="switch"
        aria-checked={play}
        className="play-toggle__switch"
        onClick={() => {
          setPlay(!play);
          setHint(!play);
          if (!play) setTimeout(() => setHint(false), 6000);
        }}
        title="Anime & game interactions, effects and sound"
      >
        <span className="play-toggle__track" aria-hidden="true"><span /></span>
        <span>Play mode</span>
      </button>
      {hint && (
        <p className="play-toggle__hint" role="status">
          <kbd>J</kbd>/<kbd>K</kbd> ride with Wukong · <kbd>L</kbd> Leap of Faith · hold <kbd>E</kbd> Eagle Vision · ⚔ Arsenal bottom-left
        </p>
      )}
    </div>
  );
}
