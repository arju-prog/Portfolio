'use client';

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import FigureViewer from './FigureViewer';
import type { FigureViewerEngine, ViewerMode } from '@/lib/viewer';

type Model = { model: string; title: string; sub?: string };

const ModelDialogContext = createContext<((m: Model) => void) | null>(null);

/** Open any Blender diorama in the shared 3D dialog. */
export function useModelDialog() {
  const open = useContext(ModelDialogContext);
  if (!open) throw new Error('useModelDialog must be used inside <ModelDialogProvider>');
  return open;
}

const MODES: { id: ViewerMode; label: string }[] = [
  { id: 'real', label: 'Real' },
  { id: 'anime', label: 'Anime' },
  { id: 'manga', label: 'Manga' },
];

// One <dialog> and one WebGL viewer for every "Inspect 3D" button on the page.
// The viewer only exists while the dialog is open.
export default function ModelDialogProvider({ children }: { children: ReactNode }) {
  const [current, setCurrent] = useState<Model | null>(null);
  const [mode, setMode] = useState<ViewerMode>('real');
  const dialogRef = useRef<HTMLDialogElement>(null);
  const engineRef = useRef<FigureViewerEngine | null>(null);
  const returnFocus = useRef<HTMLElement | null>(null);

  const open = useCallback((m: Model) => {
    returnFocus.current = document.activeElement as HTMLElement | null;
    setCurrent(m);
  }, []);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (current && !dialog.open) dialog.showModal();
    if (!current && dialog.open) dialog.close();
  }, [current]);

  const close = () => {
    setCurrent(null);
    returnFocus.current?.focus();
  };

  return (
    <ModelDialogContext.Provider value={open}>
      {children}
      <dialog
        ref={dialogRef}
        className="model-dialog"
        aria-labelledby="model-dialog-title"
        onClose={close}
        onClick={(e) => {
          if (e.target === dialogRef.current) close();
        }}
      >
        {current && (
          <div className="model-dialog__body">
            <header className="model-dialog__head">
              <div>
                {current.sub && <p className="eyebrow">{current.sub}</p>}
                <h2 id="model-dialog-title">{current.title}</h2>
              </div>
              <button type="button" className="icon-btn" onClick={close} aria-label="Close">✕</button>
            </header>
            <div className="model-dialog__stage">
              <div className="speedlines" aria-hidden="true" />
              <FigureViewer src={`/props/${current.model}.glb`} mode={mode} zoom autoRotate engineRef={engineRef} />
            </div>
            <footer className="model-dialog__foot">
              <div className="seg" role="radiogroup" aria-label="Render style">
                {MODES.map((m) => (
                  <button key={m.id} type="button" role="radio" aria-checked={mode === m.id} onClick={() => setMode(m.id)}>
                    {m.label}
                  </button>
                ))}
              </div>
              <button type="button" className="btn btn--sm" onClick={() => engineRef.current?.resetView()}>Reset view</button>
              <p className="hint">Drag to rotate · scroll or pinch to zoom · Esc to close</p>
            </footer>
          </div>
        )}
      </dialog>
    </ModelDialogContext.Provider>
  );
}
