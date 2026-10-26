'use client';

import { useEffect, useRef, useState, type RefObject } from 'react';
import type { FigureViewerEngine, ViewerMode, ViewerStatus } from '@/lib/viewer';

type Props = {
  src: string; // GLB url
  mode: ViewerMode;
  controls?: boolean;
  zoom?: boolean;
  autoRotate?: boolean;
  engineRef?: RefObject<FigureViewerEngine | null>;
  className?: string;
};

// React wrapper around the three.js engine. three is loaded lazily on first mount.
export default function FigureViewer({ src, mode, controls = true, zoom = false, autoRotate = true, engineRef, className }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engine = useRef<FigureViewerEngine | null>(null);
  const [status, setStatus] = useState<ViewerStatus | 'unsupported'>('loading');
  const latest = useRef({ src, mode, autoRotate });
  latest.current = { src, mode, autoRotate };

  useEffect(() => {
    let cancelled = false;
    import('@/lib/viewer')
      .then(({ FigureViewerEngine }) => {
        if (cancelled || !canvasRef.current) return;
        const e = new FigureViewerEngine(canvasRef.current, {
          controls,
          zoom,
          autoRotate: latest.current.autoRotate,
          onStatus: setStatus,
        });
        e.setMode(latest.current.mode);
        void e.show(latest.current.src);
        engine.current = e;
        if (engineRef) engineRef.current = e;
      })
      .catch((err) => {
        console.warn('3D viewer unavailable:', err);
        setStatus('unsupported');
      });

    // Stop rendering while off-screen.
    const io = new IntersectionObserver(([entry]) => engine.current?.setPaused(!entry.isIntersecting));
    if (canvasRef.current) io.observe(canvasRef.current);

    return () => {
      cancelled = true;
      io.disconnect();
      engine.current?.dispose();
      engine.current = null;
      if (engineRef) engineRef.current = null;
    };
    // The engine is created once; prop changes are pushed through the effects below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void engine.current?.show(src);
  }, [src]);

  useEffect(() => {
    engine.current?.setMode(mode);
  }, [mode]);

  useEffect(() => {
    engine.current?.setAutoRotate(autoRotate);
  }, [autoRotate]);

  return (
    <div className={`viewer ${className ?? ''}`} data-status={status}>
      <canvas ref={canvasRef} aria-label="Interactive 3D model — drag to rotate" />
      {status === 'loading' && <span className="viewer__msg">Loading model…</span>}
      {status === 'error' && <span className="viewer__msg">Model unavailable</span>}
      {status === 'unsupported' && <span className="viewer__msg">3D needs WebGL</span>}
    </div>
  );
}
