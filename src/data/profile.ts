// Who I am — identity, skills, achievements and links (from resume.pdf).

export const profile = {
  name: 'Arjun Aggarwal',
  firstName: 'Arjun',
  lastName: 'Aggarwal',
  nameJp: 'アルジュン',
  title: 'AI & Full-Stack Engineer',
  tagline:
    'I build reinforcement-learning environments that train and evaluate LLM agents — and ship full-stack products end to end.',
  location: 'India',
  email: 'arjun2019aggarwal@gmail.com',
  resumeUrl: '/resume.pdf',
  github: 'https://github.com/arju-prog',
  linkedin: 'https://www.linkedin.com/in/arjun-agg06',
};

// Skills as manga "power levels" (0–100 — tune to taste).
export const skills: { name: string; level: number; detail: string }[] = [
  { name: 'Python', level: 92, detail: 'RL environments, data pipelines, Pandas, NumPy' },
  { name: 'Generative AI', level: 90, detail: 'LLM integration, RAG, multi-agent orchestration, agentic workflows' },
  { name: 'JavaScript / React', level: 86, detail: 'React.js, Node.js, Express.js, Tailwind CSS, REST APIs' },
  { name: 'C++ / DSA', level: 85, detail: 'Competitive programming — CodeChef 3★, Codeforces Pupil' },
  { name: 'ML & NLP', level: 82, detail: 'Scikit-learn, NLTK, data analysis' },
  { name: 'Databases', level: 78, detail: 'MongoDB, MySQL, vector databases' },
  { name: 'DevOps', level: 76, detail: 'Docker, Kubernetes, CI/CD, GitHub Actions, Datadog, Mixpanel' },
];

export const languages = ['C++', 'Java', 'JavaScript', 'Python', 'SQL', 'HTML/CSS'];

export const tools = ['Claude', 'ChatGPT', 'Claude Code', 'Git', 'GitHub', 'Google Colab'];

export const achievements: { title: string; detail: string }[] = [
  { title: 'CodeChef 3★', detail: 'Peak rating 1615' },
  { title: 'Codeforces Pupil', detail: 'Competitive programming' },
  { title: 'BuildVerse Hackathon', detail: 'Scaler × HackWithIndia, May 2025' },
  { title: 'Clubs', detail: 'AI/ML Club · NlogN CP Club' },
];

export const socials: { label: string; handle: string; url: string }[] = [
  { label: 'Email', handle: profile.email, url: `mailto:${profile.email}` },
  { label: 'LinkedIn', handle: 'in/arjun-agg06', url: profile.linkedin },
  { label: 'GitHub', handle: 'arju-prog', url: profile.github },
  { label: 'Résumé', handle: 'Download PDF', url: profile.resumeUrl },
];
