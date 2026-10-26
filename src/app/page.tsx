import Experience from '@/components/experience/Experience';
import Intro from '@/components/intro/Intro';
import Armory from '@/components/play/Armory';
import PlayProvider from '@/components/play/PlayProvider';
import Projects from '@/components/projects/Projects';
import Hero from '@/components/sections/Hero';
import { Contact, Footer, Nav, Skills } from '@/components/sections/sections';
import ModelDialogProvider from '@/components/three/ModelDialog';

export default function Home() {
  return (
    <PlayProvider>
      <ModelDialogProvider>
        <Nav />
        <main id="main">
          <Hero />
          <Experience />
          <Projects />
          <Skills />
          <Armory />
          <Contact />
        </main>
        <Footer />
        <Intro />
      </ModelDialogProvider>
    </PlayProvider>
  );
}
