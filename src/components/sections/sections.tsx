// Static sections — server components with small client islands.
import ContactForm from './ContactForm';
import SectionHead from '@/components/layout/SectionHead';
import PlayToggle from '@/components/play/PlayToggle';
import Sticker from '@/components/play/Sticker';
import Treasure from '@/components/play/Treasure';
import { achievements, languages, profile, skills, socials, tools } from '@/data/profile';
import { vars } from '@/lib/format';

export function Nav() {
  return (
    <header className="nav">
      <a className="skip-link" href="#experience">Skip to experience</a>
      <a className="nav__logo" href="#top" data-nav>{profile.firstName}<span>{profile.nameJp}</span></a>
      <nav aria-label="Sections" className="nav__links">
        <a href="#experience" data-nav>Experience</a>
        <a href="#projects" data-nav>Projects</a>
        <a href="#skills" data-nav>Skills</a>
        <a href="#contact" data-nav>Contact</a>
      </nav>
      <div className="nav__end">
        <PlayToggle />
        <a className="btn btn--ink btn--sm nav__resume" href={profile.resumeUrl} target="_blank" rel="noopener noreferrer">Résumé</a>
      </div>
    </header>
  );
}

export function Skills() {
  return (
    <section className="section" id="skills" data-stop>
      <SectionHead chapter="03" title="Skills" jp="戦闘力" sub="The stack I fight with, and the side quests along the way." />
      <div className="skills">
        <div className="panel panel--ink">
          <h3 className="panel__title">Power levels</h3>
          <ul className="levels">
            {skills.map((s) => (
              <li key={s.name}>
                <span className="levels__name">{s.name}<small>{s.detail}</small></span>
                <span className="meter" aria-hidden="true"><span style={vars({ '--v': `${s.level}%` })} /></span>
                <b aria-label={`${s.level} out of 100`}>{s.level}</b>
              </li>
            ))}
          </ul>
        </div>
        <div className="skills__side">
          <div className="panel">
            <Sticker id="apple_of_eden" className="sticker--corner" />
            <Treasure id="t-skills" className="treasure--skills" />
            <h3 className="panel__title">Achievements</h3>
            <ul className="achievements">
              {achievements.map((a) => (
                <li key={a.title}><strong>{a.title}</strong><span>{a.detail}</span></li>
              ))}
            </ul>
          </div>
          <div className="panel">
            <h3 className="panel__title">Languages</h3>
            <ul className="chips">{languages.map((l) => <li key={l}>{l}</li>)}</ul>
            <h3 className="panel__title panel__title--gap">AI tools &amp; platforms</h3>
            <ul className="chips">{tools.map((l) => <li key={l}>{l}</li>)}</ul>
          </div>
        </div>
      </div>
    </section>
  );
}

export function Contact() {
  return (
    <section className="section section--ink" id="contact" data-stop>
      <div className="speedlines speedlines--ink" aria-hidden="true" />
      <Sticker id="ramen_bowl" className="sticker--ramen" />
      <SectionHead chapter="04" title="Contact" jp="連絡" sub="Hiring for AI or full-stack work, or want to collaborate? My inbox is open." />
      <div className="contact">
        <ul className="socials">
          {socials.map((s, i) => (
            <li key={s.label} className={`bubble bubble--${i % 2 ? 'right' : 'left'}`}>
              <a href={s.url} target={s.url.startsWith('http') || s.url.endsWith('.pdf') ? '_blank' : undefined} rel="noopener noreferrer">
                <strong>{s.label}</strong>
                <span>{s.handle}</span>
              </a>
            </li>
          ))}
        </ul>
        <div className="contact__form">
          <Treasure id="t-contact" className="treasure--contact" />
          <ContactForm />
        </div>
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="footer">
      <p className="footer__next">To be continued <span>つづく</span></p>
      <p>© {new Date().getFullYear()} {profile.name} · Built with Next.js, Three.js &amp; Blender</p>
      <p><a href="/?intro">↺ Replay the intro</a></p>
      <p className="footer__note">Play mode’s anime & game references are fan-made for a personal portfolio; all characters belong to their creators.</p>
    </footer>
  );
}
