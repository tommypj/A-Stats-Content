"use client";

import { cn } from "@/lib/utils";

const tierConfig = {
  A: {
    label: "Tier A",
    title: "Full pipeline — SERP, research, outline, article, SEO + fact-check repair",
    bg: "bg-green-100",
    text: "text-green-700",
    border: "border-green-200",
    dot: "bg-green-500",
  },
  B: {
    label: "Tier B",
    title: "Partial fallback — some pipeline steps skipped or cached",
    bg: "bg-yellow-100",
    text: "text-yellow-700",
    border: "border-yellow-200",
    dot: "bg-yellow-500",
  },
  C: {
    label: "Tier C",
    title: "Full Claude fallback — no SERP/research data available",
    bg: "bg-orange-100",
    text: "text-orange-700",
    border: "border-orange-200",
    dot: "bg-orange-500",
  },
} as const;

interface QualityTierBadgeProps {
  tier: string | null | undefined;
  className?: string;
}

export function QualityTierBadge({ tier, className }: QualityTierBadgeProps) {
  if (!tier) return null;

  const config = tierConfig[tier as keyof typeof tierConfig];
  if (!config) return null;

  return (
    <span
      title={config.title}
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold border",
        config.bg,
        config.text,
        config.border,
        className
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", config.dot)} />
      {config.label}
    </span>
  );
}
