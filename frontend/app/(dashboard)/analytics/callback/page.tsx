"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import { toast } from "sonner";

import { api, parseApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AnalyticsCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    handleCallback();
  }, []);

  async function handleCallback() {
    const code = searchParams.get("code");
    const state = searchParams.get("state");

    if (!code || !state) {
      setStatus("error");
      setErrorMessage("Missing authorization code or state parameter");
      toast.error("Invalid OAuth callback");
      return;
    }

    try {
      await api.analytics.handleCallback(code, state);
      setStatus("success");
      toast.success("Google Search Console connected successfully!");

      setTimeout(() => {
        router.push("/analytics");
      }, 2000);
    } catch (error) {
      setStatus("error");
      const apiError = parseApiError(error);
      setErrorMessage(apiError.message);
      toast.error(apiError.message || "Failed to connect Google Search Console");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">
            {status === "loading" && "Connecting to Google Search Console..."}
            {status === "success" && "Connection Successful!"}
            {status === "error" && "Connection Failed"}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-6">
          {status === "loading" && (
            <>
              <Loader2 className="h-16 w-16 text-primary-500 animate-spin" />
              <p className="text-sm text-text-secondary text-center">
                Please wait while we complete the authorization process...
              </p>
            </>
          )}

          {status === "success" && (
            <>
              <CheckCircle className="h-16 w-16 text-green-500" />
              <p className="text-sm text-text-secondary text-center">
                Your Google Search Console account has been connected successfully.
                You will be redirected to the analytics dashboard shortly.
              </p>
            </>
          )}

          {status === "error" && (
            <>
              <XCircle className="h-16 w-16 text-red-500" />
              <div className="text-center space-y-4">
                <p className="text-sm text-text-secondary">
                  {errorMessage || "An error occurred during the connection process."}
                </p>
                <Button
                  onClick={() => router.push("/analytics")}
                  variant="outline"
                >
                  Return to Analytics
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
