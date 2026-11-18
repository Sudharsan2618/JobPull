/** @type {import('next').NextConfig} */

// The Next dev server proxies /api/* to the FastAPI backend so the browser makes
// same-origin calls (no CORS). Override the target with BACKEND_ORIGIN in
// .env.local when the backend runs elsewhere.
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN || 'http://localhost:8000';

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      { source: '/api/:path*', destination: `${BACKEND_ORIGIN}/api/:path*` },
    ];
  },
};

export default nextConfig;
