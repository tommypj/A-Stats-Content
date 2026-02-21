"use client";

import { Badge } from "@/components/ui/badge";
import { SocialPostStatus } from "@/lib/api";
import { Loader2 } from "lucide-react";

interface PostStatusBadgeProps {
  status: SocialPostStatus;
  className?: string;
}

export function PostStatusBadge({ status, className }: PostStatusBadgeProps) {
  const statusConfig: Record<
    SocialPostStatus,
    { label: string; variant: "default" | "secondary" | "success" | "warning" | "danger"; icon?: React.ReactNode }
  > = {
    pending: {
      label: "Pending",
      variant: "warning",
    },
    queued: {
      label: "Queued",
      variant: "default",
    },
    posting: {
      label: "Posting",
      variant: "default",
      icon: <Loader2 className="w-3 h-3 animate-spin mr-1" />,
    },
    posted: {
      label: "Posted",
      variant: "success",
    },
    failed: {
      label: "Failed",
      variant: "danger",
    },
    cancelled: {
      label: "Cancelled",
      variant: "secondary",
    },
  };

  const config = statusConfig[status];

  return (
    <Badge variant={config.variant} className={className}>
      {config.icon}
      {config.label}
    </Badge>
  );
}
