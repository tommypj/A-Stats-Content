"use client";

import { useState } from "react";
import { useProject } from "@/contexts/ProjectContext";
import { Check, ChevronDown, Plus, User, FolderOpen } from "lucide-react";
import { toast } from "sonner";
import { clsx } from "clsx";
import type { Project } from "@/lib/api";

export function ProjectSwitcher() {
  const { projects, currentProject, isPersonalWorkspace, switchProject, isLoading } = useProject();
  const [isOpen, setIsOpen] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const handleSwitch = async (projectId: string | null) => {
    try {
      await switchProject(projectId);
      setIsOpen(false);
    } catch (error) {
      toast.error("Failed to switch project");
    }
  };

  const displayName = isPersonalWorkspace ? "Personal Workspace" : currentProject?.name || "Select Project";
  const displayIcon = isPersonalWorkspace ? User : FolderOpen;
  const Icon = displayIcon;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        aria-expanded={isOpen}
        aria-label="Switch project"
        className={clsx(
          "flex w-full items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
          "bg-primary-900/60 hover:bg-primary-800 border border-primary-700/50",
          isLoading && "opacity-50 cursor-not-allowed"
        )}
      >
        <div className="flex items-center gap-2.5 flex-1 min-w-0">
          {currentProject?.logo_url ? (
            <img
              src={currentProject.logo_url}
              alt={currentProject.name}
              className="h-6 w-6 rounded object-cover"
            />
          ) : (
            <div
              className={clsx(
                "h-6 w-6 rounded flex items-center justify-center",
                isPersonalWorkspace ? "bg-primary-700" : "bg-primary-700"
              )}
            >
              <Icon
                className={clsx(
                  "h-3.5 w-3.5",
                  isPersonalWorkspace ? "text-cream-200" : "text-cream-200"
                )}
              />
            </div>
          )}
          <span className="truncate text-cream-100">{displayName}</span>
        </div>
        <ChevronDown className={clsx("h-4 w-4 text-primary-400 transition-transform", isOpen && "rotate-180")} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute left-0 right-0 mt-2 rounded-xl bg-primary-900/95 backdrop-blur-md border border-primary-700 shadow-lg z-50 max-h-[60vh] overflow-y-auto scrollbar-sidebar">
            <div className="p-2">
              {/* Personal Workspace */}
              <button
                onClick={() => handleSwitch(null)}
                className={clsx(
                  "flex w-full items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors min-h-[44px]",
                  isPersonalWorkspace
                    ? "bg-primary-700/60 text-cream-50"
                    : "text-cream-300 hover:bg-primary-800 hover:text-cream-100"
                )}
              >
                <div className="h-8 w-8 rounded bg-primary-700 flex items-center justify-center">
                  <User className="h-4 w-4 text-cream-200" />
                </div>
                <div className="flex-1 text-left">
                  <div className="font-medium">Personal Workspace</div>
                  <div className="text-xs text-primary-400">Your private workspace</div>
                </div>
                {isPersonalWorkspace && <Check className="h-4 w-4 text-cream-200" />}
              </button>

              {/* Divider */}
              {projects.filter(p => !p.is_personal).length > 0 && <div className="my-2 border-t border-primary-700" />}

              {/* Projects */}
              {projects.filter(p => !p.is_personal).map((project) => (
                <button
                  key={project.id}
                  onClick={() => handleSwitch(project.id)}
                  className={clsx(
                    "flex w-full items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors min-h-[44px]",
                    currentProject?.id === project.id
                      ? "bg-primary-700/60 text-cream-50"
                      : "text-cream-300 hover:bg-primary-800 hover:text-cream-100"
                  )}
                >
                  {project.logo_url ? (
                    <img src={project.logo_url} alt={project.name} className="h-8 w-8 rounded object-cover" />
                  ) : (
                    <div className="h-8 w-8 rounded bg-primary-700 flex items-center justify-center">
                      <FolderOpen className="h-4 w-4 text-cream-200" />
                    </div>
                  )}
                  <div className="flex-1 text-left min-w-0">
                    <div className="font-medium truncate">{project.name}</div>
                    <div className="text-xs text-primary-400">
                      {project.member_count} {project.member_count === 1 ? "member" : "members"} · {getRoleLabel(project.my_role)}
                    </div>
                  </div>
                  {currentProject?.id === project.id && <Check className="h-4 w-4 text-cream-200" />}
                </button>
              ))}

              {/* Create Project */}
              <div className="mt-2 pt-2 border-t border-primary-700">
                <button
                  onClick={() => {
                    setIsOpen(false);
                    setShowCreateModal(true);
                  }}
                  className="flex w-full items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-cream-300 hover:bg-primary-800 hover:text-cream-100 transition-colors min-h-[44px]"
                >
                  <div className="h-8 w-8 rounded border-2 border-dashed border-primary-600 flex items-center justify-center">
                    <Plus className="h-4 w-4 text-primary-400" />
                  </div>
                  <span className="font-medium">Create Project</span>
                </button>
              </div>

              {/* Keyboard hint */}
              <div className="mt-2 px-3 py-2 text-xs text-primary-400 text-center border-t border-primary-700">
                <kbd className="px-2 py-1 bg-primary-800 rounded text-xs font-mono text-cream-300">⌘</kbd>
                {" + "}
                <kbd className="px-2 py-1 bg-primary-800 rounded text-xs font-mono text-cream-300">T</kbd>
                {" to switch projects"}
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
