import createMiddleware from "next-intl/middleware";
import { locales, defaultLocale } from "./i18n/config";

export default createMiddleware({
  // A list of all locales that are supported
  locales,

  // Used when no locale matches
  defaultLocale,

  // Don't redirect to locale-prefixed paths for the default locale
  localePrefix: "as-needed",
});

export const config = {
  // Match only internationalized pathnames
  matcher: [
    // Match all pathnames except for
    // - API routes (/api/...)
    // - Static files (/_next/static/..., /favicon.ico, etc.)
    // - Files with extensions (.png, .jpg, etc.)
    "/((?!api|_next|_vercel|.*\\..*).*)",
  ],
};
