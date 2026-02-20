"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const passwordSchema = z
  .object({
    currentPassword: z.string().min(1),
    newPassword: z
      .string()
      .min(8)
      .regex(/[A-Z]/, "Must contain at least one uppercase letter")
      .regex(/[a-z]/, "Must contain at least one lowercase letter")
      .regex(/[0-9]/, "Must contain at least one digit"),
    confirmPassword: z.string().min(8),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type PasswordFormData = z.infer<typeof passwordSchema>;

export default function PasswordSettingsPage() {
  const t = useTranslations("settings.password");
  const [isLoading, setIsLoading] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
  });

  const onSubmit = async (data: PasswordFormData) => {
    setIsLoading(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/password/change`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("auth_token")}`,
          },
          body: JSON.stringify({
            current_password: data.currentPassword,
            new_password: data.newPassword,
          }),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to change password");
      }

      toast.success("Password changed successfully");
      reset();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to change password");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="p-6 border-b border-surface-tertiary">
        <h2 className="font-display text-lg font-semibold text-text-primary">
          {t("title")}
        </h2>
        <p className="mt-1 text-sm text-text-secondary">{t("description")}</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6">
        {/* Current Password */}
        <div className="relative">
          <Input
            label={t("current")}
            type={showCurrentPassword ? "text" : "password"}
            autoComplete="current-password"
            error={errors.currentPassword?.message}
            {...register("currentPassword")}
          />
          <button
            type="button"
            onClick={() => setShowCurrentPassword(!showCurrentPassword)}
            className="absolute right-3 top-[38px] text-text-muted hover:text-text-secondary"
          >
            {showCurrentPassword ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* New Password */}
        <div className="relative">
          <Input
            label={t("new")}
            type={showNewPassword ? "text" : "password"}
            autoComplete="new-password"
            error={errors.newPassword?.message}
            helperText="At least 8 characters with uppercase, lowercase, and number"
            {...register("newPassword")}
          />
          <button
            type="button"
            onClick={() => setShowNewPassword(!showNewPassword)}
            className="absolute right-3 top-[38px] text-text-muted hover:text-text-secondary"
          >
            {showNewPassword ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* Confirm Password */}
        <div className="relative">
          <Input
            label={t("confirm")}
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

        {/* Submit */}
        <div className="flex justify-end pt-4">
          <Button type="submit" disabled={isLoading} isLoading={isLoading}>
            {t("update")}
          </Button>
        </div>
      </form>
    </div>
  );
}
