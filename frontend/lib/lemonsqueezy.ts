/**
 * LemonSqueezy overlay checkout helper.
 *
 * The lemon.js script is loaded statically in app/layout.tsx via next/script.
 * This module uses the documented `.lemonsqueezy-button` class approach:
 * lemon.js automatically intercepts clicks on elements with that class
 * and opens the checkout as an in-app overlay.
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
 * Uses the `.lemonsqueezy-button` approach: creates a hidden <a> element
 * with the checkout URL and the class that lemon.js intercepts, then
 * programmatically clicks it to trigger the overlay.
 *
 * Falls back to window.open if lemon.js hasn't loaded.
 */
export async function openCheckoutOverlay(
  checkoutUrl: string,
  onSuccess?: () => void
): Promise<void> {
  // Re-initialize lemon.js for SPA navigation
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

    // Create a hidden anchor with the lemonsqueezy-button class
    // that lemon.js will intercept and open as an overlay
    const anchor = document.createElement("a");
    anchor.href = checkoutUrl;
    anchor.classList.add("lemonsqueezy-button");
    anchor.style.display = "none";
    document.body.appendChild(anchor);
    anchor.click();

    // Clean up after a short delay
    setTimeout(() => anchor.remove(), 500);
  } else {
    // Fallback: open in new tab if script failed to load
    console.warn("LemonSqueezy overlay not available, opening in new tab");
    window.open(checkoutUrl, "_blank", "noopener,noreferrer");
  }
}
