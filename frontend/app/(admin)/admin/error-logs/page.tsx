"use client";

import { useEffect, useState, useCallback } from "react";
import { api, parseApiError } from "@/lib/api";
import type {
  AdminErrorLog,
  AdminErrorStats,
  AdminErrorFilterOptions,
  AdminErrorLogQueryParams,
} from "@/lib/api";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  Bug,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Search,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertTriangle,
  TrendingUp,
  Clock,
  Server,
  Copy,
  Filter,
} from "lucide-react";
import { clsx } from "clsx";

function SeverityBadge({ severity }: { severity: string }) {
  const styles: Record<string, string> = {
    critical: "bg-red-100 text-red-800",
    error: "bg-orange-100 text-orange-800",
    warning: "bg-yellow-100 text-yellow-800",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${
        styles[severity] ?? "bg-surface-tertiary text-text-primary"
      }`}
    >
      {severity}
    </span>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  color,
  subtext,
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
  color: string;
  subtext?: string;
}) {
  const bgColors: Record<string, string> = {
    red: "bg-red-50",
    orange: "bg-orange-50",
    yellow: "bg-yellow-50",
    blue: "bg-blue-50",
    green: "bg-green-50",
  };
  const iconColors: Record<string, string> = {
    red: "text-red-600",
    orange: "text-orange-600",
    yellow: "text-yellow-600",
    blue: "text-blue-600",
    green: "text-green-600",
  };
  return (
    <div className="bg-surface rounded-xl border border-surface-tertiary p-5">
      <div className="flex items-center justify-between mb-3">
        <div className={`p-2.5 rounded-lg ${bgColors[color] ?? "bg-surface-secondary"}`}>
          <Icon className={`h-5 w-5 ${iconColors[color] ?? "text-text-secondary"}`} />
        </div>
      </div>
      <h3 className="text-2xl font-bold text-text-primary">{value}</h3>
      <p className="text-sm text-text-muted mt-1">{label}</p>
      {subtext && <p className="text-xs text-text-muted mt-1">{subtext}</p>}
    </div>
  );
}

function TrendChart({ data }: { data: AdminErrorStats["daily_trend"] }) {
  if (data.length === 0) {
    return (
      <div className="h-[200px] flex items-center justify-center text-text-muted text-sm">
        No error data yet
      </div>
    );
  }

  const maxCount = Math.max(...data.map((d) => d.count), 1);

  return (
    <div className="h-[200px] flex items-end gap-1 px-2">
      {data.map((day, i) => {
        const height = (day.count / maxCount) * 100;
        const criticalHeight = day.count > 0 ? (day.critical / day.count) * height : 0;
        const errorHeight = day.count > 0 ? (day.error / day.count) * height : 0;
        const warningHeight = height - criticalHeight - errorHeight;

        return (
          <div
            key={i}
            className="flex-1 flex flex-col justify-end group relative"
            title={`${day.date}: ${day.count} errors (${day.critical} critical, ${day.error} error, ${day.warning} warning)`}
          >
            {day.count > 0 && (
              <div className="absolute -top-6 left-1/2 -translate-x-1/2 hidden group-hover:block bg-text-primary text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                {day.count} errors
              </div>
            )}
            <div className="flex flex-col rounded-t-sm overflow-hidden">
              {criticalHeight > 0 && (
                <div
                  className="bg-red-500 w-full"
                  style={{ height: `${criticalHeight}%`, minHeight: criticalHeight > 0 ? 2 : 0 }}
                />
              )}
              {errorHeight > 0 && (
                <div
                  className="bg-orange-500 w-full"
                  style={{ height: `${errorHeight}%`, minHeight: errorHeight > 0 ? 2 : 0 }}
                />
              )}
              {warningHeight > 0 && (
                <div
                  className="bg-yellow-400 w-full"
                  style={{ height: `${warningHeight}%`, minHeight: warningHeight > 0 ? 2 : 0 }}
                />
              )}
            </div>
            {day.count === 0 && (
              <div className="bg-surface-tertiary w-full rounded-t-sm" style={{ height: 2 }} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function AdminErrorLogsPage() {
  const [errors, setErrors] = useState<AdminErrorLog[]>([]);
  const [stats, setStats] = useState<AdminErrorStats | null>(null);
  const [filterOptions, setFilterOptions] = useState<AdminErrorFilterOptions | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [severityFilter, setSeverityFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [serviceFilter, setServiceFilter] = useState("all");
  const [resolvedFilter, setResolvedFilter] = useState("unresolved");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchInput, setSearchInput] = useState("");

  // UI state
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [updatingIds, setUpdatingIds] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{
    action: () => void;
    title: string;
    message: string;
    confirmLabel?: string;
    variant?: "danger" | "warning" | "default";
  } | null>(null);

  const pageSize = 20;

  const loadStats = useCallback(async () => {
    try {
      setStatsLoading(true);
      const [statsData, options] = await Promise.all([
        api.admin.errorLogs.stats(),
        api.admin.errorLogs.filterOptions(),
      ]);
      setStats(statsData);
      setFilterOptions(options);
    } catch (err) {
      // Stats are non-critical, don't block the page
      console.error("Failed to load error stats:", err);
    } finally {
      setStatsLoading(false);
    }
  }, []);

  const loadErrors = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params: AdminErrorLogQueryParams = {
        page,
        page_size: pageSize,
      };
      if (severityFilter !== "all") params.severity = severityFilter;
      if (typeFilter !== "all") params.error_type = typeFilter;
      if (serviceFilter !== "all") params.service = serviceFilter;
      if (resolvedFilter === "unresolved") params.is_resolved = false;
      if (resolvedFilter === "resolved") params.is_resolved = true;
      if (searchQuery) params.search = searchQuery;

      const response = await api.admin.errorLogs.list(params);
      setErrors(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [page, severityFilter, typeFilter, serviceFilter, resolvedFilter, searchQuery]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    loadErrors();
  }, [loadErrors]);

  const handleSearch = () => {
    setSearchQuery(searchInput);
    setPage(1);
  };

  const handleResolve = (errorItem: AdminErrorLog) => {
    setConfirmAction({
      action: async () => {
        setUpdatingIds((prev) => new Set(prev).add(errorItem.id));
        try {
          const updated = await api.admin.errorLogs.update(errorItem.id, {
            is_resolved: !errorItem.is_resolved,
          });
          setErrors((prev) =>
            prev.map((e) => (e.id === errorItem.id ? updated : e))
          );
          loadStats();
          toast.success(
            errorItem.is_resolved ? "Error reopened" : "Error marked as resolved"
          );
        } catch (err) {
          toast.error(parseApiError(err).message);
        } finally {
          setUpdatingIds((prev) => {
            const next = new Set(prev);
            next.delete(errorItem.id);
            return next;
          });
        }
      },
      title: errorItem.is_resolved ? "Reopen Error" : "Resolve Error",
      message: errorItem.is_resolved
        ? "Reopen this error for further investigation?"
        : "Mark this error as resolved?",
      confirmLabel: errorItem.is_resolved ? "Reopen" : "Resolve",
      variant: "default",
    });
  };

  const copyErrorDetails = (errorItem: AdminErrorLog) => {
    const details = [
      `Error: ${errorItem.title}`,
      `Type: ${errorItem.error_type}`,
      `Severity: ${errorItem.severity}`,
      errorItem.service && `Service: ${errorItem.service}`,
      errorItem.endpoint && `Endpoint: ${errorItem.http_method ?? "GET"} ${errorItem.endpoint}`,
      errorItem.http_status && `HTTP Status: ${errorItem.http_status}`,
      errorItem.error_code && `Error Code: ${errorItem.error_code}`,
      `Occurrences: ${errorItem.occurrence_count}`,
      `First seen: ${new Date(errorItem.first_seen_at).toLocaleString()}`,
      `Last seen: ${new Date(errorItem.last_seen_at).toLocaleString()}`,
      errorItem.user_email && `User: ${errorItem.user_email}`,
      errorItem.message && `\nMessage:\n${errorItem.message}`,
      errorItem.stack_trace && `\nStack Trace:\n${errorItem.stack_trace}`,
      errorItem.context && `\nContext:\n${JSON.stringify(errorItem.context, null, 2)}`,
    ]
      .filter(Boolean)
      .join("\n");

    navigator.clipboard.writeText(details);
    toast.success("Error details copied to clipboard");
  };

  return (
    <div className="space-y-6">
      <ConfirmDialog
        isOpen={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        onConfirm={() => {
          confirmAction?.action();
          setConfirmAction(null);
        }}
        title={confirmAction?.title ?? ""}
        message={confirmAction?.message ?? ""}
        variant={confirmAction?.variant ?? "default"}
        confirmLabel={confirmAction?.confirmLabel ?? "Confirm"}
      />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Error Logs</h1>
          <p className="text-text-muted mt-1">
            Track, investigate, and resolve system errors
          </p>
        </div>
        <button
          onClick={() => {
            loadErrors();
            loadStats();
          }}
          className="flex items-center gap-2 px-4 py-2 bg-surface border border-surface-tertiary rounded-lg hover:bg-surface-secondary text-sm font-medium"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard
          label="Unresolved"
          value={statsLoading ? "—" : (stats?.unresolved_errors ?? 0)}
          icon={XCircle}
          color="red"
        />
        <StatCard
          label="Critical"
          value={statsLoading ? "—" : (stats?.critical_errors ?? 0)}
          icon={AlertTriangle}
          color="orange"
        />
        <StatCard
          label="Today"
          value={statsLoading ? "—" : (stats?.errors_today ?? 0)}
          icon={Clock}
          color="blue"
        />
        <StatCard
          label="This Week"
          value={statsLoading ? "—" : (stats?.errors_this_week ?? 0)}
          icon={TrendingUp}
          color="yellow"
        />
        <StatCard
          label="This Month"
          value={statsLoading ? "—" : (stats?.errors_this_month ?? 0)}
          icon={Bug}
          color="orange"
        />
        <StatCard
          label="Total"
          value={statsLoading ? "—" : (stats?.total_errors ?? 0)}
          icon={Server}
          color="blue"
        />
      </div>

      {/* Trend Chart + Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Error Trend */}
        <div className="lg:col-span-2 bg-surface rounded-xl border border-surface-tertiary p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">
            Error Trend (30 days)
          </h2>
          <div className="flex items-center gap-4 mb-3 text-xs text-text-muted">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-sm bg-red-500" /> Critical
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-sm bg-orange-500" /> Error
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-sm bg-yellow-400" /> Warning
            </span>
          </div>
          {statsLoading ? (
            <div className="h-[200px] flex items-center justify-center">
              <div className="h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <TrendChart data={stats?.daily_trend ?? []} />
          )}
        </div>

        {/* By Service */}
        <div className="bg-surface rounded-xl border border-surface-tertiary p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">
            By Service
          </h2>
          {statsLoading ? (
            <div className="h-[200px] flex items-center justify-center">
              <div className="h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : stats?.by_service && stats.by_service.length > 0 ? (
            <div className="space-y-3">
              {stats.by_service.map((s) => {
                const maxCount = Math.max(
                  ...stats.by_service.map((x) => x.count),
                  1
                );
                return (
                  <div key={s.service}>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-text-secondary capitalize">
                        {s.service.replace(/_/g, " ")}
                      </span>
                      <span className="font-medium text-text-primary">
                        {s.count}
                      </span>
                    </div>
                    <div className="h-2 bg-surface-tertiary rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary-500 rounded-full"
                        style={{
                          width: `${(s.count / maxCount) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="h-[200px] flex items-center justify-center text-text-muted text-sm">
              No data yet
            </div>
          )}
        </div>
      </div>

      {/* Top Recurring Errors */}
      {stats?.top_recurring && stats.top_recurring.length > 0 && (
        <div className="bg-surface rounded-xl border border-surface-tertiary p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">
            Top Recurring Errors
          </h2>
          <div className="space-y-3">
            {stats.top_recurring.map((e) => (
              <div
                key={e.id}
                className="flex items-center justify-between p-3 bg-surface-secondary rounded-lg"
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <SeverityBadge severity={e.severity} />
                  <span className="text-sm text-text-primary truncate">
                    {e.title}
                  </span>
                  {e.service && (
                    <span className="text-xs text-text-muted">
                      {e.service}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <span className="text-sm font-bold text-red-600">
                    {e.occurrence_count}x
                  </span>
                  <span className="text-xs text-text-muted">
                    last: {new Date(e.last_seen_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters + Search */}
      <div className="bg-surface rounded-xl border border-surface-tertiary p-4">
        <div className="flex flex-col gap-4">
          {/* Search bar */}
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
              <input
                type="text"
                placeholder="Search error titles and messages..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="w-full pl-10 pr-4 py-2 border border-surface-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              />
            </div>
            <button
              onClick={handleSearch}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium"
            >
              Search
            </button>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 border rounded-lg text-sm font-medium transition-colors",
                showFilters
                  ? "border-primary-300 bg-primary-50 text-primary-700"
                  : "border-surface-tertiary hover:bg-surface-secondary"
              )}
            >
              <Filter className="h-4 w-4" />
              Filters
            </button>
          </div>

          {/* Filter dropdowns */}
          {showFilters && (
            <div className="flex flex-col sm:flex-row gap-3 pt-2 border-t border-surface-tertiary">
              <select
                value={severityFilter}
                onChange={(e) => {
                  setSeverityFilter(e.target.value);
                  setPage(1);
                }}
                className="px-4 py-2 border border-surface-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              >
                <option value="all">All Severities</option>
                <option value="warning">Warning</option>
                <option value="error">Error</option>
                <option value="critical">Critical</option>
              </select>

              <select
                value={typeFilter}
                onChange={(e) => {
                  setTypeFilter(e.target.value);
                  setPage(1);
                }}
                className="px-4 py-2 border border-surface-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              >
                <option value="all">All Error Types</option>
                {filterOptions?.error_types.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>

              <select
                value={serviceFilter}
                onChange={(e) => {
                  setServiceFilter(e.target.value);
                  setPage(1);
                }}
                className="px-4 py-2 border border-surface-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              >
                <option value="all">All Services</option>
                {filterOptions?.services.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>

              <select
                value={resolvedFilter}
                onChange={(e) => {
                  setResolvedFilter(e.target.value);
                  setPage(1);
                }}
                className="px-4 py-2 border border-surface-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              >
                <option value="all">All Status</option>
                <option value="unresolved">Unresolved</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Error List */}
      {loading ? (
        <div className="bg-surface rounded-xl border border-surface-tertiary p-12 text-center">
          <div className="inline-block h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          <p className="mt-4 text-text-muted">Loading error logs...</p>
        </div>
      ) : error ? (
        <div className="bg-surface rounded-xl border border-surface-tertiary p-12 text-center">
          <p className="text-red-600">{error}</p>
          <button
            onClick={loadErrors}
            className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Retry
          </button>
        </div>
      ) : errors.length === 0 ? (
        <div className="bg-surface rounded-xl border border-surface-tertiary p-12 text-center">
          <Bug className="h-12 w-12 text-text-muted mx-auto mb-4" />
          <p className="text-lg font-medium text-text-primary mb-1">No errors found</p>
          <p className="text-text-muted">
            {resolvedFilter === "unresolved"
              ? "All clear! No unresolved errors."
              : "No errors match the current filters."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {errors.map((errorItem) => {
            const isExpanded = expandedId === errorItem.id;
            const isUpdating = updatingIds.has(errorItem.id);

            return (
              <div
                key={errorItem.id}
                className={clsx(
                  "bg-surface rounded-xl border transition-colors",
                  errorItem.is_resolved
                    ? "border-surface-tertiary opacity-70"
                    : "border-surface-tertiary shadow-sm",
                  !errorItem.is_resolved &&
                    errorItem.severity === "critical" &&
                    "border-l-4 border-l-red-500",
                  !errorItem.is_resolved &&
                    errorItem.severity === "error" &&
                    "border-l-4 border-l-orange-500",
                  !errorItem.is_resolved &&
                    errorItem.severity === "warning" &&
                    "border-l-4 border-l-yellow-500"
                )}
              >
                {/* Main row */}
                <div className="p-5">
                  <div className="flex flex-col sm:flex-row sm:items-start gap-4">
                    <div className="flex-1 min-w-0">
                      {/* Title + badges */}
                      <div className="flex items-center flex-wrap gap-2 mb-2">
                        <SeverityBadge severity={errorItem.severity} />
                        <span className="text-xs font-mono px-2 py-0.5 bg-surface-secondary rounded text-text-secondary">
                          {errorItem.error_type}
                        </span>
                        {errorItem.occurrence_count > 1 && (
                          <span className="text-xs font-bold px-2 py-0.5 bg-red-50 text-red-700 rounded-full">
                            {errorItem.occurrence_count}x
                          </span>
                        )}
                        {errorItem.is_resolved && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-800">
                            <CheckCircle className="h-3 w-3" />
                            Resolved
                          </span>
                        )}
                      </div>

                      {/* Title */}
                      <h3 className="text-sm font-semibold text-text-primary mb-1 break-all">
                        {errorItem.title.length > 200
                          ? errorItem.title.substring(0, 200) + "..."
                          : errorItem.title}
                      </h3>

                      {/* Meta info */}
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
                        {errorItem.service && (
                          <span>
                            Service:{" "}
                            <span className="text-text-secondary capitalize">
                              {errorItem.service.replace(/_/g, " ")}
                            </span>
                          </span>
                        )}
                        {errorItem.endpoint && (
                          <span>
                            <span className="text-text-secondary font-mono">
                              {errorItem.http_method ?? "GET"}{" "}
                              {errorItem.endpoint.length > 60
                                ? errorItem.endpoint.substring(0, 60) + "..."
                                : errorItem.endpoint}
                            </span>
                          </span>
                        )}
                        {errorItem.http_status && (
                          <span>
                            Status:{" "}
                            <span className="text-text-secondary font-mono">
                              {errorItem.http_status}
                            </span>
                          </span>
                        )}
                        {errorItem.user_email && (
                          <span>
                            User:{" "}
                            <span className="text-text-secondary">
                              {errorItem.user_email}
                            </span>
                          </span>
                        )}
                        <span>
                          Last seen:{" "}
                          {new Date(errorItem.last_seen_at).toLocaleDateString()}{" "}
                          {new Date(errorItem.last_seen_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 sm:flex-shrink-0">
                      <button
                        onClick={() => copyErrorDetails(errorItem)}
                        title="Copy error details"
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-surface-tertiary text-text-secondary hover:bg-surface-secondary transition-colors"
                      >
                        <Copy className="h-3.5 w-3.5" />
                        Copy
                      </button>
                      <button
                        onClick={() => handleResolve(errorItem)}
                        disabled={isUpdating}
                        className={clsx(
                          "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors disabled:opacity-50",
                          errorItem.is_resolved
                            ? "border-yellow-200 text-yellow-700 bg-yellow-50 hover:bg-yellow-100"
                            : "border-green-200 text-green-700 bg-green-50 hover:bg-green-100"
                        )}
                      >
                        {errorItem.is_resolved ? (
                          <>
                            <XCircle className="h-3.5 w-3.5" />
                            Reopen
                          </>
                        ) : (
                          <>
                            <CheckCircle className="h-3.5 w-3.5" />
                            Resolve
                          </>
                        )}
                      </button>
                      <button
                        onClick={() =>
                          setExpandedId(isExpanded ? null : errorItem.id)
                        }
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-surface-tertiary text-text-secondary hover:bg-surface-secondary transition-colors"
                      >
                        {isExpanded ? (
                          <>
                            <ChevronUp className="h-3.5 w-3.5" />
                            Less
                          </>
                        ) : (
                          <>
                            <ChevronDown className="h-3.5 w-3.5" />
                            More
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Expanded detail */}
                {isExpanded && (
                  <div className="border-t border-surface-tertiary p-5 bg-surface-secondary/50 space-y-4">
                    {/* Full message */}
                    {errorItem.message && (
                      <div>
                        <h4 className="text-xs font-semibold text-text-secondary uppercase mb-1">
                          Error Message
                        </h4>
                        <pre className="text-sm text-text-primary bg-surface p-3 rounded-lg overflow-x-auto whitespace-pre-wrap break-all border border-surface-tertiary">
                          {errorItem.message}
                        </pre>
                      </div>
                    )}

                    {/* Stack trace */}
                    {errorItem.stack_trace && (
                      <div>
                        <h4 className="text-xs font-semibold text-text-secondary uppercase mb-1">
                          Stack Trace
                        </h4>
                        <pre className="text-xs text-text-secondary bg-surface p-3 rounded-lg overflow-x-auto whitespace-pre-wrap break-all border border-surface-tertiary max-h-[300px] overflow-y-auto font-mono">
                          {errorItem.stack_trace}
                        </pre>
                      </div>
                    )}

                    {/* Context JSON */}
                    {errorItem.context &&
                      Object.keys(errorItem.context).length > 0 && (
                        <div>
                          <h4 className="text-xs font-semibold text-text-secondary uppercase mb-1">
                            Context
                          </h4>
                          <pre className="text-xs text-text-secondary bg-surface p-3 rounded-lg overflow-x-auto whitespace-pre-wrap break-all border border-surface-tertiary font-mono">
                            {JSON.stringify(errorItem.context, null, 2)}
                          </pre>
                        </div>
                      )}

                    {/* Metadata grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <span className="text-xs text-text-muted block">
                          Error ID
                        </span>
                        <span className="font-mono text-text-secondary text-xs break-all">
                          {errorItem.id}
                        </span>
                      </div>
                      <div>
                        <span className="text-xs text-text-muted block">
                          First Seen
                        </span>
                        <span className="text-text-secondary text-xs">
                          {new Date(errorItem.first_seen_at).toLocaleString()}
                        </span>
                      </div>
                      <div>
                        <span className="text-xs text-text-muted block">
                          Last Seen
                        </span>
                        <span className="text-text-secondary text-xs">
                          {new Date(errorItem.last_seen_at).toLocaleString()}
                        </span>
                      </div>
                      <div>
                        <span className="text-xs text-text-muted block">
                          Occurrences
                        </span>
                        <span className="text-text-primary font-bold">
                          {errorItem.occurrence_count}
                        </span>
                      </div>
                      {errorItem.request_id && (
                        <div>
                          <span className="text-xs text-text-muted block">
                            Request ID
                          </span>
                          <span className="font-mono text-text-secondary text-xs break-all">
                            {errorItem.request_id}
                          </span>
                        </div>
                      )}
                      {errorItem.ip_address && (
                        <div>
                          <span className="text-xs text-text-muted block">
                            IP Address
                          </span>
                          <span className="text-text-secondary text-xs">
                            {errorItem.ip_address}
                          </span>
                        </div>
                      )}
                      {errorItem.resource_type && (
                        <div>
                          <span className="text-xs text-text-muted block">
                            Resource
                          </span>
                          <span className="text-text-secondary text-xs capitalize">
                            {errorItem.resource_type}
                            {errorItem.resource_id && (
                              <span className="font-mono ml-1">
                                ({errorItem.resource_id.substring(0, 8)}...)
                              </span>
                            )}
                          </span>
                        </div>
                      )}
                      {errorItem.user_agent && (
                        <div className="col-span-2">
                          <span className="text-xs text-text-muted block">
                            User Agent
                          </span>
                          <span className="text-text-secondary text-xs break-all">
                            {errorItem.user_agent}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Resolution info */}
                    {errorItem.is_resolved && (
                      <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                        <h4 className="text-xs font-semibold text-green-800 uppercase mb-1">
                          Resolution
                        </h4>
                        <div className="text-sm text-green-700">
                          <p>
                            Resolved by{" "}
                            <span className="font-medium">
                              {errorItem.resolver_email ?? "Unknown"}
                            </span>
                            {errorItem.resolved_at && (
                              <span>
                                {" "}
                                on{" "}
                                {new Date(
                                  errorItem.resolved_at
                                ).toLocaleString()}
                              </span>
                            )}
                          </p>
                          {errorItem.resolution_notes && (
                            <p className="mt-1">{errorItem.resolution_notes}</p>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {!loading && !error && errors.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 px-1">
          <p className="text-sm text-text-muted">
            Showing {(page - 1) * pageSize + 1} to{" "}
            {Math.min(page * pageSize, total)} of {total} errors
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 rounded-lg border border-surface-tertiary hover:bg-surface-secondary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page * pageSize >= total}
              className="p-2 rounded-lg border border-surface-tertiary hover:bg-surface-secondary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
