'use client';

import type { ReactNode } from 'react';
import { useModelDialog } from './ModelDialog';

// Opens a Blender diorama in the shared 3D dialog.
export default function Inspect3D({
  model,
  title,
  sub,
  className = 'btn btn--sm',
  children = 'Inspect 3D',
  label,
}: {
  model: string;
  title: string;
  sub?: string;
  className?: string;
  children?: ReactNode;
  label?: string;
}) {
  const open = useModelDialog();
  return (
    <button type="button" className={className} aria-label={label} onClick={() => open({ model, title, sub })}>
      {children}
    </button>
  );
}
