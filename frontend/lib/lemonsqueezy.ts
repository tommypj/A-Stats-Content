/**
 * LemonSqueezy overlay checkout helper.
 *
 * The lemon.js script is loaded statically in app/layout.tsx via next/script.
 * This module provides a typed wrapper for opening checkout overlays
 * and listening for success events.
 */

declare global {
  interface Window {
    createLemonSqueezy?: () => void;
    LemonSqueezy?: {
      Url: { Open: (url: string) => void };
      Setup: (opts: { eventHandler: (event: LemonSqueezyEvent) => void }) => void;
    };
  }
}

export interface LemonSqueezyEvent {
  event: string;
  data?: Record<string, unknown>;
}

/**
 * Open a LemonSqueezy checkout URL as an in-app overlay.
 *
 * The checkout URL must come from the LemonSqueezy Checkouts API
 * (POST /v1/checkouts) — manually constructed /checkout/buy/ URLs
 * do not support overlay mode.
 *
 * Falls back to window.open if lemon.js hasn't loaded yet.
 */
export async function openCheckoutOverlay(
  checkoutUrl: string,
  onSuccess?: () => void
): Promise<void> {
  // Re-initialize in case SPA navigation happened after script load
  window.createLemonSqueezy?.();

  if (window.LemonSqueezy) {
    // Listen for checkout success
    if (onSuccess) {
      window.LemonSqueezy.Setup({
        eventHandler: (event: LemonSqueezyEvent) => {
          if (event.event === "Checkout.Success") {
            onSuccess();
          }
        },
      });
    }

    window.LemonSqueezy.Url.Open(checkoutUrl);
  } else {
    // Fallback: open in new tab if script failed to load
    console.warn("LemonSqueezy overlay not available, opening in new tab");
    window.open(checkoutUrl, "_blank", "noopener,noreferrer");
  }
}
