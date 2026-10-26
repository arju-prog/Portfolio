import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Static export → plain HTML/CSS/JS in ./out, hostable on Cloudflare Pages (or any static host).
  output: 'export',
};

export default nextConfig;
