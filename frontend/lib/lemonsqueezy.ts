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
    // Try calling createLemonSqueezy to force init
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
  console.log("[LS] openCheckoutOverlay called with:", checkoutUrl);
  console.log("[LS] window.createLemonSqueezy exists:", !!window.createLemonSqueezy);
  console.log("[LS] window.LemonSqueezy exists:", !!window.LemonSqueezy);

  // Wait for lemon.js to fully initialize
  const ready = await waitForLemonSqueezy();

  console.log("[LS] After wait — ready:", ready, "LemonSqueezy:", !!window.LemonSqueezy);

  if (!ready || !window.LemonSqueezy) {
    console.warn("[LS] LemonSqueezy overlay not available, opening in new tab");
    window.open(checkoutUrl, "_blank", "noopener,noreferrer");
    return;
  }

  // Listen for checkout success
  if (onSuccess) {
    window.LemonSqueezy.Setup({
      eventHandler: (event: LemonSqueezyEvent) => {
        console.log("[LS] Event received:", event.event);
        if (event.event === "Checkout.Success") {
          onSuccess();
        }
      },
    });
  }

  console.log("[LS] Calling LemonSqueezy.Url.Open()...");
  window.LemonSqueezy.Url.Open(checkoutUrl);
  console.log("[LS] Url.Open() called successfully");
}
