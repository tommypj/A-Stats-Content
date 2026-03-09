"use client";

import { ReactNode } from "react";
import Link from "next/link";
import {
  Lock,
  Sparkles,
  Check,
  ArrowRight,
  Zap,
  BarChart3,
  Globe,
  Users,
  FileText,
  Shield,
  Calendar,
  Search,
  Layers,
  Building2,
} from "lucide-react";
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

const TIER_PRICES: Record<Tier, number> = {
  free: 0,
  starter: 29,
  professional: 79,
  enterprise: 199,
};

const TIER_COLORS: Record<
  Tier,
  { bg: string; border: string; text: string; badge: string; icon: string; glow: string }
> = {
  free: {
    bg: "bg-surface-secondary",
    border: "border-surface-tertiary",
    text: "text-text-secondary",
    badge: "bg-surface-tertiary text-text-secondary",
    icon: "text-text-muted",
    glow: "",
  },
  starter: {
    bg: "bg-blue-50",
    border: "border-blue-200",
    text: "text-blue-700",
    badge: "bg-blue-100 text-blue-700",
    icon: "text-blue-500",
    glow: "shadow-blue-100/50",
  },
  professional: {
    bg: "bg-purple-50",
    border: "border-purple-200",
    text: "text-purple-700",
    badge: "bg-purple-100 text-purple-700",
    icon: "text-purple-500",
    glow: "shadow-purple-100/50",
  },
  enterprise: {
    bg: "bg-amber-50",
    border: "border-amber-200",
    text: "text-amber-700",
    badge: "bg-amber-100 text-amber-700",
    icon: "text-amber-500",
    glow: "shadow-amber-100/50",
  },
};

interface TierHighlight {
  icon: ReactNode;
  text: string;
}

const TIER_HIGHLIGHTS: Record<Exclude<Tier, "free">, TierHighlight[]> = {
  starter: [
    { icon: <FileText className="h-4 w-4" />, text: "30 articles & 60 images per month" },
    { icon: <Search className="h-4 w-4" />, text: "60 keyword researches per month" },
    { icon: <Globe className="h-4 w-4" />, text: "WordPress & Google Search Console" },
    { icon: <Zap className="h-4 w-4" />, text: "Social media scheduling" },
    { icon: <Users className="h-4 w-4" />, text: "Project management & collaboration" },
    { icon: <Shield className="h-4 w-4" />, text: "Site audits (10 pages)" },
  ],
  professional: [
    { icon: <FileText className="h-4 w-4" />, text: "100 articles & 200 images per month" },
    { icon: <BarChart3 className="h-4 w-4" />, text: "Competitor analysis & SEO reports" },
    { icon: <Calendar className="h-4 w-4" />, text: "Content calendar with auto-publish" },
    { icon: <Layers className="h-4 w-4" />, text: "Bulk content generation & templates" },
    { icon: <Zap className="h-4 w-4" />, text: "Content decay detection & auto-alerts" },
    { icon: <Shield className="h-4 w-4" />, text: "Site audits (100 pages) & GA4 integration" },
  ],
  enterprise: [
    { icon: <FileText className="h-4 w-4" />, text: "300 articles & 600 images per month" },
    { icon: <Building2 className="h-4 w-4" />, text: "White-label agency mode" },
    { icon: <Users className="h-4 w-4" />, text: "Client portals & custom branding" },
    { icon: <Globe className="h-4 w-4" />, text: "Custom integrations & API access" },
    { icon: <Shield className="h-4 w-4" />, text: "Site audits (1,000 pages)" },
    { icon: <Sparkles className="h-4 w-4" />, text: "Dedicated support & SLA guarantee" },
  ],
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
 * Shows a polished upgrade prompt if the user's tier is below the minimum.
 */
export function TierGate({ minimum, children, feature }: TierGateProps) {
  const user = useAuthStore((s) => s.user);
  const currentTier = (user?.subscription_tier || "free") as Tier;
  const currentRank = TIER_ORDER.indexOf(currentTier);
  const requiredRank = TIER_ORDER.indexOf(minimum);

  if (currentRank >= requiredRank) {
    return <>{children}</>;
  }

  const colors = TIER_COLORS[minimum];
  const highlights = minimum !== "free" ? TIER_HIGHLIGHTS[minimum] : [];
  const price = TIER_PRICES[minimum];

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className={`max-w-lg w-full rounded-2xl border ${colors.border} bg-surface shadow-lg ${colors.glow} overflow-hidden`}>
        {/* Header */}
        <div className={`${colors.bg} px-6 py-5 border-b ${colors.border}`}>
          <div className="flex items-center gap-3">
            <div className={`h-10 w-10 rounded-xl ${colors.bg} border ${colors.border} flex items-center justify-center`}>
              <Lock className={`h-5 w-5 ${colors.icon}`} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-display text-lg font-semibold text-text-primary">
                  Unlock {feature || "this feature"}
                </h2>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${colors.badge}`}>
                  {TIER_LABELS[minimum]}
                </span>
              </div>
              <p className="text-sm text-text-secondary mt-0.5">
                Upgrade from <span className="font-medium">{TIER_LABELS[currentTier]}</span> to{" "}
                <span className={`font-medium ${colors.text}`}>{TIER_LABELS[minimum]}</span> to get access.
              </p>
            </div>
          </div>
        </div>

        {/* Highlights */}
        <div className="px-6 py-5">
          <p className="text-xs font-medium text-text-secondary uppercase tracking-wider mb-3">
            What you get with {TIER_LABELS[minimum]}
          </p>
          <div className="grid grid-cols-1 gap-2.5">
            {highlights.map((highlight, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className={`flex-shrink-0 h-8 w-8 rounded-lg ${colors.bg} flex items-center justify-center`}>
                  <span className={colors.icon}>{highlight.icon}</span>
                </div>
                <span className="text-sm text-text-primary">{highlight.text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className={`px-6 py-4 border-t ${colors.border} bg-surface-secondary/50 flex items-center justify-between gap-4`}>
          <div>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-bold text-text-primary">${price}</span>
              <span className="text-sm text-text-secondary">/month</span>
            </div>
            {price > 0 && (
              <p className="text-xs text-text-tertiary mt-0.5">
                or ${Math.round(price * 10)}/year (save ~17%)
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Link href="/settings/billing">
              <Button variant="outline" size="sm">
                View Plans
              </Button>
            </Link>
            <Link href="/settings/billing">
              <Button variant="primary" size="sm" rightIcon={<ArrowRight className="h-3.5 w-3.5" />}>
                Upgrade Now
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Additional reassurance */}
      <div className="flex items-center gap-4 mt-5 text-xs text-text-tertiary">
        <span className="flex items-center gap-1">
          <Check className="h-3.5 w-3.5" />
          No contracts
        </span>
        <span className="flex items-center gap-1">
          <Check className="h-3.5 w-3.5" />
          Cancel anytime
        </span>
        <span className="flex items-center gap-1">
          <Check className="h-3.5 w-3.5" />
          Instant access
        </span>
      </div>
    </div>
  );
}
