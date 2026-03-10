"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Plus,
  Image as ImageIcon,
  Loader2,
  MoreVertical,
  Trash2,
  CheckCircle2,
  XCircle,
  Clock,
  Download,
  Copy,
  ExternalLink,
  Sparkles,
  Globe,
  Search,
  ChevronLeft,
  ChevronRight,
  X,
  RefreshCw,
} from "lucide-react";
import { api, getImageUrl, parseApiError, GeneratedImage } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { clsx } from "clsx";

const statusConfig = {
  generating: { label: "Generating", color: "bg-yellow-100 text-yellow-700", icon: Loader2 },
  completed: { label: "Completed", color: "bg-green-100 text-green-700", icon: CheckCircle2 },
  failed: { label: "Failed", color: "bg-red-100 text-red-700", icon: XCircle },
};

const IMAGE_STYLES = [
  { value: "realistic", label: "Realistic" },
  { value: "photographic", label: "Photographic" },
  { value: "artistic", label: "Artistic" },
  { value: "minimalist", label: "Minimalist" },
  { value: "dramatic", label: "Dramatic" },
  { value: "vintage", label: "Vintage" },
  { value: "modern", label: "Modern" },
  { value: "abstract", label: "Abstract" },
  { value: "watercolor", label: "Watercolor" },
];

const IMAGE_SIZES = [
  { value: "1024x1024", label: "Square (1024x1024)", width: 1024, height: 1024 },
  { value: "1024x768", label: "Landscape (1024x768)", width: 1024, height: 768 },
  { value: "768x1024", label: "Portrait (768x1024)", width: 768, height: 1024 },
  { value: "1792x1024", label: "Wide (1792x1024)", width: 1792, height: 1024 },
  { value: "1024x1792", label: "Tall (1024x1792)", width: 1024, height: 1792 },
];

const PAGE_SIZE = 20;

export default function ImagesPage() {
  const [images, setImages] = useState<GeneratedImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<GeneratedImage | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [wpConnected, setWpConnected] = useState(false);
  const [wpUploading, setWpUploading] = useState<string | null>(null);
  const [wpUploaded, setWpUploaded] = useState<Set<string>>(new Set());
  const [wpError, setWpError] = useState("");
  const copiedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wpErrorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (copiedTimerRef.current) clearTimeout(copiedTimerRef.current);
      if (wpErrorTimerRef.current) clearTimeout(wpErrorTimerRef.current);
      if (regenPollRef.current) clearInterval(regenPollRef.current);
    };
  }, []);

  // Pagination state
  const [page, setPage] = useState(1);
  const [pageSize] = useState(PAGE_SIZE);
  const [totalPages, setTotalPages] = useState(0);
  const [totalCount, setTotalCount] = useState(0);

  // Search / filter state
  // FE-IMAGES-03: Client-side filtering only applies to loaded page — full-text search requires server-side filtering
  const [searchPrompt, setSearchPrompt] = useState("");
  const [styleFilter, setStyleFilter] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // FE-IMAGES-04: Per-image loading state for copy/download/send operations
  const [loadingImageId, setLoadingImageId] = useState<string | null>(null);

  // Regenerate modal state
  const [regenImage, setRegenImage] = useState<GeneratedImage | null>(null);
  const [regenPrompt, setRegenPrompt] = useState("");
  const [regenStyle, setRegenStyle] = useState("realistic");
  const [regenSize, setRegenSize] = useState("1024x1024");
  const [regenLoading, setRegenLoading] = useState(false);
  const regenPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Bulk selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{ action: () => void; title: string; message: string } | null>(null);

  // Debounce search input; reset to page 1 when search changes
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchPrompt);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchPrompt]);

  // Reset page when style filter changes
  useEffect(() => {
    setPage(1);
  }, [styleFilter]);

  // Clear selection when page changes
  useEffect(() => {
    setSelectedIds(new Set());
  }, [page]);

  const loadImages = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.images.list({
        page,
        page_size: pageSize,
        ...(debouncedSearch ? { prompt: debouncedSearch } : {}),
        ...(styleFilter ? { style: styleFilter } : {}),
      });
      setImages(response.items);
      setTotalCount(response.total);
      setTotalPages(Math.ceil(response.total / pageSize));
    } catch (error) {
      toast.error(parseApiError(error).message);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, debouncedSearch, styleFilter]);

  useEffect(() => {
    loadImages();
  }, [loadImages]);

  // Close image modal on Escape key
  useEffect(() => {
    if (!selectedImage) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelectedImage(null);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedImage]);

  useEffect(() => {
    checkWpConnection();
  }, []);

  // Server-side filtering — images already filtered by API
  const filteredImages = images;
  const isFiltering = !!(debouncedSearch || styleFilter);

  // Collect unique styles from the current page for the dropdown
  const availableStyles = useMemo(() => Array.from(
    new Set(images.map((img) => img.style).filter((s): s is string => Boolean(s)))
  ).sort(), [images]);

  const displayTotal = totalCount;
  const pageStart = (page - 1) * pageSize + 1;
  const pageEnd = Math.min(page * pageSize, totalCount);

  function handleDelete(id: string) {
    setActiveMenu(null);
    setConfirmAction({
      action: async () => {
        try {
          await api.images.delete(id);
          setImages((prev) => prev.filter((img) => img.id !== id));
          setTotalCount((prev) => prev - 1);
        } catch (error) {
          toast.error(parseApiError(error).message);
        }
      },
      title: "Delete Image",
      message: "Are you sure you want to delete this image? This action cannot be undone.",
    });
  }

  async function handleCopyUrl(url: string, id: string) {
    setLoadingImageId(id);
    try {
      await navigator.clipboard.writeText(url);
      setCopiedId(id);
      if (copiedTimerRef.current) clearTimeout(copiedTimerRef.current);
      copiedTimerRef.current = setTimeout(() => setCopiedId(null), 2000);
    } catch {
      toast.error("Failed to copy URL");
    } finally {
      setLoadingImageId(null);
    }
    setActiveMenu(null);
  }

  function handleDownload(url: string, id: string) {
    const link = document.createElement("a");
    link.href = url;
    link.download = `image-${id}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setActiveMenu(null);
  }

  async function checkWpConnection() {
    try {
      const status = await api.wordpress.status();
      setWpConnected(status.is_connected);
    } catch {
      setWpConnected(false);
    }
  }

  async function handleSendToWordPress(image: GeneratedImage) {
    setWpError("");
    setWpUploading(image.id);
    setActiveMenu(null);
    try {
      await api.wordpress.uploadMedia({
        image_id: image.id,
        alt_text: image.alt_text || undefined,
      });
      setWpUploaded((prev) => new Set(prev).add(image.id));
    } catch (err) {
      setWpError(parseApiError(err).message);
      if (wpErrorTimerRef.current) clearTimeout(wpErrorTimerRef.current);
      wpErrorTimerRef.current = setTimeout(() => setWpError(""), 5000);
    } finally {
      setWpUploading(null);
    }
  }

  // --- Bulk selection helpers ---

  // Only allow selecting completed images that are currently visible after filtering
  const selectableIds = filteredImages
    .filter((img) => img.status === "completed")
    .map((img) => img.id);
  const allSelected =
    selectableIds.length > 0 && selectableIds.every((id) => selectedIds.has(id));
  const someSelected = selectedIds.size > 0;

  function toggleSelectAll() {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(selectableIds));
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
          await api.images.bulkDelete(Array.from(selectedIds));
          setSelectedIds(new Set());
          await loadImages();
        } catch (error) {
          toast.error(parseApiError(error).message);
        } finally {
          setIsBulkDeleting(false);
        }
      },
      title: `Delete ${count} Image${count !== 1 ? "s" : ""}`,
      message: `Delete ${count} image${count !== 1 ? "s" : ""}? This cannot be undone.`,
    });
  }

  function handleBulkExport() {
    const selected = filteredImages.filter((img) => selectedIds.has(img.id));
    const exportData = selected.map((img) => ({
      prompt: img.prompt,
      style: img.style ?? "",
      url: img.url ? getImageUrl(img.url) : "",
      alt_text: img.alt_text ?? "",
    }));
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `images-export-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function openRegenModal(image: GeneratedImage) {
    setRegenImage(image);
    setRegenPrompt(image.prompt);
    setRegenStyle(image.style || "realistic");
    // Infer size from dimensions
    const sizeMatch = IMAGE_SIZES.find(s => s.width === image.width && s.height === image.height);
    setRegenSize(sizeMatch?.value || "1024x1024");
    setActiveMenu(null);
  }

  function closeRegenModal() {
    if (regenLoading) return;
    setRegenImage(null);
    setRegenPrompt("");
    if (regenPollRef.current) clearInterval(regenPollRef.current);
  }

  async function handleRegenerate() {
    if (!regenPrompt.trim() || regenLoading) return;
    setRegenLoading(true);

    try {
      const selectedSize = IMAGE_SIZES.find(s => s.value === regenSize);
      const image = await api.images.generate({
        prompt: regenPrompt.trim(),
        style: regenStyle,
        width: selectedSize?.width,
        height: selectedSize?.height,
        article_id: regenImage?.article_id || undefined,
      });

      // Poll for completion
      let attempts = 0;
      if (regenPollRef.current) clearInterval(regenPollRef.current);
      regenPollRef.current = setInterval(async () => {
        try {
          attempts++;
          const updated = await api.images.get(image.id);
          if (updated.status === "completed") {
            if (regenPollRef.current) clearInterval(regenPollRef.current);
            regenPollRef.current = null;
            setRegenLoading(false);
            setRegenImage(null);
            toast.success("New image generated!");
            loadImages();
          } else if (updated.status === "failed" || attempts >= 90) {
            if (regenPollRef.current) clearInterval(regenPollRef.current);
            regenPollRef.current = null;
            setRegenLoading(false);
            toast.error(updated.status === "failed" ? "Image generation failed" : "Generation timed out");
          }
        } catch (error) {
          if (regenPollRef.current) clearInterval(regenPollRef.current);
          regenPollRef.current = null;
          setRegenLoading(false);
          toast.error(parseApiError(error).message);
        }
      }, 2000);
    } catch (err) {
      setRegenLoading(false);
      toast.error(parseApiError(err).message);
    }
  }

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
            Images
          </h1>
          <p className="text-text-secondary mt-1">
            Manage your AI-generated images
          </p>
        </div>
        <Link href="/images/generate">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Generate Image
          </Button>
        </Link>
      </div>

      {/* Search and Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted pointer-events-none" />
          <input
            type="text"
            placeholder="Search by prompt..."
            value={searchPrompt}
            onChange={(e) => setSearchPrompt(e.target.value)}
            className="w-full bg-surface rounded-xl border border-surface-tertiary pl-9 pr-4 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500"
          />
        </div>
        {availableStyles.length > 0 && (
          <select
            value={styleFilter}
            onChange={(e) => setStyleFilter(e.target.value)}
            className="bg-surface rounded-xl border border-surface-tertiary px-4 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500"
          >
            <option value="">All styles</option>
            {availableStyles.map((style) => (
              <option key={style} value={style}>
                {style}
              </option>
            ))}
          </select>
        )}
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
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-primary-300 bg-surface text-sm font-medium text-primary-700 hover:bg-primary-50 transition-colors"
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

      {/* Images Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
        </div>
      ) : filteredImages.length === 0 ? (
        <Card className="p-12 text-center">
          <ImageIcon className="h-12 w-12 text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-medium text-text-primary mb-2">
            {isFiltering ? "No images match your search" : "No images yet"}
          </h3>
          <p className="text-text-secondary mb-6">
            {isFiltering
              ? "Try adjusting your search or filter"
              : "Generate your first AI image to get started"}
          </p>
          {!isFiltering && (
            <Link href="/images/generate">
              <Button>
                <Sparkles className="h-4 w-4 mr-2" />
                Generate Image
              </Button>
            </Link>
          )}
        </Card>
      ) : (
        <>
          {/* Select All header row */}
          {selectableIds.length > 0 && (
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

          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filteredImages.map((image) => {
              const status = statusConfig[image.status as keyof typeof statusConfig];
              const StatusIcon = status?.icon;
              const isChecked = selectedIds.has(image.id);
              const isSelectable = image.status === "completed";

              return (
                <Card
                  key={image.id}
                  className={clsx(
                    "overflow-hidden hover:shadow-md transition-shadow",
                    isChecked && "ring-2 ring-primary-400"
                  )}
                >
                  {/* Image Thumbnail */}
                  <div className="relative aspect-square bg-surface-secondary">
                    {image.status === "completed" && image.url ? (
                      <button
                        onClick={() => setSelectedImage(image)}
                        className="w-full h-full group cursor-pointer"
                      >
                        <Image
                          src={getImageUrl(image.url)}
                          alt={image.alt_text || image.prompt}
                          fill
                          className="object-cover group-hover:opacity-90 transition-opacity"
                          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
                        />
                      </button>
                    ) : image.status === "generating" ? (
                      <div className="flex items-center justify-center h-full">
                        <div className="text-center">
                          <Loader2 className="h-8 w-8 animate-spin text-primary-500 mx-auto mb-2" />
                          <p className="text-sm text-text-muted">Generating...</p>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center h-full">
                        <XCircle className="h-8 w-8 text-red-500" />
                      </div>
                    )}

                    {/* Checkbox overlay (top-left) — only for selectable images */}
                    {isSelectable && (
                      <div className="absolute top-2 left-2 z-20">
                        <label
                          className={clsx(
                            "flex items-center justify-center w-6 h-6 rounded cursor-pointer transition-opacity",
                            isChecked
                              ? "opacity-100"
                              : "opacity-0 group-hover:opacity-100"
                          )}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleSelectOne(image.id)}
                            className="h-4 w-4 rounded border-white bg-surface/90 text-primary-600 focus:ring-primary-500 cursor-pointer shadow"
                          />
                        </label>
                      </div>
                    )}

                    {/* Status Badge */}
                    {status && (
                      <div className={clsx("absolute top-2", isSelectable ? "left-9" : "left-2")}>
                        <span className={clsx("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium", status.color)}>
                          <StatusIcon className={clsx("h-3.5 w-3.5", image.status === "generating" && "animate-spin")} />
                          {status.label}
                        </span>
                      </div>
                    )}

                    {/* Actions Menu */}
                    {image.status === "completed" && (
                      <div className="absolute top-2 right-2">
                        <button
                          onClick={() => setActiveMenu(activeMenu === image.id ? null : image.id)}
                          aria-label="Image actions"
                          className="p-1.5 rounded-lg bg-surface/90 hover:bg-surface shadow-sm backdrop-blur-sm"
                        >
                          <MoreVertical className="h-4 w-4 text-text-muted" />
                        </button>

                        {activeMenu === image.id && (
                          <>
                            <div className="fixed inset-0 z-40" onClick={() => setActiveMenu(null)} />
                            <div className="absolute right-0 mt-1 w-48 bg-surface rounded-lg border border-surface-tertiary shadow-lg z-50">
                              <button
                                onClick={() => handleCopyUrl(getImageUrl(image.url), image.id)}
                                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary"
                              >
                                <Copy className="h-4 w-4" />
                                {copiedId === image.id ? "Copied!" : "Copy URL"}
                              </button>
                              <button
                                onClick={() => handleDownload(getImageUrl(image.url), image.id)}
                                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary"
                              >
                                <Download className="h-4 w-4" />
                                Download
                              </button>
                              <a
                                href={getImageUrl(image.url)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary"
                              >
                                <ExternalLink className="h-4 w-4" />
                                Open in New Tab
                              </a>
                              {wpConnected && (
                                <button
                                  onClick={() => handleSendToWordPress(image)}
                                  disabled={wpUploading === image.id || wpUploaded.has(image.id)}
                                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary disabled:opacity-50"
                                >
                                  {wpUploading === image.id ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                  ) : wpUploaded.has(image.id) ? (
                                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                                  ) : (
                                    <Globe className="h-4 w-4" />
                                  )}
                                  {wpUploaded.has(image.id) ? "Sent to WordPress" : "Send to WordPress"}
                                </button>
                              )}
                              <button
                                onClick={() => openRegenModal(image)}
                                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary"
                              >
                                <RefreshCw className="h-4 w-4" />
                                Regenerate
                              </button>
                              <button
                                onClick={() => handleDelete(image.id)}
                                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 border-t border-surface-tertiary"
                              >
                                <Trash2 className="h-4 w-4" />
                                Delete
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Image Details */}
                  <div className="p-3">
                    <p className="text-sm text-text-primary line-clamp-2 mb-2">
                      {image.prompt}
                    </p>

                    <div className="flex items-center justify-between text-xs text-text-muted">
                      <div className="flex items-center gap-2">
                        {image.style && (
                          <span className="px-2 py-0.5 bg-surface-secondary rounded-md">
                            {image.style}
                          </span>
                        )}
                        {image.width && image.height && (
                          <span>
                            {image.width}x{image.height}
                          </span>
                        )}
                      </div>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(image.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </>
      )}

      {/* Pagination Controls */}
      {!loading && !isFiltering && totalCount > 0 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          <p className="text-sm text-text-secondary">
            Showing {pageStart}-{pageEnd} of {totalCount} images
          </p>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Previous
            </Button>
            <span className="text-sm text-text-secondary">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}

      {/* Filter result count when filtering */}
      {!loading && isFiltering && filteredImages.length > 0 && (
        <p className="text-sm text-text-secondary pt-2">
          Showing {displayTotal} {displayTotal === 1 ? "image" : "images"} matching your search
        </p>
      )}

      {/* Full Size Image Modal */}
      {selectedImage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80" onClick={() => setSelectedImage(null)} />
          <div className="relative bg-surface rounded-2xl shadow-xl max-w-5xl w-full max-h-[90vh] overflow-auto">
            <div className="sticky top-0 bg-surface border-b border-surface-tertiary p-4 flex items-center justify-between z-10">
              <div>
                <h3 className="font-medium text-text-primary">Generated Image</h3>
                <p className="text-sm text-text-secondary mt-0.5">
                  {selectedImage.width}x{selectedImage.height} · {selectedImage.style}
                </p>
              </div>
              <button
                onClick={() => setSelectedImage(null)}
                className="p-2 rounded-lg hover:bg-surface-secondary"
              >
                <XCircle className="h-5 w-5 text-text-muted" />
              </button>
            </div>

            <div className="p-6">
              <div className="relative w-full" style={{ aspectRatio: `${selectedImage.width}/${selectedImage.height}` }}>
                <Image
                  src={getImageUrl(selectedImage.url)}
                  alt={selectedImage.alt_text || selectedImage.prompt}
                  fill
                  className="object-contain"
                  sizes="90vw"
                />
              </div>

              <div className="mt-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1">
                    Prompt
                  </label>
                  <p className="text-text-primary">
                    {selectedImage.prompt}
                  </p>
                </div>

                {selectedImage.alt_text && (
                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-1">
                      Alt Text
                    </label>
                    <p className="text-text-primary">
                      {selectedImage.alt_text}
                    </p>
                  </div>
                )}

                <div className="flex flex-wrap gap-3 pt-4">
                  <Button
                    variant="outline"
                    onClick={() => handleCopyUrl(getImageUrl(selectedImage.url), selectedImage.id)}
                    className="flex-1"
                  >
                    <Copy className="h-4 w-4 mr-2" />
                    {copiedId === selectedImage.id ? "Copied!" : "Copy URL"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => handleDownload(getImageUrl(selectedImage.url), selectedImage.id)}
                    className="flex-1"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => { setSelectedImage(null); openRegenModal(selectedImage); }}
                    className="flex-1"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Regenerate
                  </Button>
                  {wpConnected && (
                    <Button
                      variant="outline"
                      onClick={() => handleSendToWordPress(selectedImage)}
                      disabled={wpUploading === selectedImage.id || wpUploaded.has(selectedImage.id)}
                      className="flex-1"
                    >
                      {wpUploading === selectedImage.id ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      ) : wpUploaded.has(selectedImage.id) ? (
                        <CheckCircle2 className="h-4 w-4 text-green-600 mr-2" />
                      ) : (
                        <Globe className="h-4 w-4 mr-2" />
                      )}
                      {wpUploaded.has(selectedImage.id) ? "Sent!" : "Send to WordPress"}
                    </Button>
                  )}
                </div>
                {wpError && (
                  <p className="text-sm text-red-600 mt-2">{wpError}</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Regenerate Modal */}
      {regenImage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={closeRegenModal} />
          <div className="relative bg-surface rounded-2xl shadow-xl max-w-lg w-full overflow-hidden">
            <div className="border-b border-surface-tertiary p-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <RefreshCw className="h-4 w-4 text-primary-600" />
                <h3 className="font-medium text-text-primary">Regenerate Image</h3>
              </div>
              <button
                onClick={closeRegenModal}
                disabled={regenLoading}
                className="p-1.5 rounded-lg hover:bg-surface-secondary disabled:opacity-50"
              >
                <X className="h-4 w-4 text-text-muted" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              {/* Original image thumbnail */}
              {regenImage.url && (
                <div className="relative h-32 bg-surface-secondary rounded-lg overflow-hidden">
                  <Image
                    src={getImageUrl(regenImage.url)}
                    alt={regenImage.alt_text || regenImage.prompt}
                    fill
                    className="object-contain"
                    sizes="480px"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">
                  Prompt
                </label>
                <textarea
                  value={regenPrompt}
                  onChange={(e) => setRegenPrompt(e.target.value)}
                  rows={3}
                  disabled={regenLoading}
                  className="w-full px-3 py-2 rounded-lg border border-surface-tertiary text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 disabled:opacity-50 resize-none"
                  placeholder="Describe the image..."
                />
                <p className="text-xs text-text-muted mt-1">
                  Edit the prompt to change the generated image
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1.5">
                    Style
                  </label>
                  <select
                    value={regenStyle}
                    onChange={(e) => setRegenStyle(e.target.value)}
                    disabled={regenLoading}
                    className="w-full px-3 py-2 rounded-lg border border-surface-tertiary text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 disabled:opacity-50"
                  >
                    {IMAGE_STYLES.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1.5">
                    Size
                  </label>
                  <select
                    value={regenSize}
                    onChange={(e) => setRegenSize(e.target.value)}
                    disabled={regenLoading}
                    className="w-full px-3 py-2 rounded-lg border border-surface-tertiary text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 disabled:opacity-50"
                  >
                    {IMAGE_SIZES.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="border-t border-surface-tertiary p-4 flex items-center justify-end gap-3">
              <Button
                variant="outline"
                onClick={closeRegenModal}
                disabled={regenLoading}
              >
                Cancel
              </Button>
              <Button
                onClick={handleRegenerate}
                disabled={regenLoading || !regenPrompt.trim()}
              >
                {regenLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Generate New Image
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
