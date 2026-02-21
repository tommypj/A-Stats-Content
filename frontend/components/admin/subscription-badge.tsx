"use client";

import { Badge } from "@/components/ui/badge";

interface SubscriptionBadgeProps {
  tier: string;
  status?: string;
}

export function SubscriptionBadge({ tier, status }: SubscriptionBadgeProps) {
  const getTierConfig = (tier: string) => {
    switch (tier.toLowerCase()) {
      case "enterprise":
        return {
          label: "Enterprise",
          variant: "danger" as const,
        };
      case "professional":
        return {
          label: "Professional",
          variant: "warning" as const,
        };
      case "starter":
        return {
          label: "Starter",
          variant: "default" as const,
        };
      case "free":
      default:
        return {
          label: "Free",
          variant: "secondary" as const,
        };
    }
  };

  const getStatusConfig = (status: string) => {
    switch (status?.toLowerCase()) {
      case "active":
        return {
          label: "Active",
          variant: "success" as const,
        };
      case "cancelled":
      case "expired":
        return {
          label: status,
          variant: "danger" as const,
        };
      case "paused":
        return {
          label: "Paused",
          variant: "warning" as const,
        };
      default:
        return null;
    }
  };

  const tierConfig = getTierConfig(tier);
  const statusConfig = status ? getStatusConfig(status) : null;

  return (
    <div className="flex items-center gap-2">
      <Badge variant={tierConfig.variant}>{tierConfig.label}</Badge>
      {statusConfig && (
        <Badge variant={statusConfig.variant}>{statusConfig.label}</Badge>
      )}
    </div>
  );
}
