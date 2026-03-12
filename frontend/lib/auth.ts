/**
 * Authentication utilities and hooks.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth";
import { api } from "./api";

/**
 * Hook to require authentication.
 * Redirects to login if not authenticated.
 * Validates the session server-side via /auth/me on initial load.
 */
export function useRequireAuth(redirectTo: string = "/login") {
  const router = useRouter();
  const { isAuthenticated, isLoading, setUser, setLoading } = useAuthStore();

  useEffect(() => {
    async function checkAuth() {
      if (isAuthenticated) {
        // Zustand says we are authenticated — verify server-side via cookie.
        try {
          const user = await api.auth.me();
          setUser({
            id: user.id,
            email: user.email,
            name: user.name,
            role: user.role as "user" | "admin" | "super_admin",
            subscription_tier: (user.subscription_tier || "free") as "free" | "starter" | "professional" | "enterprise",
          });
        } catch (error) {
          const status = (error instanceof Error && "response" in error) ? (error as { response?: { status?: number } }).response?.status : undefined;
          if (status === 401 || status === 403) {
            // Cookie invalid or expired — clear state and redirect.
            // No localStorage to clean up — cookies are managed by the browser.
            setUser(null);
            router.push(redirectTo);
          } else {
            // Network or server error — don't log the user out.
            console.error("Auth check failed:", error);
            setLoading(false);
          }
        }
      } else {
        router.push(redirectTo);
      }
      setLoading(false);
    }

    if (isLoading) {
      checkAuth();
    } else if (!isAuthenticated) {
      router.push(redirectTo);
    }
  }, [isAuthenticated, isLoading, router, redirectTo, setUser, setLoading]);

  return { isAuthenticated, isLoading };
}

