"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from "react";
import { api } from "@/lib/api";
import type { Project, ProjectCreateRequest } from "@/lib/api";

export interface ProjectContextType {
  currentProject: Project | null;
  projects: Project[];
  isLoading: boolean;
  isPersonalWorkspace: boolean;

  // Actions
  switchProject: (projectId: string | null) => Promise<void>;
  refreshProjects: () => Promise<void>;
  createProject: (data: ProjectCreateRequest) => Promise<Project>;

  // Permission helpers
  canCreate: boolean; // MEMBER+ in project, or personal workspace
  canEdit: boolean; // MEMBER+ in project, or personal workspace
  canManage: boolean; // ADMIN+ in project
  canBilling: boolean; // OWNER in project
  isViewer: boolean; // VIEWER role in project

  // Usage tracking
  usage: { articles_used: number; outlines_used: number; images_used: number } | null;
  limits: { articles_per_month: number; outlines_per_month: number; images_per_month: number } | null;
  isAtLimit: (resource: "articles" | "outlines" | "images") => boolean;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

const STORAGE_KEY = "current_project_id";

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check if user is in personal workspace (no project selected or personal project)
  const isPersonalWorkspace = currentProject === null || currentProject?.is_personal === true;

  // Permission helpers
  const canEdit = isPersonalWorkspace || ["owner", "admin", "member"].includes(currentProject?.my_role || "");
  const canCreate = canEdit;
  const canManage = !isPersonalWorkspace && ["owner", "admin"].includes(currentProject?.my_role || "");
  const canBilling = !isPersonalWorkspace && currentProject?.my_role === "owner";
  const isViewer = !isPersonalWorkspace && currentProject?.my_role === "viewer";

  // Usage and limits stubs (populated when project billing is loaded)
  const [usage, setUsage] = useState<{ articles_used: number; outlines_used: number; images_used: number } | null>(null);
  const [limits, setLimits] = useState<{ articles_per_month: number; outlines_per_month: number; images_per_month: number } | null>(null);

  const isAtLimit = useCallback((resource: "articles" | "outlines" | "images"): boolean => {
    if (!usage || !limits) return false;
    const usageMap = { articles: usage.articles_used, outlines: usage.outlines_used, images: usage.images_used };
    const limitMap = { articles: limits.articles_per_month, outlines: limits.outlines_per_month, images: limits.images_per_month };
    return usageMap[resource] >= limitMap[resource];
  }, [usage, limits]);

  // Load projects and current project on mount
  const loadProjects = useCallback(async () => {
    try {
      setIsLoading(true);

      // Fetch all projects
      const allProjects = await api.projects.list();
      setProjects(allProjects);

      // Try to get current project from API
      try {
        const current = await api.projects.getCurrent();
        setCurrentProject(current);

        // Update localStorage
        if (current) {
          localStorage.setItem(STORAGE_KEY, current.id);
        } else {
          localStorage.removeItem(STORAGE_KEY);
        }
      } catch (error) {
        // If API doesn't return current project, try localStorage
        const savedProjectId = localStorage.getItem(STORAGE_KEY);
        if (savedProjectId) {
          const savedProject = allProjects.find((t) => t.id === savedProjectId);
          if (savedProject) {
            setCurrentProject(savedProject);
          } else {
            // Project no longer exists, clear localStorage
            localStorage.removeItem(STORAGE_KEY);
            setCurrentProject(null);
          }
        } else {
          setCurrentProject(null);
        }
      }
    } catch (error) {
      console.error("Failed to load projects:", error);
      setProjects([]);
      setCurrentProject(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial load — only fire if a token is present; the interceptor handles
  // the redirect when no token exists or when refresh fails.
  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
    if (token) {
      loadProjects();
    }
  }, [loadProjects]);

  // Switch to a different project (or null for personal workspace)
  const switchProject = useCallback(async (projectId: string | null) => {
    try {
      // Call API to switch context
      await api.projects.switch(projectId);

      // Update local state
      if (projectId === null) {
        setCurrentProject(null);
        localStorage.removeItem(STORAGE_KEY);
      } else {
        const project = projects.find((t) => t.id === projectId);
        if (project) {
          setCurrentProject(project);
          localStorage.setItem(STORAGE_KEY, projectId);
        }
      }
    } catch (error) {
      console.error("Failed to switch project:", error);
      throw error;
    }
  }, [projects]);

  // Refresh projects from API
  const refreshProjects = useCallback(async () => {
    await loadProjects();
  }, [loadProjects]);

  // Create a new project
  const createProject = useCallback(async (data: ProjectCreateRequest): Promise<Project> => {
    try {
      const newProject = await api.projects.create(data);

      // Refresh projects list
      await refreshProjects();

      // Auto-switch to the new project
      await switchProject(newProject.id);

      return newProject;
    } catch (error) {
      console.error("Failed to create project:", error);
      throw error;
    }
  }, [refreshProjects, switchProject]);

  const value: ProjectContextType = {
    projects,
    currentProject,
    isLoading,
    isPersonalWorkspace,
    switchProject,
    refreshProjects,
    createProject,
    canCreate,
    canEdit,
    canManage,
    canBilling,
    isViewer,
    usage,
    limits,
    isAtLimit,
  };

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProject() {
  const context = useContext(ProjectContext);
  if (context === undefined) {
    throw new Error("useProject must be used within a ProjectProvider");
  }
  return context;
}
