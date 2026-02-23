import { useProject } from "@/contexts/ProjectContext";
import type { ProjectRole } from "@/lib/api";

export interface ProjectPermissions {
  // Role checks
  isOwner: boolean;
  isAdmin: boolean;
  isMember: boolean;
  isViewer: boolean;

  // Permission checks
  canCreateContent: boolean; // MEMBER+ or personal workspace
  canEditContent: boolean; // MEMBER+ or personal workspace
  canDeleteContent: boolean; // ADMIN+ or personal workspace
  canManageMembers: boolean; // ADMIN+ in project
  canManageBilling: boolean; // OWNER in project
  canManageSettings: boolean; // ADMIN+ in project
  canInviteMembers: boolean; // ADMIN+ in project

  // Helpers
  hasRole: (role: ProjectRole) => boolean;
  hasMinRole: (minRole: ProjectRole) => boolean;
}

const roleHierarchy: ProjectRole[] = ["viewer", "member", "admin", "owner"];

function getRoleLevel(role: ProjectRole): number {
  return roleHierarchy.indexOf(role);
}

export function useProjectPermissions(): ProjectPermissions {
  const { currentProject, isPersonalWorkspace } = useProject();

  const currentRole = currentProject?.my_role;

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
  const hasRole = (role: ProjectRole): boolean => {
    if (isPersonalWorkspace) return false;
    return currentRole === role;
  };

  const hasMinRole = (minRole: ProjectRole): boolean => {
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

// Backward-compatible alias
export const useTeamPermissions = useProjectPermissions;
export type TeamPermissions = ProjectPermissions;
