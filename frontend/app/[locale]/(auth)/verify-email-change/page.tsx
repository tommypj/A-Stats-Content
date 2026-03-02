"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle, XCircle } from "lucide-react";

import { api, parseApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function VerifyEmailChangePage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");
  // Guard against double-invocation in React strict mode
  const calledRef = useRef(false);

  useEffect(() => {
    if (calledRef.current) return;
    calledRef.current = true;

    if (!token) {
      setStatus("error");
      setMessage("No verification token provided.");
      return;
    }

    api.auth
      .verifyEmailChange(token)
      .then(() => {
        setStatus("success");
        setMessage("Your email address has been updated successfully.");
      })
      .catch((err) => {
        setStatus("error");
        setMessage(
          parseApiError(err).message ||
            "This link is invalid or has expired. Please request a new email change."
        );
      });
  }, [token]);

  if (status === "loading") {
    return (
      <div className="card p-8 text-center">
        <div className="h-16 w-16 rounded-full bg-primary-50 flex items-center justify-center mx-auto mb-6">
          <div className="h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
        </div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          Confirming email change...
        </h1>
        <p className="mt-2 text-text-secondary">Please wait a moment.</p>
      </div>
    );
  }

  if (status === "success") {
    return (
      <div className="card p-8 text-center">
        <div className="h-16 w-16 rounded-full bg-healing-sage/20 flex items-center justify-center mx-auto mb-6">
          <CheckCircle className="h-8 w-8 text-healing-sage" />
        </div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          Email Updated
        </h1>
        <p className="mt-2 text-text-secondary">{message}</p>
        <p className="mt-1 text-sm text-text-muted">
          Please log in again with your new email address.
        </p>
        <Link href="/login" className="inline-block mt-6">
          <Button>Go to Login</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="card p-8 text-center">
      <div className="h-16 w-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-6">
        <XCircle className="h-8 w-8 text-red-500" />
      </div>
      <h1 className="text-2xl font-display font-bold text-text-primary">
        Verification Failed
      </h1>
      <p className="mt-2 text-text-secondary">{message}</p>
      <div className="mt-6 space-y-3">
        <Link href="/settings" className="block">
          <Button className="w-full">Back to Settings</Button>
        </Link>
        <p className="text-sm text-text-muted">
          You can request a new email change from your profile settings.
        </p>
      </div>
    </div>
  );
}
