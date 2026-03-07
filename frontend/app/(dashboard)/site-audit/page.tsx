"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import {
  ScanSearch,
  Globe,
  Loader2,
  Trash2,
  ExternalLink,
  ArrowLeft,
  AlertCircle,
  Download,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  Info,
  Check,
  X as XIcon,
  Filter,
  Gauge,
} from "lucide-react";
import { api, SiteAudit, AuditPage, AuditIssue, parseApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useRequireAuth } from "@/lib/auth";
import { useAuthStore } from "@/stores/auth";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isInProgress(status: string) {
  return ["pending", "crawling", "analyzing"].includes(status);
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function scoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 50) return "text-yellow-600";
  return "text-red-600";
}

function scoreRingColor(score: number): string {
  if (score >= 80) return "border-green-500";
  if (score >= 50) return "border-yellow-500";
  return "border-red-500";
}

function scoreBgColor(score: number): string {
  if (score >= 80) return "bg-green-50";
  if (score >= 50) return "bg-yellow-50";
  return "bg-red-50";
}

function severityBadge(severity: string) {
  const classes = cn(
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
    severity === "critical" && "bg-red-100 text-red-700",
    severity === "warning" && "bg-amber-100 text-amber-700",
    severity === "info" && "bg-blue-100 text-blue-700"
  );
  return <span className={classes}>{severity}</span>;
}

function statusBadge(status: string) {
  const classes = cn(
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
    status === "completed" && "bg-green-100 text-green-700",
    status === "failed" && "bg-red-100 text-red-700",
    status === "pending" && "bg-gray-100 text-gray-700",
    status === "crawling" && "bg-blue-100 text-blue-700",
    status === "analyzing" && "bg-purple-100 text-purple-700"
  );
  const label =
    status === "completed"
      ? "Completed"
      : status === "failed"
      ? "Failed"
      : status === "pending"
      ? "Pending"
      : status === "crawling"
      ? "Crawling..."
      : status === "analyzing"
      ? "Analyzing..."
      : status;
  return <span className={classes}>{label}</span>;
}

function statusCodeColor(code: number | undefined): string {
  if (!code) return "text-text-muted";
  if (code >= 200 && code < 300) return "text-green-600";
  if (code >= 300 && code < 400) return "text-yellow-600";
  return "text-red-600";
}

function truncateUrl(url: string, maxLen = 60): string {
  if (url.length <= maxLen) return url;
  return url.slice(0, maxLen - 3) + "...";
}

// ---------------------------------------------------------------------------
// Sub-components: Tabs
// ---------------------------------------------------------------------------

type ResultTab = "overview" | "issues" | "pages" | "performance";

function OverviewTab({ audit }: { audit: SiteAudit }) {
  const [issues, setIssues] = useState<AuditIssue[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.siteAudit
      .issues(audit.id, { page: 1, page_size: 100 })
      .then((data) => setIssues(data.items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [audit.id]);

  // Aggregate issues by type
  const issuesByType = issues.reduce<Record<string, { count: number; severity: string }>>((acc, issue) => {
    if (!acc[issue.issue_type]) {
      acc[issue.issue_type] = { count: 0, severity: issue.severity };
    }
    acc[issue.issue_type].count += 1;
    // Keep the most severe level
    if (issue.severity === "critical" && acc[issue.issue_type].severity !== "critical") {
      acc[issue.issue_type].severity = "critical";
    } else if (issue.severity === "warning" && acc[issue.issue_type].severity === "info") {
      acc[issue.issue_type].severity = "warning";
    }
    return acc;
  }, {});

  const topIssues = Object.entries(issuesByType)
    .sort(([, a], [, b]) => b.count - a.count)
    .slice(0, 10);

  const totalIssues = audit.total_issues || 1;

  return (
    <div className="p-6 space-y-8">
      {/* Severity distribution */}
      <div>
        <h3 className="text-sm font-semibold text-text-primary mb-4">Issue Severity Distribution</h3>
        <div className="space-y-3">
          {[
            { label: "Critical", count: audit.critical_issues, color: "bg-red-500", textColor: "text-red-700" },
            { label: "Warnings", count: audit.warning_issues, color: "bg-amber-500", textColor: "text-amber-700" },
            { label: "Info", count: audit.info_issues, color: "bg-blue-500", textColor: "text-blue-700" },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-3">
              <span className={cn("text-sm font-medium w-20", item.textColor)}>{item.label}</span>
              <div className="flex-1 h-6 bg-surface-secondary rounded-full overflow-hidden">
                <div
                  className={cn("h-full rounded-full transition-all duration-500", item.color)}
                  style={{ width: `${Math.max((item.count / totalIssues) * 100, item.count > 0 ? 3 : 0)}%` }}
                />
              </div>
              <span className="text-sm font-semibold text-text-primary w-10 text-right">{item.count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Top Issues */}
      <div>
        <h3 className="text-sm font-semibold text-text-primary mb-4">Top Issues</h3>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-primary-500" />
          </div>
        ) : topIssues.length === 0 ? (
          <p className="text-sm text-text-secondary py-4">No issues found. Great job!</p>
        ) : (
          <div className="divide-y divide-surface-tertiary">
            {topIssues.map(([type, data]) => (
              <div key={type} className="flex items-center gap-3 py-3">
                <span className="flex-1 text-sm text-text-primary">{type.replace(/_/g, " ")}</span>
                {severityBadge(data.severity)}
                <span className="text-sm font-semibold text-text-primary w-10 text-right">{data.count}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function IssuesTab({ auditId }: { auditId: string }) {
  const [issues, setIssues] = useState<AuditIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [severity, setSeverity] = useState("");
  const [issueType, setIssueType] = useState("");
  const [issueTypes, setIssueTypes] = useState<string[]>([]);

  const loadIssues = useCallback(
    async (pg: number, sev: string, type: string) => {
      setLoading(true);
      try {
        const data = await api.siteAudit.issues(auditId, {
          page: pg,
          page_size: 20,
          severity: sev || undefined,
          issue_type: type || undefined,
        });
        setIssues(data.items);
        setTotalPages(data.pages);
        setTotal(data.total);
      } catch (err) {
        toast.error(parseApiError(err).message);
      } finally {
        setLoading(false);
      }
    },
    [auditId]
  );

  // Collect unique issue types on first load
  useEffect(() => {
    api.siteAudit
      .issues(auditId, { page: 1, page_size: 100 })
      .then((data) => {
        const types = [...new Set(data.items.map((i) => i.issue_type))].sort();
        setIssueTypes(types);
      })
      .catch(() => {});
  }, [auditId]);

  useEffect(() => {
    loadIssues(page, severity, issueType);
  }, [page, severity, issueType, loadIssues]);

  return (
    <div>
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 p-4 border-b border-surface-tertiary">
        <Filter className="h-4 w-4 text-text-muted" />
        <select
          value={severity}
          onChange={(e) => {
            setSeverity(e.target.value);
            setPage(1);
          }}
          className="text-sm border border-surface-tertiary rounded-lg px-3 py-1.5 bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500/30"
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
        </select>
        <select
          value={issueType}
          onChange={(e) => {
            setIssueType(e.target.value);
            setPage(1);
          }}
          className="text-sm border border-surface-tertiary rounded-lg px-3 py-1.5 bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500/30"
        >
          <option value="">All Issue Types</option>
          {issueTypes.map((t) => (
            <option key={t} value={t}>
              {t.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        <span className="text-xs text-text-muted ml-auto">{total} total issues</span>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
        </div>
      ) : issues.length === 0 ? (
        <p className="text-center text-text-secondary py-12">No issues match the current filters.</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-tertiary">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
                    Page URL
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
                    Issue Type
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
                    Severity
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
                    Message
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-tertiary">
                {issues.map((issue) => (
                  <tr key={issue.id} className="hover:bg-surface-secondary/50 transition-colors">
                    <td className="px-4 py-3 max-w-[200px]">
                      {issue.page_url ? (
                        <a
                          href={issue.page_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-primary-600 hover:underline truncate"
                          title={issue.page_url}
                        >
                          <span className="truncate">{truncateUrl(issue.page_url)}</span>
                          <ExternalLink className="h-3 w-3 shrink-0" />
                        </a>
                      ) : (
                        <span className="text-text-muted italic">Site-wide</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-surface-secondary text-text-primary">
                        {issue.issue_type.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3">{severityBadge(issue.severity)}</td>
                    <td className="px-4 py-3 text-text-secondary max-w-[300px] truncate" title={issue.message}>
                      {issue.message}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-surface-tertiary">
              <span className="text-xs text-text-muted">
                Page {page} of {totalPages}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function PagesTab({ auditId }: { auditId: string }) {
  const [pages, setPages] = useState<AuditPage[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [onlyWithIssues, setOnlyWithIssues] = useState(false);
  const [expandedPage, setExpandedPage] = useState<string | null>(null);

  const loadPages = useCallback(
    async (pg: number, hasIssues: boolean) => {
      setLoading(true);
      try {
        const data = await api.siteAudit.pages(auditId, {
          page: pg,
          page_size: 20,
          has_issues: hasIssues || undefined,
        });
        setPages(data.items);
        setTotalPages(data.pages);
        setTotal(data.total);
      } catch (err) {
        toast.error(parseApiError(err).message);
      } finally {
        setLoading(false);
      }
    },
    [auditId]
  );

  useEffect(() => {
    loadPages(page, onlyWithIssues);
  }, [page, onlyWithIssues, loadPages]);

  function toggleExpand(pageId: string) {
    setExpandedPage((prev) => (prev === pageId ? null : pageId));
  }

  const checkIcon = <Check className="h-3.5 w-3.5 text-green-500" />;
  const xIcon = <XIcon className="h-3.5 w-3.5 text-red-400" />;

  return (
    <div>
      {/* Filter bar */}
      <div className="flex items-center gap-3 p-4 border-b border-surface-tertiary">
        <label className="flex items-center gap-2 text-sm text-text-secondary cursor-pointer">
          <input
            type="checkbox"
            checked={onlyWithIssues}
            onChange={(e) => {
              setOnlyWithIssues(e.target.checked);
              setPage(1);
            }}
            className="rounded border-surface-tertiary text-primary-500 focus:ring-primary-500/30"
          />
          Only pages with issues
        </label>
        <span className="text-xs text-text-muted ml-auto">{total} pages</span>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
        </div>
      ) : pages.length === 0 ? (
        <p className="text-center text-text-secondary py-12">No pages found.</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-tertiary">
                  <th className="w-8" />
                  <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
                    URL
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
                    Status
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
                    Response
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
                    Words
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
                    Issues
                  </th>
                  <th className="text-center px-2 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
                    Canonical
                  </th>
                  <th className="text-center px-2 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
                    OG
                  </th>
                  <th className="text-center px-2 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
                    Schema
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-tertiary">
                {pages.map((pg) => {
                  const issueCount = pg.issues?.length ?? 0;
                  const isExpanded = expandedPage === pg.id;
                  return (
                    <Fragment key={pg.id}>
                      <tr
                        className={cn(
                          "hover:bg-surface-secondary/50 transition-colors cursor-pointer",
                          isExpanded && "bg-surface-secondary/30"
                        )}
                        onClick={() => toggleExpand(pg.id)}
                      >
                        <td className="pl-3">
                          {issueCount > 0 ? (
                            isExpanded ? (
                              <ChevronDown className="h-4 w-4 text-text-muted" />
                            ) : (
                              <ChevronRight className="h-4 w-4 text-text-muted" />
                            )
                          ) : null}
                        </td>
                        <td className="px-4 py-3 max-w-[250px]">
                          <a
                            href={pg.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-primary-600 hover:underline truncate"
                            title={pg.url}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <span className="truncate">{truncateUrl(pg.url)}</span>
                            <ExternalLink className="h-3 w-3 shrink-0" />
                          </a>
                        </td>
                        <td className={cn("px-4 py-3 font-medium", statusCodeColor(pg.status_code))}>
                          {pg.status_code ?? "---"}
                        </td>
                        <td
                          className={cn(
                            "px-4 py-3",
                            pg.response_time_ms != null && pg.response_time_ms > 3000
                              ? "text-red-600 font-medium"
                              : "text-text-secondary"
                          )}
                        >
                          {pg.response_time_ms != null ? `${pg.response_time_ms}ms` : "---"}
                        </td>
                        <td className="px-4 py-3 text-text-secondary">
                          {pg.word_count != null ? pg.word_count.toLocaleString() : "---"}
                        </td>
                        <td className="px-4 py-3">
                          {issueCount > 0 ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                              {issueCount}
                            </span>
                          ) : (
                            <span className="text-xs text-text-muted">0</span>
                          )}
                        </td>
                        <td className="text-center px-2 py-3">{pg.has_canonical ? checkIcon : xIcon}</td>
                        <td className="text-center px-2 py-3">{pg.has_og_tags ? checkIcon : xIcon}</td>
                        <td className="text-center px-2 py-3">{pg.has_structured_data ? checkIcon : xIcon}</td>
                      </tr>
                      {isExpanded && issueCount > 0 && (
                        <tr>
                          <td colSpan={9} className="bg-surface-secondary/50 px-8 py-3">
                            <div className="space-y-2">
                              {pg.issues?.map((issue, idx) => (
                                <div key={idx} className="flex items-center gap-3 text-sm">
                                  {severityBadge(issue.severity)}
                                  <span className="text-text-primary">{issue.type.replace(/_/g, " ")}</span>
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-surface-tertiary">
              <span className="text-xs text-text-muted">
                Page {page} of {totalPages}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Performance Tab (PageSpeed Insights)
// ---------------------------------------------------------------------------

const METRIC_NAMES: Record<string, string> = {
  lcp: "Largest Contentful Paint",
  cls: "Cumulative Layout Shift",
  tbt: "Total Blocking Time",
  fcp: "First Contentful Paint",
  si: "Speed Index",
  tti: "Time to Interactive",
};

function perfScoreClasses(score: number): { bg: string; text: string } {
  if (score >= 90) return { bg: "bg-green-100", text: "text-green-800" };
  if (score >= 50) return { bg: "bg-amber-100", text: "text-amber-800" };
  return { bg: "bg-red-100", text: "text-red-800" };
}

function perfScoreRing(score: number): string {
  if (score >= 90) return "border-green-500 bg-green-50 text-green-700";
  if (score >= 50) return "border-amber-500 bg-amber-50 text-amber-700";
  return "border-red-500 bg-red-50 text-red-700";
}

function PerformanceTab({ auditId }: { auditId: string }) {
  const [pages, setPages] = useState<AuditPage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.siteAudit
      .pages(auditId, { page: 1, page_size: 20 })
      .then((data) => {
        setPages(data.items.filter((p) => p.performance_score != null));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [auditId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
      </div>
    );
  }

  if (pages.length === 0) {
    return (
      <div className="p-8 text-center">
        <Gauge className="h-10 w-10 text-surface-tertiary mx-auto mb-3" />
        <p className="text-sm text-text-secondary">
          PageSpeed data is collected automatically for your top pages during the audit. No data available for this audit.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {pages.map((pg) => {
        const psd = pg.pagespeed_data;
        const score = pg.performance_score ?? 0;
        const ringClasses = perfScoreRing(score);

        // Extract the 6 core metrics in display order
        const metricKeys = ["lcp", "cls", "tbt", "fcp", "si", "tti"];
        const metrics = psd?.metrics ?? {};

        return (
          <Card key={pg.id} className="p-5 space-y-5">
            {/* Header: score circle + URL */}
            <div className="flex items-center gap-4">
              <div
                className={cn(
                  "w-12 h-12 rounded-full border-4 flex items-center justify-center shrink-0 font-bold text-sm",
                  ringClasses
                )}
              >
                {score}
              </div>
              <div className="min-w-0 flex-1">
                <a
                  href={pg.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-primary-600 hover:underline truncate block"
                  title={pg.url}
                >
                  {pg.url}
                </a>
                {psd?.strategy && (
                  <p className="text-xs text-text-muted mt-0.5">
                    Strategy: {psd.strategy.charAt(0).toUpperCase() + psd.strategy.slice(1)}
                  </p>
                )}
              </div>
            </div>

            {/* Core Web Vitals — 2x3 grid */}
            {Object.keys(metrics).length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">
                  Core Web Vitals
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {metricKeys.map((key) => {
                    const m = metrics[key];
                    if (!m) return null;
                    const sc = perfScoreClasses(m.score);
                    return (
                      <div
                        key={key}
                        className="flex items-center justify-between rounded-lg border border-surface-tertiary px-3 py-2"
                      >
                        <div className="min-w-0">
                          <p className="text-xs text-text-muted truncate">
                            {METRIC_NAMES[key] ?? key.toUpperCase()}
                          </p>
                          <p className="text-sm font-semibold text-text-primary">{m.display}</p>
                        </div>
                        <span
                          className={cn(
                            "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium shrink-0 ml-2",
                            sc.bg,
                            sc.text
                          )}
                        >
                          {m.score}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Opportunities */}
            {psd?.opportunities && psd.opportunities.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">
                  Top Opportunities
                </h4>
                <div className="space-y-2">
                  {psd.opportunities
                    .sort((a, b) => b.savings_ms - a.savings_ms)
                    .slice(0, 5)
                    .map((opp) => (
                      <div
                        key={opp.id}
                        className="flex items-center justify-between rounded-lg bg-surface-secondary/50 px-3 py-2"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="text-sm text-text-primary truncate">{opp.title}</p>
                          {opp.description && (
                            <p className="text-xs text-text-muted truncate mt-0.5">{opp.description}</p>
                          )}
                        </div>
                        {opp.savings_ms > 0 && (
                          <span className="text-xs font-medium text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full shrink-0 ml-2">
                            -{opp.savings_ms}ms
                          </span>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Need Fragment for table row expansion
// ---------------------------------------------------------------------------
import { Fragment } from "react";

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function SiteAuditPage() {
  useRequireAuth();

  const user = useAuthStore((s) => s.user);
  const isFree = !user?.subscription_tier || user.subscription_tier === "free";

  // History list
  const [audits, setAudits] = useState<SiteAudit[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  // Input state
  const [domain, setDomain] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Selected audit
  const [selected, setSelected] = useState<SiteAudit | null>(null);
  const [selectedLoading, setSelectedLoading] = useState(false);

  // Active tab in results view
  const [activeTab, setActiveTab] = useState<ResultTab>("overview");

  // Poll ref
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------

  const loadHistory = useCallback(async () => {
    try {
      const data = await api.siteAudit.list({ page: 1, page_size: 20 });
      setAudits(data.items);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const loadDetail = useCallback(async (id: string) => {
    setSelectedLoading(true);
    try {
      const data = await api.siteAudit.get(id);
      setSelected(data);
      return data;
    } catch (err) {
      toast.error(parseApiError(err).message);
      return null;
    } finally {
      setSelectedLoading(false);
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Polling for in-progress audits
  // ---------------------------------------------------------------------------

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (id: string) => {
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const data = await api.siteAudit.get(id);
          setSelected(data);
          // Update status in history list too
          setAudits((prev) =>
            prev.map((a) =>
              a.id === id
                ? { ...a, status: data.status, pages_crawled: data.pages_crawled, pages_discovered: data.pages_discovered }
                : a
            )
          );
          if (!isInProgress(data.status)) {
            stopPolling();
            if (data.status === "completed") {
              setActiveTab("overview");
            }
          }
        } catch {
          // silent poll failure
        }
      }, 3000);
    },
    [stopPolling]
  );

  useEffect(() => {
    if (selected && isInProgress(selected.status)) {
      startPolling(selected.id);
    } else {
      stopPolling();
    }
    return () => stopPolling();
  }, [selected?.id, selected?.status, startPolling, stopPolling]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  async function handleStart(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = domain.trim();
    if (!trimmed) return;
    setSubmitting(true);
    try {
      const audit = await api.siteAudit.start(trimmed);
      toast.success(`Audit started for ${trimmed}`);
      setDomain("");
      setAudits((prev) => [audit, ...prev]);
      const detail = await loadDetail(audit.id);
      if (detail) {
        setActiveTab("overview");
      }
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await api.siteAudit.delete(id);
      setAudits((prev) => prev.filter((a) => a.id !== id));
      if (selected?.id === id) {
        setSelected(null);
        stopPolling();
      }
      toast.success("Audit deleted.");
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  }

  async function handleSelectAudit(audit: SiteAudit) {
    setActiveTab("overview");
    await loadDetail(audit.id);
  }

  function handleBack() {
    setSelected(null);
    stopPolling();
    loadHistory();
  }

  async function handleExportCsv() {
    if (!selected) return;
    try {
      const csvText = await api.siteAudit.exportCsv(selected.id);
      const blob = new Blob([csvText], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `site-audit-${selected.domain}-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("CSV exported successfully.");
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  }

  // ---------------------------------------------------------------------------
  // Score circle component
  // ---------------------------------------------------------------------------

  function ScoreCircle({ score, size = "large" }: { score: number; size?: "large" | "small" }) {
    const isLarge = size === "large";
    return (
      <div
        className={cn(
          "rounded-full border-4 flex items-center justify-center shrink-0",
          scoreRingColor(score),
          scoreBgColor(score),
          isLarge ? "w-20 h-20" : "w-10 h-10"
        )}
      >
        <span className={cn("font-bold", scoreColor(score), isLarge ? "text-2xl" : "text-sm")}>
          {score}
        </span>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render: State 2 -- In Progress
  // ---------------------------------------------------------------------------

  if (selected && isInProgress(selected.status)) {
    const discoveredCount = selected.pages_discovered || 0;
    const crawledCount = selected.pages_crawled || 0;
    const progress = discoveredCount > 0 ? Math.round((crawledCount / discoveredCount) * 100) : 0;
    const barWidth = discoveredCount > 0 ? Math.max(progress, 5) : 0;

    return (
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleBack}
            className="p-2 rounded-xl hover:bg-surface-secondary transition-colors"
            aria-label="Back"
          >
            <ArrowLeft className="h-5 w-5 text-text-secondary" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
              <Globe className="h-6 w-6 text-primary-500" />
              {selected.domain}
            </h1>
            <p className="text-sm text-text-secondary mt-0.5">Audit in progress</p>
          </div>
        </div>

        <Card className="p-6 space-y-5">
          <div className="flex items-center gap-3">
            {statusBadge(selected.status)}
            <Loader2 className="h-4 w-4 animate-spin text-primary-500" />
            <span className="text-sm text-text-secondary">
              {selected.status === "crawling" ? "Crawling pages..." : "Analyzing pages..."}
            </span>
          </div>

          {discoveredCount > 0 && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm text-text-secondary">
                <span>Pages crawled</span>
                <span>
                  {crawledCount} / {discoveredCount}
                </span>
              </div>
              <div className="h-2 bg-surface-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-500 rounded-full transition-all duration-500"
                  style={{ width: `${barWidth}%` }}
                />
              </div>
              <p className="text-xs text-text-muted">{progress}% complete</p>
            </div>
          )}

          {discoveredCount === 0 && (
            <div className="h-2 bg-surface-secondary rounded-full overflow-hidden">
              <div className="h-full bg-primary-400 rounded-full animate-pulse w-1/3" />
            </div>
          )}

          <p className="text-xs text-text-muted">
            This usually takes 1-5 minutes depending on the site size. You can navigate away and come back.
          </p>
        </Card>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render: State 3 -- Results (completed)
  // ---------------------------------------------------------------------------

  if (selected && selected.status === "completed") {
    const tabs: { key: ResultTab; label: string; icon?: React.ReactNode }[] = [
      { key: "overview", label: "Overview" },
      { key: "issues", label: "Issues" },
      { key: "pages", label: "Pages" },
      { key: "performance", label: "Performance", icon: <Gauge className="h-3.5 w-3.5" /> },
    ];

    return (
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleBack}
            className="p-2 rounded-xl hover:bg-surface-secondary transition-colors"
            aria-label="Back"
          >
            <ArrowLeft className="h-5 w-5 text-text-secondary" />
          </button>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
              <Globe className="h-6 w-6 text-primary-500" />
              {selected.domain}
            </h1>
            <p className="text-sm text-text-secondary mt-0.5">
              {selected.completed_at ? `Completed ${formatDate(selected.completed_at)}` : ""}
            </p>
          </div>
          <ScoreCircle score={selected.score} size="large" />
          <Button variant="outline" onClick={handleExportCsv} className="ml-2">
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          <Card className="p-4 flex flex-col items-center justify-center text-center">
            <ScoreCircle score={selected.score} size="large" />
            <p className="text-xs text-text-secondary mt-2 font-medium">Score</p>
          </Card>

          <Card className="p-4 flex flex-col items-center justify-center text-center border-red-200 bg-red-50/50">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-red-500" />
              <span className="text-2xl font-bold text-red-700">{selected.critical_issues}</span>
            </div>
            <p className="text-xs text-red-600 mt-1 font-medium">Critical</p>
          </Card>

          <Card className="p-4 flex flex-col items-center justify-center text-center border-amber-200 bg-amber-50/50">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              <span className="text-2xl font-bold text-amber-700">{selected.warning_issues}</span>
            </div>
            <p className="text-xs text-amber-600 mt-1 font-medium">Warnings</p>
          </Card>

          <Card className="p-4 flex flex-col items-center justify-center text-center border-blue-200 bg-blue-50/50">
            <div className="flex items-center gap-2">
              <Info className="h-5 w-5 text-blue-500" />
              <span className="text-2xl font-bold text-blue-700">{selected.info_issues}</span>
            </div>
            <p className="text-xs text-blue-600 mt-1 font-medium">Info</p>
          </Card>

          <Card className="p-4 flex flex-col items-center justify-center text-center">
            <div className="flex items-center gap-2">
              <ScanSearch className="h-5 w-5 text-primary-500" />
              <span className="text-2xl font-bold text-text-primary">{selected.pages_crawled}</span>
            </div>
            <p className="text-xs text-text-secondary mt-1 font-medium">Pages Crawled</p>
          </Card>
        </div>

        {/* Tabs */}
        <Card className="overflow-hidden">
          <div className="flex border-b border-surface-tertiary">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={cn(
                  "px-5 py-3 text-sm font-medium transition-colors border-b-2 -mb-px",
                  activeTab === tab.key
                    ? "border-primary-500 text-primary-600"
                    : "border-transparent text-text-secondary hover:text-text-primary"
                )}
              >
                {tab.icon && <span className="mr-1.5">{tab.icon}</span>}
                {tab.label}
              </button>
            ))}
          </div>

          <div className="min-h-[300px]">
            {activeTab === "overview" && <OverviewTab audit={selected} />}
            {activeTab === "issues" && <IssuesTab auditId={selected.id} />}
            {activeTab === "pages" && <PagesTab auditId={selected.id} />}
            {activeTab === "performance" && <PerformanceTab auditId={selected.id} />}
          </div>
        </Card>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render: State 1 -- Input + History
  // ---------------------------------------------------------------------------

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
          <ScanSearch className="h-6 w-6 text-primary-500" />
          Site Audit
        </h1>
        <p className="text-text-secondary mt-1">
          Scan your website for SEO issues and get actionable recommendations.
        </p>
      </div>

      {/* Free tier gate */}
      {isFree && (
        <Card className="p-6 border-amber-200 bg-amber-50/50">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-800">
                Site Audit is a premium feature.
              </p>
              <p className="text-sm text-amber-700 mt-1">
                Upgrade your plan to access website scanning and SEO issue detection.
              </p>
              <Link
                href="/settings/billing"
                className="inline-flex items-center gap-1 text-sm font-medium text-primary-600 hover:text-primary-700 mt-3 hover:underline"
              >
                Upgrade now
                <ChevronRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </Card>
      )}

      {/* Failed state inline banner */}
      {selected && selected.status === "failed" && (
        <Card className="p-4 border-red-200 bg-red-50 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-800">
              Audit failed for {selected.domain}
            </p>
            {selected.error_message && (
              <p className="text-xs text-red-600 mt-0.5">{selected.error_message}</p>
            )}
          </div>
          <button
            onClick={() => setSelected(null)}
            className="text-xs text-red-600 hover:text-red-800"
          >
            Dismiss
          </button>
        </Card>
      )}

      {/* Domain input form */}
      {!isFree && (
        <Card className="p-6">
          <h2 className="text-base font-semibold text-text-primary mb-4">Start a New Audit</h2>
          <form onSubmit={handleStart} className="flex gap-3">
            <div className="relative flex-1">
              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
              <input
                type="text"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="e.g. example.com"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-surface-tertiary bg-surface text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 transition-colors"
                disabled={submitting}
              />
            </div>
            <Button type="submit" disabled={submitting || !domain.trim()}>
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Starting...
                </>
              ) : (
                <>
                  <ScanSearch className="h-4 w-4 mr-2" />
                  Start Audit
                </>
              )}
            </Button>
          </form>
        </Card>
      )}

      {/* Previous audits */}
      <div>
        <h2 className="text-base font-semibold text-text-primary mb-3">Previous Audits</h2>

        {historyLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
          </div>
        ) : audits.length === 0 ? (
          <Card className="p-8 text-center">
            <ScanSearch className="h-10 w-10 text-surface-tertiary mx-auto mb-3" />
            <p className="text-text-secondary text-sm">
              No audits yet. Enter a domain above to get started.
            </p>
          </Card>
        ) : (
          <div className="space-y-3">
            {audits.map((audit) => (
              <Card
                key={audit.id}
                className={cn(
                  "p-4 flex items-center gap-4 cursor-pointer hover:bg-surface-secondary/50 transition-colors",
                  selectedLoading && "opacity-60 pointer-events-none"
                )}
                onClick={() => handleSelectAudit(audit)}
              >
                {/* Score circle */}
                <ScoreCircle score={audit.score} size="small" />

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-text-primary truncate">
                    {audit.domain}
                  </p>
                  <p className="text-xs text-text-muted mt-0.5">
                    {formatDate(audit.created_at)}
                    {audit.total_issues > 0 && ` \u00b7 ${audit.total_issues} issues`}
                    {audit.pages_crawled > 0 && ` \u00b7 ${audit.pages_crawled} pages`}
                  </p>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {audit.critical_issues > 0 && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                      <AlertCircle className="h-3 w-3" />
                      {audit.critical_issues}
                    </span>
                  )}
                  {audit.warning_issues > 0 && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                      <AlertTriangle className="h-3 w-3" />
                      {audit.warning_issues}
                    </span>
                  )}
                  {statusBadge(audit.status)}
                  <button
                    onClick={(e) => handleDelete(audit.id, e)}
                    aria-label={`Delete audit for ${audit.domain}`}
                    className="p-1.5 rounded-lg text-text-muted hover:text-red-500 hover:bg-red-50 transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
