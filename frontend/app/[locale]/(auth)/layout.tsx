"use client";

import Link from "next/link";
import Image from "next/image";
import { useTranslations } from "next-intl";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const t = useTranslations("common");

  return (
    <div className="min-h-screen flex">
      {/* Left panel - Dark sage branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-primary-950 relative flex-col justify-between p-12">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <Image src="/icon.png" alt="A-Stats" width={32} height={32} className="rounded-lg" />
          <span className="font-display text-xl font-semibold text-cream-100">
            {t("appName")}
          </span>
        </Link>

        {/* Branding text */}
        <div>
          <h1 className="font-display text-4xl font-bold text-cream-100 leading-tight">
            Welcome to your
            <br />
            <span className="text-primary-300">Content Sanctuary</span>
          </h1>
          <p className="mt-4 text-lg text-cream-300 max-w-md">
            A calm, focused space to craft meaningful content that resonates
            with your audience and ranks on Google.
          </p>
        </div>

        {/* Footer */}
        <p className="text-sm text-primary-400">
          Relational SEO for therapy practices
        </p>
      </div>

      {/* Right panel - Form area */}
      <div className="flex-1 flex flex-col bg-cream-50">
        {/* Mobile header */}
        <header className="lg:hidden w-full py-4 px-4">
          <div className="max-w-7xl mx-auto">
            <Link href="/" className="flex items-center gap-2">
              <Image src="/icon.png" alt="A-Stats" width={32} height={32} className="rounded-lg" />
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
    </div>
  );
}
