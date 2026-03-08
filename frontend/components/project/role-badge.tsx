import { clsx } from "clsx";
import type { ProjectRole } from "@/lib/api";
import { Crown, Shield, Pencil, Eye } from "lucide-react";

interface RoleBadgeProps {
  role: ProjectRole;
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
}

const roleConfig: Record<
  ProjectRole,
  {
    label: string;
    icon: typeof Crown;
    colorClasses: string;
  }
> = {
  owner: {
    label: "Owner",
    icon: Crown,
    colorClasses: "bg-orange-100 text-orange-700 border-orange-200",
  },
  admin: {
    label: "Admin",
    icon: Shield,
    colorClasses: "bg-purple-100 text-purple-700 border-purple-200",
  },
  editor: {
    label: "Editor",
    icon: Pencil,
    colorClasses: "bg-green-100 text-green-700 border-green-200",
  },
  viewer: {
    label: "Viewer",
    icon: Eye,
    colorClasses: "bg-surface-tertiary text-text-secondary border-surface-tertiary",
  },
};

export function RoleBadge({ role, size = "md", showIcon = true }: RoleBadgeProps) {
  const config = roleConfig[role];
  const Icon = config.icon;

  const sizeClasses = {
    sm: "text-xs px-2 py-0.5",
    md: "text-sm px-2.5 py-1",
    lg: "text-base px-3 py-1.5",
  };

  const iconSizes = {
    sm: "h-3 w-3",
    md: "h-3.5 w-3.5",
    lg: "h-4 w-4",
  };

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full font-medium border",
        config.colorClasses,
        sizeClasses[size]
      )}
    >
      {showIcon && <Icon className={iconSizes[size]} />}
      {config.label}
    </span>
  );
}
