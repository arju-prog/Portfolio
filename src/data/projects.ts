// Projects (from resume.pdf), each with a Blender diorama and an architecture sketch.
import type { Architecture } from './architecture';

export type Project = {
  id: string;
  model: string; // Blender diorama: public/props/<model>.glb + .png
  title: string;
  period: string;
  summary: string;
  highlights: string[];
  stack: string[];
  architecture: Architecture;
  live?: string;
  source?: string;
};

export const projects: Project[] = [
  {
    id: 'lightup',
    model: 'lightup_phone',
    title: 'Light Up',
    period: 'Nov 2025 — Present',
    summary: 'A full-stack real-time communication app on the MERN stack.',
    highlights: [
      'Messaging, file & image sharing and video calls via GetStream.io.',
      'Friend-request system, real-time notifications and JWT-based authentication securing all API routes.',
    ],
    stack: ['React.js', 'Node.js', 'Express.js', 'MongoDB', 'GetStream.io', 'JWT'],
    source: 'https://github.com/arju-prog', // TODO: link the Light Up repo + live demo
    architecture: {
      title: 'Light Up — system',
      caption: 'MERN app with GetStream.io for real-time messaging and calls.',
      nodes: [
        { id: 'client', label: 'React client', sub: 'web app', kind: 'source', col: 0, row: 0, detail: 'React.js front end for chat, file sharing, calls and friends.' },
        { id: 'api', label: 'Express API', sub: 'Node.js · JWT', kind: 'service', col: 1, row: 0, detail: 'REST API on Node.js + Express; JWT-based authentication secures every route.' },
        { id: 'db', label: 'MongoDB', sub: 'users · friends', kind: 'store', col: 2, row: 0, detail: 'Stores users, friend requests and app data.' },
        { id: 'social', label: 'Friends & notifications', sub: 'real-time', kind: 'process', col: 2, row: 1, detail: 'Friend-request system with real-time notifications.' },
        { id: 'stream', label: 'GetStream.io', sub: 'chat · files · video', kind: 'service', col: 1, row: 1, detail: 'Messaging, file & image sharing and video calls are powered by GetStream.io.' },
      ],
      edges: [
        { from: 'client', to: 'api', label: 'REST' },
        { from: 'api', to: 'db' },
        { from: 'api', to: 'social' },
        { from: 'client', to: 'stream', label: 'real-time' },
      ],
    },
  },
  {
    id: 'imdb',
    model: 'imdb_reel',
    title: 'IMDb Sentiment Analysis',
    period: 'May 2025',
    summary: 'An NLP sentiment classifier trained on 50,000 IMDb movie reviews.',
    highlights: [
      'Preprocessed text with tokenization and stop-word removal (NLTK).',
      'Trained and compared several classification models — 89% test accuracy with Logistic Regression.',
    ],
    stack: ['Python', 'Pandas', 'NumPy', 'Scikit-learn', 'NLTK'],
    source: 'https://github.com/arju-prog',
    architecture: {
      title: 'Sentiment pipeline',
      caption: 'From raw reviews to the best-performing classifier.',
      nodes: [
        { id: 'data', label: '50,000 reviews', sub: 'IMDb', kind: 'source', col: 0, row: 0, detail: '50,000 labelled IMDb movie reviews.' },
        { id: 'prep', label: 'Preprocessing', sub: 'NLTK', kind: 'process', col: 1, row: 0, detail: 'Tokenization and stop-word removal with NLTK.' },
        { id: 'models', label: 'Model comparison', sub: 'Scikit-learn', kind: 'process', col: 2, row: 0, detail: 'Several classification models trained and compared.' },
        { id: 'best', label: 'Logistic Regression', sub: '89% test accuracy', kind: 'output', col: 3, row: 0, detail: 'The best model: 89% accuracy on the held-out test set.' },
      ],
      edges: [
        { from: 'data', to: 'prep' },
        { from: 'prep', to: 'models' },
        { from: 'models', to: 'best' },
      ],
    },
  },
  {
    id: 'portfolio',
    model: 'manga_portfolio',
    title: 'This portfolio',
    period: '2026',
    summary: 'A manga-styled portfolio whose 3D dioramas and effects are generated from code.',
    highlights: [
      'Every 3D object is a Python script run headless in Blender, exported as Draco-compressed glTF.',
      'Next.js static site with a Three.js viewer, an SVG architecture renderer and an opt-in Play mode with Web Audio sound.',
    ],
    stack: ['Next.js', 'TypeScript', 'Three.js', 'Blender (Python)', 'Web Audio'],
    source: 'https://github.com/arju-prog',
    architecture: {
      title: 'Asset & render pipeline',
      caption: 'Assets are code: scripts in, static site out.',
      nodes: [
        { id: 'scripts', label: 'Blender scripts', sub: 'Python', kind: 'source', col: 0, row: 0, detail: 'Each diorama and relic is a Python script using a shared modelling kit.' },
        { id: 'assets', label: 'glTF + sprites', sub: 'Draco · ink renders', kind: 'store', col: 1, row: 0, detail: 'Headless Blender exports compressed GLB models and ink-outlined PNG sprites.' },
        { id: 'next', label: 'Next.js', sub: 'static export', kind: 'service', col: 2, row: 0, detail: 'Content is server-rendered to static HTML; interactive parts hydrate on the client.' },
        { id: 'three', label: 'Three.js viewer', sub: 'real · anime · manga', kind: 'process', col: 3, row: 0, detail: 'Loads the GLBs lazily and renders them with PBR, toon or ink shading.' },
        { id: 'play', label: 'Play mode', sub: 'opt-in effects', kind: 'output', col: 3, row: 1, detail: 'Canvas effects and synthesised Web Audio sound, off by default.' },
      ],
      edges: [
        { from: 'scripts', to: 'assets' },
        { from: 'assets', to: 'next' },
        { from: 'next', to: 'three' },
        { from: 'next', to: 'play' },
      ],
    },
  },
];
