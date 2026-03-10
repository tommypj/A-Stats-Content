"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { Globe, Menu, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { locales, localeNames, localeFlags, type Locale } from "@/i18n/config";

export default function PublicNav() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [langOpen, setLangOpen] = useState(false);
  const langRef = useRef<HTMLDivElement>(null);
  const t = useTranslations("landing");
  const currentLocale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  // Close language dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (langRef.current && !langRef.current.contains(e.target as Node)) {
        setLangOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const switchLocale = (newLocale: Locale) => {
    const segments = pathname.split("/");
    // If current path starts with a locale prefix, replace it
    if (locales.includes(segments[1] as Locale)) {
      segments[1] = newLocale;
    } else {
      // No locale prefix (default locale) — prepend it
      segments.splice(1, 0, newLocale);
    }
    router.push(segments.join("/") || "/");
    setLangOpen(false);
    setMobileMenuOpen(false);
  };

  const NAV_LINKS = [
    { label: t("nav.features"), href: "/#features" },
    { label: t("nav.howItWorks"), href: "/#how-it-works" },
    { label: t("nav.pricing"), href: "/#pricing" },
    { label: t("nav.blog"), href: "/blog" },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/70 backdrop-blur-xl border-b border-surface-tertiary/60">
      <div className="page-container">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5">
            <Image src="/icon.png" alt="A-Stats" width={32} height={32} className="rounded-lg" />
            <span className="font-display text-xl font-semibold text-text-primary">A-Stats</span>
          </Link>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-8">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm text-text-secondary hover:text-text-primary transition-colors"
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Desktop CTA */}
          <div className="hidden md:flex items-center gap-4">
            {/* Language switcher */}
            <div ref={langRef} className="relative">
              <button
                onClick={() => setLangOpen(!langOpen)}
                className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary transition-colors p-1.5 rounded-lg hover:bg-surface-secondary"
                aria-label="Change language"
              >
                <Globe className="h-4 w-4" />
                <span className="text-xs">{localeFlags[currentLocale as Locale]}</span>
              </button>
              {langOpen && (
                <div className="absolute right-0 top-full mt-2 w-44 bg-white rounded-xl border border-surface-tertiary shadow-lg py-1 z-50">
                  {locales.map((locale) => (
                    <button
                      key={locale}
                      onClick={() => switchLocale(locale)}
                      className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                        locale === currentLocale
                          ? "text-primary-600 bg-primary-50 font-medium"
                          : "text-text-secondary hover:bg-surface-secondary hover:text-text-primary"
                      }`}
                    >
                      <span>{localeFlags[locale]}</span>
                      <span>{localeNames[locale]}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <Link href="/login" className="text-sm text-text-secondary hover:text-text-primary transition-colors">
              {t("nav.signIn")}
            </Link>
            <Link href="/register" className="btn-primary text-sm">
              {t("nav.getStartedFree")}
            </Link>
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden p-2 text-text-secondary hover:text-text-primary"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-white/95 backdrop-blur-xl border-b border-surface-tertiary animate-in">
          <div className="page-container py-4 flex flex-col gap-3">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm text-text-secondary hover:text-text-primary py-2"
                onClick={() => setMobileMenuOpen(false)}
              >
                {link.label}
              </Link>
            ))}
            <hr className="border-surface-tertiary" />
            {/* Mobile language switcher */}
            <div className="flex flex-wrap gap-2 py-2">
              {locales.map((locale) => (
                <button
                  key={locale}
                  onClick={() => switchLocale(locale)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition-colors ${
                    locale === currentLocale
                      ? "bg-primary-50 text-primary-600 font-medium"
                      : "text-text-secondary hover:bg-surface-secondary"
                  }`}
                >
                  <span>{localeFlags[locale]}</span>
                  <span>{localeNames[locale]}</span>
                </button>
              ))}
            </div>
            <hr className="border-surface-tertiary" />
            <Link href="/login" className="text-sm text-text-secondary py-2" onClick={() => setMobileMenuOpen(false)}>
              {t("nav.signIn")}
            </Link>
            <Link href="/register" className="btn-primary text-sm text-center" onClick={() => setMobileMenuOpen(false)}>
              {t("nav.getStartedFree")}
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
