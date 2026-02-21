"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from "react";
import { api } from "@/lib/api";
import type { Team, TeamCreateRequest } from "@/lib/api";

export interface TeamContextType {
  currentTeam: Team | null;
  teams: Team[];
  isLoading: boolean;
  isPersonalWorkspace: boolean;

  // Actions
  switchTeam: (teamId: string | null) => Promise<void>;
  refreshTeams: () => Promise<void>;
  createTeam: (data: TeamCreateRequest) => Promise<Team>;

  // Permission helpers
  canCreate: boolean; // MEMBER+ in team, or personal workspace
  canEdit: boolean; // MEMBER+ in team, or personal workspace
  canManage: boolean; // ADMIN+ in team
  canBilling: boolean; // OWNER in team
  isViewer: boolean; // VIEWER role in team

  // Usage tracking
  usage: { articles_used: number; outlines_used: number; images_used: number } | null;
  limits: { articles_per_month: number; outlines_per_month: number; images_per_month: number } | null;
  isAtLimit: (resource: "articles" | "outlines" | "images") => boolean;
}

const TeamContext = createContext<TeamContextType | undefined>(undefined);

const STORAGE_KEY = "current_team_id";

export function TeamProvider({ children }: { children: ReactNode }) {
  const [teams, setTeams] = useState<Team[]>([]);
  const [currentTeam, setCurrentTeam] = useState<Team | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check if user is in personal workspace (no team selected)
  const isPersonalWorkspace = currentTeam === null;

  // Permission helpers
  const canEdit = isPersonalWorkspace || ["owner", "admin", "member"].includes(currentTeam?.my_role || "");
  const canCreate = canEdit;
  const canManage = !isPersonalWorkspace && ["owner", "admin"].includes(currentTeam?.my_role || "");
  const canBilling = !isPersonalWorkspace && currentTeam?.my_role === "owner";
  const isViewer = !isPersonalWorkspace && currentTeam?.my_role === "viewer";

  // Usage and limits stubs (populated when team billing is loaded)
  const [usage, setUsage] = useState<{ articles_used: number; outlines_used: number; images_used: number } | null>(null);
  const [limits, setLimits] = useState<{ articles_per_month: number; outlines_per_month: number; images_per_month: number } | null>(null);

  const isAtLimit = useCallback((resource: "articles" | "outlines" | "images"): boolean => {
    if (!usage || !limits) return false;
    const usageMap = { articles: usage.articles_used, outlines: usage.outlines_used, images: usage.images_used };
    const limitMap = { articles: limits.articles_per_month, outlines: limits.outlines_per_month, images: limits.images_per_month };
    return usageMap[resource] >= limitMap[resource];
  }, [usage, limits]);

  // Load teams and current team on mount
  const loadTeams = useCallback(async () => {
    try {
      setIsLoading(true);

      // Fetch all teams
      const allTeams = await api.teams.list();
      setTeams(allTeams);

      // Try to get current team from API
      try {
        const current = await api.teams.getCurrent();
        setCurrentTeam(current);

        // Update localStorage
        if (current) {
          localStorage.setItem(STORAGE_KEY, current.id);
        } else {
          localStorage.removeItem(STORAGE_KEY);
        }
      } catch (error) {
        // If API doesn't return current team, try localStorage
        const savedTeamId = localStorage.getItem(STORAGE_KEY);
        if (savedTeamId) {
          const savedTeam = allTeams.find((t) => t.id === savedTeamId);
          if (savedTeam) {
            setCurrentTeam(savedTeam);
          } else {
            // Team no longer exists, clear localStorage
            localStorage.removeItem(STORAGE_KEY);
            setCurrentTeam(null);
          }
        } else {
          setCurrentTeam(null);
        }
      }
    } catch (error) {
      console.error("Failed to load teams:", error);
      setTeams([]);
      setCurrentTeam(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadTeams();
  }, [loadTeams]);

  // Switch to a different team (or null for personal workspace)
  const switchTeam = useCallback(async (teamId: string | null) => {
    try {
      // Call API to switch context
      await api.teams.switch(teamId);

      // Update local state
      if (teamId === null) {
        setCurrentTeam(null);
        localStorage.removeItem(STORAGE_KEY);
      } else {
        const team = teams.find((t) => t.id === teamId);
        if (team) {
          setCurrentTeam(team);
          localStorage.setItem(STORAGE_KEY, teamId);
        }
      }
    } catch (error) {
      console.error("Failed to switch team:", error);
      throw error;
    }
  }, [teams]);

  // Refresh teams from API
  const refreshTeams = useCallback(async () => {
    await loadTeams();
  }, [loadTeams]);

  // Create a new team
  const createTeam = useCallback(async (data: TeamCreateRequest): Promise<Team> => {
    try {
      const newTeam = await api.teams.create(data);

      // Refresh teams list
      await refreshTeams();

      // Auto-switch to the new team
      await switchTeam(newTeam.id);

      return newTeam;
    } catch (error) {
      console.error("Failed to create team:", error);
      throw error;
    }
  }, [refreshTeams, switchTeam]);

  const value: TeamContextType = {
    teams,
    currentTeam,
    isLoading,
    isPersonalWorkspace,
    switchTeam,
    refreshTeams,
    createTeam,
    canCreate,
    canEdit,
    canManage,
    canBilling,
    isViewer,
    usage,
    limits,
    isAtLimit,
  };

  return <TeamContext.Provider value={value}>{children}</TeamContext.Provider>;
}

export function useTeam() {
  const context = useContext(TeamContext);
  if (context === undefined) {
    throw new Error("useTeam must be used within a TeamProvider");
  }
  return context;
}
