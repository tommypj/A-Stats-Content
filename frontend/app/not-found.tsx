import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Page Not Found",
};

export default function NotFound() {
  return (
    <div className="min-h-screen bg-healing-cream flex items-center justify-center p-6">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="space-y-2">
          <p className="text-8xl font-bold text-primary-200 select-none">404</p>
          <h1 className="text-2xl font-bold text-text-primary">Page not found</h1>
          <p className="text-text-muted">
            The page you&apos;re looking for doesn&apos;t exist or has been moved.
          </p>
        </div>
        <div className="flex items-center justify-center gap-3">
          <Link
            href="/"
            className="px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
          >
            Go home
          </Link>
          <Link
            href="/dashboard"
            className="px-4 py-2 rounded-lg border border-surface-tertiary text-sm font-medium text-text-primary hover:bg-surface-secondary transition-colors"
          >
            Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
