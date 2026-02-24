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
            role: user.role as "user" | "admin",
            subscription_tier: (user.subscription_tier || "free") as "free" | "starter" | "professional" | "enterprise",
          });
        } catch {
          // Token invalid, clear it
          localStorage.removeItem("auth_token");
          setUser(null);
          router.push(redirectTo);
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
export function useRequireRole(requiredRole: "admin" | "user") {
  const { user, isAuthenticated } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated && user) {
      if (requiredRole === "admin" && user.role !== "admin") {
        router.push("/dashboard");
      }
    }
  }, [user, isAuthenticated, requiredRole, router]);

  return { hasRole: user?.role === requiredRole || user?.role === "admin" };
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
