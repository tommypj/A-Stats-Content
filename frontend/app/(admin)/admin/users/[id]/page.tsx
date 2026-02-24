"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, AdminUserDetail, AdminAuditLog, parseApiError } from "@/lib/api";
import { toast } from "sonner";
import { RoleBadge } from "@/components/admin/role-badge";
import { SubscriptionBadge } from "@/components/admin/subscription-badge";
import { UserEditModal } from "@/components/admin/user-edit-modal";
import { SuspendUserModal } from "@/components/admin/suspend-user-modal";
import { DeleteUserModal } from "@/components/admin/delete-user-modal";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  ArrowLeft,
  Edit,
  Ban,
  CheckCircle,
  Key,
  Trash2,
  FileText,
  Image,
  FileEdit,
  Activity,
} from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";

export default function AdminUserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const userId = params.id as string;

  const [user, setUser] = useState<AdminUserDetail | null>(null);
  const [auditLogs, setAuditLogs] = useState<AdminAuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [showEditModal, setShowEditModal] = useState(false);
  const [showSuspendModal, setShowSuspendModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{ action: () => void; title: string; message: string } | null>(null);

  const fetchUser = async () => {
    try {
      setLoading(true);
      setError(null);
      const userData = await api.admin.users.get(userId);
      setUser(userData);
    } catch (err) {
      const apiError = parseApiError(err);
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      const response = await api.admin.auditLogs({
        user_id: userId,
        page_size: 10,
      });
      setAuditLogs(response.logs);
    } catch (err) {
      console.error("Failed to fetch audit logs:", err);
    }
  };

  useEffect(() => {
    fetchUser();
    fetchAuditLogs();
  }, [userId]);

  const handleUnsuspend = async () => {
    if (!user) return;
    try {
      await api.admin.users.unsuspend(user.id);
      await fetchUser();
    } catch (err) {
      const apiError = parseApiError(err);
      toast.error(`Failed to unsuspend user: ${apiError.message}`);
    }
  };

  const handleResetPassword = () => {
    if (!user) return;
    setConfirmAction({
      action: async () => {
        try {
          const response = await api.admin.users.resetPassword(user.id);
          toast.success(
            `Password reset successfully! Temporary password: ${response.temporary_password}`
          );
        } catch (err) {
          const apiError = parseApiError(err);
          toast.error(`Failed to reset password: ${apiError.message}`);
        }
      },
      title: "Reset Password",
      message: "Are you sure you want to reset this user's password? A temporary password will be generated.",
    });
  };

  const handleSuccess = () => {
    setShowEditModal(false);
    setShowSuspendModal(false);
    fetchUser();
    fetchAuditLogs();
  };

  const handleDelete = () => {
    setShowDeleteModal(false);
    router.push("/admin/users");
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-500 border-r-transparent"></div>
        </div>
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="p-6">
        <Card className="p-12 text-center">
          <p className="text-red-500">{error || "User not found"}</p>
          <Button
            className="mt-4"
            variant="outline"
            onClick={() => router.push("/admin/users")}
          >
            Back to Users
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <ConfirmDialog
        isOpen={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        onConfirm={() => { confirmAction?.action(); setConfirmAction(null); }}
        title={confirmAction?.title ?? ""}
        message={confirmAction?.message ?? ""}
        variant="warning"
        confirmLabel="Reset Password"
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push("/admin/users")}
            leftIcon={<ArrowLeft className="h-4 w-4" />}
          >
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-text-primary">
              {user.name}
            </h1>
            <p className="text-text-muted mt-1">{user.email}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowEditModal(true)}
            leftIcon={<Edit className="h-4 w-4" />}
          >
            Edit
          </Button>
          {user.is_suspended ? (
            <Button
              variant="outline"
              size="sm"
              onClick={handleUnsuspend}
              leftIcon={<CheckCircle className="h-4 w-4" />}
            >
              Unsuspend
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowSuspendModal(true)}
              leftIcon={<Ban className="h-4 w-4" />}
            >
              Suspend
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleResetPassword}
            leftIcon={<Key className="h-4 w-4" />}
          >
            Reset Password
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setShowDeleteModal(true)}
            leftIcon={<Trash2 className="h-4 w-4" />}
          >
            Delete
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* User Info Card */}
        <Card className="p-6 space-y-4">
          <h2 className="text-lg font-semibold text-text-primary">
            User Information
          </h2>

          <div className="flex items-center justify-center">
            <div className="h-24 w-24 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white text-3xl font-semibold">
              {user.name.charAt(0).toUpperCase()}
            </div>
          </div>

          <div className="space-y-3 text-sm">
            <div>
              <div className="text-text-muted">Role</div>
              <div className="mt-1">
                <RoleBadge role={user.role} />
              </div>
            </div>

            <div>
              <div className="text-text-muted">Status</div>
              <div className="mt-1">
                {user.is_suspended ? (
                  <Badge variant="danger">Suspended</Badge>
                ) : (
                  <Badge variant="success">Active</Badge>
                )}
              </div>
            </div>

            {user.is_suspended && user.suspension_reason && (
              <div>
                <div className="text-text-muted">Suspension Reason</div>
                <div className="mt-1 text-text-primary">
                  {user.suspension_reason}
                </div>
              </div>
            )}

            <div>
              <div className="text-text-muted">Created</div>
              <div className="mt-1 text-text-primary">
                {format(new Date(user.created_at), "PPP")}
              </div>
            </div>

            {user.last_login && (
              <div>
                <div className="text-text-muted">Last Login</div>
                <div className="mt-1 text-text-primary">
                  {formatDistanceToNow(new Date(user.last_login), {
                    addSuffix: true,
                  })}
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* Subscription Info */}
        <Card className="p-6 space-y-4">
          <h2 className="text-lg font-semibold text-text-primary">
            Subscription
          </h2>

          <div className="space-y-3 text-sm">
            <div>
              <div className="text-text-muted">Tier</div>
              <div className="mt-1">
                <SubscriptionBadge
                  tier={user.subscription_tier}
                  status={user.subscription_status}
                />
              </div>
            </div>

            {user.subscription_expires && (
              <div>
                <div className="text-text-muted">Expires</div>
                <div className="mt-1 text-text-primary">
                  {format(new Date(user.subscription_expires), "PPP")}
                </div>
              </div>
            )}

            {user.lemonsqueezy_customer_id && (
              <div>
                <div className="text-text-muted">Customer ID</div>
                <div className="mt-1 text-text-primary font-mono text-xs">
                  {user.lemonsqueezy_customer_id}
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* Usage Stats */}
        <Card className="p-6 space-y-4">
          <h2 className="text-lg font-semibold text-text-primary">
            Usage Stats
          </h2>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-surface-secondary rounded-lg">
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-primary-500" />
                <span className="text-sm text-text-primary">Articles</span>
              </div>
              <span className="text-lg font-semibold text-text-primary">
                {user.total_articles}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-surface-secondary rounded-lg">
              <div className="flex items-center gap-3">
                <FileEdit className="h-5 w-5 text-primary-500" />
                <span className="text-sm text-text-primary">Outlines</span>
              </div>
              <span className="text-lg font-semibold text-text-primary">
                {user.total_outlines}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-surface-secondary rounded-lg">
              <div className="flex items-center gap-3">
                <Image className="h-5 w-5 text-primary-500" />
                <span className="text-sm text-text-primary">Images</span>
              </div>
              <span className="text-lg font-semibold text-text-primary">
                {user.total_images}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-surface-secondary rounded-lg">
              <div className="flex items-center gap-3">
                <Activity className="h-5 w-5 text-primary-500" />
                <span className="text-sm text-text-primary">Storage</span>
              </div>
              <span className="text-lg font-semibold text-text-primary">
                {user.storage_used_mb.toFixed(1)} MB
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4">
          Recent Activity
        </h2>

        {auditLogs.length === 0 ? (
          <p className="text-text-muted text-center py-8">No recent activity</p>
        ) : (
          <div className="space-y-3">
            {auditLogs.map((log) => (
              <div
                key={log.id}
                className="flex items-start justify-between p-3 bg-surface-secondary rounded-lg"
              >
                <div className="flex-1">
                  <div className="text-sm text-text-primary font-medium">
                    {log.action}
                  </div>
                  {log.resource_type && (
                    <div className="text-xs text-text-muted mt-1">
                      {log.resource_type}
                      {log.resource_id && ` • ${log.resource_id.slice(0, 8)}`}
                    </div>
                  )}
                </div>
                <div className="text-xs text-text-muted">
                  {formatDistanceToNow(new Date(log.created_at), {
                    addSuffix: true,
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Modals */}
      {showEditModal && user && (
        <UserEditModal
          user={user}
          onClose={() => setShowEditModal(false)}
          onSuccess={handleSuccess}
        />
      )}

      {showSuspendModal && user && (
        <SuspendUserModal
          user={user}
          onClose={() => setShowSuspendModal(false)}
          onSuccess={handleSuccess}
        />
      )}

      {showDeleteModal && user && (
        <DeleteUserModal
          user={user}
          onClose={() => setShowDeleteModal(false)}
          onSuccess={handleDelete}
        />
      )}
    </div>
  );
}
