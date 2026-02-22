import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface User {
  id: string;
  email: string;
  name: string;
  role: "user" | "admin";
  subscription_tier: "free" | "starter" | "professional" | "enterprise";
}

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setRefreshToken: (refreshToken: string | null) => void;
  login: (user: User, token: string, refreshToken?: string) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: true,

      setUser: (user) =>
        set({
          user,
          isAuthenticated: !!user,
        }),

      setToken: (token) => {
        if (token) {
          localStorage.setItem("auth_token", token);
        } else {
          localStorage.removeItem("auth_token");
        }
        set({ token });
      },

      setRefreshToken: (refreshToken) => {
        if (refreshToken) {
          localStorage.setItem("refresh_token", refreshToken);
        } else {
          localStorage.removeItem("refresh_token");
        }
        set({ refreshToken });
      },

      login: (user, token, refreshToken) => {
        localStorage.setItem("auth_token", token);
        if (refreshToken) {
          localStorage.setItem("refresh_token", refreshToken);
        }
        set({
          user,
          token,
          refreshToken: refreshToken || null,
          isAuthenticated: true,
          isLoading: false,
        });
      },

      logout: () => {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("refresh_token");
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
        });
      },

      setLoading: (isLoading) => set({ isLoading }),
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
