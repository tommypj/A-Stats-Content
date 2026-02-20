"use client";

import { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useLocale } from "next-intl";
import { Globe, Check, ChevronDown } from "lucide-react";
import { clsx } from "clsx";

import { locales, localeNames, localeFlags, type Locale } from "@/i18n/config";

export function LanguageSwitcher() {
  const [isOpen, setIsOpen] = useState(false);
  const currentLocale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  const handleLanguageChange = (newLocale: Locale) => {
    const newPath = pathname.replace(`/${currentLocale}`, `/${newLocale}`);
    router.push(newPath);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm text-text-secondary hover:bg-surface-secondary transition-colors"
      >
        <Globe className="h-4 w-4" />
        <span>{localeFlags[currentLocale as Locale]}</span>
        <ChevronDown className="h-3 w-3" />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl border border-surface-tertiary shadow-lg z-50 py-1">
            {locales.map((locale) => {
              const isSelected = locale === currentLocale;

              return (
                <button
                  key={locale}
                  onClick={() => handleLanguageChange(locale)}
                  className={clsx(
                    "flex items-center justify-between w-full px-4 py-2.5 text-sm text-left transition-colors",
                    isSelected
                      ? "bg-primary-50 text-primary-600"
                      : "text-text-secondary hover:bg-surface-secondary hover:text-text-primary"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <span>{localeFlags[locale]}</span>
                    <span>{localeNames[locale]}</span>
                  </div>
                  {isSelected && <Check className="h-4 w-4" />}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
