"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Copy,
  Globe,
  FileText,
  Trash2,
  Check,
  Shield,
  BarChart3,
  Sparkles,
  Share2,
  Calendar,
  Mail,
  ExternalLink,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import {
  api,
  parseApiError,
  ClientWorkspace,
  GeneratedReport,
  AgencyReportTemplate,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";

const FEATURE_OPTIONS = [
  { key: "analytics", label: "Analytics", icon: BarChart3, description: "View traffic, rankings, and performance data" },
  { key: "content", label: "Content", icon: Sparkles, description: "Access AI content generation tools" },
  { key: "social", label: "Social", icon: Share2, description: "Manage and schedule social media posts" },
] as const;

type FeatureKey = (typeof FEATURE_OPTIONS)[number]["key"];

interface ReportForm {
  report_type: string;
  period_start: string;
  period_end: string;
  report_template_id: string;
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function formatDateShort(dateString: string) {
  return new Date(dateString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function ClientDetailPage() {
  const params = useParams();
  const router = useRouter();
  const clientId = params.id as string;

  // Core state
  const [workspace, setWorkspace] = useState<ClientWorkspace | null>(null);
  const [reports, setReports] = useState<GeneratedReport[]>([]);
  const [templates, setTemplates] = useState<AgencyReportTemplate[]>([]);

  // Loading states
  const [isLoading, setIsLoading] = useState(true);
  const [isToggling, setIsToggling] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isSavingFeatures, setIsSavingFeatures] = useState(false);

  // UI state
  const [copied, setCopied] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // Report form state
  const [reportForm, setReportForm] = useState<ReportForm>({
    report_type: "monthly",
    period_start: "",
    period_end: "",
    report_template_id: "",
  });

  useEffect(() => {
    loadAll();
  }, [clientId]);

  async function loadAll() {
    setIsLoading(true);
    try {
      const [clientData, reportsData, templatesData] = await Promise.all([
        api.agency.getClient(clientId),
        api.agency.reports({ page_size: 50 }),
        api.agency.reportTemplates(),
      ]);
      setWorkspace(clientData);
      // Filter reports for this specific client
      setReports(reportsData.items.filter((r) => r.client_workspace_id === clientId));
      setTemplates(templatesData.items);
    } catch (error) {
      toast.error(parseApiError(error).message);
      router.push("/agency");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleTogglePortal() {
    if (!workspace) return;
    setIsToggling(true);
    try {
      const updated = workspace.is_portal_enabled
        ? await api.agency.disablePortal(clientId)
        : await api.agency.enablePortal(clientId);
      setWorkspace(updated);
      toast.success(
        updated.is_portal_enabled
          ? "Client portal enabled successfully"
          : "Client portal disabled"
      );
    } catch (error) {
      toast.error(parseApiError(error).message);
    } finally {
      setIsToggling(false);
    }
  }

  async function handleCopyPortalUrl() {
    if (!workspace?.portal_access_token) return;
    const url = `${window.location.origin}/portal/${workspace.portal_access_token}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      toast.success("Portal URL copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  }

  async function handleFeatureChange(key: FeatureKey, value: boolean) {
    if (!workspace) return;
    const currentFeatures = workspace.allowed_features ?? {};
    const updatedFeatures = { ...currentFeatures, [key]: value };

    setIsSavingFeatures(true);
    try {
      const updated = await api.agency.updateClient(clientId, {
        allowed_features: updatedFeatures,
      });
      setWorkspace(updated);
      toast.success("Feature access updated");
    } catch (error) {
      toast.error(parseApiError(error).message);
    } finally {
      setIsSavingFeatures(false);
    }
  }

  async function handleGenerateReport() {
    if (!reportForm.period_start || !reportForm.period_end) {
      toast.error("Please select a date range for the report");
      return;
    }
    if (new Date(reportForm.period_start) >= new Date(reportForm.period_end)) {
      toast.error("Start date must be before end date");
      return;
    }

    setIsGenerating(true);
    try {
      const newReport = await api.agency.generateReport({
        client_workspace_id: clientId,
        report_type: reportForm.report_type || undefined,
        period_start: reportForm.period_start,
        period_end: reportForm.period_end,
        report_template_id: reportForm.report_template_id || undefined,
      });
      setReports((prev) => [newReport, ...prev]);
      setReportForm({
        report_type: "monthly",
        period_start: "",
        period_end: "",
        report_template_id: "",
      });
      toast.success("Report generated successfully");
    } catch (error) {
      toast.error(parseApiError(error).message);
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleDeleteClient() {
    setIsDeleting(true);
    try {
      await api.agency.deleteClient(clientId);
      toast.success("Client workspace deleted");
      router.push("/agency");
    } catch (error) {
      toast.error(parseApiError(error).message);
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-20" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Skeleton className="h-48" />
            <Skeleton className="h-48" />
            <Skeleton className="h-64" />
          </div>
          <div className="space-y-6">
            <Skeleton className="h-48" />
            <Skeleton className="h-40" />
          </div>
        </div>
      </div>
    );
  }

  if (!workspace) return null;

  const portalUrl = workspace.portal_access_token
    ? `${typeof window !== "undefined" ? window.location.origin : ""}/portal/${workspace.portal_access_token}`
    : null;

  const allowedFeatures = workspace.allowed_features ?? {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/agency"
          className="inline-flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary mb-4 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Agency
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            {workspace.client_logo_url ? (
              <img
                src={workspace.client_logo_url}
                alt={`${workspace.client_name} logo`}
                className="h-14 w-14 rounded-xl object-cover flex-shrink-0"
              />
            ) : (
              <div className="h-14 w-14 rounded-xl bg-primary-100 flex items-center justify-center flex-shrink-0">
                <span className="text-xl font-bold text-primary-600">
                  {workspace.client_name.charAt(0).toUpperCase()}
                </span>
              </div>
            )}
            <div>
              <h1 className="font-display text-3xl font-bold text-text-primary">
                {workspace.client_name}
              </h1>
              {workspace.client_email && (
                <p className="mt-0.5 text-text-muted text-sm flex items-center gap-1.5">
                  <Mail className="h-3.5 w-3.5" />
                  {workspace.client_email}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setShowDeleteDialog(true)}
              leftIcon={<Trash2 className="h-4 w-4" />}
            >
              Delete
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Client Info Card */}
          <Card>
            <CardHeader>
              <CardTitle>Client Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">
                    Email
                  </p>
                  <p className="text-sm text-text-primary">
                    {workspace.client_email ?? (
                      <span className="text-text-muted italic">Not provided</span>
                    )}
                  </p>
                </div>

                <div>
                  <p className="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">
                    Created
                  </p>
                  <p className="text-sm text-text-primary flex items-center gap-1.5">
                    <Calendar className="h-3.5 w-3.5 text-text-muted" />
                    {formatDate(workspace.created_at)}
                  </p>
                </div>

                <div>
                  <p className="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">
                    Project ID
                  </p>
                  <p className="text-sm text-text-primary font-mono">
                    {workspace.project_id}
                  </p>
                </div>

                <div>
                  <p className="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">
                    Logo
                  </p>
                  {workspace.client_logo_url ? (
                    <a
                      href={workspace.client_logo_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1 transition-colors"
                    >
                      View logo
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  ) : (
                    <span className="text-sm text-text-muted italic">No logo set</span>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Portal Section */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Globe className="h-5 w-5" />
                  Client Portal
                </CardTitle>
                <Button
                  variant={workspace.is_portal_enabled ? "outline" : "primary"}
                  size="sm"
                  onClick={handleTogglePortal}
                  isLoading={isToggling}
                >
                  {workspace.is_portal_enabled ? "Disable Portal" : "Enable Portal"}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {workspace.is_portal_enabled ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
                    <Check className="h-4 w-4 flex-shrink-0" />
                    <span>Portal is active. Your client can access their dashboard via the link below.</span>
                  </div>

                  {portalUrl && (
                    <div>
                      <p className="text-xs font-medium text-text-muted uppercase tracking-wide mb-2">
                        Portal URL
                      </p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-surface-secondary rounded-lg px-3 py-2 font-mono text-sm text-text-primary truncate border border-surface-tertiary">
                          {portalUrl}
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleCopyPortalUrl}
                          leftIcon={
                            copied ? (
                              <Check className="h-4 w-4 text-green-600" />
                            ) : (
                              <Copy className="h-4 w-4" />
                            )
                          }
                        >
                          {copied ? "Copied" : "Copy"}
                        </Button>
                        <a
                          href={portalUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Button
                            variant="ghost"
                            size="sm"
                            leftIcon={<ExternalLink className="h-4 w-4" />}
                          >
                            Open
                          </Button>
                        </a>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-6">
                  <Globe className="h-10 w-10 text-text-muted mx-auto mb-3" />
                  <p className="text-sm text-text-secondary mb-1">
                    The client portal is currently disabled.
                  </p>
                  <p className="text-xs text-text-muted">
                    Enable it to give your client a branded dashboard to view their reports and analytics.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Allowed Features */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Allowed Features
                </CardTitle>
                {isSavingFeatures && (
                  <Loader2 className="h-4 w-4 animate-spin text-text-muted" />
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-text-secondary">
                Control which features this client can access in their portal.
              </p>
              <div className="space-y-2">
                {FEATURE_OPTIONS.map(({ key, label, icon: Icon, description }) => {
                  const isEnabled = allowedFeatures[key] ?? false;
                  return (
                    <label
                      key={key}
                      className="flex items-start gap-3 p-3 rounded-lg border border-surface-tertiary hover:bg-surface-secondary transition-colors cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={isEnabled}
                        onChange={(e) => handleFeatureChange(key, e.target.checked)}
                        disabled={isSavingFeatures}
                        className="mt-0.5 h-4 w-4 rounded border-surface-tertiary text-primary-600 focus:ring-primary-500 cursor-pointer"
                      />
                      <div className="flex items-start gap-2 flex-1">
                        <Icon className="h-4 w-4 text-text-muted mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="text-sm font-medium text-text-primary">{label}</p>
                          <p className="text-xs text-text-muted">{description}</p>
                        </div>
                      </div>
                    </label>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Reports Section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Reports
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Generate Report Form */}
              <div className="p-4 rounded-xl bg-surface-secondary border border-surface-tertiary space-y-4">
                <h3 className="text-sm font-semibold text-text-primary">Generate New Report</h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-text-muted mb-1">
                      Report Type
                    </label>
                    <select
                      value={reportForm.report_type}
                      onChange={(e) =>
                        setReportForm((prev) => ({ ...prev, report_type: e.target.value }))
                      }
                      className="w-full h-10 rounded-xl border border-surface-tertiary bg-surface px-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="monthly">Monthly</option>
                      <option value="weekly">Weekly</option>
                      <option value="quarterly">Quarterly</option>
                      <option value="custom">Custom</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-text-muted mb-1">
                      Template (optional)
                    </label>
                    <select
                      value={reportForm.report_template_id}
                      onChange={(e) =>
                        setReportForm((prev) => ({
                          ...prev,
                          report_template_id: e.target.value,
                        }))
                      }
                      className="w-full h-10 rounded-xl border border-surface-tertiary bg-surface px-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="">No template</option>
                      {templates.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-text-muted mb-1">
                      Period Start
                    </label>
                    <input
                      type="date"
                      value={reportForm.period_start}
                      onChange={(e) =>
                        setReportForm((prev) => ({
                          ...prev,
                          period_start: e.target.value,
                        }))
                      }
                      className="w-full h-10 rounded-xl border border-surface-tertiary bg-surface px-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-text-muted mb-1">
                      Period End
                    </label>
                    <input
                      type="date"
                      value={reportForm.period_end}
                      onChange={(e) =>
                        setReportForm((prev) => ({
                          ...prev,
                          period_end: e.target.value,
                        }))
                      }
                      className="w-full h-10 rounded-xl border border-surface-tertiary bg-surface px-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                </div>

                <Button
                  onClick={handleGenerateReport}
                  isLoading={isGenerating}
                  leftIcon={<FileText className="h-4 w-4" />}
                  disabled={!reportForm.period_start || !reportForm.period_end}
                >
                  {isGenerating ? "Generating..." : "Generate Report"}
                </Button>
              </div>

              {/* Reports List */}
              {reports.length > 0 ? (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold text-text-primary">
                    Previous Reports ({reports.length})
                  </h3>
                  <div className="divide-y divide-surface-tertiary">
                    {reports.map((report) => (
                      <div
                        key={report.id}
                        className="flex items-center justify-between py-3"
                      >
                        <div className="flex items-start gap-3">
                          <FileText className="h-4 w-4 text-text-muted mt-0.5 flex-shrink-0" />
                          <div>
                            <p className="text-sm font-medium text-text-primary capitalize">
                              {report.report_type} Report
                            </p>
                            <p className="text-xs text-text-muted">
                              {formatDateShort(report.period_start)} &ndash;{" "}
                              {formatDateShort(report.period_end)}
                            </p>
                            <p className="text-xs text-text-muted">
                              Generated {formatDateShort(report.generated_at)}
                            </p>
                          </div>
                        </div>

                        {report.pdf_url && (
                          <a
                            href={report.pdf_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <Button
                              variant="outline"
                              size="sm"
                              leftIcon={<ExternalLink className="h-3.5 w-3.5" />}
                            >
                              View PDF
                            </Button>
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center py-6">
                  <FileText className="h-8 w-8 text-text-muted mx-auto mb-2" />
                  <p className="text-sm text-text-secondary">No reports generated yet.</p>
                  <p className="text-xs text-text-muted">
                    Use the form above to create your first report.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Portal Status Card */}
          <Card>
            <CardHeader>
              <CardTitle>Portal Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Status</span>
                <span
                  className={`inline-flex items-center gap-1.5 text-sm font-medium ${
                    workspace.is_portal_enabled
                      ? "text-green-600"
                      : "text-text-muted"
                  }`}
                >
                  <span
                    className={`h-2 w-2 rounded-full ${
                      workspace.is_portal_enabled ? "bg-green-500" : "bg-surface-tertiary"
                    }`}
                  />
                  {workspace.is_portal_enabled ? "Active" : "Disabled"}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Reports</span>
                <span className="text-sm font-medium text-text-primary">
                  {reports.length}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Features</span>
                <span className="text-sm font-medium text-text-primary">
                  {Object.values(allowedFeatures).filter(Boolean).length} /{" "}
                  {FEATURE_OPTIONS.length}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button
                variant={workspace.is_portal_enabled ? "outline" : "primary"}
                className="w-full"
                onClick={handleTogglePortal}
                isLoading={isToggling}
                leftIcon={<Globe className="h-4 w-4" />}
              >
                {workspace.is_portal_enabled ? "Disable Portal" : "Enable Portal"}
              </Button>

              {workspace.is_portal_enabled && portalUrl && (
                <Button
                  variant="secondary"
                  className="w-full"
                  onClick={handleCopyPortalUrl}
                  leftIcon={
                    copied ? (
                      <Check className="h-4 w-4 text-green-600" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )
                  }
                >
                  {copied ? "URL Copied!" : "Copy Portal URL"}
                </Button>
              )}

              <Button
                variant="destructive"
                className="w-full"
                onClick={() => setShowDeleteDialog(true)}
                leftIcon={<Trash2 className="h-4 w-4" />}
              >
                Delete Client
              </Button>
            </CardContent>
          </Card>

          {/* Client Details Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">
                  Client ID
                </p>
                <p className="text-xs font-mono text-text-secondary break-all">
                  {workspace.id}
                </p>
              </div>

              <div>
                <p className="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">
                  Agency ID
                </p>
                <p className="text-xs font-mono text-text-secondary break-all">
                  {workspace.agency_id}
                </p>
              </div>

              <div>
                <p className="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">
                  Added
                </p>
                <p className="text-sm text-text-secondary">
                  {formatDate(workspace.created_at)}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog
        isOpen={showDeleteDialog}
        onClose={() => setShowDeleteDialog(false)}
        title="Delete Client Workspace"
        description="This action cannot be undone. All associated reports and portal access will be permanently removed."
        size="sm"
      >
        <div className="space-y-4">
          <div className="p-4 bg-red-50 rounded-lg border border-red-200">
            <p className="text-sm text-red-700">
              You are about to permanently delete{" "}
              <strong>{workspace.client_name}</strong> and all their associated
              data, including reports and portal access.
            </p>
          </div>

          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteClient}
              isLoading={isDeleting}
            >
              Delete Permanently
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
