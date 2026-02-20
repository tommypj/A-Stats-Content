import { getRequestConfig } from "next-intl/server";
import { locales, defaultLocale, type Locale } from "./config";

export default getRequestConfig(async ({ locale }) => {
  // Validate that the incoming locale is valid
  const validLocale = locales.includes(locale as Locale) ? locale : defaultLocale;

  return {
    messages: (await import(`./messages/${validLocale}.json`)).default,
  };
});
