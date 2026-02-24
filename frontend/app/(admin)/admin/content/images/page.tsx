"use client";

import { useEffect, useState } from "react";
import { api, parseApiError } from "@/lib/api";
import type { GeneratedImage, AdminContentQueryParams } from "@/lib/api";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Search, Trash2, Image as ImageIcon, ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import Image from "next/image";

export default function AdminImagesPage() {
  const [images, setImages] = useState<GeneratedImage[]>([]);
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
    loadImages();
  }, [page, statusFilter]);

  const loadImages = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: AdminContentQueryParams = {
        page,
        page_size: pageSize,
        search: search || undefined,
        status: statusFilter === "all" ? undefined : statusFilter,
      };
      const response = await api.admin.content.images(params);
      setImages(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPage(1);
    loadImages();
  };

  const handleDelete = (id: string) => {
    setConfirmAction({
      action: async () => {
        try {
          setDeleting(true);
          await api.admin.content.deleteImage(id);
          await loadImages();
        } catch (err) {
          toast.error(parseApiError(err).message);
        } finally {
          setDeleting(false);
        }
      },
      title: "Delete Image",
      message: "Are you sure you want to delete this image? This action cannot be undone.",
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
            Array.from(selectedIds).map(id => api.admin.content.deleteImage(id))
          );
          setSelectedIds(new Set());
          await loadImages();
        } catch (err) {
          toast.error(parseApiError(err).message);
        } finally {
          setDeleting(false);
        }
      },
      title: `Delete ${count} Image${count !== 1 ? "s" : ""}`,
      message: `Delete ${count} selected image${count !== 1 ? "s" : ""}? This action cannot be undone.`,
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
          <h1 className="text-3xl font-bold text-text-primary">Images</h1>
          <p className="text-text-muted mt-1">
            Manage all AI-generated images
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
                placeholder="Search by prompt or user..."
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
            <option value="completed">Completed</option>
            <option value="generating">Generating</option>
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
              {selectedIds.size} image{selectedIds.size !== 1 ? "s" : ""} selected
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

      {/* Images Grid */}
      <div className="bg-white rounded-xl border border-surface-tertiary p-6">
        {loading ? (
          <div className="p-12 text-center">
            <div className="inline-block h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
            <p className="mt-4 text-text-muted">Loading images...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <p className="text-red-600">{error}</p>
            <button
              onClick={loadImages}
              className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Retry
            </button>
          </div>
        ) : images.length === 0 ? (
          <div className="p-12 text-center">
            <ImageIcon className="h-12 w-12 text-text-muted mx-auto mb-4" />
            <p className="text-text-muted">No images found</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {images.map((image) => (
                <div
                  key={image.id}
                  className="group relative aspect-square rounded-lg overflow-hidden border border-surface-tertiary hover:border-primary-300 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.has(image.id)}
                    onChange={() => toggleSelect(image.id)}
                    className="absolute top-2 left-2 z-10 rounded border-gray-300"
                  />
                  {image.url ? (
                    <Image
                      src={image.url}
                      alt={image.alt_text || image.prompt}
                      fill
                      className="object-cover"
                    />
                  ) : (
                    <div className="w-full h-full bg-surface-secondary flex items-center justify-center">
                      <ImageIcon className="h-12 w-12 text-text-muted" />
                    </div>
                  )}
                  <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-3">
                    <p className="text-white text-xs line-clamp-2 mb-2">
                      {image.prompt}
                    </p>
                    <div className="flex items-center justify-between">
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${
                          image.status === "completed"
                            ? "bg-green-100 text-green-800"
                            : image.status === "generating"
                            ? "bg-yellow-100 text-yellow-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {image.status}
                      </span>
                      <button
                        onClick={() => handleDelete(image.id)}
                        disabled={deleting}
                        className="p-1 rounded bg-red-600 hover:bg-red-700 disabled:opacity-50"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4 text-white" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between mt-6 pt-6 border-t border-surface-tertiary">
              <p className="text-sm text-text-muted">
                Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} images
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
