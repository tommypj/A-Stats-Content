"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Upload, Search, Filter, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { api, parseApiError, KnowledgeSource } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { SourceCard } from "@/components/knowledge/source-card";
import { UploadModal } from "@/components/knowledge/upload-modal";

const STATUS_OPTIONS = [
  { value: "all", label: "All" },
  { value: "completed", label: "Completed" },
  { value: "processing", label: "Processing" },
  { value: "pending", label: "Pending" },
  { value: "failed", label: "Failed" },
];

export default function SourcesPage() {
  const router = useRouter();
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pageSize] = useState(12);
  // Track previous statuses to detect transitions; also keep current filter
  // values accessible inside the polling callback without re-creating it.
  const prevStatusesRef = useRef<Record<string, string>>({});
  const filtersRef = useRef({ page, pageSize, statusFilter, searchQuery });
  useEffect(() => {
    filtersRef.current = { page, pageSize, statusFilter, searchQuery };
  });

  const applyResponse = useCallback(
    (items: KnowledgeSource[], total: number) => {
      const prev = prevStatusesRef.current;
      items.forEach((s) => {
        if (prev[s.id] && prev[s.id] !== "completed" && s.status === "completed") {
          toast.success(`"${s.title}" indexed and ready`);
        }
        if (prev[s.id] && prev[s.id] !== "failed" && s.status === "failed") {
          toast.error(`"${s.title}" failed to index`);
        }
      });
      prevStatusesRef.current = Object.fromEntries(items.map((s) => [s.id, s.status]));
      setSources(items);
      setTotal(total);
    },
    []
  );

  async function loadSources(silent = false) {
    const { page, pageSize, statusFilter, searchQuery } = filtersRef.current;
    try {
      if (!silent) setIsLoading(true);
      const response = await api.knowledge.sources({
        page,
        page_size: pageSize,
        status: statusFilter === "all" ? undefined : statusFilter,
        search: searchQuery || undefined,
      });
      applyResponse(response.items, response.total);
    } catch (error) {
      if (!silent) {
        const apiError = parseApiError(error);
        toast.error(apiError.message || "Failed to load sources");
      }
    } finally {
      if (!silent) setIsLoading(false);
    }
  }

  // Reload when page or status filter changes (immediate)
  useEffect(() => {
    loadSources();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, statusFilter]);

  // Debounce search — reset to page 1 when query changes
  useEffect(() => {
    const timer = setTimeout(() => {
      if (page === 1) {
        loadSources();
      } else {
        setPage(1); // page change triggers the effect above
      }
    }, 500);
    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery]);

  // Poll every 5 s while any source is pending/processing
  useEffect(() => {
    const hasActive = sources.some(
      (s) => s.status === "pending" || s.status === "processing"
    );
    if (!hasActive) return;

    const interval = setInterval(() => loadSources(true), 5000);
    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sources]);

  const handleRefresh = () => {
    loadSources();
    toast.success("Sources refreshed");
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-text-primary">
            Knowledge Sources
          </h1>
          <p className="mt-2 text-text-secondary">
            Manage your uploaded documents and knowledge base
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            leftIcon={<RefreshCw className="h-4 w-4" />}
            onClick={handleRefresh}
            disabled={isLoading}
          >
            Refresh
          </Button>
          <Button
            leftIcon={<Upload className="h-4 w-4" />}
            onClick={() => setIsUploadModalOpen(true)}
          >
            Upload Document
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Search */}
        <div className="flex-1">
          <Input
            placeholder="Search sources..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            leftIcon={<Search className="h-4 w-4" />}
          />
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-text-muted" />
          <div className="flex gap-2 flex-wrap">
            {STATUS_OPTIONS.map((option) => (
              <Badge
                key={option.value}
                variant={statusFilter === option.value ? "default" : "outline"}
                className="cursor-pointer hover:bg-primary-100 transition-colors"
                onClick={() => {
                  setStatusFilter(option.value);
                  setPage(1);
                }}
              >
                {option.label}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      {/* Sources Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      ) : sources.length === 0 ? (
        <div className="text-center py-12">
          <div className="mx-auto w-24 h-24 rounded-full bg-surface-secondary flex items-center justify-center mb-4">
            <Upload className="h-12 w-12 text-text-muted" />
          </div>
          <h3 className="font-semibold text-lg text-text-primary mb-2">
            No sources found
          </h3>
          <p className="text-text-secondary mb-6">
            {searchQuery || statusFilter !== "all"
              ? "Try adjusting your search or filters"
              : "Upload your first document to get started"}
          </p>
          {!searchQuery && statusFilter === "all" && (
            <Button onClick={() => setIsUploadModalOpen(true)}>
              Upload Document
            </Button>
          )}
        </div>
      ) : (
        <>
          {/* Results Count */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-text-secondary">
              Showing {sources.length} of {total} sources
            </p>
          </div>

          {/* Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sources.map((source) => (
              <SourceCard
                key={source.id}
                source={source}
                onClick={() => router.push(`/knowledge/sources/${source.id}`)}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
              >
                Previous
              </Button>
              <div className="flex items-center gap-1">
                {[...Array(totalPages)].map((_, i) => {
                  const pageNum = i + 1;
                  // Show first, last, current, and adjacent pages
                  if (
                    pageNum === 1 ||
                    pageNum === totalPages ||
                    Math.abs(pageNum - page) <= 1
                  ) {
                    return (
                      <Button
                        key={pageNum}
                        variant={pageNum === page ? "primary" : "outline"}
                        size="sm"
                        onClick={() => setPage(pageNum)}
                      >
                        {pageNum}
                      </Button>
                    );
                  } else if (pageNum === page - 2 || pageNum === page + 2) {
                    return (
                      <span key={pageNum} className="px-2 text-text-muted">
                        ...
                      </span>
                    );
                  }
                  return null;
                })}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(page + 1)}
                disabled={page === totalPages}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSuccess={() => {
          loadSources();
          setPage(1);
        }}
      />
    </div>
  );
}
