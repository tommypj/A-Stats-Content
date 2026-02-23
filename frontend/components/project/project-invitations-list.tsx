"use client";

import { useState } from "react";
import { ProjectInvitation, ProjectRole } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Mail, X, RefreshCw, Clock, CheckCircle, XCircle } from "lucide-react";
import { format, isPast } from "date-fns";

interface ProjectInvitationsListProps {
  invitations: ProjectInvitation[];
  onRevoke: (invitationId: string) => Promise<void>;
  onResend: (invitationId: string) => Promise<void>;
}

const statusConfig = {
  pending: { icon: Clock, color: "bg-yellow-100 text-yellow-800 border-yellow-300", label: "Pending" },
  accepted: { icon: CheckCircle, color: "bg-green-100 text-green-800 border-green-300", label: "Accepted" },
  expired: { icon: XCircle, color: "bg-gray-100 text-gray-800 border-gray-300", label: "Expired" },
  revoked: { icon: XCircle, color: "bg-red-100 text-red-800 border-red-300", label: "Revoked" },
};

const roleColors = {
  owner: "bg-yellow-100 text-yellow-800",
  admin: "bg-purple-100 text-purple-800",
  member: "bg-blue-100 text-blue-800",
  viewer: "bg-gray-100 text-gray-800",
};

export function ProjectInvitationsList({ invitations, onRevoke, onResend }: ProjectInvitationsListProps) {
  const [loadingInvitation, setLoadingInvitation] = useState<string | null>(null);

  const handleRevoke = async (invitationId: string) => {
    if (!confirm("Are you sure you want to revoke this invitation?")) {
      return;
    }

    setLoadingInvitation(invitationId);
    try {
      await onRevoke(invitationId);
    } finally {
      setLoadingInvitation(null);
    }
  };

  const handleResend = async (invitationId: string) => {
    setLoadingInvitation(invitationId);
    try {
      await onResend(invitationId);
    } finally {
      setLoadingInvitation(null);
    }
  };

  const isExpired = (invitation: ProjectInvitation) => {
    return isPast(new Date(invitation.expires_at)) && invitation.status === "pending";
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-text-primary">
          Pending Invitations ({invitations.filter(i => i.status === "pending").length})
        </h3>
      </div>

      <div className="space-y-3">
        {invitations.map((invitation) => {
          const status = isExpired(invitation) ? "expired" : invitation.status;
          const StatusIcon = statusConfig[status].icon;
          const canRevoke = status === "pending";
          const canResend = status === "expired" || status === "pending";

          return (
            <div
              key={invitation.id}
              className={`flex items-center justify-between p-4 rounded-xl border transition-colors ${
                status === "expired" || status === "revoked"
                  ? "border-surface-tertiary opacity-60"
                  : "border-surface-tertiary hover:border-primary-200"
              }`}
            >
              <div className="flex items-center gap-4 flex-1">
                {/* Icon */}
                <div className="h-12 w-12 rounded-full bg-primary-100 flex items-center justify-center">
                  <Mail className="h-6 w-6 text-primary-600" />
                </div>

                {/* Info */}
                <div className="flex-1">
                  <p className="font-medium text-text-primary">{invitation.email}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge className={roleColors[invitation.role]}>
                      {invitation.role.charAt(0).toUpperCase() + invitation.role.slice(1)}
                    </Badge>
                    <Badge className={statusConfig[status].color}>
                      <StatusIcon className="h-3 w-3 mr-1" />
                      {statusConfig[status].label}
                    </Badge>
                  </div>
                  <p className="text-xs text-text-muted mt-1">
                    Invited by {invitation.invited_by_name} on{" "}
                    {format(new Date(invitation.created_at), "MMM d, yyyy")}
                  </p>
                  <p className="text-xs text-text-muted">
                    Expires {format(new Date(invitation.expires_at), "MMM d, yyyy")}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  {canResend && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleResend(invitation.id)}
                      disabled={loadingInvitation === invitation.id}
                      leftIcon={<RefreshCw className="h-3 w-3" />}
                    >
                      Resend
                    </Button>
                  )}
                  {canRevoke && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRevoke(invitation.id)}
                      disabled={loadingInvitation === invitation.id}
                      className="text-red-500 hover:text-red-600 hover:bg-red-50"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {invitations.length === 0 && (
          <div className="text-center py-8 text-text-muted">
            No invitations sent yet
          </div>
        )}
      </div>
    </Card>
  );
}
