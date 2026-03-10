"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Plus,
  Loader2,
  Trash2,
  FileText,
  Download,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react";
import { toast } from "sonner";
import {
  api,
  parseApiError,
  SEOReport,
  CreateReportInput,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useRequireAuth } from "@/lib/auth";
import { useProject } from "@/contexts/ProjectContext";
import { TierGate } from "@/components/ui/tier-gate";

const REPORT_TYPES = [
  { value: "overview", label: "SEO Overview" },
  { value: "keywords", label: "Keyword Rankings" },
  { value: "pages", label: "Page Performance" },
  { value: "content_health", label: "Content Health" },
];

const STATUS_CONFIG: Record<
  string,
  { icon: React.ElementType; color: string; label: string }
> = {
  pending: { icon: Clock, color: "text-yellow-500", label: "Pending" },
  generating: { icon: Loader2, color: "text-blue-500", label: "Generating" },
  completed: { icon: CheckCircle2, color: "text-green-500", label: "Completed" },
  failed: { icon: XCircle, color: "text-red-500", label: "Failed" },
};

export default function ReportsPage() {
  const { isLoading: authLoading } = useRequireAuth();
  const { currentProject } = useProject();

  const [reports, setReports] = useState<SEOReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  // Modal
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<CreateReportInput>({ name: "", report_type: "overview" });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Polling for in-progress reports
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.reports.list({
        page,
        page_size: pageSize,
        project_id: currentProject?.id,
      });
      setReports(res.items);
      setTotalPages(res.pages);
      setTotal(res.total);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [page, currentProject?.id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Poll while any report is pending/generating
  useEffect(() => {
    const hasInProgress = reports.some(
      (r) => r.status === "pending" || r.status === "generating"
    );
    if (hasInProgress && !pollRef.current) {
      pollRef.current = setInterval(loadData, 3000);
    } else if (!hasInProgress && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [reports, loadData]);

  const handleCreate = async () => {
    if (!form.name.trim()) {
      toast.error("Report name is required");
      return;
    }
    setSaving(true);
    try {
      await api.reports.create({
        ...form,
        project_id: currentProject?.id,
      });
      toast.success("Report generation started");
      setShowModal(false);
      setForm({ name: "", report_type: "overview" });
      loadData();
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeleting(id);
    try {
      await api.reports.delete(id);
      toast.success("Report deleted");
      loadData();
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setDeleting(null);
    }
  };

  const handleDownload = (report: SEOReport) => {
    if (!report.report_data) return;
    const blob = new Blob([JSON.stringify(report.report_data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${report.name.replace(/\s+/g, "_")}_report.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (authLoading) return null;

  return (
    <TierGate minimum="professional" feature="SEO Reports">
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-text-primary">
            Reports
          </h1>
          <p className="mt-2 text-text-secondary">
            Generate and download SEO analytics reports
          </p>
        </div>
        <Button onClick={() => setShowModal(true)}>
          <Plus className="h-4 w-4 mr-2" /> New Report
        </Button>
      </div>

      {/* Loading */}
      {loading && reports.length === 0 ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 bg-surface-tertiary animate-pulse rounded-2xl"
            />
          ))}
        </div>
      ) : reports.length === 0 ? (
        <Card>
          <CardContent className="text-center py-16">
            <FileText className="h-12 w-12 mx-auto text-text-muted mb-4" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              No reports yet
            </h3>
            <p className="text-text-secondary mb-6 max-w-md mx-auto">
              Generate reports to get a snapshot of your SEO performance over any
              date range. Reports can be downloaded as JSON.
            </p>
            <Button onClick={() => setShowModal(true)}>
              <Plus className="h-4 w-4 mr-2" /> Generate your first report
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {reports.map((r) => {
            const sc = STATUS_CONFIG[r.status] || STATUS_CONFIG.pending;
            const StatusIcon = sc.icon;
            return (
              <Card key={r.id}>
                <CardContent className="flex items-center justify-between py-4">
                  <div className="flex items-center gap-4 min-w-0">
                    <StatusIcon
                      className={`h-5 w-5 flex-shrink-0 ${sc.color} ${
                        r.status === "generating" ? "animate-spin" : ""
                      }`}
                    />
                    <div className="min-w-0">
                      <h3 className="font-semibold text-text-primary truncate">
                        {r.name}
                      </h3>
                      <div className="flex items-center gap-3 text-xs text-text-muted mt-0.5">
                        <span className="capitalize">
                          {REPORT_TYPES.find((t) => t.value === r.report_type)?.label || r.report_type}
                        </span>
                        {r.date_from && r.date_to && (
                          <span>
                            {r.date_from} - {r.date_to}
                          </span>
                        )}
                        <span>{new Date(r.created_at).toLocaleDateString()}</span>
                      </div>
                      {r.error_message && (
                        <p className="text-xs text-red-500 mt-1 truncate">
                          {r.error_message}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {r.status === "completed" && r.report_data && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDownload(r)}
                        aria-label="Download report"
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(r.id)}
                      disabled={deleting === r.id}
                      aria-label="Delete report"
                      className="text-red-500 hover:text-red-600"
                    >
                      {deleting === r.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-text-secondary">
            Showing {(page - 1) * pageSize + 1}-
            {Math.min(page * pageSize, total)} of {total}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Create Modal */}
      <Dialog
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="Generate Report"
      >
        <div className="space-y-4">
          <div>
            <label htmlFor="report-name" className="block text-sm font-medium text-text-secondary mb-1">
              Report Name *
            </label>
            <input
              id="report-name"
              type="text"
              value={form.name}
              onChange={(e) =>
                setForm((f) => ({ ...f, name: e.target.value }))
              }
              placeholder="e.g. March 2026 SEO Overview"
              className="w-full px-3 py-2 bg-surface-secondary border border-border rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-brand-primary"
            />
          </div>

          <div>
            <label htmlFor="report-type" className="block text-sm font-medium text-text-secondary mb-1">
              Report Type
            </label>
            <select
              id="report-type"
              value={form.report_type}
              onChange={(e) =>
                setForm((f) => ({ ...f, report_type: e.target.value }))
              }
              className="w-full px-3 py-2 bg-surface-secondary border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-brand-primary"
            >
              {REPORT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="from" className="block text-sm font-medium text-text-secondary mb-1">
                From
              </label>
              <input
                id="from"
                type="date"
                value={form.date_from || ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    date_from: e.target.value || undefined,
                  }))
                }
                className="w-full px-3 py-2 bg-surface-secondary border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-brand-primary"
              />
            </div>
            <div>
              <label htmlFor="to" className="block text-sm font-medium text-text-secondary mb-1">
                To
              </label>
              <input
                id="to"
                type="date"
                value={form.date_to || ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    date_to: e.target.value || undefined,
                  }))
                }
                className="w-full px-3 py-2 bg-surface-secondary border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-brand-primary"
              />
            </div>
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-text-secondary mb-1">
              Description
            </label>
            <input
              id="description"
              type="text"
              value={form.description || ""}
              onChange={(e) =>
                setForm((f) => ({ ...f, description: e.target.value }))
              }
              placeholder="Optional notes about this report"
              className="w-full px-3 py-2 bg-surface-secondary border border-border rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-brand-primary"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-border">
          <Button variant="outline" onClick={() => setShowModal(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={saving}>
            {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Generate Report
          </Button>
        </div>
      </Dialog>
    </div>
    </TierGate>
  );
}
