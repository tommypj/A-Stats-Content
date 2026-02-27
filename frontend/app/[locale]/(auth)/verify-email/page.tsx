"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { CheckCircle, XCircle, Mail } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api, parseApiError } from "@/lib/api";

export default function VerifyEmailPage() {
  const t = useTranslations("auth.verifyEmail");
  const tErrors = useTranslations("auth.errors");
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"pending" | "loading" | "success" | "error">("pending");
  const [errorMessage, setErrorMessage] = useState("");

  if (!token) {
    return (
      <div className="card p-8 text-center">
        <div className="h-16 w-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-6">
          <XCircle className="h-8 w-8 text-red-500" />
        </div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          Verification Failed
        </h1>
        <p className="mt-2 text-text-secondary">
          No verification token provided.
        </p>
        <div className="mt-6">
          <Link href="/login" className="block">
            <Button className="w-full">Go to Login</Button>
          </Link>
        </div>
      </div>
    );
  }

  const handleVerify = async () => {
    setStatus("loading");
    try {
      await api.auth.verifyEmail(token);
      setStatus("success");
    } catch (error) {
      setStatus("error");
      const apiError = parseApiError(error);
      setErrorMessage(apiError.message || "Verification failed");
    }
  };

  if (status === "pending") {
    return (
      <div className="card p-8 text-center">
        <div className="h-16 w-16 rounded-full bg-primary-50 flex items-center justify-center mx-auto mb-6">
          <Mail className="h-8 w-8 text-primary-500" />
        </div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          Verify Your Email
        </h1>
        <p className="mt-2 text-text-secondary">
          Click the button below to confirm your email address and activate your account.
        </p>
        <Button className="mt-6 w-full" onClick={handleVerify}>
          Verify Email
        </Button>
        <div className="mt-4">
          <Link href="/login" className="text-sm text-primary-500 hover:text-primary-600">
            Back to Login
          </Link>
        </div>
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div className="card p-8 text-center">
        <div className="h-16 w-16 rounded-full bg-primary-50 flex items-center justify-center mx-auto mb-6">
          <div className="h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
        </div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          Verifying your email...
        </h1>
        <p className="mt-2 text-text-secondary">
          Please wait while we verify your email address.
        </p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="card p-8 text-center">
        <div className="h-16 w-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-6">
          <XCircle className="h-8 w-8 text-red-500" />
        </div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          Verification Failed
        </h1>
        <p className="mt-2 text-text-secondary">
          {errorMessage || tErrors("tokenExpired")}
        </p>
        <div className="mt-6 space-y-3">
          <Link href="/login" className="block">
            <Button className="w-full">Go to Login</Button>
          </Link>
          <p className="text-sm text-text-muted">
            Need a new verification link? Sign in and request one from your dashboard.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-8 text-center">
      <div className="h-16 w-16 rounded-full bg-healing-sage/20 flex items-center justify-center mx-auto mb-6">
        <CheckCircle className="h-8 w-8 text-healing-sage" />
      </div>
      <h1 className="text-2xl font-display font-bold text-text-primary">
        Email Verified!
      </h1>
      <p className="mt-2 text-text-secondary">
        Your email has been verified successfully. You can now access all features.
      </p>
      <Link href="/dashboard" className="inline-block mt-6">
        <Button>Go to Dashboard</Button>
      </Link>
    </div>
  );
}
