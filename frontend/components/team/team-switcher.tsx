"use client";

import { useState } from "react";
import { useTeam } from "@/contexts/TeamContext";
import { Check, ChevronDown, Plus, User, Users } from "lucide-react";
import { clsx } from "clsx";
import type { Team } from "@/lib/api";

export function TeamSwitcher() {
  const { teams, currentTeam, isPersonalWorkspace, switchTeam, isLoading } = useTeam();
  const [isOpen, setIsOpen] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const handleSwitch = async (teamId: string | null) => {
    try {
      await switchTeam(teamId);
      setIsOpen(false);
    } catch (error) {
      console.error("Failed to switch team:", error);
    }
  };

  const displayName = isPersonalWorkspace ? "Personal Workspace" : currentTeam?.name || "Select Team";
  const displayIcon = isPersonalWorkspace ? User : Users;
  const Icon = displayIcon;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className={clsx(
          "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
          "hover:bg-surface-secondary",
          "border border-surface-tertiary",
          "min-w-[200px]",
          isLoading && "opacity-50 cursor-not-allowed"
        )}
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {currentTeam?.logo_url ? (
            <img
              src={currentTeam.logo_url}
              alt={currentTeam.name}
              className="h-5 w-5 rounded object-cover"
            />
          ) : (
            <div
              className={clsx(
                "h-5 w-5 rounded flex items-center justify-center",
                isPersonalWorkspace ? "bg-blue-100" : "bg-primary-100"
              )}
            >
              <Icon
                className={clsx(
                  "h-3 w-3",
                  isPersonalWorkspace ? "text-blue-600" : "text-primary-600"
                )}
              />
            </div>
          )}
          <span className="truncate text-text-primary">{displayName}</span>
        </div>
        <ChevronDown className={clsx("h-4 w-4 text-text-muted transition-transform", isOpen && "rotate-180")} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute left-0 mt-2 w-64 bg-white rounded-xl border border-surface-tertiary shadow-lg z-50">
            <div className="p-2">
              {/* Personal Workspace */}
              <button
                onClick={() => handleSwitch(null)}
                className={clsx(
                  "flex w-full items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                  isPersonalWorkspace
                    ? "bg-primary-50 text-primary-600"
                    : "text-text-secondary hover:bg-surface-secondary hover:text-text-primary"
                )}
              >
                <div className="h-8 w-8 rounded bg-blue-100 flex items-center justify-center">
                  <User className="h-4 w-4 text-blue-600" />
                </div>
                <div className="flex-1 text-left">
                  <div className="font-medium">Personal Workspace</div>
                  <div className="text-xs text-text-muted">Your private workspace</div>
                </div>
                {isPersonalWorkspace && <Check className="h-4 w-4 text-primary-600" />}
              </button>

              {/* Divider */}
              {teams.length > 0 && <div className="my-2 border-t border-surface-tertiary" />}

              {/* Teams */}
              {teams.map((team) => (
                <button
                  key={team.id}
                  onClick={() => handleSwitch(team.id)}
                  className={clsx(
                    "flex w-full items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                    currentTeam?.id === team.id
                      ? "bg-primary-50 text-primary-600"
                      : "text-text-secondary hover:bg-surface-secondary hover:text-text-primary"
                  )}
                >
                  {team.logo_url ? (
                    <img src={team.logo_url} alt={team.name} className="h-8 w-8 rounded object-cover" />
                  ) : (
                    <div className="h-8 w-8 rounded bg-primary-100 flex items-center justify-center">
                      <Users className="h-4 w-4 text-primary-600" />
                    </div>
                  )}
                  <div className="flex-1 text-left min-w-0">
                    <div className="font-medium truncate">{team.name}</div>
                    <div className="text-xs text-text-muted">
                      {team.member_count} {team.member_count === 1 ? "member" : "members"} · {getRoleLabel(team.my_role)}
                    </div>
                  </div>
                  {currentTeam?.id === team.id && <Check className="h-4 w-4 text-primary-600" />}
                </button>
              ))}

              {/* Create Team */}
              <div className="mt-2 pt-2 border-t border-surface-tertiary">
                <button
                  onClick={() => {
                    setIsOpen(false);
                    setShowCreateModal(true);
                  }}
                  className="flex w-full items-center gap-3 px-3 py-2 rounded-lg text-sm text-text-secondary hover:bg-surface-secondary hover:text-text-primary transition-colors"
                >
                  <div className="h-8 w-8 rounded border-2 border-dashed border-surface-tertiary flex items-center justify-center">
                    <Plus className="h-4 w-4 text-text-muted" />
                  </div>
                  <span className="font-medium">Create Team</span>
                </button>
              </div>

              {/* Keyboard hint */}
              <div className="mt-2 px-3 py-2 text-xs text-text-muted text-center border-t border-surface-tertiary">
                <kbd className="px-2 py-1 bg-surface-secondary rounded text-xs font-mono">⌘</kbd>
                {" + "}
                <kbd className="px-2 py-1 bg-surface-secondary rounded text-xs font-mono">T</kbd>
                {" to switch teams"}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function getRoleLabel(role: string): string {
  const labels: Record<string, string> = {
    owner: "Owner",
    admin: "Admin",
    member: "Member",
    viewer: "Viewer",
  };
  return labels[role] || role;
}
