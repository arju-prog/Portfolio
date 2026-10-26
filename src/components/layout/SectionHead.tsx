// Manga chapter title card. No hooks — usable from server and client components.
// Content is never hidden waiting for scroll observers: what renders is what you see.
export default function SectionHead({ chapter, title, jp, sub }: { chapter: string; title: string; jp: string; sub?: string }) {
  return (
    <header className="sec-head">
      <span className="sec-head__jp" aria-hidden="true">{jp}</span>
      <p className="sec-head__ch">{/^\d/.test(chapter) ? `Chapter ${chapter}` : chapter}</p>
      <h2>{title}</h2>
      {sub && <p className="sec-head__sub">{sub}</p>}
    </header>
  );
}
