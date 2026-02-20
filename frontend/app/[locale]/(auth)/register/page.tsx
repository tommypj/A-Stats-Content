"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, parseApiError } from "@/lib/api";

const registerSchema = z
  .object({
    name: z.string().min(1).max(255),
    email: z.string().email(),
    password: z
      .string()
      .min(8)
      .regex(/[A-Z]/, "Must contain at least one uppercase letter")
      .regex(/[a-z]/, "Must contain at least one lowercase letter")
      .regex(/[0-9]/, "Must contain at least one digit"),
    confirmPassword: z.string().min(8),
    terms: z.boolean().refine((val) => val === true, {
      message: "You must accept the terms and conditions",
    }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type RegisterFormData = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const t = useTranslations("auth.register");
  const tErrors = useTranslations("auth.errors");
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      name: "",
      email: "",
      password: "",
      confirmPassword: "",
      terms: false,
    },
  });

  const onSubmit = async (data: RegisterFormData) => {
    setIsLoading(true);
    try {
      await api.auth.register({
        name: data.name,
        email: data.email,
        password: data.password,
      });

      toast.success("Account created! Please check your email to verify.");
      router.push("/login");
    } catch (error) {
      const apiError = parseApiError(error);
      if (apiError.message.includes("already exists")) {
        toast.error(tErrors("emailExists"));
      } else {
        toast.error(apiError.message || tErrors("serverError"));
      }
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
          label={t("name")}
          type="text"
          autoComplete="name"
          error={errors.name?.message}
          {...register("name")}
        />

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
        </div>

        <div>
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
        </div>

        <label className="flex items-start gap-2 cursor-pointer">
          <input
            type="checkbox"
            className="h-4 w-4 mt-0.5 rounded border-surface-tertiary text-primary-500 focus:ring-primary-500"
            {...register("terms")}
          />
          <span className="text-sm text-text-secondary">
            {t("terms")}{" "}
            <Link
              href="/terms"
              className="text-primary-500 hover:text-primary-600"
            >
              {t("termsLink")}
            </Link>{" "}
            &{" "}
            <Link
              href="/privacy"
              className="text-primary-500 hover:text-primary-600"
            >
              {t("privacyLink")}
            </Link>
          </span>
        </label>
        {errors.terms && (
          <p className="text-xs text-red-500">{errors.terms.message}</p>
        )}

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
        {t("hasAccount")}{" "}
        <Link
          href="/login"
          className="font-medium text-primary-500 hover:text-primary-600"
        >
          {t("signIn")}
        </Link>
      </p>
    </div>
  );
}
