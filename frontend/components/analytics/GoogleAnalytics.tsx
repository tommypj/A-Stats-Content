"use client";

import { useEffect, useState } from "react";
import Script from "next/script";
import { getCookieConsent } from "@/components/ui/cookie-banner";

const GA_MEASUREMENT_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;

/**
 * Consent-aware Google Analytics loader.
 * Only loads gtag.js when the user has accepted "all" cookies.
 * Listens for consent changes via a storage event so it activates
 * immediately after the user clicks "Accept All" on the banner.
 */
export function GoogleAnalytics() {
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    // Check on mount
    setAllowed(getCookieConsent() === "all");

    // Listen for changes (same tab — banner sets localStorage)
    const onStorage = () => {
      setAllowed(getCookieConsent() === "all");
    };

    // localStorage doesn't fire "storage" in the same tab,
    // so we also listen for a custom event the banner dispatches.
    window.addEventListener("storage", onStorage);
    window.addEventListener("cookie-consent-change", onStorage);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("cookie-consent-change", onStorage);
    };
  }, []);

  if (!GA_MEASUREMENT_ID || !allowed) return null;

  return (
    <>
      <Script
        src={`https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`}
        strategy="afterInteractive"
      />
      <Script id="google-analytics" strategy="afterInteractive">
        {`
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());
          gtag('config', '${GA_MEASUREMENT_ID}', { anonymize_ip: true });
        `}
      </Script>
    </>
  );
}
