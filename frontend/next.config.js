const createNextIntlPlugin = require("next-intl/plugin");
const { withSentryConfig } = require("@sentry/nextjs");

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable React strict mode
  reactStrictMode: true,

  // Image optimization
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "replicate.delivery",
      },
      {
        protocol: "https",
        hostname: "*.replicate.delivery",
      },
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
      },
      {
        protocol: "https",
        hostname: "*.up.railway.app",
      },
      {
        protocol: "https",
        hostname: "picsum.photos",
      },
      {
        protocol: "https",
        hostname: "*.ideogram.ai",
      },
    ],
  },

  // Environment variables exposed to the browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
};

module.exports = withSentryConfig(withNextIntl(nextConfig), {
  // Sentry organisation and project (used for source map uploads to Sentry)
  org: process.env.SENTRY_ORG || "a-stats",
  project: process.env.SENTRY_PROJECT || "a-stats-content",

  // Only print logs for uploading source maps in CI
  silent: !process.env.CI,

  // Upload larger source maps for accurate stack traces
  widenClientFileUpload: true,

  // Hide source maps from the browser bundle
  hideSourceMaps: true,

  // Suppress tree-shaking warnings from the Sentry SDK logger
  disableLogger: true,

  // Skip source map upload if DSN is not configured
  sourcemaps: {
    disable: !process.env.NEXT_PUBLIC_SENTRY_DSN,
  },
});
