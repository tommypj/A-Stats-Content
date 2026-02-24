"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Plus,
  FileText,
  Loader2,
  MoreVertical,
  Trash2,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Clock,
  Sparkles,
  BarChart2,
  Filter,
  User,
  Users,
  Search,
  ChevronLeft,
  ChevronRight,
  Download,
  X,
} from "lucide-react";
import { api, Article } from "@/lib/api";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { clsx } from "clsx";
import { useProject } from "@/contexts/ProjectContext";
import { ContentOwnershipBadge } from "@/components/project/content-ownership-badge";
import { UsageLimitBanner } from "@/components/project/usage-limit-warning";

const statusConfig = {
  draft: { label: "Draft", color: "bg-gray-100 text-gray-700", icon: FileText },
  generating: { label: "Generating", color: "bg-yellow-100 text-yellow-700", icon: Loader2 },
  completed: { label: "Completed", color: "bg-green-100 text-green-700", icon: CheckCircle2 },
  published: { label: "Published", color: "bg-blue-100 text-blue-700", icon: ExternalLink },
  failed: { label: "Failed", color: "bg-red-100 text-red-700", icon: XCircle },
};

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "draft", label: "Draft" },
  { value: "generating", label: "Generating" },
  { value: "completed", label: "Completed" },
  { value: "published", label: "Published" },
  { value: "failed", label: "Failed" },
];

type ContentFilter = "all" | "personal" | "project";

function getSeoScoreColor(score: number | undefined) {
  if (!score) return "text-text-muted";
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  return "text-red-600";
}

export default function ArticlesPage() {
  const router = useRouter();
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const [contentFilter, setContentFilter] = useState<ContentFilter>("all");

  // Pagination state
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [totalPages, setTotalPages] = useState(0);
  const [totalArticles, setTotalArticles] = useState(0);

  // Search/filter state
  const [searchKeyword, setSearchKeyword] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [debouncedKeyword, setDebouncedKeyword] = useState("");

  // Bulk selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{ action: () => void; title: string; message: string } | null>(null);

  const {
    currentProject,
    isPersonalWorkspace,
    canCreate,
    canEdit,
    isViewer,
    usage,
    limits,
    isAtLimit,
  } = useProject();

  // Ctrl+N / Cmd+N: navigate to new article
  useKeyboardShortcuts([
    {
      key: "n",
      ctrl: true,
      handler: () => router.push("/articles/new"),
    },
  ]);

  // Debounce search keyword — reset to page 1 when keyword changes
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedKeyword(searchKeyword);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchKeyword]);

  // Reset page when status filter or content filter changes
  useEffect(() => {
    setPage(1);
  }, [statusFilter, contentFilter]);

  // Clear selection when page/filters change
  useEffect(() => {
    setSelectedIds(new Set());
  }, [page, debouncedKeyword, statusFilter, contentFilter]);

  useEffect(() => {
    loadArticles();
  }, [currentProject, contentFilter, page, debouncedKeyword, statusFilter]);

  async function loadArticles() {
    try {
      setLoading(true);
      const params: any = {
        page,
        page_size: pageSize,
      };

      if (debouncedKeyword) {
        params.keyword = debouncedKeyword;
      }

      if (statusFilter) {
        params.status = statusFilter;
      }

      // Apply project context
      if (!isPersonalWorkspace && currentProject) {
        params.project_id = currentProject.id;
      }

      // Apply content filter
      if (contentFilter === "personal") {
        delete params.project_id;
      } else if (contentFilter === "project" && currentProject) {
        params.project_id = currentProject.id;
      }

      const response = await api.articles.list(params);
      setArticles(response.items);
      setTotalArticles(response.total);
      setTotalPages(response.pages ?? Math.ceil(response.total / pageSize));
    } catch (error) {
      console.error("Failed to load articles:", error);
      toast.error("Failed to load articles. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function handleDelete(id: string) {
    setActiveMenu(null);
    setConfirmAction({
      action: async () => {
        try {
          await api.articles.delete(id);
          setArticles((prev) => prev.filter((a) => a.id !== id));
          setTotalArticles((prev) => Math.max(0, prev - 1));
        } catch (error) {
          console.error("Failed to delete article:", error);
          toast.error("Failed to delete article.");
        }
      },
      title: "Delete Article",
      message: "Are you sure you want to delete this article? This action cannot be undone.",
    });
  }

  // --- Bulk selection helpers ---

  const allVisibleIds = articles.map((a) => a.id);
  const allSelected =
    allVisibleIds.length > 0 && allVisibleIds.every((id) => selectedIds.has(id));
  const someSelected = selectedIds.size > 0;

  function toggleSelectAll() {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(allVisibleIds));
    }
  }

  function toggleSelectOne(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function clearSelection() {
    setSelectedIds(new Set());
  }

  function handleBulkDelete() {
    const count = selectedIds.size;
    setConfirmAction({
      action: async () => {
        setIsBulkDeleting(true);
        try {
          await Promise.all(Array.from(selectedIds).map((id) => api.articles.delete(id)));
          setSelectedIds(new Set());
          await loadArticles();
        } catch (error) {
          console.error("Failed to bulk delete articles:", error);
          toast.error("Failed to delete articles. Please try again.");
        } finally {
          setIsBulkDeleting(false);
        }
      },
      title: `Delete ${count} Article${count !== 1 ? "s" : ""}`,
      message: `Delete ${count} article${count !== 1 ? "s" : ""}? This cannot be undone.`,
    });
  }

  function triggerBlobDownload(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  async function handleExportAllCsv() {
    try {
      const response = await api.articles.exportAll("csv");
      triggerBlobDownload(
        response.data as Blob,
        `articles-${new Date().toISOString().slice(0, 10)}.csv`
      );
      toast.success("Articles exported as CSV");
    } catch {
      toast.error("Failed to export articles");
    }
  }

  function handleBulkExport() {
    const selected = articles.filter((a) => selectedIds.has(a.id));
    const exportData = selected.map((a) => ({
      title: a.title,
      keyword: a.keyword,
      content: a.content ?? "",
      meta_description: a.meta_description ?? "",
      status: a.status,
    }));
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `articles-export-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  const showCreateButton = canCreate && !isAtLimit("articles");
  const articlesUsed = usage?.articles_used || 0;
  const articlesLimit = limits?.articles_per_month || Infinity;

  // Calculate displayed range for "Showing X-Y of Z"
  const rangeStart = totalArticles === 0 ? 0 : (page - 1) * pageSize + 1;
  const rangeEnd = Math.min(page * pageSize, totalArticles);

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

      {/* Usage Limit Warning */}
      {!isPersonalWorkspace && currentProject && usage && limits && (
        <UsageLimitBanner
          resource="articles"
          used={articlesUsed}
          limit={articlesLimit}
          isProject={true}
          projectName={currentProject.name}
        />
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-bold text-text-primary">
            Articles
          </h1>
          <p className="text-text-secondary mt-1">
            {isPersonalWorkspace
              ? "Manage and edit your generated articles"
              : `Managing articles for ${currentProject?.name}`}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {/* Content Filter (only show in project context) */}
          {!isPersonalWorkspace && currentProject && (
            <div className="flex items-center gap-1 bg-surface-secondary rounded-lg p-1">
              <button
                onClick={() => setContentFilter("all")}
                className={clsx(
                  "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  contentFilter === "all"
                    ? "bg-white text-text-primary shadow-sm"
                    : "text-text-secondary hover:text-text-primary"
                )}
              >
                <span className="flex items-center gap-1.5">
                  <Filter className="h-4 w-4" />
                  All
                </span>
              </button>
              <button
                onClick={() => setContentFilter("personal")}
                className={clsx(
                  "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  contentFilter === "personal"
                    ? "bg-white text-text-primary shadow-sm"
                    : "text-text-secondary hover:text-text-primary"
                )}
              >
                <span className="flex items-center gap-1.5">
                  <User className="h-4 w-4" />
                  Personal
                </span>
              </button>
              <button
                onClick={() => setContentFilter("project")}
                className={clsx(
                  "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  contentFilter === "project"
                    ? "bg-white text-text-primary shadow-sm"
                    : "text-text-secondary hover:text-text-primary"
                )}
              >
                <span className="flex items-center gap-1.5">
                  <Users className="h-4 w-4" />
                  Project
                </span>
              </button>
            </div>
          )}

          <Button variant="outline" onClick={handleExportAllCsv}>
            <Download className="h-4 w-4 mr-2" />
            Export All as CSV
          </Button>

          <Link href="/outlines">
            <Button variant="outline">
              <FileText className="h-4 w-4 mr-2" />
              From Outline
            </Button>
          </Link>
          {showCreateButton ? (
            <Link href="/articles/new">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                New Article
              </Button>
            </Link>
          ) : isViewer ? (
            <Button disabled title="Viewers cannot create content">
              <Plus className="h-4 w-4 mr-2" />
              New Article
            </Button>
          ) : (
            <Button disabled title="Article limit reached">
              <Plus className="h-4 w-4 mr-2" />
              Limit Reached
            </Button>
          )}
        </div>
      </div>

      {/* Search and Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted pointer-events-none" />
          <input
            type="text"
            placeholder="Search articles by keyword or title..."
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            className="w-full bg-surface rounded-xl border border-surface-tertiary pl-9 pr-4 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-surface rounded-xl border border-surface-tertiary px-4 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent sm:w-44"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Bulk Action Toolbar */}
      {someSelected && (
        <div className="sticky top-4 z-30 bg-primary-50 border border-primary-200 rounded-xl p-3 flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-primary-800">
            {selectedIds.size} selected
          </span>
          <div className="flex items-center gap-2 ml-auto">
            <button
              onClick={handleBulkExport}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-primary-300 bg-white text-sm font-medium text-primary-700 hover:bg-primary-50 transition-colors"
            >
              <Download className="h-4 w-4" />
              Export
            </button>
            <button
              onClick={handleBulkDelete}
              disabled={isBulkDeleting}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isBulkDeleting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
              Delete
            </button>
            <button
              onClick={clearSelection}
              className="p-1.5 rounded-lg hover:bg-primary-100 text-primary-600 transition-colors"
              title="Clear selection"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Articles List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
        </div>
      ) : articles.length === 0 ? (
        <Card className="p-12 text-center">
          <Sparkles className="h-12 w-12 text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-medium text-text-primary mb-2">
            {debouncedKeyword || statusFilter ? "No articles match your search" : "No articles yet"}
          </h3>
          <p className="text-text-secondary mb-6">
            {debouncedKeyword || statusFilter
              ? "Try adjusting your search or filter to find what you're looking for"
              : isViewer
              ? "Your project has not created any articles yet"
              : "Create an outline first, then generate an article from it"}
          </p>
          {!isViewer && !debouncedKeyword && !statusFilter && (
            <Link href="/outlines">
              <Button>
                <FileText className="h-4 w-4 mr-2" />
                Create Outline
              </Button>
            </Link>
          )}
        </Card>
      ) : (
        <div className="space-y-4">
          {/* Select All header row */}
          {!isViewer && (
            <div className="flex items-center gap-3 px-1">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={toggleSelectAll}
                className="h-4 w-4 rounded border-surface-tertiary text-primary-600 focus:ring-primary-500 cursor-pointer"
                title="Select all on page"
              />
              <span className="text-sm text-text-muted">
                {allSelected ? "Deselect all" : "Select all on page"}
              </span>
            </div>
          )}

          {articles.map((article) => {
            const status = statusConfig[article.status];
            const StatusIcon = status.icon;
            const isProjectContent = !!article.project_id;
            const canModify = canEdit;
            const isChecked = selectedIds.has(article.id);

            return (
              <Card
                key={article.id}
                className={clsx(
                  "p-4 hover:shadow-md transition-shadow",
                  isChecked && "ring-2 ring-primary-400 bg-primary-50/30"
                )}
              >
                <div className="flex items-start gap-4">
                  {/* Checkbox */}
                  {!isViewer && (
                    <div className="flex-shrink-0 pt-0.5">
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleSelectOne(article.id)}
                        className="h-4 w-4 rounded border-surface-tertiary text-primary-600 focus:ring-primary-500 cursor-pointer"
                      />
                    </div>
                  )}

                  {/* Status & SEO Score */}
                  <div className="flex flex-col items-center gap-2 w-16">
                    <span className={clsx("w-full text-center px-2 py-1 rounded-lg text-xs font-medium", status.color)}>
                      {status.label}
                    </span>
                    {article.seo_score !== undefined && (
                      <div className={clsx("text-center", getSeoScoreColor(article.seo_score))}>
                        <BarChart2 className="h-4 w-4 mx-auto" />
                        <span className="text-xs font-medium">{Math.round(article.seo_score)}</span>
                      </div>
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-2 mb-2">
                      <Link href={`/articles/${article.id}`} className="group flex-1">
                        <h3 className="font-medium text-text-primary group-hover:text-primary-600 line-clamp-1">
                          {article.title}
                        </h3>
                      </Link>
                      <ContentOwnershipBadge
                        projectId={article.project_id}
                        projectName={currentProject?.name}
                        isPersonal={!isProjectContent}
                        variant="compact"
                      />
                    </div>

                    {article.meta_description && (
                      <p className="text-sm text-text-secondary mt-1 line-clamp-2">
                        {article.meta_description}
                      </p>
                    )}

                    <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-text-muted">
                      <span className="px-2 py-0.5 bg-surface-secondary rounded-md">
                        {article.keyword}
                      </span>
                      <span className="flex items-center gap-1">
                        <FileText className="h-3.5 w-3.5" />
                        {article.word_count} words
                      </span>
                      {article.read_time && (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3.5 w-3.5" />
                          {article.read_time} min read
                        </span>
                      )}
                      <span>{new Date(article.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="relative flex items-center gap-1">
                    {/* Show delete button directly for failed/stuck articles */}
                    {(article.status === "failed" || article.status === "generating") && (
                      <button
                        onClick={() => handleDelete(article.id)}
                        className="p-1.5 rounded-lg hover:bg-red-50 text-red-400 hover:text-red-600 transition-colors"
                        title="Delete article"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                    <button
                      onClick={() => setActiveMenu(activeMenu === article.id ? null : article.id)}
                      className="p-1.5 rounded-lg hover:bg-surface-secondary"
                      disabled={isViewer}
                    >
                      <MoreVertical className="h-4 w-4 text-text-muted" />
                    </button>

                    {activeMenu === article.id && (
                      <>
                        <div className="fixed inset-0 z-40" onClick={() => setActiveMenu(null)} />
                        <div className="absolute right-0 mt-1 w-40 bg-white rounded-lg border border-surface-tertiary shadow-lg z-50">
                          <Link
                            href={`/articles/${article.id}`}
                            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary"
                            onClick={() => setActiveMenu(null)}
                          >
                            <FileText className="h-4 w-4" />
                            {canModify ? "Edit" : "View"}
                          </Link>
                          {article.published_url && (
                            <a
                              href={article.published_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary"
                            >
                              <ExternalLink className="h-4 w-4" />
                              View Live
                            </a>
                          )}
                          <button
                            onClick={() => handleDelete(article.id)}
                            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                          >
                            <Trash2 className="h-4 w-4" />
                            Delete
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {/* Viewer Banner */}
                {isViewer && (
                  <div className="mt-3 pt-3 border-t border-surface-tertiary">
                    <p className="text-xs text-text-muted italic">
                      View-only mode: You cannot edit project content
                    </p>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {!loading && totalPages > 0 && (
        <Card className="p-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <p className="text-sm text-text-muted">
              {totalArticles === 0
                ? "No articles"
                : `Showing ${rangeStart}\u2013${rangeEnd} of ${totalArticles} article${totalArticles !== 1 ? "s" : ""}`}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className={clsx(
                  "flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                  page <= 1
                    ? "text-text-muted cursor-not-allowed"
                    : "text-text-secondary hover:bg-surface-secondary"
                )}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </button>
              <span className="px-3 py-1.5 text-sm text-text-primary font-medium">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className={clsx(
                  "flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                  page >= totalPages
                    ? "text-text-muted cursor-not-allowed"
                    : "text-text-secondary hover:bg-surface-secondary"
                )}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
