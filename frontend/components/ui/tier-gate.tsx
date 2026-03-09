"use client";

import { ReactNode } from "react";
import Link from "next/link";
import { Lock } from "lucide-react";
import { useAuthStore } from "@/stores/auth";
import { Button } from "@/components/ui/button";

const TIER_ORDER = ["free", "starter", "professional", "enterprise"] as const;
type Tier = (typeof TIER_ORDER)[number];

const TIER_LABELS: Record<Tier, string> = {
  free: "Free",
  starter: "Starter",
  professional: "Professional",
  enterprise: "Enterprise",
};

interface TierGateProps {
  /** Minimum tier required to access this feature */
  minimum: Tier;
  /** Content to render when the user has access */
  children: ReactNode;
  /** Optional feature name for the upgrade message */
  feature?: string;
}

/**
 * Wraps content that requires a minimum subscription tier.
 * Shows an upgrade prompt if the user's tier is below the minimum.
 */
export function TierGate({ minimum, children, feature }: TierGateProps) {
  const user = useAuthStore((s) => s.user);
  const currentTier = (user?.subscription_tier || "free") as Tier;
  const currentRank = TIER_ORDER.indexOf(currentTier);
  const requiredRank = TIER_ORDER.indexOf(minimum);

  if (currentRank >= requiredRank) {
    return <>{children}</>;
  }

  const featureLabel = feature ? `"${feature}"` : "This feature";

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="max-w-md text-center space-y-4">
        <div className="mx-auto w-14 h-14 rounded-2xl bg-surface-secondary flex items-center justify-center">
          <Lock className="h-7 w-7 text-text-muted" />
        </div>
        <h2 className="font-display text-xl font-semibold text-text-primary">
          {TIER_LABELS[minimum]} Plan Required
        </h2>
        <p className="text-sm text-text-secondary leading-relaxed">
          {featureLabel} is available on the{" "}
          <span className="font-medium text-text-primary">{TIER_LABELS[minimum]}</span>{" "}
          plan and above. You are currently on the{" "}
          <span className="font-medium text-text-primary">{TIER_LABELS[currentTier]}</span>{" "}
          plan.
        </p>
        <Link href="/settings/billing">
          <Button variant="primary" className="mt-2">
            Upgrade to {TIER_LABELS[minimum]}
          </Button>
        </Link>
      </div>
    </div>
  );
}
