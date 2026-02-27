"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/stores/auth";
import { api, parseApiError } from "@/lib/api";

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
  rememberMe: z.boolean().optional(),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const t = useTranslations("auth.login");
  const tErrors = useTranslations("auth.errors");
  const router = useRouter();
  const { login } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
      rememberMe: false,
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true);
    try {
      const response = await api.auth.login(data.email, data.password);

      // Temporarily store token only long enough to fetch user info.
      // We write to localStorage here so the apiClient interceptor can
      // attach the Authorization header for the /auth/me call that follows.
      // The authoritative write (including Zustand state) happens in login()
      // below. If me() fails the token is removed in the catch block.
      localStorage.setItem("auth_token", response.access_token);
      if (response.refresh_token) {
        localStorage.setItem("refresh_token", response.refresh_token);
      }
      let user;
      try {
        user = await api.auth.me();
      } catch (meError) {
        // /me failed — remove the tokens we just stored so the user is not
        // left in a half-authenticated state.
        localStorage.removeItem("auth_token");
        localStorage.removeItem("refresh_token");
        throw meError;
      }

      login(
        {
          id: user.id,
          email: user.email,
          name: user.name,
          role: user.role as "user" | "admin",
          subscription_tier: (user.subscription_tier as "free" | "starter" | "professional" | "enterprise") || "free",
        },
        response.access_token,
        response.refresh_token
      );

      toast.success("Welcome back!");
      router.push("/dashboard");
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || tErrors("invalidCredentials"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card p-8">
      <div className="text-center mb-8">
        <h1 className="text-2xl font-display font-bold text-text-primary">
          {t("title")}
        </h1>
        <p className="mt-2 text-text-secondary">{t("description")}</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        <Input
          label={t("email")}
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />

        <div>
          <div className="relative">
            <Input
              label={t("password")}
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              error={errors.password?.message}
              {...register("password")}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-[38px] text-text-muted hover:text-text-secondary"
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-surface-tertiary text-primary-500 focus:ring-primary-500"
              {...register("rememberMe")}
            />
            <span className="text-sm text-text-secondary">{t("rememberMe")}</span>
          </label>
          <Link
            href="/forgot-password"
            className="text-sm text-primary-500 hover:text-primary-600"
          >
            {t("forgotPassword")}
          </Link>
        </div>

        <Button
          type="submit"
          className="w-full"
          disabled={isLoading}
          isLoading={isLoading}
        >
          {t("submit")}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-text-secondary">
        {t("noAccount")}{" "}
        <Link
          href="/register"
          className="font-medium text-primary-500 hover:text-primary-600"
        >
          {t("signUp")}
        </Link>
      </p>
    </div>
  );
}
