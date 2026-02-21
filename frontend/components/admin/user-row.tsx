"use client";

import { AdminUserDetail } from "@/lib/api";
import { RoleBadge } from "./role-badge";
import { SubscriptionBadge } from "./subscription-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Eye, Edit, Ban, CheckCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { formatDistanceToNow } from "date-fns";

interface UserRowProps {
  user: AdminUserDetail;
  onEdit: (user: AdminUserDetail) => void;
  onSuspend: (user: AdminUserDetail) => void;
  onUnsuspend: (user: AdminUserDetail) => void;
  isSelected?: boolean;
  onSelect?: (selected: boolean) => void;
}

export function UserRow({
  user,
  onEdit,
  onSuspend,
  onUnsuspend,
  isSelected,
  onSelect,
}: UserRowProps) {
  const router = useRouter();

  return (
    <tr className="border-b border-surface-tertiary hover:bg-surface-secondary transition-colors">
      <td className="p-4">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => onSelect?.(e.target.checked)}
          className="h-4 w-4 rounded border-surface-tertiary text-primary-500 focus:ring-primary-500"
        />
      </td>
      <td className="p-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white font-semibold">
            {user.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="font-medium text-text-primary">{user.name}</div>
            <div className="text-sm text-text-muted">{user.email}</div>
          </div>
        </div>
      </td>
      <td className="p-4">
        <RoleBadge role={user.role} />
      </td>
      <td className="p-4">
        <SubscriptionBadge
          tier={user.subscription_tier}
          status={user.subscription_status}
        />
      </td>
      <td className="p-4 text-sm text-text-secondary">
        {formatDistanceToNow(new Date(user.created_at), { addSuffix: true })}
      </td>
      <td className="p-4">
        {user.is_suspended ? (
          <Badge variant="danger">Suspended</Badge>
        ) : (
          <Badge variant="success">Active</Badge>
        )}
      </td>
      <td className="p-4">
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => router.push(`/admin/users/${user.id}`)}
          >
            <Eye className="h-4 w-4" />
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onEdit(user)}>
            <Edit className="h-4 w-4" />
          </Button>
          {user.is_suspended ? (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onUnsuspend(user)}
            >
              <CheckCircle className="h-4 w-4 text-green-500" />
            </Button>
          ) : (
            <Button size="sm" variant="ghost" onClick={() => onSuspend(user)}>
              <Ban className="h-4 w-4 text-red-500" />
            </Button>
          )}
        </div>
      </td>
    </tr>
  );
}
