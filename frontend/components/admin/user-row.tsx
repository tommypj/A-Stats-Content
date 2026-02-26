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
      <td className="p-2 sm:p-3 md:p-4">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => onSelect?.(e.target.checked)}
          className="h-4 w-4 rounded border-surface-tertiary text-primary-500 focus:ring-primary-500"
        />
      </td>
      <td className="p-2 sm:p-3 md:p-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white font-semibold flex-shrink-0">
            {user.name.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <div className="font-medium text-text-primary truncate">{user.name}</div>
            <div className="text-sm text-text-muted truncate">{user.email}</div>
          </div>
        </div>
      </td>
      <td className="p-2 sm:p-3 md:p-4 hidden md:table-cell">
        <RoleBadge role={user.role} />
      </td>
      <td className="p-2 sm:p-3 md:p-4 hidden lg:table-cell">
        <SubscriptionBadge
          tier={user.subscription_tier}
          status={user.subscription_status}
        />
      </td>
      <td className="p-2 sm:p-3 md:p-4 text-sm text-text-secondary hidden lg:table-cell">
        {formatDistanceToNow(new Date(user.created_at), { addSuffix: true })}
      </td>
      <td className="p-2 sm:p-3 md:p-4">
        {user.is_suspended ? (
          <Badge variant="danger">Suspended</Badge>
        ) : (
          <Badge variant="success">Active</Badge>
        )}
      </td>
      <td className="p-2 sm:p-3 md:p-4">
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => router.push(`/admin/users/${user.id}`)}
            className="min-h-[44px] min-w-[44px] flex items-center justify-center"
          >
            <Eye className="h-4 w-4" />
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onEdit(user)} className="min-h-[44px] min-w-[44px] flex items-center justify-center">
            <Edit className="h-4 w-4" />
          </Button>
          {user.is_suspended ? (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onUnsuspend(user)}
              className="min-h-[44px] min-w-[44px] flex items-center justify-center"
            >
              <CheckCircle className="h-4 w-4 text-green-500" />
            </Button>
          ) : (
            <Button size="sm" variant="ghost" onClick={() => onSuspend(user)} className="min-h-[44px] min-w-[44px] flex items-center justify-center">
              <Ban className="h-4 w-4 text-red-500" />
            </Button>
          )}
        </div>
      </td>
    </tr>
  );
}
