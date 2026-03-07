"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Search, Plus, Trash2, Edit, Eye, ChevronLeft, ChevronRight } from "lucide-react";
import { api, parseApiError } from "@/lib/api";
import type { AdminBlogPostListItem, BlogCategory } from "@/lib/api";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

export default function AdminBlogPostsPage() {
  const [posts, setPosts] = useState<AdminBlogPostListItem[]>([]);
  const [categories, setCategories] = useState<BlogCategory[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [confirmAction, setConfirmAction] = useState<{ action: () => void; title: string; message: string } | null>(null);

  const pageSize = 20;
  const totalPages = Math.ceil(total / pageSize);

  const loadPosts = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.admin.blog.posts.list({
        page,
        page_size: pageSize,
        search: search || undefined,
        status: statusFilter === "all" ? undefined : statusFilter,
        category_id: categoryFilter || undefined,
      });
      setPosts(response.items);
      setTotal(response.total);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, categoryFilter]);

  useEffect(() => {
    loadPosts();
  }, [loadPosts]);

  useEffect(() => {
    api.admin.blog.categories.list().then(setCategories).catch(() => {});
  }, []);

  const handleSearch = () => {
    setPage(1);
    loadPosts();
  };

  const handleDelete = (id: string, title: string) => {
    setConfirmAction({
      title: "Delete Post",
      message: `Are you sure you want to delete "${title}"? This action cannot be undone.`,
      action: async () => {
        try {
          await api.admin.blog.posts.delete(id);
          toast.success("Post deleted");
          loadPosts();
        } catch (err) {
          toast.error(parseApiError(err).message);
        }
      },
    });
  };

  const handleBulkDelete = () => {
    if (selectedIds.size === 0) return;
    setConfirmAction({
      title: "Delete Posts",
      message: `Delete ${selectedIds.size} selected post(s)? This cannot be undone.`,
      action: async () => {
        try {
          await Promise.all(Array.from(selectedIds).map(id => api.admin.blog.posts.delete(id)));
          toast.success(`${selectedIds.size} post(s) deleted`);
          setSelectedIds(new Set());
          loadPosts();
        } catch (err) {
          toast.error(parseApiError(err).message);
        }
      },
    });
  };

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === posts.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(posts.map(p => p.id)));
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Blog Posts</h1>
          <p className="text-sm text-text-secondary mt-1">{total} posts total</p>
        </div>
        <Link
          href="/admin/blog/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium"
        >
          <Plus className="h-4 w-4" />
          New Post
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="flex items-center gap-2 flex-1 min-w-[200px]">
          <input
            type="text"
            placeholder="Search posts..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSearch()}
            className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <button
            onClick={handleSearch}
            className="p-2 bg-surface border border-surface-tertiary rounded-lg hover:bg-surface-secondary"
          >
            <Search className="h-4 w-4 text-text-secondary" />
          </button>
        </div>

        <select
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="all">All Status</option>
          <option value="draft">Draft</option>
          <option value="published">Published</option>
        </select>

        <select
          value={categoryFilter}
          onChange={e => { setCategoryFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="">All Categories</option>
          {categories.map(c => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>

        {selectedIds.size > 0 && (
          <button
            onClick={handleBulkDelete}
            className="inline-flex items-center gap-2 px-3 py-2 bg-red-50 text-red-600 border border-red-200 rounded-lg text-sm hover:bg-red-100"
          >
            <Trash2 className="h-4 w-4" />
            Delete {selectedIds.size}
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-surface border border-surface-tertiary rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-text-secondary">Loading...</div>
        ) : posts.length === 0 ? (
          <div className="p-12 text-center text-text-secondary">No posts found.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-surface-secondary border-b border-surface-tertiary">
              <tr>
                <th className="w-10 p-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.size === posts.length && posts.length > 0}
                    onChange={toggleSelectAll}
                    className="rounded"
                  />
                </th>
                <th className="p-3 text-left font-medium text-text-secondary">Title</th>
                <th className="p-3 text-left font-medium text-text-secondary hidden md:table-cell">Category</th>
                <th className="p-3 text-left font-medium text-text-secondary">Status</th>
                <th className="p-3 text-left font-medium text-text-secondary hidden lg:table-cell">Author</th>
                <th className="p-3 text-left font-medium text-text-secondary hidden lg:table-cell">Published</th>
                <th className="p-3 text-left font-medium text-text-secondary">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-tertiary">
              {posts.map(post => (
                <tr key={post.id} className="hover:bg-surface-secondary/50">
                  <td className="p-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(post.id)}
                      onChange={() => toggleSelect(post.id)}
                      className="rounded"
                    />
                  </td>
                  <td className="p-3">
                    <span className="font-medium text-text-primary line-clamp-1" title={post.title}>
                      {post.title}
                    </span>
                    <span className="text-xs text-text-muted block">/{post.slug}</span>
                  </td>
                  <td className="p-3 hidden md:table-cell">
                    {post.category_name ? (
                      <span className="px-2 py-0.5 bg-primary-50 text-primary-700 text-xs rounded-full">
                        {post.category_name}
                      </span>
                    ) : (
                      <span className="text-text-muted">—</span>
                    )}
                  </td>
                  <td className="p-3">
                    <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                      post.status === "published"
                        ? "bg-green-100 text-green-700"
                        : "bg-surface-tertiary text-text-secondary"
                    }`}>
                      {post.status}
                    </span>
                  </td>
                  <td className="p-3 hidden lg:table-cell text-text-secondary">
                    {post.author_name || "—"}
                  </td>
                  <td className="p-3 hidden lg:table-cell text-text-secondary">
                    {post.published_at
                      ? new Date(post.published_at).toLocaleDateString()
                      : "—"}
                  </td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/admin/blog/${post.id}/edit`}
                        className="p-1.5 rounded-lg hover:bg-surface-secondary text-text-secondary hover:text-primary-600"
                        aria-label={`Edit ${post.title}`}
                      >
                        <Edit className="h-4 w-4" />
                      </Link>
                      {post.status === "published" && (
                        <a
                          href={`/en/blog/${post.slug}`}
                          target="_blank"
                          rel="noreferrer"
                          className="p-1.5 rounded-lg hover:bg-surface-secondary text-text-secondary hover:text-primary-600"
                          aria-label={`Preview ${post.title}`}
                        >
                          <Eye className="h-4 w-4" />
                        </a>
                      )}
                      <button
                        onClick={() => handleDelete(post.id, post.title)}
                        className="p-1.5 rounded-lg hover:bg-red-50 text-text-secondary hover:text-red-600"
                        aria-label={`Delete ${post.title}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-sm text-text-secondary">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 rounded-lg border border-surface-tertiary disabled:opacity-50 hover:bg-surface-secondary"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-2 rounded-lg border border-surface-tertiary disabled:opacity-50 hover:bg-surface-secondary"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Confirm dialog */}
      <ConfirmDialog
        isOpen={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        onConfirm={() => { confirmAction?.action(); setConfirmAction(null); }}
        title={confirmAction?.title ?? ""}
        message={confirmAction?.message ?? ""}
        variant="danger"
        confirmLabel="Delete"
      />
    </div>
  );
}
