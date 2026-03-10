"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Download,
  FileText,
  BarChart3,
  MousePointerClick,
  Eye,
  TrendingUp,
  DollarSign,
} from "lucide-react";
import { toast } from "sonner";
import { api, parseApiError, GeneratedReport, ClientWorkspace } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TierGate } from "@/components/ui/tier-gate";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

function formatPeriod(start: string, end: string): string {
  return `${formatDate(start)} – ${formatDate(end)}`;
}

function formatReportType(type: string): string {
  return type
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatNumber(n: number): string {
  return n.toLocaleString();
}

function formatCurrency(n: number): string {
  return `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="bg-surface-tertiary animate-pulse rounded-2xl h-10 w-64" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-surface-tertiary animate-pulse rounded-2xl h-28" />
        ))}
      </div>
      <div className="bg-surface-tertiary animate-pulse rounded-2xl h-64" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Metric Card
// ---------------------------------------------------------------------------

function MetricCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center gap-3 mb-2">
          <div className="h-9 w-9 rounded-xl bg-primary-50 flex items-center justify-center">
            <Icon className="h-4.5 w-4.5 text-primary-600" />
          </div>
          <span className="text-sm text-text-secondary">{label}</span>
        </div>
        <p className="text-2xl font-bold text-text-primary">{value}</p>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AgencyReportDetailPage() {
  const params = useParams<{ id: string }>();
  const [report, setReport] = useState<GeneratedReport | null>(null);
  const [clientName, setClientName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params.id) return;

    (async () => {
      setLoading(true);
      setError(null);
      try {
        const r = await api.agency.getReport(params.id);
        setReport(r);

        // Attempt to resolve client name
        try {
          const clients = await api.agency.clients();
          const match = clients.items.find((c: ClientWorkspace) => c.id === r.client_workspace_id);
          if (match) setClientName(match.client_name);
        } catch {
          // Non-fatal
        }
      } catch (err) {
        const msg = parseApiError(err).message;
        setError(msg);
        toast.error(msg);
      } finally {
        setLoading(false);
      }
    })();
  }, [params.id]);

  const data = report?.report_data as Record<string, unknown> | null;
  const totalClicks = typeof data?.total_clicks === "number" ? data.total_clicks : null;
  const totalImpressions = typeof data?.total_impressions === "number" ? data.total_impressions : null;
  const totalConversions = typeof data?.total_conversions === "number" ? data.total_conversions : null;
  const totalRevenue = typeof data?.total_revenue === "number" ? data.total_revenue : null;
  const topPages = Array.isArray(data?.top_pages) ? (data.top_pages as { page: string; clicks: number; impressions: number }[]) : [];
  const topKeywords = Array.isArray(data?.top_keywords) ? (data.top_keywords as { keyword: string; clicks: number; impressions: number; avg_position: number }[]) : [];

  return (
    <TierGate minimum="enterprise" feature="Agency Mode">
      <div className="space-y-6 animate-in">
        {/* Back button */}
        <div className="flex items-center gap-3">
          <Link href="/agency/reports">
            <Button variant="ghost" size="sm" className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Reports
            </Button>
          </Link>
        </div>

        {loading ? (
          <DetailSkeleton />
        ) : error ? (
          <Card>
            <CardContent className="p-10 text-center">
              <div className="h-14 w-14 rounded-2xl bg-surface-tertiary flex items-center justify-center mx-auto mb-4">
                <FileText className="h-7 w-7 text-text-muted" />
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-1">
                Failed to load report
              </h3>
              <p className="text-sm text-text-secondary mb-4">{error}</p>
              <Link href="/agency/reports">
                <Button variant="outline">Back to Reports</Button>
              </Link>
            </CardContent>
          </Card>
        ) : report ? (
          <>
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <h1 className="text-2xl font-display font-bold text-text-primary">
                  {formatReportType(report.report_type)} Report
                </h1>
                <p className="mt-1 text-text-secondary">
                  {clientName ?? report.client_workspace_id}
                  {" \u00b7 "}
                  {formatPeriod(report.period_start, report.period_end)}
                </p>
                <p className="mt-0.5 text-xs text-text-muted">
                  Generated {formatDate(report.generated_at)}
                </p>
              </div>

              {report.pdf_url && (
                <a
                  href={report.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Button variant="outline" className="gap-2">
                    <Download className="h-4 w-4" />
                    Download PDF
                  </Button>
                </a>
              )}
            </div>

            {/* Summary metrics */}
            {data && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {totalClicks !== null && (
                  <MetricCard label="Clicks" value={formatNumber(totalClicks)} icon={MousePointerClick} />
                )}
                {totalImpressions !== null && (
                  <MetricCard label="Impressions" value={formatNumber(totalImpressions)} icon={Eye} />
                )}
                {totalConversions !== null && (
                  <MetricCard label="Conversions" value={formatNumber(totalConversions)} icon={TrendingUp} />
                )}
                {totalRevenue !== null && (
                  <MetricCard label="Revenue" value={formatCurrency(totalRevenue)} icon={DollarSign} />
                )}
              </div>
            )}

            {/* Top Pages */}
            {topPages.length > 0 && (
              <Card>
                <CardHeader className="pb-0">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <BarChart3 className="h-4 w-4 text-primary-500" />
                    Top Pages
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-surface-tertiary">
                          <th className="text-left px-6 py-3 text-text-muted font-medium">Page</th>
                          <th className="text-right px-6 py-3 text-text-muted font-medium">Clicks</th>
                          <th className="text-right px-6 py-3 text-text-muted font-medium">Impressions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {topPages.map((p, idx) => (
                          <tr
                            key={idx}
                            className={idx !== topPages.length - 1 ? "border-b border-surface-tertiary" : undefined}
                          >
                            <td className="px-6 py-3 text-text-primary truncate max-w-xs" title={p.page}>
                              {p.page}
                            </td>
                            <td className="px-6 py-3 text-right text-text-secondary tabular-nums">
                              {formatNumber(p.clicks)}
                            </td>
                            <td className="px-6 py-3 text-right text-text-secondary tabular-nums">
                              {formatNumber(p.impressions)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Top Keywords */}
            {topKeywords.length > 0 && (
              <Card>
                <CardHeader className="pb-0">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <BarChart3 className="h-4 w-4 text-primary-500" />
                    Top Keywords
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-surface-tertiary">
                          <th className="text-left px-6 py-3 text-text-muted font-medium">Keyword</th>
                          <th className="text-right px-6 py-3 text-text-muted font-medium">Clicks</th>
                          <th className="text-right px-6 py-3 text-text-muted font-medium">Impressions</th>
                          <th className="text-right px-6 py-3 text-text-muted font-medium">Avg Position</th>
                        </tr>
                      </thead>
                      <tbody>
                        {topKeywords.map((kw, idx) => (
                          <tr
                            key={idx}
                            className={idx !== topKeywords.length - 1 ? "border-b border-surface-tertiary" : undefined}
                          >
                            <td className="px-6 py-3 text-text-primary">{kw.keyword}</td>
                            <td className="px-6 py-3 text-right text-text-secondary tabular-nums">
                              {formatNumber(kw.clicks)}
                            </td>
                            <td className="px-6 py-3 text-right text-text-secondary tabular-nums">
                              {formatNumber(kw.impressions)}
                            </td>
                            <td className="px-6 py-3 text-right text-text-secondary tabular-nums">
                              {kw.avg_position}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* No data fallback */}
            {!data && (
              <Card>
                <CardContent className="p-10 text-center">
                  <p className="text-text-secondary">No report data available.</p>
                </CardContent>
              </Card>
            )}
          </>
        ) : null}
      </div>
    </TierGate>
  );
}
