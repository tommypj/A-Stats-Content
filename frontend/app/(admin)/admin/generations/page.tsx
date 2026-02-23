"use client";

import { useEffect, useState } from "react";
import { api, parseApiError } from "@/lib/api";
import type { AdminGenerationLog, AdminGenerationStats } from "@/lib/api";
import {
  Search,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  CheckCircle,
  XCircle,
  Clock,
  Zap,
  CreditCard,
  Activity,
} from "lucide-react";

function StatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-surface-tertiary p-5">
      <div className="flex items-center gap-3">
        <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm text-text-muted">{label}</p>
          <p className="text-xl font-bold text-text-primary">{value}</p>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    success: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    started: "bg-yellow-100 text-yellow-800",
  };
  return (
    <span
      className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
        styles[status] ?? "bg-gray-100 text-gray-800"
      }`}
    >
      {status}
    </span>
  );
}

function formatDuration(ms?: number): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function truncateId(id?: string): string {
  if (!id) return "—";
  return id.length > 12 ? `${id.substring(0, 8)}...` : id;
}

export default function AdminGenerationsPage() {
  const [logs, setLogs] = useState<AdminGenerationLog[]>([]);
  const [stats, setStats] = useState<AdminGenerationStats | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userSearch, setUserSearch] = useState("");
  const [resourceTypeFilter, setResourceTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const pageSize = 20;

  useEffect(() => {
    loadStats();
  }, []);

  useEffect(() => {
    loadLogs();
  }, [page, resourceTypeFilter, statusFilter]);

  const loadStats = async () => {
    try {
      setStatsLoading(true);
      const data = await api.admin.generations.stats();
      setStats(data);
    } catch {
      // Stats are non-critical; silently fail
    } finally {
      setStatsLoading(false);
    }
  };

  const loadLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.admin.generations.list({
        page,
        page_size: pageSize,
        resource_type: resourceTypeFilter === "all" ? undefined : resourceTypeFilter,
        status: statusFilter === "all" ? undefined : statusFilter,
        user_id: userSearch || undefined,
      });
      setLogs(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Generation Logs</h1>
          <p className="text-text-muted mt-1">Monitor AI generation activity across all users</p>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {statsLoading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border border-surface-tertiary p-5 animate-pulse">
              <div className="h-10 w-10 rounded-lg bg-surface-secondary mb-3" />
              <div className="h-3 w-20 bg-surface-secondary rounded mb-2" />
              <div className="h-5 w-12 bg-surface-secondary rounded" />
            </div>
          ))
        ) : stats ? (
          <>
            <StatCard
              label="Total Generations"
              value={stats.total_generations.toLocaleString()}
              icon={Activity}
              color="bg-primary-100 text-primary-700"
            />
            <StatCard
              label="Success Rate"
              value={`${stats.success_rate.toFixed(1)}%`}
              icon={CheckCircle}
              color="bg-green-100 text-green-700"
            />
            <StatCard
              label="Failed"
              value={stats.failed.toLocaleString()}
              icon={XCircle}
              color="bg-red-100 text-red-700"
            />
            <StatCard
              label="Avg Duration"
              value={formatDuration(stats.avg_duration_ms)}
              icon={Clock}
              color="bg-yellow-100 text-yellow-700"
            />
            <StatCard
              label="Total Credits"
              value={stats.total_credits.toLocaleString()}
              icon={CreditCard}
              color="bg-purple-100 text-purple-700"
            />
          </>
        ) : null}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-surface-tertiary p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-text-muted" />
              <input
                type="text"
                placeholder="Filter by user ID..."
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="w-full pl-10 pr-4 py-2 border border-surface-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
          <select
            value={resourceTypeFilter}
            onChange={(e) => {
              setResourceTypeFilter(e.target.value);
              setPage(1);
            }}
            className="px-4 py-2 border border-surface-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Types</option>
            <option value="article">Article</option>
            <option value="outline">Outline</option>
            <option value="image">Image</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-4 py-2 border border-surface-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Status</option>
            <option value="started">Started</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
          </select>
          <button
            onClick={handleSearch}
            className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium"
          >
            Search
          </button>
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-xl border border-surface-tertiary overflow-hidden">
        {loading ? (
          <div className="p-12 text-center">
            <div className="inline-block h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
            <p className="mt-4 text-text-muted">Loading generation logs...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <p className="text-red-600">{error}</p>
            <button
              onClick={loadLogs}
              className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Retry
            </button>
          </div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center">
            <Sparkles className="h-12 w-12 text-text-muted mx-auto mb-4" />
            <p className="text-text-muted">No generation logs found</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-surface-secondary">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      Type
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      Resource ID
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      User
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      Duration
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      Credits
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      Date
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-tertiary">
                  {logs.map((log) => (
                    <tr key={log.id} className="hover:bg-surface-secondary">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Zap className="h-4 w-4 text-text-muted flex-shrink-0" />
                          <span className="text-sm font-medium text-text-primary capitalize">
                            {log.resource_type}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-text-secondary font-mono">
                        {truncateId(log.resource_id)}
                      </td>
                      <td className="px-4 py-3 text-sm text-text-secondary">
                        {log.user_email ?? truncateId(log.user_id)}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={log.status} />
                      </td>
                      <td className="px-4 py-3 text-sm text-text-secondary">
                        {formatDuration(log.duration_ms)}
                      </td>
                      <td className="px-4 py-3 text-sm text-text-secondary">
                        {log.cost_credits != null ? log.cost_credits : "—"}
                      </td>
                      <td className="px-4 py-3 text-sm text-text-secondary">
                        {new Date(log.created_at).toLocaleDateString()}{" "}
                        <span className="text-text-muted">
                          {new Date(log.created_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-surface-tertiary">
              <p className="text-sm text-text-muted">
                Showing {(page - 1) * pageSize + 1} to{" "}
                {Math.min(page * pageSize, total)} of {total} logs
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
          </>
        )}
      </div>
    </div>
  );
}
