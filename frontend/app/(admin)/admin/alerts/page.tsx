"use client";

import { useEffect, useState } from "react";
import { api, parseApiError } from "@/lib/api";
import type { AdminAlert } from "@/lib/api";
import {
  Bell,
  ChevronLeft,
  ChevronRight,
  CheckCheck,
  Check,
  ShieldAlert,
  Info,
  AlertTriangle,
  XOctagon,
} from "lucide-react";
import { clsx } from "clsx";

function SeverityIcon({ severity }: { severity: string }) {
  if (severity === "critical") {
    return <XOctagon className="h-4 w-4 text-red-600" />;
  }
  if (severity === "warning") {
    return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
  }
  return <Info className="h-4 w-4 text-blue-600" />;
}

function SeverityBadge({ severity }: { severity: string }) {
  const styles: Record<string, string> = {
    critical: "bg-red-100 text-red-800",
    warning: "bg-yellow-100 text-yellow-800",
    info: "bg-blue-100 text-blue-800",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${
        styles[severity] ?? "bg-gray-100 text-gray-800"
      }`}
    >
      <SeverityIcon severity={severity} />
      {severity}
    </span>
  );
}

function SeverityDot({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: "bg-red-500",
    warning: "bg-yellow-500",
    info: "bg-blue-500",
  };
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full flex-shrink-0 ${
        colors[severity] ?? "bg-gray-400"
      }`}
    />
  );
}

export default function AdminAlertsPage() {
  const [alerts, setAlerts] = useState<AdminAlert[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState("all");
  const [readFilter, setReadFilter] = useState("all");
  const [markingAllRead, setMarkingAllRead] = useState(false);
  const [updatingIds, setUpdatingIds] = useState<Set<string>>(new Set());

  const pageSize = 20;

  useEffect(() => {
    loadAlerts();
  }, [page, severityFilter, readFilter]);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: {
        page: number;
        page_size: number;
        severity?: string;
        is_read?: boolean;
      } = {
        page,
        page_size: pageSize,
      };
      if (severityFilter !== "all") params.severity = severityFilter;
      if (readFilter === "unread") params.is_read = false;
      if (readFilter === "read") params.is_read = true;

      const response = await api.admin.alerts.list(params);
      setAlerts(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkAllRead = async () => {
    if (!confirm("Mark all alerts as read?")) return;
    try {
      setMarkingAllRead(true);
      await api.admin.alerts.markAllRead();
      await loadAlerts();
    } catch (err) {
      window.alert(parseApiError(err).message);
    } finally {
      setMarkingAllRead(false);
    }
  };

  const handleToggleRead = async (alertItem: AdminAlert) => {
    setUpdatingIds((prev) => new Set(prev).add(alertItem.id));
    try {
      const updated = await api.admin.alerts.update(alertItem.id, {
        is_read: !alertItem.is_read,
      });
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertItem.id ? updated : a))
      );
    } catch (err) {
      window.alert(parseApiError(err).message);
    } finally {
      setUpdatingIds((prev) => {
        const next = new Set(prev);
        next.delete(alertItem.id);
        return next;
      });
    }
  };

  const handleResolve = async (alertItem: AdminAlert) => {
    if (!confirm("Mark this alert as resolved?")) return;
    setUpdatingIds((prev) => new Set(prev).add(alertItem.id));
    try {
      const updated = await api.admin.alerts.update(alertItem.id, {
        is_resolved: true,
      });
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertItem.id ? updated : a))
      );
    } catch (err) {
      window.alert(parseApiError(err).message);
    } finally {
      setUpdatingIds((prev) => {
        const next = new Set(prev);
        next.delete(alertItem.id);
        return next;
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Alerts</h1>
          <p className="text-text-muted mt-1">
            Review and manage system alerts
          </p>
        </div>
        <button
          onClick={handleMarkAllRead}
          disabled={markingAllRead}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-surface-tertiary rounded-lg hover:bg-surface-secondary text-sm font-medium disabled:opacity-50"
        >
          <CheckCheck className="h-4 w-4" />
          {markingAllRead ? "Marking..." : "Mark All Read"}
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-surface-tertiary p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <select
            value={severityFilter}
            onChange={(e) => {
              setSeverityFilter(e.target.value);
              setPage(1);
            }}
            className="px-4 py-2 border border-surface-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Severities</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>
          <select
            value={readFilter}
            onChange={(e) => {
              setReadFilter(e.target.value);
              setPage(1);
            }}
            className="px-4 py-2 border border-surface-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Alerts</option>
            <option value="unread">Unread</option>
            <option value="read">Read</option>
          </select>
        </div>
      </div>

      {/* Alerts List */}
      {loading ? (
        <div className="bg-white rounded-xl border border-surface-tertiary p-12 text-center">
          <div className="inline-block h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          <p className="mt-4 text-text-muted">Loading alerts...</p>
        </div>
      ) : error ? (
        <div className="bg-white rounded-xl border border-surface-tertiary p-12 text-center">
          <p className="text-red-600">{error}</p>
          <button
            onClick={loadAlerts}
            className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Retry
          </button>
        </div>
      ) : alerts.length === 0 ? (
        <div className="bg-white rounded-xl border border-surface-tertiary p-12 text-center">
          <Bell className="h-12 w-12 text-text-muted mx-auto mb-4" />
          <p className="text-text-muted">No alerts found</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => {
            const isUpdating = updatingIds.has(alert.id);
            return (
              <div
                key={alert.id}
                className={clsx(
                  "bg-white rounded-xl border p-5 transition-colors",
                  alert.is_read
                    ? "border-surface-tertiary opacity-75"
                    : "border-surface-tertiary shadow-sm",
                  alert.severity === "critical" && !alert.is_read && "border-l-4 border-l-red-500",
                  alert.severity === "warning" && !alert.is_read && "border-l-4 border-l-yellow-500",
                  alert.severity === "info" && !alert.is_read && "border-l-4 border-l-blue-500"
                )}
              >
                <div className="flex items-start gap-4">
                  {/* Severity dot */}
                  <div className="mt-1">
                    <SeverityDot severity={alert.severity} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center flex-wrap gap-2 mb-1">
                      <h3
                        className={clsx(
                          "text-sm font-semibold text-text-primary",
                          alert.is_read && "font-normal"
                        )}
                      >
                        {alert.title}
                      </h3>
                      <SeverityBadge severity={alert.severity} />
                      {alert.is_resolved && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-800">
                          <ShieldAlert className="h-3 w-3" />
                          Resolved
                        </span>
                      )}
                      {!alert.is_read && (
                        <span className="inline-flex h-2 w-2 rounded-full bg-primary-500" />
                      )}
                    </div>

                    <p className="text-sm text-text-secondary mb-2">{alert.message}</p>

                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
                      {alert.resource_type && (
                        <span>
                          Resource:{" "}
                          <span className="text-text-secondary capitalize">
                            {alert.resource_type}
                          </span>
                          {alert.resource_id && (
                            <span className="font-mono ml-1 text-text-muted">
                              ({alert.resource_id.substring(0, 8)}...)
                            </span>
                          )}
                        </span>
                      )}
                      {alert.user_email && (
                        <span>
                          User:{" "}
                          <span className="text-text-secondary">{alert.user_email}</span>
                        </span>
                      )}
                      {alert.alert_type && (
                        <span>
                          Type:{" "}
                          <span className="text-text-secondary capitalize">
                            {alert.alert_type.replace(/_/g, " ")}
                          </span>
                        </span>
                      )}
                      <span>
                        {new Date(alert.created_at).toLocaleDateString()}{" "}
                        {new Date(alert.created_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => handleToggleRead(alert)}
                      disabled={isUpdating}
                      title={alert.is_read ? "Mark as unread" : "Mark as read"}
                      className={clsx(
                        "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors disabled:opacity-50",
                        alert.is_read
                          ? "border-surface-tertiary text-text-secondary hover:bg-surface-secondary"
                          : "border-primary-200 text-primary-700 bg-primary-50 hover:bg-primary-100"
                      )}
                    >
                      <Check className="h-3.5 w-3.5" />
                      {alert.is_read ? "Unread" : "Read"}
                    </button>
                    {!alert.is_resolved && (
                      <button
                        onClick={() => handleResolve(alert)}
                        disabled={isUpdating}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-green-200 text-green-700 bg-green-50 hover:bg-green-100 transition-colors disabled:opacity-50"
                      >
                        <ShieldAlert className="h-3.5 w-3.5" />
                        Resolve
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {!loading && !error && alerts.length > 0 && (
        <div className="flex items-center justify-between px-1">
          <p className="text-sm text-text-muted">
            Showing {(page - 1) * pageSize + 1} to{" "}
            {Math.min(page * pageSize, total)} of {total} alerts
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
