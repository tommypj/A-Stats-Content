"use client";

import { useEffect, useState } from "react";
import { api, parseApiError } from "@/lib/api";
import type { AdminAuditLog, AdminAuditQueryParams } from "@/lib/api";
import { Search, ChevronDown, ChevronRight, ChevronLeft, Filter } from "lucide-react";

export default function AdminAuditLogsPage() {
  const [logs, setLogs] = useState<AdminAuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState<string>("all");
  const [resourceFilter, setResourceFilter] = useState<string>("all");
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const pageSize = 50;

  useEffect(() => {
    loadLogs();
  }, [page, actionFilter, resourceFilter]);

  const loadLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: AdminAuditQueryParams = {
        page,
        page_size: pageSize,
        action: actionFilter === "all" ? undefined : actionFilter,
        resource_type: resourceFilter === "all" ? undefined : resourceFilter,
      };
      const response = await api.admin.auditLogs(params);
      setLogs(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  };

  const toggleRow = (id: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const getActionBadgeColor = (action: string) => {
    const lowerAction = action.toLowerCase();
    if (lowerAction.includes("create")) return "bg-green-100 text-green-800";
    if (lowerAction.includes("update") || lowerAction.includes("edit")) return "bg-blue-100 text-blue-800";
    if (lowerAction.includes("delete") || lowerAction.includes("remove")) return "bg-red-100 text-red-800";
    if (lowerAction.includes("view") || lowerAction.includes("read")) return "bg-gray-100 text-gray-800";
    return "bg-purple-100 text-purple-800";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Audit Logs</h1>
          <p className="text-text-muted mt-1">
            Track all administrative actions and system events
          </p>
        </div>
        <button
          onClick={loadLogs}
          className="px-4 py-2 bg-white border border-surface-tertiary rounded-lg hover:bg-surface-secondary text-sm font-medium"
        >
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-surface-tertiary p-4">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-text-muted" />
              <input
                type="text"
                placeholder="Search by user email or resource ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-surface-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
          <div className="flex gap-3">
            <select
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.target.value);
                setPage(1);
              }}
              className="px-4 py-2 border border-surface-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">All Actions</option>
              <option value="create">Create</option>
              <option value="update">Update</option>
              <option value="delete">Delete</option>
              <option value="view">View</option>
            </select>
            <select
              value={resourceFilter}
              onChange={(e) => {
                setResourceFilter(e.target.value);
                setPage(1);
              }}
              className="px-4 py-2 border border-surface-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">All Resources</option>
              <option value="user">User</option>
              <option value="article">Article</option>
              <option value="outline">Outline</option>
              <option value="image">Image</option>
              <option value="subscription">Subscription</option>
            </select>
          </div>
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-xl border border-surface-tertiary overflow-hidden">
        {loading ? (
          <div className="p-12 text-center">
            <div className="inline-block h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
            <p className="mt-4 text-text-muted">Loading audit logs...</p>
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
            <Filter className="h-12 w-12 text-text-muted mx-auto mb-4" />
            <p className="text-text-muted">No audit logs found</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-surface-secondary">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase w-8">
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      User
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      Action
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      Resource
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      IP Address
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      Timestamp
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-tertiary">
                  {logs.map((log) => (
                    <>
                      <tr
                        key={log.id}
                        className="hover:bg-surface-secondary cursor-pointer"
                        onClick={() => toggleRow(log.id)}
                      >
                        <td className="px-4 py-3">
                          {expandedRows.has(log.id) ? (
                            <ChevronDown className="h-4 w-4 text-text-secondary" />
                          ) : (
                            <ChevronRight className="h-4 w-4 text-text-secondary" />
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div>
                            <p className="font-medium text-text-primary text-sm">
                              {log.user_email}
                            </p>
                            <p className="text-xs text-text-muted">
                              {log.user_id.substring(0, 8)}...
                            </p>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getActionBadgeColor(
                              log.action
                            )}`}
                          >
                            {log.action}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div>
                            <p className="text-sm font-medium text-text-primary">
                              {log.resource_type}
                            </p>
                            {log.resource_id && (
                              <p className="text-xs text-text-muted">
                                ID: {log.resource_id.substring(0, 12)}...
                              </p>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-text-secondary">
                          {log.ip_address || "—"}
                        </td>
                        <td className="px-4 py-3 text-sm text-text-secondary">
                          {new Date(log.created_at).toLocaleString()}
                        </td>
                      </tr>
                      {expandedRows.has(log.id) && (
                        <tr className="bg-surface-secondary">
                          <td colSpan={6} className="px-4 py-4">
                            <div className="space-y-2">
                              <div className="flex gap-4">
                                <div className="flex-1">
                                  <h4 className="text-xs font-medium text-text-secondary uppercase mb-1">
                                    User Agent
                                  </h4>
                                  <p className="text-sm text-text-primary">
                                    {log.user_agent || "—"}
                                  </p>
                                </div>
                              </div>
                              {log.details && Object.keys(log.details).length > 0 && (
                                <div>
                                  <h4 className="text-xs font-medium text-text-secondary uppercase mb-1">
                                    Details
                                  </h4>
                                  <pre className="text-xs bg-white p-3 rounded-lg border border-surface-tertiary overflow-x-auto">
                                    {JSON.stringify(log.details, null, 2)}
                                  </pre>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-surface-tertiary">
              <p className="text-sm text-text-muted">
                Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of{" "}
                {total} logs
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
