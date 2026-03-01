"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Cookie, X } from "lucide-react";
import { Button } from "@/components/ui/button";

const CONSENT_KEY = "cookie_consent";

export type CookieConsent = "all" | "necessary";

export function getCookieConsent(): CookieConsent | null {
  if (typeof window === "undefined") return null;
  const v = localStorage.getItem(CONSENT_KEY);
  if (v === "all" || v === "necessary") return v;
  return null;
}

export function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (getCookieConsent() === null) {
      // Small delay so the page renders first
      const t = setTimeout(() => setVisible(true), 600);
      return () => clearTimeout(t);
    }
  }, []);

  function accept(level: CookieConsent) {
    localStorage.setItem(CONSENT_KEY, level);
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div
      role="dialog"
      aria-label="Cookie consent"
      className="fixed bottom-4 left-4 right-4 z-50 mx-auto max-w-2xl animate-in slide-in-from-bottom-4 duration-300"
    >
      <div className="rounded-2xl border border-surface-tertiary bg-white/95 backdrop-blur-md shadow-xl p-4 sm:p-5">
        <div className="flex items-start gap-3">
          <div className="h-9 w-9 rounded-xl bg-primary-50 flex items-center justify-center shrink-0 mt-0.5">
            <Cookie className="h-4 w-4 text-primary-500" />
          </div>

          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-text-primary">
              We use cookies
            </p>
            <p className="text-sm text-text-secondary mt-0.5">
              We use necessary cookies to keep the app running and optional analytics
              cookies to improve your experience.{" "}
              <Link
                href="/legal/cookies"
                className="text-primary-500 hover:text-primary-600 underline underline-offset-2"
              >
                Cookie Policy
              </Link>{" "}
              &middot;{" "}
              <Link
                href="/legal/privacy"
                className="text-primary-500 hover:text-primary-600 underline underline-offset-2"
              >
                Privacy Policy
              </Link>
            </p>

            <div className="flex flex-wrap items-center gap-2 mt-3">
              <Button
                size="sm"
                variant="primary"
                onClick={() => accept("all")}
              >
                Accept All
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => accept("necessary")}
              >
                Necessary Only
              </Button>
            </div>
          </div>

          <button
            onClick={() => accept("necessary")}
            aria-label="Dismiss — necessary cookies only"
            className="p-1.5 rounded-lg hover:bg-surface-secondary text-text-muted hover:text-text-secondary transition-colors shrink-0"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
