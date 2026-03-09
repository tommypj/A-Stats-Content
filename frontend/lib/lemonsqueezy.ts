/**
 * LemonSqueezy overlay checkout helper.
 *
 * Loads the lemon.js script once and provides a function to open
 * checkout URLs as an in-app overlay instead of redirecting away.
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

let scriptLoaded = false;
let scriptLoading = false;
const loadCallbacks: (() => void)[] = [];

function ensureScript(): Promise<void> {
  if (scriptLoaded && window.LemonSqueezy) {
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    if (scriptLoading) {
      loadCallbacks.push(resolve);
      return;
    }

    // Check if script tag already exists
    if (document.querySelector('script[src*="lemonsqueezy"]')) {
      scriptLoaded = true;
      window.createLemonSqueezy?.();
      resolve();
      return;
    }

    scriptLoading = true;
    const script = document.createElement("script");
    script.src = "https://app.lemonsqueezy.com/js/lemon.js";
    script.defer = true;
    script.onload = () => {
      scriptLoaded = true;
      scriptLoading = false;
      window.createLemonSqueezy?.();
      resolve();
      loadCallbacks.forEach((cb) => cb());
      loadCallbacks.length = 0;
    };
    script.onerror = () => {
      scriptLoading = false;
      // Fallback: resolve anyway so callers can fall back to redirect
      resolve();
    };
    document.head.appendChild(script);
  });
}

/**
 * Open a LemonSqueezy checkout URL as an in-app overlay.
 *
 * The checkout URL must come from the LemonSqueezy Checkouts API
 * (POST /v1/checkouts) — manually constructed /checkout/buy/ URLs
 * do not support overlay mode.
 *
 * Falls back to window.open if the overlay script fails to load.
 */
export async function openCheckoutOverlay(
  checkoutUrl: string,
  onSuccess?: () => void
): Promise<void> {
  await ensureScript();

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
    // Fallback: open in new tab
    window.open(checkoutUrl, "_blank", "noopener,noreferrer");
  }
}
