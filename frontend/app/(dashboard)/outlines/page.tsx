"use client";

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Plus,
  FileText,
  Clock,
  Loader2,
  RefreshCw,
  Trash2,
  MoreVertical,
  CheckCircle2,
  XCircle,
  Sparkles,
  Search,
  ChevronLeft,
  ChevronRight,
  Download,
  X,
} from "lucide-react";
import { api, Outline } from "@/lib/api";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { AIGenerationProgress } from "@/components/ui/ai-generation-progress";
import { clsx } from "clsx";

const statusConfig: Record<string, { label: string; color: string; icon: typeof FileText }> = {
  draft: { label: "Draft", color: "bg-gray-100 text-gray-700", icon: FileText },
  generating: { label: "Generating", color: "bg-yellow-100 text-yellow-700", icon: Loader2 },
  completed: { label: "Completed", color: "bg-green-100 text-green-700", icon: CheckCircle2 },
  failed: { label: "Failed", color: "bg-red-100 text-red-700", icon: XCircle },
};
const defaultStatus = { label: "Unknown", color: "bg-gray-100 text-gray-500", icon: FileText };

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "draft", label: "Draft" },
  { value: "generating", label: "Generating" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
];

export default function OutlinesPage() {
  const searchParams = useSearchParams();
  const [outlines, setOutlines] = useState<Outline[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [initialKeyword, setInitialKeyword] = useState("");
  const [activeMenu, setActiveMenu] = useState<string | null>(null);

  // Pagination & filter state
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(0);
  const [totalItems, setTotalItems] = useState(0);
  const [searchKeyword, setSearchKeyword] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [debouncedKeyword, setDebouncedKeyword] = useState("");

  // Bulk selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{ action: () => void; title: string; message: string } | null>(null);

  // Open create modal with pre-filled keyword when ?keyword= is in the URL
  useEffect(() => {
    const kw = searchParams.get("keyword");
    if (kw) {
      setInitialKeyword(kw);
      setShowCreateModal(true);
    }
  }, [searchParams]);

  // Ctrl+N / Cmd+N: open create outline modal
  useKeyboardShortcuts([
    {
      key: "n",
      ctrl: true,
      handler: () => setShowCreateModal(true),
    },
  ]);

  // Debounce search input — reset page to 1 when keyword changes
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedKeyword(searchKeyword);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchKeyword]);

  // Reset page to 1 when status filter changes
  useEffect(() => {
    setPage(1);
  }, [statusFilter]);

  // Clear selection when page/filters change
  useEffect(() => {
    setSelectedIds(new Set());
  }, [page, debouncedKeyword, statusFilter]);

  const loadOutlines = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.outlines.list({
        page,
        page_size: pageSize,
        keyword: debouncedKeyword || undefined,
        status: statusFilter || undefined,
      });
      setOutlines(response.items);
      setTotalItems(response.total);
      setTotalPages(response.pages);
    } catch (error) {
      toast.error("Failed to load outlines. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, debouncedKeyword, statusFilter]);

  // Load outlines whenever page, debouncedKeyword, or statusFilter changes
  useEffect(() => {
    loadOutlines();
  }, [loadOutlines]);

  function handleDelete(id: string) {
    setActiveMenu(null);
    setConfirmAction({
      action: async () => {
        try {
          await api.outlines.delete(id);
          setOutlines((prev) => prev.filter((o) => o.id !== id));
          setTotalItems((prev) => Math.max(0, prev - 1));
        } catch (error) {
          toast.error("Failed to delete outline.");
        }
      },
      title: "Delete Outline",
      message: "Are you sure you want to delete this outline? This action cannot be undone.",
    });
  }

  async function handleRegenerate(id: string) {
    try {
      const updated = await api.outlines.regenerate(id);
      setOutlines(outlines.map((o) => (o.id === id ? updated : o)));
    } catch (error) {
      toast.error("Failed to regenerate outline. Please try again.");
    }
    setActiveMenu(null);
  }

  // --- Bulk selection helpers ---

  const allVisibleIds = outlines.map((o) => o.id);
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
          await api.outlines.bulkDelete(Array.from(selectedIds));
          setSelectedIds(new Set());
          await loadOutlines();
        } catch (error) {
          toast.error("Failed to delete outlines. Please try again.");
        } finally {
          setIsBulkDeleting(false);
        }
      },
      title: `Delete ${count} Outline${count !== 1 ? "s" : ""}`,
      message: `Delete ${count} outline${count !== 1 ? "s" : ""}? This cannot be undone.`,
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
      const response = await api.outlines.exportAll("csv");
      triggerBlobDownload(
        response.data as Blob,
        `outlines-${new Date().toISOString().slice(0, 10)}.csv`
      );
      toast.success("Outlines exported as CSV");
    } catch {
      toast.error("Failed to export outlines");
    }
  }

  function handleBulkExport() {
    const selected = outlines.filter((o) => selectedIds.has(o.id));
    const exportData = selected.map((o) => ({
      title: o.title,
      keyword: o.keyword,
      sections: o.sections,
      status: o.status,
    }));
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `outlines-export-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  // Pagination helpers
  const firstItem = totalItems === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastItem = Math.min(page * pageSize, totalItems);

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

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-bold text-text-primary">
            Outlines
          </h1>
          <p className="text-text-secondary mt-1">
            Create and manage your article outlines
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleExportAllCsv}>
            <Download className="h-4 w-4 mr-2" />
            Export All as CSV
          </Button>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Outline
          </Button>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted pointer-events-none" />
          <input
            type="text"
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            placeholder="Search by keyword or title..."
            className="w-full pl-9 pr-4 py-2 bg-surface rounded-xl border border-surface-tertiary text-sm text-text-primary placeholder:text-text-muted focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-surface rounded-xl border border-surface-tertiary px-4 py-2 text-sm text-text-primary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
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

      {/* Outlines Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
        </div>
      ) : outlines.length === 0 ? (
        <Card className="p-12 text-center">
          <FileText className="h-12 w-12 text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-medium text-text-primary mb-2">
            {debouncedKeyword || statusFilter ? "No outlines match your filters" : "No outlines yet"}
          </h3>
          <p className="text-text-secondary mb-6">
            {debouncedKeyword || statusFilter
              ? "Try adjusting your search or filter criteria"
              : "Create your first outline to start generating content"}
          </p>
          {!debouncedKeyword && !statusFilter && (
            <Button onClick={() => setShowCreateModal(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Outline
            </Button>
          )}
        </Card>
      ) : (
        <>
          {/* Select All header row */}
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

          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {outlines.map((outline) => {
              const status = statusConfig[outline.status] || defaultStatus;
              const StatusIcon = status.icon;
              const isChecked = selectedIds.has(outline.id);

              return (
                <Card
                  key={outline.id}
                  className={clsx(
                    "p-4 hover:shadow-md transition-shadow",
                    isChecked && "ring-2 ring-primary-400 bg-primary-50/30"
                  )}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      {/* Checkbox */}
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleSelectOne(outline.id)}
                        className="h-4 w-4 rounded border-surface-tertiary text-primary-600 focus:ring-primary-500 cursor-pointer flex-shrink-0"
                      />
                      <span className={clsx("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium", status.color)}>
                        <StatusIcon className={clsx("h-3.5 w-3.5", outline.status === "generating" && "animate-spin")} />
                        {status.label}
                      </span>
                    </div>

                    <div className="relative">
                      <button
                        onClick={() => setActiveMenu(activeMenu === outline.id ? null : outline.id)}
                        className="p-1.5 rounded-lg hover:bg-surface-secondary"
                      >
                        <MoreVertical className="h-4 w-4 text-text-muted" />
                      </button>

                      {activeMenu === outline.id && (
                        <>
                          <div className="fixed inset-0 z-40" onClick={() => setActiveMenu(null)} />
                          <div className="absolute right-0 mt-1 w-40 bg-white rounded-lg border border-surface-tertiary shadow-lg z-50">
                            <button
                              onClick={() => handleRegenerate(outline.id)}
                              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary"
                            >
                              <RefreshCw className="h-4 w-4" />
                              Regenerate
                            </button>
                            <button
                              onClick={() => handleDelete(outline.id)}
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

                  <Link href={`/outlines/${outline.id}`} className="block group">
                    <h3 className="font-medium text-text-primary group-hover:text-primary-600 line-clamp-2 mb-2">
                      {outline.title}
                    </h3>

                    <div className="flex items-center gap-2 text-sm text-text-muted mb-3">
                      <span className="px-2 py-0.5 bg-surface-secondary rounded-md">
                        {outline.keyword}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5" />
                        {outline.estimated_read_time || Math.ceil(outline.word_count_target / 200)} min
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs text-text-muted">
                      <span>{outline.sections?.length || 0} sections</span>
                      <span>{new Date(outline.created_at).toLocaleDateString()}</span>
                    </div>
                  </Link>

                  {outline.status === "completed" && (
                    <Link
                      href={`/articles/new?outline=${outline.id}`}
                      className="mt-4 flex items-center justify-center gap-2 w-full py-2 rounded-lg bg-primary-50 text-primary-600 text-sm font-medium hover:bg-primary-100 transition-colors"
                    >
                      <Sparkles className="h-4 w-4" />
                      Generate Article
                    </Link>
                  )}
                </Card>
              );
            })}
          </div>
        </>
      )}

      {/* Pagination Controls */}
      {!loading && totalPages > 0 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          <p className="text-sm text-text-muted">
            Showing {firstItem}&ndash;{lastItem} of {totalItems} outline{totalItems !== 1 ? "s" : ""}
          </p>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-surface-tertiary text-sm text-text-secondary hover:bg-surface-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>

            <span className="px-3 py-1.5 text-sm text-text-secondary">
              Page {page} of {totalPages}
            </span>

            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-surface-tertiary text-sm text-text-secondary hover:bg-surface-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreateOutlineModal
          initialKeyword={initialKeyword}
          onClose={() => { setShowCreateModal(false); setInitialKeyword(""); }}
          onCreate={(outline) => {
            setOutlines([outline, ...outlines]);
            setTotalItems((prev) => prev + 1);
            setShowCreateModal(false);
          }}
        />
      )}
    </div>
  );
}

function CreateOutlineModal({
  initialKeyword = "",
  onClose,
  onCreate,
}: {
  initialKeyword?: string;
  onClose: () => void;
  onCreate: (outline: Outline) => void;
}) {
  const [keyword, setKeyword] = useState(initialKeyword);
  const [targetAudience, setTargetAudience] = useState("");
  const [tone, setTone] = useState("professional");
  const [wordCount, setWordCount] = useState(1500);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!keyword.trim()) {
      setError("Keyword is required");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const outline = await api.outlines.create({
        keyword: keyword.trim(),
        target_audience: targetAudience.trim() || undefined,
        tone,
        word_count_target: wordCount,
        auto_generate: true,
      });
      onCreate(outline);
    } catch (err) {
      setError("Failed to create outline. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop: only dismissible when not generating */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={loading ? undefined : onClose}
      />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 p-6">
        <h2 className="text-xl font-display font-bold text-text-primary mb-4">
          Create New Outline
        </h2>

        {loading ? (
          /* Progress view shown while the API call is in flight */
          <div>
            <AIGenerationProgress
              type="outline"
              keyword={keyword}
              isGenerating={loading}
            />
            <div className="mt-4 flex justify-center">
              <button
                type="button"
                onClick={onClose}
                className="text-sm text-text-muted hover:text-text-secondary underline underline-offset-2 transition-colors"
              >
                Cancel and close
              </button>
            </div>
          </div>
        ) : (
          /* Normal form view */
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">
                Target Keyword *
              </label>
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="e.g., anxiety relief techniques"
                className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">
                Target Audience
              </label>
              <input
                type="text"
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
                placeholder="e.g., adults dealing with work stress"
                className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">
                  Tone
                </label>
                <select
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
                >
                  <option value="professional">Professional</option>
                  <option value="friendly">Friendly</option>
                  <option value="empathetic">Empathetic</option>
                  <option value="informative">Informative</option>
                  <option value="conversational">Conversational</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">
                  Word Count
                </label>
                <select
                  value={wordCount}
                  onChange={(e) => setWordCount(Number(e.target.value))}
                  className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
                >
                  <option value={800}>Short (~800 words)</option>
                  <option value={1500}>Medium (~1500 words)</option>
                  <option value={2500}>Long (~2500 words)</option>
                  <option value={4000}>Very Long (~4000 words)</option>
                </select>
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-600">{error}</p>
            )}

            <div className="flex gap-3 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button type="submit" className="flex-1">
                <Sparkles className="h-4 w-4 mr-2" />
                Generate Outline
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
