"use client";

import { useState } from "react";
import { ProjectMember, ProjectRole } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Trash2, Crown, Shield, User as UserIcon, Eye } from "lucide-react";
import { format } from "date-fns";

interface ProjectMembersListProps {
  members: ProjectMember[];
  myRole: ProjectRole;
  onUpdateRole: (userId: string, role: ProjectRole) => Promise<void>;
  onRemove: (userId: string, memberName: string) => Promise<void>;
}

const roleIcons = {
  owner: Crown,
  admin: Shield,
  member: UserIcon,
  viewer: Eye,
};

const roleColors = {
  owner: "bg-yellow-100 text-yellow-800 border-yellow-300",
  admin: "bg-purple-100 text-purple-800 border-purple-300",
  member: "bg-blue-100 text-blue-800 border-blue-300",
  viewer: "bg-gray-100 text-gray-800 border-gray-300",
};

export function ProjectMembersList({ members, myRole, onUpdateRole, onRemove }: ProjectMembersListProps) {
  const [loadingMember, setLoadingMember] = useState<string | null>(null);

  const canManageMembers = myRole === "owner" || myRole === "admin";

  const handleRoleChange = async (userId: string, newRole: ProjectRole) => {
    setLoadingMember(userId);
    try {
      await onUpdateRole(userId, newRole);
    } finally {
      setLoadingMember(null);
    }
  };

  const handleRemove = async (userId: string, memberName: string) => {
    if (!confirm(`Are you sure you want to remove ${memberName} from the project?`)) {
      return;
    }

    setLoadingMember(userId);
    try {
      await onRemove(userId, memberName);
    } finally {
      setLoadingMember(null);
    }
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-text-primary">
          Project Members ({members.length})
        </h3>
      </div>

      <div className="space-y-3">
        {members.map((member) => {
          const RoleIcon = roleIcons[member.role];
          const isOwner = member.role === "owner";
          const canEdit = canManageMembers && !isOwner && member.user_id !== loadingMember;

          return (
            <div
              key={member.id}
              className="flex items-center justify-between p-4 rounded-xl border border-surface-tertiary hover:border-primary-200 transition-colors"
            >
              <div className="flex items-center gap-4 flex-1">
                {/* Avatar */}
                <div className="h-12 w-12 rounded-full bg-primary-100 flex items-center justify-center">
                  {member.avatar_url ? (
                    <img
                      src={member.avatar_url}
                      alt={member.name}
                      className="h-full w-full rounded-full object-cover"
                    />
                  ) : (
                    <span className="text-lg font-medium text-primary-600">
                      {member.name.charAt(0).toUpperCase()}
                    </span>
                  )}
                </div>

                {/* Info */}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-text-primary">{member.name}</p>
                    {isOwner && <Crown className="h-4 w-4 text-yellow-500" />}
                  </div>
                  <p className="text-sm text-text-muted">{member.email}</p>
                  <p className="text-xs text-text-muted mt-1">
                    Joined {format(new Date(member.joined_at), "MMM d, yyyy")}
                  </p>
                </div>

                {/* Role Badge & Selector */}
                <div className="flex items-center gap-3">
                  {canEdit ? (
                    <select
                      value={member.role}
                      onChange={(e) => handleRoleChange(member.user_id, e.target.value as ProjectRole)}
                      disabled={loadingMember === member.user_id}
                      className="px-3 py-1.5 rounded-lg border border-surface-tertiary bg-white text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="admin">Admin</option>
                      <option value="member">Member</option>
                      <option value="viewer">Viewer</option>
                    </select>
                  ) : (
                    <Badge className={roleColors[member.role]}>
                      <RoleIcon className="h-3 w-3 mr-1" />
                      {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                    </Badge>
                  )}

                  {/* Remove Button */}
                  {canEdit && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemove(member.user_id, member.name)}
                      disabled={loadingMember === member.user_id}
                      className="text-red-500 hover:text-red-600 hover:bg-red-50"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {members.length === 0 && (
          <div className="text-center py-8 text-text-muted">
            No members found
          </div>
        )}
      </div>
    </Card>
  );
}
