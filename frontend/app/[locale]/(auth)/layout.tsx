"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const t = useTranslations("common");

  return (
    <div className="min-h-screen flex flex-col bg-healing-cream">
      {/* Header */}
      <header className="w-full py-4 px-4">
        <div className="max-w-7xl mx-auto">
          <Link href="/" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary-400 to-primary-600" />
            <span className="font-display text-xl font-semibold text-text-primary">
              {t("appName")}
            </span>
          </Link>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="py-4 text-center">
        <p className="text-sm text-text-muted">
          &copy; {new Date().getFullYear()} A-Stats. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
