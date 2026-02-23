"use client";

import { useState, useEffect } from "react";
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
} from "lucide-react";
import { api, getImageUrl, parseApiError, GeneratedImage } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { clsx } from "clsx";

const statusConfig = {
  generating: { label: "Generating", color: "bg-yellow-100 text-yellow-700", icon: Loader2 },
  completed: { label: "Completed", color: "bg-green-100 text-green-700", icon: CheckCircle2 },
  failed: { label: "Failed", color: "bg-red-100 text-red-700", icon: XCircle },
};

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

  // Pagination state
  const [page, setPage] = useState(1);
  const [pageSize] = useState(PAGE_SIZE);
  const [totalPages, setTotalPages] = useState(0);
  const [totalCount, setTotalCount] = useState(0);

  // Search / filter state
  const [searchPrompt, setSearchPrompt] = useState("");
  const [styleFilter, setStyleFilter] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Bulk selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);

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

  useEffect(() => {
    loadImages();
  }, [page, pageSize]);

  useEffect(() => {
    checkWpConnection();
  }, []);

  async function loadImages() {
    try {
      setLoading(true);
      const response = await api.images.list({ page, page_size: pageSize });
      setImages(response.items);
      setTotalCount(response.total);
      setTotalPages(Math.ceil(response.total / pageSize));
    } catch (error) {
      console.error("Failed to load images:", error);
    } finally {
      setLoading(false);
    }
  }

  // Client-side filtering applied after load
  const filteredImages = images.filter((img) => {
    const matchesSearch =
      debouncedSearch === "" ||
      img.prompt.toLowerCase().includes(debouncedSearch.toLowerCase());
    const matchesStyle =
      styleFilter === "" ||
      (img.style ?? "").toLowerCase() === styleFilter.toLowerCase();
    return matchesSearch && matchesStyle;
  });

  // Collect unique styles from the current page for the dropdown
  const availableStyles = Array.from(
    new Set(images.map((img) => img.style).filter((s): s is string => Boolean(s)))
  ).sort();

  // When filters are active the visible count is the filtered set; otherwise use server total
  const isFiltering = debouncedSearch !== "" || styleFilter !== "";
  const displayTotal = isFiltering ? filteredImages.length : totalCount;

  // Items shown on this page (filtered)
  const pageStart = isFiltering ? 1 : (page - 1) * pageSize + 1;
  const pageEnd = isFiltering
    ? filteredImages.length
    : Math.min(page * pageSize, totalCount);

  async function handleDelete(id: string) {
    if (!confirm("Are you sure you want to delete this image?")) return;

    try {
      await api.images.delete(id);
      setImages(images.filter((img) => img.id !== id));
      setTotalCount((prev) => prev - 1);
    } catch (error) {
      console.error("Failed to delete image:", error);
    }
    setActiveMenu(null);
  }

  async function handleCopyUrl(url: string, id: string) {
    try {
      await navigator.clipboard.writeText(url);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (error) {
      console.error("Failed to copy URL:", error);
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
      setTimeout(() => setWpError(""), 5000);
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

  async function handleBulkDelete() {
    const count = selectedIds.size;
    if (!confirm(`Delete ${count} image${count !== 1 ? "s" : ""}? This cannot be undone.`)) return;

    setIsBulkDeleting(true);
    try {
      await Promise.all(Array.from(selectedIds).map((id) => api.images.delete(id)));
      setSelectedIds(new Set());
      await loadImages();
    } catch (error) {
      console.error("Failed to bulk delete images:", error);
    } finally {
      setIsBulkDeleting(false);
    }
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

  return (
    <div className="space-y-6">
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
                            className="h-4 w-4 rounded border-white bg-white/90 text-primary-600 focus:ring-primary-500 cursor-pointer shadow"
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
                          className="p-1.5 rounded-lg bg-white/90 hover:bg-white shadow-sm backdrop-blur-sm"
                        >
                          <MoreVertical className="h-4 w-4 text-text-muted" />
                        </button>

                        {activeMenu === image.id && (
                          <>
                            <div className="fixed inset-0 z-40" onClick={() => setActiveMenu(null)} />
                            <div className="absolute right-0 mt-1 w-48 bg-white rounded-lg border border-surface-tertiary shadow-lg z-50">
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
          <div className="relative bg-white rounded-2xl shadow-xl max-w-5xl w-full max-h-[90vh] overflow-auto">
            <div className="sticky top-0 bg-white border-b border-surface-tertiary p-4 flex items-center justify-between z-10">
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
    </div>
  );
}
