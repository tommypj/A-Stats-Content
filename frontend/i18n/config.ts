export const locales = ["en", "ro", "es", "de", "fr"] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = "en";

export const localeNames: Record<Locale, string> = {
  en: "English",
  ro: "Română",
  es: "Español",
  de: "Deutsch",
  fr: "Français",
};

export const localeFlags: Record<Locale, string> = {
  en: "🇺🇸",
  ro: "🇷🇴",
  es: "🇪🇸",
  de: "🇩🇪",
  fr: "🇫🇷",
};
