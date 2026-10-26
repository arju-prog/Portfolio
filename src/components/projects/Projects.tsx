// Chapter 02 — projects as compact case studies (server component).
import ArchitectureDiagram from '@/components/experience/ArchitectureDiagram';
import SafeImg from '@/components/layout/SafeImg';
import SectionHead from '@/components/layout/SectionHead';
import Sticker from '@/components/play/Sticker';
import Treasure from '@/components/play/Treasure';
import Inspect3D from '@/components/three/Inspect3D';
import { projects } from '@/data/projects';

export default function Projects() {
  return (
    <section className="section" id="projects" data-stop>
      <Sticker id="map_scroll" className="sticker--head" />
      <SectionHead chapter="02" title="Projects" jp="作品" sub="Things I’ve built outside work — each with its architecture." />
      <ul className="projects">
        {projects.map((p, i) => (
          <li key={p.id} id={`proj-${p.id}`} className="project panel" data-stop>
            {i === 1 && <Treasure id="t-projects" className="treasure--project" />}
            <div className="project__top">
              <Inspect3D model={p.model} title={p.title} sub={p.period} className="project__diorama" label={`Inspect the ${p.title} diorama in 3D`}>
                <SafeImg src={`/props/${p.model}.png`} loading="lazy" />
              </Inspect3D>
              <div>
                <p className="eyebrow">{p.period}</p>
                <h3>{p.title}</h3>
                <p className="project__summary">{p.summary}</p>
              </div>
            </div>
            <ul className="project__points">{p.highlights.map((h) => <li key={h}>{h}</li>)}</ul>
            <ul className="chips">{p.stack.map((t) => <li key={t}>{t}</li>)}</ul>
            <details className="project__arch">
              <summary>Architecture</summary>
              <ArchitectureDiagram arch={p.architecture} />
            </details>
            <div className="project__links">
              {p.live && <a className="btn btn--ink btn--sm" href={p.live} target="_blank" rel="noopener noreferrer">Live demo</a>}
              {p.source && <a className="btn btn--sm" href={p.source} target="_blank" rel="noopener noreferrer">GitHub</a>}
              <Inspect3D model={p.model} title={p.title} sub={p.period} />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
