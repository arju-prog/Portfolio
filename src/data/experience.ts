// Experience — the centre of the site. Every claim here comes from resume.pdf;
// the leadership stories restate résumé bullets in STAR form — add your own specifics.
import type { Architecture } from './architecture';

export type Star = { title: string; situation: string; task: string; action: string; result: string };

export type Experience = {
  id: string;
  kind: 'work' | 'education' | 'side-quest';
  role: string;
  org: string;
  period: string;
  current?: boolean;
  model: string; // Blender diorama: public/props/<model>.glb + .png
  summary: string;
  impact?: { value: string; label: string }[];
  built: string[]; // what I did, résumé bullets
  architecture?: Architecture;
  leadership?: Star[];
  stack?: string[];
};

export const experience: Experience[] = [
  {
    id: 'evaratus',
    kind: 'work',
    role: 'Founding Member of Technical Staff (Intern)',
    org: 'Evaratus',
    period: 'Nov 2025 — Present',
    current: true,
    model: 'evaratus_lab',
    summary:
      'Building the reinforcement-learning environments, tool-use infrastructure and graders used to train and evaluate LLM-based AI agents.',
    impact: [
      { value: '30+', label: 'Multi-agent RL environments' },
      { value: '1 TB+', label: 'Structured data behind the tool-use API' },
      { value: '5', label: 'Enterprise data sources' },
      { value: 'Teams', label: 'Led through planning, design & reviews' },
    ],
    built: [
      'Built 30+ multi-agent reinforcement-learning environments in Python, including multi-app environments where agents complete workflows spanning several enterprise tools — used to train and evaluate LLM-based AI agents.',
      'Engineered a tool-use API over 1 TB+ of structured data from 5 enterprise sources, letting agents query state and execute long-horizon actions inside reproducible Docker containers.',
      'Designed task suites, reward functions and automated verifiers, pairing LLM-as-judge grading with programmatic checks to score agent trajectories against a standardized benchmark.',
      'Led multiple engineering teams through task planning, technical design and code reviews, mentoring teammates on simulation and grading design.',
    ],
    architecture: {
      title: 'Agent training & evaluation platform',
      caption: 'How data, environments and graders fit together. Select a component to see what I built there.',
      nodes: [
        { id: 'sources', label: '5 enterprise sources', sub: 'structured data', kind: 'source', col: 0, row: 0,
          detail: 'Structured data from five enterprise tools — the raw state agents will work against.' },
        { id: 'corpus', label: 'Structured data', sub: '1 TB+', kind: 'store', col: 1, row: 0,
          detail: 'Over a terabyte of structured data from the five sources — the state agents query and act on.' },
        { id: 'api', label: 'Tool-use API', sub: 'query state · act', kind: 'service', col: 2, row: 0,
          detail: 'The interface agents use to query state across 1 TB+ of data and take actions in the environment.' },
        { id: 'docker', label: 'Docker sandboxes', sub: 'reproducible', kind: 'service', col: 3, row: 0,
          detail: 'Long-horizon actions execute inside reproducible Docker containers, so every episode starts from a known state.' },
        { id: 'tasks', label: 'Task suites', sub: 'multi-app workflows', kind: 'source', col: 0, row: 1,
          detail: 'Task suites I designed — including workflows that span several enterprise tools.' },
        { id: 'envs', label: '30+ RL environments', sub: 'Python', kind: 'process', col: 1, row: 1,
          detail: 'Multi-agent reinforcement-learning environments, including multi-app environments, built in Python.' },
        { id: 'agent', label: 'LLM agent', sub: 'under training / eval', kind: 'agent', col: 2, row: 1,
          detail: 'The LLM-based agent being trained and evaluated. It works through tasks by calling the tool-use API.' },
        { id: 'traj', label: 'Trajectories', sub: 'actions + outcomes', kind: 'store', col: 2, row: 2,
          detail: 'Every step the agent takes is recorded as a trajectory to be graded.' },
        { id: 'verify', label: 'Verifiers', sub: 'LLM-as-judge + programmatic', kind: 'process', col: 3, row: 2,
          detail: 'Automated verifiers pairing LLM-as-judge grading with programmatic checks.' },
        { id: 'reward', label: 'Rewards & benchmark', sub: 'standardized score', kind: 'output', col: 4, row: 2,
          detail: 'Reward functions and a standardized benchmark score — the signal used to train and compare agents.' },
      ],
      edges: [
        { from: 'sources', to: 'corpus' },
        { from: 'corpus', to: 'api' },
        { from: 'api', to: 'docker', label: 'actions' },
        { from: 'tasks', to: 'envs' },
        { from: 'envs', to: 'agent', label: 'episodes' },
        { from: 'agent', to: 'api', label: 'tool calls' },
        { from: 'agent', to: 'traj' },
        { from: 'traj', to: 'verify' },
        { from: 'verify', to: 'reward' },
        { from: 'reward', to: 'agent', label: 'reward signal', dashed: true },
      ],
    },
    leadership: [
      {
        title: 'Leading engineers through the build',
        situation: 'Building 30+ environments meant several engineers working in parallel on simulations, tasks and graders.',
        task: 'Keep the work planned, the designs coherent and the quality consistent across teams.',
        action: 'Led task planning and technical design, ran code reviews, and mentored teammates on simulation and grading design.',
        result: 'Multiple teams shipped environments against a shared design and grading approach.',
      },
      {
        title: 'Grading agents you can trust',
        situation: 'Agent trajectories are long and open-ended — hard to score with rules alone.',
        task: 'Make evaluation both nuanced and reliable.',
        action: 'Designed task suites, reward functions and verifiers that pair LLM-as-judge grading with programmatic checks.',
        result: 'Agent trajectories scored against a standardized benchmark.',
      },
    ],
    stack: ['Python', 'Docker', 'LLM-as-judge', 'Reinforcement learning', 'Multi-agent orchestration', 'Data pipelines'],
  },
  {
    id: 'scaler',
    kind: 'education',
    role: 'Bachelor + Master of Science in Computer Science',
    org: 'Scaler School of Technology',
    period: 'Aug 2024 — Jul 2028',
    model: 'scaler_campus',
    summary: 'CGPA 7.63 / 10. Member of the AI/ML Club and NlogN — The Competitive Programming Club.',
    built: [],
  },
  {
    id: 'bits',
    kind: 'education',
    role: 'B.Sc. Computer Science (dual degree with Scaler)',
    org: 'BITS Pilani',
    period: 'Aug 2024 — Jul 2027',
    model: 'bits_campus',
    summary: 'CGPA 8.79 / 10.',
    built: [],
  },
  {
    id: 'cp',
    kind: 'side-quest',
    role: 'Competitive Programmer',
    org: 'CodeChef · Codeforces',
    period: 'Ongoing',
    model: 'codechef_trophy',
    summary: 'CodeChef 3★ (peak rating 1615) and Codeforces Pupil.',
    built: [],
  },
  {
    id: 'buildverse',
    kind: 'side-quest',
    role: 'Hackathon Participant',
    org: 'BuildVerse — Scaler × HackWithIndia',
    period: 'May 2025',
    model: 'hackathon_laptop',
    summary: 'Participated in the BuildVerse Hackathon by Scaler School of Technology & HackWithIndia.',
    built: [],
  },
];

export const work = experience.filter((e) => e.kind === 'work');
export const background = experience.filter((e) => e.kind !== 'work');
