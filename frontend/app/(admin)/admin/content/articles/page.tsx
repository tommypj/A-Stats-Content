"use client";

import { useEffect, useState } from "react";
import { api, parseApiError } from "@/lib/api";
import { toast } from "sonner";
import type { Article, AdminContentQueryParams } from "@/lib/api";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Search, Trash2, Eye, ChevronLeft, ChevronRight, FileText } from "lucide-react";
import Link from "next/link";

export default function AdminArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{ action: () => void; title: string; message: string } | null>(null);

  const pageSize = 20;

  useEffect(() => {
    loadArticles();
  }, [page, statusFilter]);

  const loadArticles = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: AdminContentQueryParams = {
        page,
        page_size: pageSize,
        search: search || undefined,
        status: statusFilter === "all" ? undefined : statusFilter,
      };
      const response = await api.admin.content.articles(params);
      setArticles(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPage(1);
    loadArticles();
  };

  const handleDelete = (id: string) => {
    setConfirmAction({
      action: async () => {
        try {
          setDeleting(true);
          await api.admin.content.deleteArticle(id);
          await loadArticles();
        } catch (err) {
          toast.error(parseApiError(err).message);
        } finally {
          setDeleting(false);
        }
      },
      title: "Delete Article",
      message: "Are you sure you want to delete this article? This action cannot be undone.",
    });
  };

  const handleBulkDelete = () => {
    if (selectedIds.size === 0) return;
    const count = selectedIds.size;
    setConfirmAction({
      action: async () => {
        try {
          setDeleting(true);
          await Promise.all(
            Array.from(selectedIds).map(id => api.admin.content.deleteArticle(id))
          );
          setSelectedIds(new Set());
          await loadArticles();
        } catch (err) {
          toast.error(parseApiError(err).message);
        } finally {
          setDeleting(false);
        }
      },
      title: `Delete ${count} Article${count !== 1 ? "s" : ""}`,
      message: `Delete ${count} selected article${count !== 1 ? "s" : ""}? This action cannot be undone.`,
    });
  };

  const toggleSelect = (id: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === articles.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(articles.map(a => a.id)));
    }
  };

  return (
    <div className="space-y-6">
      <ConfirmDialog
        isOpen={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        onConfirm={() => { confirmAction?.action(); setConfirmAction(null); }}
        title={confirmAction?.title ?? ""}
        message={confirmAction?.message ?? ""}
        variant="danger"
        confirmLabel="Delete"
      />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Articles</h1>
          <p className="text-text-muted mt-1">
            Manage all user-generated articles
          </p>
        </div>
        <Link
          href="/admin/content"
          className="px-4 py-2 bg-white border border-surface-tertiary rounded-lg hover:bg-surface-secondary text-sm font-medium"
        >
          Back to Content
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-surface-tertiary p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-text-muted" />
              <input
                type="text"
                placeholder="Search by title, keyword, or user..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="w-full pl-10 pr-4 py-2 border border-surface-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-4 py-2 border border-surface-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Status</option>
            <option value="draft">Draft</option>
            <option value="generating">Generating</option>
            <option value="completed">Completed</option>
            <option value="published">Published</option>
            <option value="failed">Failed</option>
          </select>
          <button
            onClick={handleSearch}
            className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium"
          >
            Search
          </button>
        </div>

        {selectedIds.size > 0 && (
          <div className="mt-4 flex items-center justify-between p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-900">
              {selectedIds.size} article{selectedIds.size !== 1 ? "s" : ""} selected
            </p>
            <button
              onClick={handleBulkDelete}
              disabled={deleting}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium disabled:opacity-50"
            >
              {deleting ? "Deleting..." : "Delete Selected"}
            </button>
          </div>
        )}
      </div>

      {/* Articles Table */}
      <div className="bg-white rounded-xl border border-surface-tertiary overflow-hidden">
        {loading ? (
          <div className="p-12 text-center">
            <div className="inline-block h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
            <p className="mt-4 text-text-muted">Loading articles...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <p className="text-red-600">{error}</p>
            <button
              onClick={loadArticles}
              className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Retry
            </button>
          </div>
        ) : articles.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="h-12 w-12 text-text-muted mx-auto mb-4" />
            <p className="text-text-muted">No articles found</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-surface-secondary">
                  <tr>
                    <th className="px-4 py-3 text-left">
                      <input
                        type="checkbox"
                        checked={selectedIds.size === articles.length && articles.length > 0}
                        onChange={toggleSelectAll}
                        className="rounded border-gray-300"
                      />
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      Title
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      Author
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      SEO Score
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                      Created
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-text-secondary uppercase">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-tertiary">
                  {articles.map((article) => (
                    <tr key={article.id} className="hover:bg-surface-secondary">
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(article.id)}
                          onChange={() => toggleSelect(article.id)}
                          className="rounded border-gray-300"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <div className="max-w-md">
                          <p className="font-medium text-text-primary truncate">
                            {article.title}
                          </p>
                          <p className="text-sm text-text-muted truncate">
                            {article.keyword}
                          </p>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-text-secondary">
                        {article.user_id.substring(0, 8)}...
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                            article.status === "published"
                              ? "bg-green-100 text-green-800"
                              : article.status === "completed"
                              ? "bg-blue-100 text-blue-800"
                              : article.status === "draft"
                              ? "bg-gray-100 text-gray-800"
                              : article.status === "generating"
                              ? "bg-yellow-100 text-yellow-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          {article.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-text-secondary">
                        {article.seo_score ? `${article.seo_score}/100` : "—"}
                      </td>
                      <td className="px-4 py-3 text-sm text-text-secondary">
                        {new Date(article.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-2">
                          <Link
                            href={`/articles/${article.id}`}
                            className="p-1 rounded hover:bg-surface-tertiary"
                            title="View"
                          >
                            <Eye className="h-4 w-4 text-text-secondary" />
                          </Link>
                          <button
                            onClick={() => handleDelete(article.id)}
                            disabled={deleting}
                            className="p-1 rounded hover:bg-red-50 disabled:opacity-50"
                            title="Delete"
                          >
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-surface-tertiary">
              <p className="text-sm text-text-muted">
                Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} articles
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2 rounded-lg border border-surface-tertiary hover:bg-surface-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
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
