'use client';

import Treasure from '@/components/play/Treasure';
import FigureViewer from '@/components/three/FigureViewer';
import Inspect3D from '@/components/three/Inspect3D';
import { work } from '@/data/experience';
import { profile } from '@/data/profile';

// Experience-first cover: who I am, what I do now, and the proof — beside a live 3D diorama of the current role.
export default function Hero() {
  const current = work[0];
  return (
    <section className="hero" id="top" data-stop>
      <div className="hero__copy">
        <p className="hero__vol"><span>Vol. 01</span> {profile.title}</p>
        <h1 className="hero__title">
          {profile.firstName}
          <span className="hero__jp" aria-hidden="true">{profile.nameJp}</span>
        </h1>
        <p className="hero__last">{profile.lastName}</p>
        <p className="hero__tag">{profile.tagline}</p>

        <a className="now panel" href={`#xp-${current.id}`} data-nav>
          <span className="badge">Now</span>
          <strong>{current.role}</strong>
          <span>@ {current.org} · {current.period}</span>
        </a>

        {current.impact && (
          <dl className="metrics metrics--hero">
            {current.impact.slice(0, 3).map((m) => (
              <div key={m.label} className="metric">
                <dd>{m.value}</dd>
                <dt>{m.label}</dt>
              </div>
            ))}
          </dl>
        )}

        <div className="actions">
          <a className="btn btn--ink" href="#experience" data-nav>See my experience</a>
          <a className="btn" href={profile.resumeUrl} target="_blank" rel="noopener noreferrer">Résumé (PDF)</a>
          <a className="btn" href="#contact" data-nav>Contact</a>
        </div>
      </div>

      <div className="hero__panel">
        <div className="speedlines" aria-hidden="true" />
        <div className="tone tone--corner" aria-hidden="true" />
        <FigureViewer src={`/props/${current.model}.glb`} mode="real" autoRotate className="viewer--hero" />
        <div className="caption">
          <small>Now building</small>
          <strong>{current.org}</strong>
          <span>RL environments for LLM agents</span>
        </div>
        <Inspect3D model={current.model} title={current.org} sub={current.role} className="btn btn--sm hero__inspect" />
        <Treasure id="t-hero" className="treasure--hero" />
      </div>
    </section>
  );
}
