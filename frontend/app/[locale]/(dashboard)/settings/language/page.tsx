"use client";

import { useRouter, usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Check } from "lucide-react";
import { clsx } from "clsx";

import { locales, localeNames, localeFlags, type Locale } from "@/i18n/config";
import { useRequireAuth } from "@/lib/auth";

export default function LanguageSettingsPage() {
  const t = useTranslations("settings.language");
  const { isAuthenticated, isLoading: authLoading } = useRequireAuth();
  const currentLocale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  if (authLoading) return null;
  if (!isAuthenticated) return null;

  const handleLanguageChange = (newLocale: Locale) => {
    // Replace the current locale in the path with the new one
    const newPath = pathname.replace(`/${currentLocale}`, `/${newLocale}`);
    router.push(newPath);
  };

  return (
    <div className="card">
      <div className="p-6 border-b border-surface-tertiary">
        <h2 className="font-display text-lg font-semibold text-text-primary">
          {t("title")}
        </h2>
        <p className="mt-1 text-sm text-text-secondary">{t("description")}</p>
      </div>

      <div className="p-6">
        <div className="grid gap-3">
          {locales.map((locale) => {
            const isSelected = locale === currentLocale;

            return (
              <button
                key={locale}
                onClick={() => handleLanguageChange(locale)}
                className={clsx(
                  "flex items-center justify-between p-4 rounded-xl border transition-all text-left",
                  isSelected
                    ? "border-primary-500 bg-primary-50"
                    : "border-surface-tertiary hover:border-primary-200 hover:bg-surface-secondary"
                )}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{localeFlags[locale]}</span>
                  <div>
                    <p
                      className={clsx(
                        "font-medium",
                        isSelected ? "text-primary-600" : "text-text-primary"
                      )}
                    >
                      {localeNames[locale]}
                    </p>
                    <p className="text-sm text-text-muted">{locale.toUpperCase()}</p>
                  </div>
                </div>
                {isSelected && (
                  <div className="h-6 w-6 rounded-full bg-primary-500 flex items-center justify-center">
                    <Check className="h-4 w-4 text-white" />
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
