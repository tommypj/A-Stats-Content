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
  // Only match locale-aware routes (marketing & auth pages).
  // Exclude dashboard app routes which don't use i18n.
  matcher: [
    "/((?!api|_next|_vercel|.*\\..*|dashboard|outlines|articles|images|social|analytics|knowledge|projects|settings|help|admin|content-calendar|keyword-research|billing|invite|bulk|agency|portal).*)",
  ],
};
