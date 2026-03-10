"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Menu, X } from "lucide-react";
import { useTranslations } from "next-intl";

export default function PublicNav() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const t = useTranslations("landing");

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
