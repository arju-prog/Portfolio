'use client';

import { useEffect, useRef, useState, type ImgHTMLAttributes } from 'react';

// <img> that hides itself if the file is missing — including when the load fails
// before React hydrates (when onError alone would never fire). Used for Blender
// renders that may not have been built yet.
export default function SafeImg({ className = '', alt = '', ...props }: ImgHTMLAttributes<HTMLImageElement>) {
  const ref = useRef<HTMLImageElement>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    const img = ref.current;
    if (img && img.complete && img.naturalWidth === 0) setMissing(true);
  }, [props.src]);

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      ref={ref}
      alt={alt}
      className={`${className} ${missing ? 'is-missing' : ''}`.trim()}
      onError={() => setMissing(true)}
      onLoad={() => setMissing(false)}
      {...props}
    />
  );
}
