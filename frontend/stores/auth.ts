import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface User {
  id: string;
  email: string;
  name: string;
  role: "user" | "admin" | "super_admin";
  subscription_tier: "free" | "starter" | "professional" | "enterprise";
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  setUser: (user: User | null) => void;
  login: (user: User) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: true,

      setUser: (user) =>
        set({
          user,
          isAuthenticated: !!user,
        }),

      login: (user) => {
        // Tokens are stored in HttpOnly cookies set by the server — no localStorage writes needed.
        set({
          user,
          isAuthenticated: true,
          isLoading: false,
        });
      },

      logout: () => {
        // Cookies are cleared by the backend /auth/logout endpoint.
        // Here we only clear Zustand state.
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
        });
      },

      setLoading: (isLoading) => set({ isLoading }),
    }),
    {
      name: "auth-storage",
      // Only persist user object and isAuthenticated flag.
      // This prevents a flash of "not authenticated" on page refresh
      // while the actual auth is re-validated server-side via cookie.
      // Tokens are NOT persisted — they live in HttpOnly cookies.
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
