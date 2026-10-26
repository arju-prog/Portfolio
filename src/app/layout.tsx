import type { Metadata, Viewport } from 'next';
import { Dela_Gothic_One, Zen_Kaku_Gothic_New } from 'next/font/google';
import type { ReactNode } from 'react';
import Cursor from '@/components/layout/Cursor';
import { profile } from '@/data/profile';
import '@/styles/base.css';
import '@/styles/layout.css';
import '@/styles/experience.css';
import '@/styles/play.css';
import '@/styles/intro.css';

const display = Dela_Gothic_One({ subsets: ['latin'], weight: '400', variable: '--font-display', preload: false });
const body = Zen_Kaku_Gothic_New({ subsets: ['latin'], weight: ['400', '500', '700', '900'], variable: '--font-body', preload: false });

export const metadata: Metadata = {
  title: `${profile.name} — ${profile.title}`,
  description: profile.tagline,
};

export const viewport: Viewport = {
  themeColor: '#f6f4ee',
};

// Decide before first paint whether the opening intro plays (once per session, `?intro` replays,
// never for reduced motion) so neither the page nor the overlay flashes.
const introGate = `(function(){var d=document.documentElement,s='seen';try{var force=new URLSearchParams(location.search).has('intro');var done=sessionStorage.getItem('pf-intro')==='1';var calm=matchMedia('(prefers-reduced-motion: reduce)').matches;s=force||(!done&&!calm)?'show':'seen'}catch(e){}d.dataset.intro=s})();`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    // data-intro / data-play are set on <html> by scripts, so its attributes differ from the server render
    <html lang="en" className={`${display.variable} ${body.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: introGate }} />
        <noscript>
          <style>{'.intro{display:none!important}html{overflow:auto!important}'}</style>
        </noscript>
      </head>
      <body>
        {children}
        <Cursor />
      </body>
    </html>
  );
}
