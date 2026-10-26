'use client';

import { useState, type FormEvent } from 'react';
import { profile } from '@/data/profile';

// No backend needed: composes a mailto: link. Swap the submit handler for
// a Route Handler / Formspree / Resend call if you want server-side delivery.
export default function ContactForm() {
  const [sent, setSent] = useState(false);

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const name = String(data.get('name') ?? '');
    const subject = `Portfolio message from ${name}`;
    const body = `${data.get('message')}\n\n— ${name} (${data.get('email')})`;
    window.location.href = `mailto:${profile.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    setSent(true);
  }

  return (
    <form className="form panel" onSubmit={onSubmit}>
      <div className="field">
        <label htmlFor="msg-name">Name</label>
        <input id="msg-name" name="name" autoComplete="name" required />
      </div>
      <div className="field">
        <label htmlFor="msg-email">Email</label>
        <input id="msg-email" name="email" type="email" autoComplete="email" required />
      </div>
      <div className="field">
        <label htmlFor="msg-body">Message</label>
        <textarea id="msg-body" name="message" rows={5} required />
      </div>
      <button className="btn btn--ink" type="submit">Send message</button>
      {sent && <p className="form__note" role="status">Opening your mail app…</p>}
    </form>
  );
}
