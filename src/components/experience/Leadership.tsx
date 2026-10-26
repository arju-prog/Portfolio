// Behavioural stories in STAR form, as manga panels — all visible, nothing hidden behind toggles.
import type { Star } from '@/data/experience';

const STEPS = [
  { key: 'situation', label: 'Situation' },
  { key: 'task', label: 'Task' },
  { key: 'action', label: 'Action' },
  { key: 'result', label: 'Result' },
] as const;

export default function Leadership({ stories }: { stories: Star[] }) {
  return (
    <ol className="stars">
      {stories.map((s, i) => (
        <li key={s.title} className="star panel">
          <h5>
            <span className="star__no" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span>
            {s.title}
          </h5>
          <dl className="star__body">
            {STEPS.map((step) => (
              <div key={step.key} className={`star__step star__step--${step.key}`}>
                <dt>{step.label}</dt>
                <dd>{s[step.key]}</dd>
              </div>
            ))}
          </dl>
        </li>
      ))}
    </ol>
  );
}
