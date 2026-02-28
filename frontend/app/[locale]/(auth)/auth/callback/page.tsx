"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api, parseApiError } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

const ERROR_MESSAGES: Record<string, string> = {
  google_denied: "Google sign-in was cancelled.",
  google_invalid: "Invalid OAuth response from Google.",
  google_state_invalid: "OAuth session expired. Please try again.",
  google_token_failed: "Failed to exchange Google token. Please try again.",
  google_token_invalid: "Invalid token received from Google.",
  google_email_unverified: "Your Google account email is not verified.",
  google_failed: "Google sign-in failed. Please try again.",
};

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuthStore();

  useEffect(() => {
    const error = searchParams.get("error");

    if (error) {
      const message = ERROR_MESSAGES[error] ?? "Sign-in failed. Please try again.";
      toast.error(message);
      router.replace("/login");
      return;
    }

    // Cookies were set by the backend — just call /me to hydrate Zustand
    const hydrate = async () => {
      try {
        const user = await api.auth.me();
        login({
          id: user.id,
          email: user.email,
          name: user.name,
          role: user.role as "user" | "admin" | "super_admin",
          subscription_tier:
            (user.subscription_tier as "free" | "starter" | "professional" | "enterprise") ||
            "free",
        });

        const isNew = searchParams.get("new") === "1";
        if (isNew) {
          toast.success("Welcome to A-Stats Content!");
        } else {
          toast.success("Welcome back!");
        }

        router.replace("/dashboard");
      } catch (err) {
        toast.error(parseApiError(err).message || "Sign-in failed. Please try again.");
        router.replace("/login");
      }
    };

    hydrate();
  }, [searchParams, router, login]);

  return (
    <div className="card p-8 text-center space-y-4">
      <Loader2 className="h-8 w-8 animate-spin text-primary-500 mx-auto" />
      <p className="text-text-secondary text-sm">Signing you in…</p>
    </div>
  );
}
