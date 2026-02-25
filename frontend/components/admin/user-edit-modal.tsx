"use client";

import { useState } from "react";
import { api, AdminUserDetail, AdminUpdateUserInput, parseApiError } from "@/lib/api";
import { toast } from "sonner";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";

interface UserEditModalProps {
  user: AdminUserDetail;
  onClose: () => void;
  onSuccess: () => void;
}

export function UserEditModal({ user, onClose, onSuccess }: UserEditModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [role, setRole] = useState(user.role);
  const [subscriptionTier, setSubscriptionTier] = useState(user.subscription_tier);
  const [isSuspended, setIsSuspended] = useState(user.is_suspended);
  const [suspensionReason, setSuspensionReason] = useState(user.suspension_reason || "");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const data: AdminUpdateUserInput = {
        role,
        subscription_tier: subscriptionTier,
      };

      await api.admin.users.update(user.id, data);

      // Handle suspension separately
      if (isSuspended && !user.is_suspended) {
        await api.admin.users.suspend(user.id, suspensionReason);
      } else if (!isSuspended && user.is_suspended) {
        await api.admin.users.unsuspend(user.id);
      }

      onSuccess();
    } catch (err) {
      const apiError = parseApiError(err);
      setError(apiError.message);
      toast.error(apiError.message || "Failed to update user");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog isOpen={true} onClose={onClose} size="md" title="Edit User">
      <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1.5">
              Role
            </label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-xl border border-surface-tertiary bg-surface px-4 py-2.5 text-sm text-text-primary focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
            >
              <option value="user">User</option>
              <option value="admin">Admin</option>
              <option value="super_admin">Super Admin</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1.5">
              Subscription Tier
            </label>
            <select
              value={subscriptionTier}
              onChange={(e) => setSubscriptionTier(e.target.value)}
              className="w-full rounded-xl border border-surface-tertiary bg-surface px-4 py-2.5 text-sm text-text-primary focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
            >
              <option value="free">Free</option>
              <option value="starter">Starter</option>
              <option value="professional">Professional</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>

          <div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isSuspended}
                onChange={(e) => setIsSuspended(e.target.checked)}
                className="h-4 w-4 rounded border-surface-tertiary text-primary-500 focus:ring-primary-500"
              />
              <span className="text-sm text-text-primary">Suspend Account</span>
            </label>
          </div>

          {isSuspended && (
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">
                Suspension Reason
              </label>
              <textarea
                value={suspensionReason}
                onChange={(e) => setSuspensionReason(e.target.value)}
                placeholder="Enter reason for suspension..."
                rows={3}
                className="w-full rounded-xl border border-surface-tertiary bg-surface px-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
              />
            </div>
          )}

          <div className="flex items-center gap-3 pt-4">
            <Button type="submit" isLoading={loading} className="flex-1">
              Save Changes
            </Button>
            <Button type="button" variant="outline" onClick={onClose} className="flex-1">
              Cancel
            </Button>
          </div>
        </form>
    </Dialog>
  );
}
