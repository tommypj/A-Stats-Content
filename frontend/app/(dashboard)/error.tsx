"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function DashboardError({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error("[Dashboard Error Boundary]", error);
  }, [error]);

  const message = error.message
    ? error.message.slice(0, 200)
    : "An unexpected error occurred.";

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <div className="card p-8 max-w-md w-full text-center space-y-5">
        {/* Icon */}
        <div className="flex justify-center">
          <div className="h-14 w-14 rounded-2xl bg-red-50 flex items-center justify-center">
            <AlertTriangle className="h-7 w-7 text-red-500" />
          </div>
        </div>

        {/* Heading */}
        <div className="space-y-2">
          <h1 className="text-xl font-display font-bold text-text-primary">
            Something went wrong
          </h1>
          <p className="text-sm text-text-secondary leading-relaxed">
            {message}
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-1">
          <button
            onClick={reset}
            className="btn-primary"
          >
            Try again
          </button>
          <Link href="/dashboard" className="btn-secondary">
            Go to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
