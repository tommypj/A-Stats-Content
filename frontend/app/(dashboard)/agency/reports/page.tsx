"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { FileText, ArrowLeft, ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { api, parseApiError, GeneratedReport, ClientWorkspace } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

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

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function TableSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="bg-surface-tertiary animate-pulse rounded-2xl h-14" />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="h-14 w-14 rounded-2xl bg-surface-tertiary flex items-center justify-center mb-4">
        <FileText className="h-7 w-7 text-text-muted" />
      </div>
      <h3 className="text-lg font-semibold text-text-primary mb-1">No reports yet</h3>
      <p className="text-sm text-text-secondary max-w-sm">
        Generate reports from the Agency dashboard to see them listed here.
      </p>
      <div className="mt-6">
        <Link href="/agency">
          <Button variant="outline">Go to Agency Dashboard</Button>
        </Link>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

const PAGE_SIZE_OPTIONS = [10, 20, 50];

export default function AgencyReportsPage() {
  const [reports, setReports] = useState<GeneratedReport[]>([]);
  const [clients, setClients] = useState<Map<string, ClientWorkspace>>(new Map());
  const [loading, setLoading] = useState(true);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(0);
  const [total, setTotal] = useState(0);

  // Load clients once so we can display client names
  useEffect(() => {
    api.agency.clients().then((res) => {
      const map = new Map<string, ClientWorkspace>();
      res.items.forEach((c) => map.set(c.id, c));
      setClients(map);
    }).catch(() => {
      // Non-fatal — client names will just show the raw ID as fallback
    });
  }, []);

  useEffect(() => {
    loadReports();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize]);

  const loadReports = async () => {
    setLoading(true);
    try {
      const res = await api.agency.reports({ page, page_size: pageSize });
      setReports(res.items);
      setTotal(res.total);
      setTotalPages(res.pages);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  };

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setPage(1);
  };

  const clientName = (workspaceId: string): string => {
    return clients.get(workspaceId)?.client_name ?? workspaceId;
  };

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/agency">
          <Button variant="ghost" size="sm" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Agency
          </Button>
        </Link>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-text-primary">Reports</h1>
          <p className="mt-1 text-text-secondary">
            All generated client reports.{" "}
            {!loading && total > 0 && (
              <span className="text-text-muted">{total} total</span>
            )}
          </p>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <Card>
          <CardContent className="p-6">
            <TableSkeleton />
          </CardContent>
        </Card>
      ) : reports.length === 0 ? (
        <Card>
          <CardContent className="p-6">
            <EmptyState />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader className="pb-0">
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4 text-primary-500" />
              Generated Reports
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-surface-tertiary">
                    <th className="text-left px-6 py-3 text-text-muted font-medium">Client</th>
                    <th className="text-left px-6 py-3 text-text-muted font-medium">Report Type</th>
                    <th className="text-left px-6 py-3 text-text-muted font-medium">Period</th>
                    <th className="text-left px-6 py-3 text-text-muted font-medium">Generated</th>
                    <th className="text-right px-6 py-3 text-text-muted font-medium">View</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map((report, idx) => (
                    <tr
                      key={report.id}
                      className={
                        idx !== reports.length - 1
                          ? "border-b border-surface-tertiary"
                          : undefined
                      }
                    >
                      {/* Client */}
                      <td className="px-6 py-4">
                        <span className="font-medium text-text-primary">
                          {clientName(report.client_workspace_id)}
                        </span>
                      </td>

                      {/* Report type */}
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-primary-50 text-primary-700 text-xs font-medium">
                          {formatReportType(report.report_type)}
                        </span>
                      </td>

                      {/* Period */}
                      <td className="px-6 py-4 text-text-secondary whitespace-nowrap">
                        {formatPeriod(report.period_start, report.period_end)}
                      </td>

                      {/* Generated date */}
                      <td className="px-6 py-4 text-text-secondary whitespace-nowrap">
                        {formatDate(report.generated_at)}
                      </td>

                      {/* View link */}
                      <td className="px-6 py-4 text-right">
                        {report.pdf_url ? (
                          <a
                            href={report.pdf_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-primary-600 hover:text-primary-700 font-medium text-xs"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                            View PDF
                          </a>
                        ) : (
                          <Link href={`/agency/reports/${report.id}`}>
                            <span className="inline-flex items-center gap-1.5 text-primary-600 hover:text-primary-700 font-medium text-xs cursor-pointer">
                              <ExternalLink className="h-3.5 w-3.5" />
                              View
                            </span>
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-6 py-4 border-t border-surface-tertiary">
              {/* Page size selector */}
              <div className="flex items-center gap-2 text-sm text-text-secondary">
                <span>Rows per page:</span>
                <select
                  value={pageSize}
                  onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                  className="rounded-lg border border-surface-tertiary bg-white px-2 py-1 text-sm text-text-primary"
                >
                  {PAGE_SIZE_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>

              {/* Page controls */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-text-secondary">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  aria-label="Previous page"
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  aria-label="Next page"
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
