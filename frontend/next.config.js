/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The whole app is client-rendered with no API routes, middleware, or
  // next/image usage, so a static export is the simplest, most predictable
  // thing to hand Netlify: a folder of plain files, no Next.js server needed.
  output: 'export',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
}

module.exports = nextConfig
