import posthog from "posthog-js";

/**
 * Safely capture a custom PostHog event.
 * No-op when PostHog is not loaded (e.g. missing env key, SSR).
 */
export function trackEvent(
  name: string,
  properties?: Record<string, any>,
): void {
  if (typeof window === "undefined") return;
  if (!posthog.__loaded) return;
  posthog.capture(name, properties);
}
