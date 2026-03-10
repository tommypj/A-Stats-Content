"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Upload, Search, Filter, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api, KnowledgeSource } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { SourceCard } from "@/components/knowledge/source-card";
import { UploadModal } from "@/components/knowledge/upload-modal";
import { TierGate } from "@/components/ui/tier-gate";

const STATUS_OPTIONS = [
  { value: "all", label: "All" },
  { value: "completed", label: "Completed" },
  { value: "processing", label: "Processing" },
  { value: "pending", label: "Pending" },
  { value: "failed", label: "Failed" },
];

export default function SourcesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(12);

  // Track previous statuses to detect transitions
  const prevStatusesRef = useRef<Record<string, string>>({});

  // Debounce search — reset to page 1 when query changes
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const queryKey = [
    "knowledge",
    "sources",
    { page, pageSize, status: statusFilter, search: debouncedSearch },
  ];

  const { data, isLoading, isFetching } = useQuery({
    queryKey,
    queryFn: () =>
      api.knowledge.sources({
        page,
        page_size: pageSize,
        status: statusFilter === "all" ? undefined : statusFilter,
        search: debouncedSearch || undefined,
      }),
    staleTime: 30_000,
    refetchInterval: (query) => {
      const items = query.state.data?.items;
      if (!items) return false;
      const hasActive = items.some(
        (s) => s.status === "pending" || s.status === "processing"
      );
      return hasActive ? 5000 : false;
    },
  });

  const sources = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);

  // Detect status transitions and show toasts
  const notifyStatusChanges = useCallback((items: KnowledgeSource[]) => {
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
  }, []);

  // Watch for status changes whenever data updates
  useEffect(() => {
    if (sources.length > 0) {
      notifyStatusChanges(sources);
    }
  }, [sources, notifyStatusChanges]);

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ["knowledge", "sources"] });
    toast.success("Sources refreshed");
  };

  return (
    <TierGate minimum="professional" feature="Knowledge Vault">
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
            disabled={isLoading || isFetching}
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
          queryClient.invalidateQueries({ queryKey: ["knowledge", "sources"] });
          setPage(1);
        }}
      />
    </div>
    </TierGate>
  );
}
