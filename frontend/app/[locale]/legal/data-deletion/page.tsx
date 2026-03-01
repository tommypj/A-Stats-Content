import type { Metadata } from "next";
import { CheckCircle2 } from "lucide-react";

export const metadata: Metadata = {
  title: "Data Deletion Status",
  description: "Facebook data deletion request status.",
  robots: { index: false, follow: false },
};

interface Props {
  searchParams: { code?: string };
}

export default function DataDeletionPage({ searchParams }: Props) {
  const { code } = searchParams;

  return (
    <article className="prose prose-neutral max-w-none">
      <div className="max-w-lg mx-auto py-12 text-center">
        <div className="flex justify-center mb-6">
          <div className="h-16 w-16 rounded-full bg-green-100 flex items-center justify-center">
            <CheckCircle2 className="h-8 w-8 text-green-600" />
          </div>
        </div>

        <h1 className="text-2xl font-bold text-text-primary mb-3">
          Data Deletion Confirmed
        </h1>

        <p className="text-text-secondary mb-6">
          Your Facebook and Instagram data has been removed from A-Stats.
          This includes any connected accounts and associated access tokens.
        </p>

        {code && (
          <div className="bg-surface-secondary rounded-xl p-4 mb-6 text-left">
            <p className="text-xs text-text-muted mb-1">Confirmation code</p>
            <p className="font-mono text-sm text-text-primary break-all">{code}</p>
          </div>
        )}

        <p className="text-sm text-text-muted">
          If you have any questions about your data, contact us at{" "}
          <a
            href="mailto:privacy@a-stats.app"
            className="text-primary-500 hover:text-primary-600"
          >
            privacy@a-stats.app
          </a>
        </p>
      </div>
    </article>
  );
}
