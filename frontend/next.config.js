const createNextIntlPlugin = require("next-intl/plugin");
const { withSentryConfig } = require("@sentry/nextjs");

// INFRA-M2: Validate NEXT_PUBLIC_API_URL at build time to catch misconfiguration early
const apiUrl = process.env.NEXT_PUBLIC_API_URL;
if (!apiUrl) {
  console.warn(
    "\n  WARNING: NEXT_PUBLIC_API_URL is not set. " +
    "All API calls will fall back to http://localhost:8000.\n" +
    "  Set NEXT_PUBLIC_API_URL in your Vercel environment variables.\n"
  );
}
if (apiUrl && apiUrl.includes("localhost") && process.env.VERCEL_ENV === "production") {
  throw new Error(
    "NEXT_PUBLIC_API_URL contains \"localhost\" but VERCEL_ENV is \"production\". " +
    "Set NEXT_PUBLIC_API_URL to your Railway backend URL."
  );
}

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
