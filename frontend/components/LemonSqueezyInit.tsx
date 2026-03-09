"use client";

import { useEffect } from "react";

/**
 * Initializes lemon.js after the script loads.
 * The script is loaded in app/layout.tsx via next/script.
 * This component calls createLemonSqueezy() on mount
 * and on every SPA navigation to ensure overlay mode works.
 */
export function LemonSqueezyInit() {
  useEffect(() => {
    // Try immediately (script may already be loaded)
    window.createLemonSqueezy?.();

    // Also retry after a short delay in case script loads after mount
    const timer = setTimeout(() => {
      window.createLemonSqueezy?.();
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  return null;
}
