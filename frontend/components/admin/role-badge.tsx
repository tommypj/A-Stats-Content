"use client";

import { Badge } from "@/components/ui/badge";

interface RoleBadgeProps {
  role: string;
}

export function RoleBadge({ role }: RoleBadgeProps) {
  const getRoleConfig = (role: string) => {
    switch (role.toLowerCase()) {
      case "super_admin":
        return {
          label: "Super Admin",
          variant: "danger" as const,
        };
      case "admin":
        return {
          label: "Admin",
          variant: "warning" as const,
        };
      case "user":
      default:
        return {
          label: "User",
          variant: "secondary" as const,
        };
    }
  };

  const config = getRoleConfig(role);

  return <Badge variant={config.variant}>{config.label}</Badge>;
}
