"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, Mail } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, parseApiError } from "@/lib/api";

const forgotPasswordSchema = z.object({
  email: z.string().email(),
});

type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPasswordPage() {
  const t = useTranslations("auth.forgotPassword");
  const tErrors = useTranslations("auth.errors");
  const [isLoading, setIsLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [sentEmail, setSentEmail] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: {
      email: "",
    },
  });

  const onSubmit = async (data: ForgotPasswordFormData) => {
    setIsLoading(true);
    try {
      await api.auth.forgotPassword(data.email);
    } catch {
      // Ignore errors to prevent email enumeration
    } finally {
      // Always show success to prevent email enumeration
      setSentEmail(data.email);
      setEmailSent(true);
      setIsLoading(false);
    }
  };

  if (emailSent) {
    return (
      <div className="card p-8 text-center">
        <div className="h-16 w-16 rounded-full bg-primary-50 flex items-center justify-center mx-auto mb-6">
          <Mail className="h-8 w-8 text-primary-500" />
        </div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          {t("sent.title")}
        </h1>
        <p className="mt-2 text-text-secondary">
          If an account exists with that email, you&apos;ll receive password reset instructions shortly.
        </p>
        <Link
          href="/login"
          className="inline-flex items-center gap-2 mt-6 text-sm text-primary-500 hover:text-primary-600"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("backToLogin")}
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
        <Input
          label={t("email")}
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />

        <Button
          type="submit"
          className="w-full"
          disabled={isLoading}
          isLoading={isLoading}
        >
          {t("submit")}
        </Button>
      </form>

      <div className="mt-6 text-center">
        <Link
          href="/login"
          className="inline-flex items-center gap-2 text-sm text-primary-500 hover:text-primary-600"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("backToLogin")}
        </Link>
      </div>
    </div>
  );
}
