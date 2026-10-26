// Chapter 01 — the centre of the site. Server component; interactive parts are client islands.
import ArchitectureDiagram from './ArchitectureDiagram';
import Leadership from './Leadership';
import SafeImg from '@/components/layout/SafeImg';
import SectionHead from '@/components/layout/SectionHead';
import Treasure from '@/components/play/Treasure';
import Inspect3D from '@/components/three/Inspect3D';
import { background, work, type Experience as Xp } from '@/data/experience';

const KIND_LABEL: Record<Xp['kind'], string> = { work: 'Work', education: 'Education', 'side-quest': 'Side quest' };

function CaseStudy({ xp }: { xp: Xp }) {
  const anchor = `xp-${xp.id}`;
  return (
    <article className="case" id={anchor} aria-labelledby={`${anchor}-title`}>
      <header className="case__head panel" data-clone data-stop>
        <Inspect3D model={xp.model} title={xp.org} sub={xp.role} className="case__diorama" label={`Inspect the ${xp.org} diorama in 3D`}>
          <SafeImg src={`/props/${xp.model}.png`} />
          <span className="case__diorama-cta">Inspect 3D</span>
        </Inspect3D>
        <div className="case__intro">
          <p className="eyebrow">
            {xp.current && <span className="badge">Current</span>} {KIND_LABEL[xp.kind]} · {xp.period}
          </p>
          <h3 id={`${anchor}-title`}>{xp.org}</h3>
          <p className="case__role">{xp.role}</p>
          <p className="case__summary">{xp.summary}</p>
          <nav className="case__tabs" aria-label={`${xp.org} sections`}>
            <a href={`#${anchor}-built`}>What I built</a>
            {xp.architecture && <a href={`#${anchor}-arch`}>Architecture</a>}
            {xp.leadership && <a href={`#${anchor}-lead`}>Leadership</a>}
          </nav>
        </div>
        {xp.impact && (
          <dl className="metrics">
            {xp.impact.map((m) => (
              <div key={m.label} className="metric">
                <dd>{m.value}</dd>
                <dt>{m.label}</dt>
              </div>
            ))}
          </dl>
        )}
        <Treasure id="t-work" className="treasure--case" />
      </header>

      <section id={`${anchor}-built`} className="case__block" aria-labelledby={`${anchor}-built-h`}>
        <h4 id={`${anchor}-built-h`} className="block-title"><span>A</span> What I built</h4>
        <div className="panel built">
          <ol className="built__list">
            {xp.built.map((b) => <li key={b}>{b}</li>)}
          </ol>
          {xp.stack && <ul className="chips">{xp.stack.map((s) => <li key={s}>{s}</li>)}</ul>}
        </div>
      </section>

      {xp.architecture && (
        <section id={`${anchor}-arch`} className="case__block" aria-labelledby={`${anchor}-arch-h`}>
          <h4 id={`${anchor}-arch-h`} className="block-title"><span>B</span> Architecture</h4>
          <div className="panel">
            <ArchitectureDiagram arch={xp.architecture} />
          </div>
        </section>
      )}

      {xp.leadership && (
        <section id={`${anchor}-lead`} className="case__block" aria-labelledby={`${anchor}-lead-h`}>
          <h4 id={`${anchor}-lead-h`} className="block-title"><span>C</span> Leadership &amp; behaviour <small>STAR</small></h4>
          <Leadership stories={xp.leadership} />
        </section>
      )}
    </article>
  );
}

export default function Experience() {
  return (
    <section className="section" id="experience" data-stop>
      <SectionHead chapter="01" title="Experience" jp="経験" sub="What I build, how it’s architected, and how I work with a team." />
      {work.map((xp) => <CaseStudy key={xp.id} xp={xp} />)}

      <h3 className="subhead" id="background">Education &amp; side quests</h3>
      <ul className="background">
        {background.map((xp) => (
          <li key={xp.id} className="mini panel" data-clone>
            <Inspect3D model={xp.model} title={xp.org} sub={xp.role} className="mini__diorama" label={`Inspect the ${xp.org} diorama in 3D`}>
              <SafeImg src={`/props/${xp.model}.png`} loading="lazy" />
            </Inspect3D>
            <div>
              <p className="eyebrow">{KIND_LABEL[xp.kind]} · {xp.period}</p>
              <h4>{xp.org}</h4>
              <p className="mini__role">{xp.role}</p>
              <p className="mini__summary">{xp.summary}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
