"use client";

import { useState } from "react";
import { api, AdminUserDetail, parseApiError } from "@/lib/api";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { X, AlertTriangle, Trash2 } from "lucide-react";

interface DeleteUserModalProps {
  user: AdminUserDetail;
  onClose: () => void;
  onSuccess: () => void;
}

export function DeleteUserModal({
  user,
  onClose,
  onSuccess,
}: DeleteUserModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmEmail, setConfirmEmail] = useState("");
  const [hardDelete, setHardDelete] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (confirmEmail !== user.email) {
      setError("Email does not match. Please type the exact email address.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await api.admin.users.delete(user.id, hardDelete);
      onSuccess();
    } catch (err) {
      const apiError = parseApiError(err);
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog isOpen={true} onClose={onClose} size="md" title="Delete User">
      <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
            <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-red-700">
              <p className="font-semibold mb-1">
                {hardDelete
                  ? "Permanent deletion — cannot be undone!"
                  : "This will deactivate the user account."}
              </p>
              <p>
                {hardDelete ? "Hard deleting" : "Soft deleting"}{" "}
                <strong>{user.name}</strong> will{" "}
                {hardDelete ? "permanently remove" : "mark as deleted"}:
              </p>
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>User account and profile</li>
                <li>All articles ({user.total_articles})</li>
                <li>All outlines ({user.total_outlines})</li>
                <li>All images ({user.total_images})</li>
                <li>All subscription data</li>
              </ul>
              {hardDelete && (
                <p className="mt-2 font-semibold">
                  The email address will be freed up for re-registration.
                </p>
              )}
            </div>
          </div>

          {/* Hard delete toggle */}
          <label className="flex items-center gap-3 p-3 rounded-lg border border-surface-tertiary bg-surface-secondary cursor-pointer hover:border-red-300 transition-colors">
            <input
              type="checkbox"
              checked={hardDelete}
              onChange={(e) => setHardDelete(e.target.checked)}
              className="h-4 w-4 rounded border-surface-tertiary text-red-600 focus:ring-red-500"
            />
            <div>
              <span className="text-sm font-medium text-text-primary">
                Hard delete (permanent)
              </span>
              <p className="text-xs text-text-secondary mt-0.5">
                Permanently removes all data from the database. The email can be reused for a new account.
              </p>
            </div>
          </label>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1.5">
              Type the user's email to confirm deletion
            </label>
            <Input
              value={confirmEmail}
              onChange={(e) => setConfirmEmail(e.target.value)}
              placeholder={user.email}
              autoComplete="off"
            />
            <p className="mt-1.5 text-xs text-text-muted">
              Type <strong>{user.email}</strong> to confirm
            </p>
          </div>

          <div className="flex items-center gap-3 pt-4">
            <Button
              type="submit"
              variant="destructive"
              isLoading={loading}
              disabled={confirmEmail !== user.email}
              className="flex-1"
              leftIcon={<Trash2 className="h-4 w-4" />}
            >
              {hardDelete ? "Permanently Delete" : "Soft Delete"} User
            </Button>
            <Button type="button" variant="outline" onClick={onClose} className="flex-1">
              Cancel
            </Button>
          </div>
        </form>
    </Dialog>
  );
}
