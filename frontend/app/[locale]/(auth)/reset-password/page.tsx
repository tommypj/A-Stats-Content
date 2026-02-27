"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff, CheckCircle, XCircle } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, parseApiError } from "@/lib/api";

const resetPasswordSchema = z
  .object({
    password: z
      .string()
      .min(8)
      .regex(/[A-Z]/, "Must contain at least one uppercase letter")
      .regex(/[a-z]/, "Must contain at least one lowercase letter")
      .regex(/[0-9]/, "Must contain at least one digit"),
    confirmPassword: z.string().min(8),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;

export default function ResetPasswordPage() {
  const t = useTranslations("auth.resetPassword");
  const tErrors = useTranslations("auth.errors");
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isInvalid, setIsInvalid] = useState(false);

  useEffect(() => {
    if (!token || token.length < 10) {
      setIsInvalid(true);
    }
  }, [token]);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
  });

  const onSubmit = async (data: ResetPasswordFormData) => {
    if (!token) return;

    setIsLoading(true);
    try {
      await api.auth.resetPassword(token, data.password);
      setIsSuccess(true);
    } catch (error) {
      const apiError = parseApiError(error);
      const message = apiError.message || "";
      if (message.toLowerCase().includes("expired") || message.toLowerCase().includes("invalid token")) {
        setIsInvalid(true);
      } else {
        toast.error(message || tErrors("serverError"));
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (isInvalid) {
    return (
      <div className="card p-8 text-center">
        <div className="h-16 w-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-6">
          <XCircle className="h-8 w-8 text-red-500" />
        </div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          Invalid or Expired Link
        </h1>
        <p className="mt-2 text-text-secondary">
          {tErrors("tokenExpired")}
        </p>
        <Link href="/forgot-password" className="inline-block mt-6">
          <Button>Request New Link</Button>
        </Link>
      </div>
    );
  }

  if (isSuccess) {
    return (
      <div className="card p-8 text-center">
        <div className="h-16 w-16 rounded-full bg-healing-sage/20 flex items-center justify-center mx-auto mb-6">
          <CheckCircle className="h-8 w-8 text-healing-sage" />
        </div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          {t("success")}
        </h1>
        <p className="mt-2 text-text-secondary">
          You can now sign in with your new password.
        </p>
        <Link href="/login" className="inline-block mt-6">
          <Button>Go to Login</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="card p-8">
      <div className="text-center mb-8">
        <h1 className="text-2xl font-display font-bold text-text-primary">
          {t("title")}
        </h1>
        <p className="mt-2 text-text-secondary">{t("description")}</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        <div className="relative">
          <Input
            label={t("password")}
            type={showPassword ? "text" : "password"}
            autoComplete="new-password"
            error={errors.password?.message}
            helperText="At least 8 characters with uppercase, lowercase, and number"
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

        <div className="relative">
          <Input
            label={t("confirmPassword")}
            type={showConfirmPassword ? "text" : "password"}
            autoComplete="new-password"
            error={errors.confirmPassword?.message}
            {...register("confirmPassword")}
          />
          <button
            type="button"
            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
            className="absolute right-3 top-[38px] text-text-muted hover:text-text-secondary"
          >
            {showConfirmPassword ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
          </button>
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
    </div>
  );
}
