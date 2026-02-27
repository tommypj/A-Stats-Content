"use client";

import { useCallback, useEffect, useRef, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle, AlertCircle, Loader2 } from "lucide-react";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [platform, setPlatform] = useState<string>("social");
  // FE-SM-03: Prevent double-firing if user refreshes during redirect
  const hasFiredRef = useRef(false);

  const handleCallback = useCallback(async () => {
    if (hasFiredRef.current) return;
    hasFiredRef.current = true;
    try {
      const success = searchParams.get("success");
      const errorParam = searchParams.get("error");
      const platformParam = searchParams.get("platform");

      if (platformParam) {
        setPlatform(platformParam);
      }

      if (errorParam) {
        const errorMessages: Record<string, string> = {
          access_denied: "You denied access to your account",
          missing_params: "Missing authorization parameters from the provider",
          invalid_state: "Session expired. Please try connecting again.",
          token_exchange_failed: "Failed to verify your account with the provider. Please try again.",
          unsupported_platform: "This platform is not yet supported.",
          user_not_found: "User session not found. Please log in and try again.",
          invalid_platform: "Invalid platform specified.",
        };
        setError(errorMessages[errorParam] || `Authorization error: ${errorParam}`);
        setStatus("error");
        return;
      }

      if (success === "true") {
        setStatus("success");
        setTimeout(() => {
          router.push("/social/accounts");
        }, 2000);
        return;
      }

      setError("Unexpected callback state. Please try connecting again.");
      setStatus("error");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect account");
      setStatus("error");
    }
  }, [searchParams, router]);

  useEffect(() => {
    handleCallback();
  }, [handleCallback]);

  if (status === "loading") {
    return (
      <div className="container mx-auto p-6 flex items-center justify-center min-h-[60vh]">
        <Card className="p-8 text-center max-w-md w-full">
          <Loader2 className="h-16 w-16 text-primary-500 animate-spin mx-auto mb-6" />
          <h2 className="text-2xl font-semibold text-text-primary mb-2">
            Connecting Your Account
          </h2>
          <p className="text-text-secondary">
            Please wait while we complete the authorization...
          </p>
        </Card>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="container mx-auto p-6 flex items-center justify-center min-h-[60vh]">
        <Card className="p-8 text-center max-w-md w-full">
          <div className="h-16 w-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <AlertCircle className="h-8 w-8 text-red-500" />
          </div>
          <h2 className="text-2xl font-semibold text-text-primary mb-2">
            Connection Failed
          </h2>
          <p className="text-text-secondary mb-6">
            {error || "We couldn't connect your account. Please try again."}
          </p>
          <div className="flex gap-3 justify-center">
            <Button variant="outline" onClick={() => router.push("/social/accounts")}>
              Go to Accounts
            </Button>
            <Button onClick={() => router.push("/social/accounts")}>Try Again</Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 flex items-center justify-center min-h-[60vh]">
      <Card className="p-8 text-center max-w-md w-full">
        <div className="h-16 w-16 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircle className="h-8 w-8 text-green-500" />
        </div>
        <h2 className="text-2xl font-semibold text-text-primary mb-2">
          Account Connected!
        </h2>
        <p className="text-text-secondary mb-6">
          Your {platform} account has been successfully connected. You can now
          schedule posts to this platform.
        </p>
        <div className="space-y-3">
          <p className="text-sm text-text-tertiary">
            Redirecting to accounts page...
          </p>
          <Button onClick={() => router.push("/social/accounts")} className="w-full">
            View Connected Accounts
          </Button>
        </div>
      </Card>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <Suspense fallback={
      <div className="container mx-auto p-6 flex items-center justify-center min-h-[60vh]">
        <Card className="p-8 text-center max-w-md w-full">
          <Loader2 className="h-16 w-16 text-primary-500 animate-spin mx-auto mb-6" />
          <h2 className="text-2xl font-semibold text-text-primary mb-2">
            Loading...
          </h2>
        </Card>
      </div>
    }>
      <CallbackContent />
    </Suspense>
  );
}
