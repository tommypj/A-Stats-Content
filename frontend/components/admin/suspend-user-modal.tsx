"use client";

import { useState } from "react";
import { api, AdminUserDetail, parseApiError } from "@/lib/api";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { X, AlertTriangle } from "lucide-react";

interface SuspendUserModalProps {
  user?: AdminUserDetail;
  userIds?: string[];
  onClose: () => void;
  onSuccess: () => void;
}

export function SuspendUserModal({
  user,
  userIds,
  onClose,
  onSuccess,
}: SuspendUserModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState("");

  const isBulk = !!userIds && userIds.length > 0;
  const count = isBulk ? userIds.length : 1;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!reason.trim()) {
      setError("Please provide a reason for suspension");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      if (isBulk && userIds) {
        await api.admin.users.bulkSuspend(userIds, reason);
      } else if (user) {
        await api.admin.users.suspend(user.id, reason);
      }
      onSuccess();
    } catch (err) {
      const apiError = parseApiError(err);
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      isOpen={true}
      onClose={onClose}
      size="md"
      title={`Suspend ${count > 1 ? `${count} Users` : "User"}`}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex items-start gap-3 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-yellow-700">
              {isBulk ? (
                <p>
                  You are about to suspend <strong>{count} users</strong>. They will
                  be unable to access the platform until unsuspended.
                </p>
              ) : (
                <p>
                  You are about to suspend <strong>{user?.name}</strong>. They will
                  be unable to access the platform until unsuspended.
                </p>
              )}
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1.5">
              Reason for Suspension *
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Enter a detailed reason for suspending this account..."
              rows={4}
              required
              disabled={loading}
              className="w-full rounded-xl border border-surface-tertiary bg-surface px-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 disabled:opacity-50"
            />
          </div>

          <div className="flex items-center gap-3 pt-4">
            <Button
              type="submit"
              variant="destructive"
              isLoading={loading}
              className="flex-1"
            >
              Suspend {count > 1 ? `${count} Users` : "User"}
            </Button>
            <Button type="button" variant="outline" onClick={onClose} className="flex-1">
              Cancel
            </Button>
          </div>
        </form>
    </Dialog>
  );
}
