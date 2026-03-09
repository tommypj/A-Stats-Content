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
      Refresh?: () => void;
    };
  }
}

export interface LemonSqueezyEvent {
  event: string;
  data?: Record<string, unknown>;
}

/**
 * Wait for the LemonSqueezy global to become available.
 * The script is loaded with strategy="afterInteractive" in layout.tsx,
 * so it may not be ready immediately.
 */
function waitForLemonSqueezy(timeoutMs = 5000): Promise<boolean> {
  return new Promise((resolve) => {
    window.createLemonSqueezy?.();

    if (window.LemonSqueezy) {
      resolve(true);
      return;
    }

    const start = Date.now();
    const interval = setInterval(() => {
      window.createLemonSqueezy?.();
      if (window.LemonSqueezy) {
        clearInterval(interval);
        resolve(true);
      } else if (Date.now() - start > timeoutMs) {
        clearInterval(interval);
        resolve(false);
      }
    }, 200);
  });
}

/**
 * Open a LemonSqueezy checkout URL as an in-app overlay.
 *
 * The checkout URL must come from the LemonSqueezy Checkouts API
 * (POST /v1/checkouts) with checkout_options.embed = true.
 *
 * Falls back to window.open if lemon.js hasn't loaded.
 */
export async function openCheckoutOverlay(
  checkoutUrl: string,
  onSuccess?: () => void
): Promise<void> {
  const ready = await waitForLemonSqueezy();

  if (!ready || !window.LemonSqueezy) {
    window.open(checkoutUrl, "_blank", "noopener,noreferrer");
    return;
  }

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
}
