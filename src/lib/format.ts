import type { CSSProperties } from 'react';

export const initials = (name: string) =>
  name.split(/\s+/).map((word) => word[0]).join('').slice(0, 2).toUpperCase();

export const cx = (...classes: (string | false | null | undefined)[]) => classes.filter(Boolean).join(' ');

// Typed helper for passing CSS custom properties through `style`.
export const vars = (values: Record<`--${string}`, string | number>) => values as CSSProperties;
