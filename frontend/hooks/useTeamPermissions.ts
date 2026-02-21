import { useTeam } from "@/contexts/TeamContext";
import type { TeamRole } from "@/lib/api";

export interface TeamPermissions {
  // Role checks
  isOwner: boolean;
  isAdmin: boolean;
  isMember: boolean;
  isViewer: boolean;

  // Permission checks
  canCreateContent: boolean; // MEMBER+ or personal workspace
  canEditContent: boolean; // MEMBER+ or personal workspace
  canDeleteContent: boolean; // ADMIN+ or personal workspace
  canManageMembers: boolean; // ADMIN+ in team
  canManageBilling: boolean; // OWNER in team
  canManageSettings: boolean; // ADMIN+ in team
  canInviteMembers: boolean; // ADMIN+ in team

  // Helpers
  hasRole: (role: TeamRole) => boolean;
  hasMinRole: (minRole: TeamRole) => boolean;
}

const roleHierarchy: TeamRole[] = ["viewer", "member", "admin", "owner"];

function getRoleLevel(role: TeamRole): number {
  return roleHierarchy.indexOf(role);
}

export function useTeamPermissions(): TeamPermissions {
  const { currentTeam, isPersonalWorkspace } = useTeam();

  const currentRole = currentTeam?.my_role;

  // Role checks
  const isOwner = currentRole === "owner";
  const isAdmin = currentRole === "admin" || isOwner;
  const isMember = currentRole === "member" || isAdmin;
  const isViewer = currentRole === "viewer";

  // Permission checks
  const canCreateContent = isPersonalWorkspace || isMember;
  const canEditContent = isPersonalWorkspace || isMember;
  const canDeleteContent = isPersonalWorkspace || isAdmin;
  const canManageMembers = !isPersonalWorkspace && isAdmin;
  const canManageBilling = !isPersonalWorkspace && isOwner;
  const canManageSettings = !isPersonalWorkspace && isAdmin;
  const canInviteMembers = !isPersonalWorkspace && isAdmin;

  // Helper functions
  const hasRole = (role: TeamRole): boolean => {
    if (isPersonalWorkspace) return false;
    return currentRole === role;
  };

  const hasMinRole = (minRole: TeamRole): boolean => {
    if (isPersonalWorkspace) {
      // In personal workspace, consider user as having all permissions
      return true;
    }
    if (!currentRole) return false;
    return getRoleLevel(currentRole) >= getRoleLevel(minRole);
  };

  return {
    isOwner,
    isAdmin,
    isMember,
    isViewer,
    canCreateContent,
    canEditContent,
    canDeleteContent,
    canManageMembers,
    canManageBilling,
    canManageSettings,
    canInviteMembers,
    hasRole,
    hasMinRole,
  };
}
