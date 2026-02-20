"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function VerifyEmailPage() {
  const t = useTranslations("auth.verifyEmail");
  const tErrors = useTranslations("auth.errors");
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setErrorMessage("No verification token provided");
      return;
    }

    const verifyEmail = async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/verify-email?token=${token}`,
          { method: "POST" }
        );

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || "Verification failed");
        }

        setStatus("success");
      } catch (error) {
        setStatus("error");
        setErrorMessage(
          error instanceof Error ? error.message : "Verification failed"
        );
      }
    };

    verifyEmail();
  }, [token]);

  if (status === "loading") {
    return (
      <div className="card p-8 text-center">
        <div className="h-16 w-16 rounded-full bg-primary-50 flex items-center justify-center mx-auto mb-6">
          <Loader2 className="h-8 w-8 text-primary-500 animate-spin" />
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
