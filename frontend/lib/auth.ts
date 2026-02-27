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
 */
export function useRequireAuth(redirectTo: string = "/login") {
  const router = useRouter();
  const { isAuthenticated, isLoading, setUser, setLoading, token } = useAuthStore();

  useEffect(() => {
    async function checkAuth() {
      if (token) {
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
          const status = (error as any)?.response?.status;
          if (status === 401 || status === 403) {
            // Token invalid or forbidden — clear and redirect
            localStorage.removeItem("auth_token");
            setUser(null);
            router.push(redirectTo);
          } else {
            // Network or server error — don't log the user out
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
  }, [isAuthenticated, isLoading, token, router, redirectTo, setUser, setLoading]);

  return { isAuthenticated, isLoading };
}

/**
 * Hook to redirect if already authenticated.
 * Used on login/register pages.
 */
export function useRedirectIfAuthenticated(redirectTo: string = "/dashboard") {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuthStore();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push(redirectTo);
    }
  }, [isAuthenticated, isLoading, router, redirectTo]);

  return { isAuthenticated, isLoading };
}

/**
 * Check if user has required role.
 */
export function useRequireRole(requiredRole: "admin" | "super_admin" | "user") {
  const { user, isAuthenticated } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated && user) {
      if (requiredRole === "admin" && user.role !== "admin" && user.role !== "super_admin") {
        router.push("/dashboard");
      }
    }
  }, [user, isAuthenticated, requiredRole, router]);

  return { hasRole: user?.role === requiredRole || user?.role === "admin" || user?.role === "super_admin" };
}

/**
 * Get auth headers for API requests.
 */
export function getAuthHeaders(): Record<string, string> {
  const token = typeof window !== "undefined"
    ? localStorage.getItem("auth_token")
    : null;

  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}
