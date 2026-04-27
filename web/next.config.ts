import type { NextConfig } from "next"

const apiBaseUrl =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"

const isDevelopment = process.env.NODE_ENV !== "production"

const scriptPolicy = isDevelopment
  ? "'self' 'unsafe-inline' 'unsafe-eval'"
  : "'self' 'unsafe-inline'"

const cspDirectives = [
  "default-src 'self'",
  "base-uri 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "form-action 'self' https:",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  "style-src 'self' 'unsafe-inline'",
  `script-src ${scriptPolicy}`,
  `connect-src 'self' ${apiBaseUrl} https://vitals.vercel-insights.com`
]

if (!isDevelopment) {
  cspDirectives.push("upgrade-insecure-requests")
}

const csp = cspDirectives.join("; ")

const securityHeaders = [
  {
    key: "Content-Security-Policy",
    value: csp
  },
  {
    key: "Cross-Origin-Opener-Policy",
    value: "same-origin"
  },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
  },
  {
    key: "Referrer-Policy",
    value: "strict-origin-when-cross-origin"
  },
  {
    key: "X-Content-Type-Options",
    value: "nosniff"
  },
  {
    key: "X-DNS-Prefetch-Control",
    value: "off"
  },
  {
    key: "X-Frame-Options",
    value: "DENY"
  }
]

if (!isDevelopment) {
  securityHeaders.push({
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains; preload"
  })
}

const nextConfig: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: securityHeaders
      }
    ]
  }
}

export default nextConfig
