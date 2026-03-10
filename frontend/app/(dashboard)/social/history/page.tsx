"use client";

import { useState } from "react";
import { toast } from "sonner";
import { PostListItem } from "@/components/social/post-list-item";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, parseApiError, SocialPost, SocialPostStatus, SocialPlatform, getPostPlatforms } from "@/lib/api";
import { History, Search, Filter, Download, Trash2, List, Grid } from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { TierGate } from "@/components/ui/tier-gate";

export default function SocialHistoryPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  // Filters
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<SocialPostStatus | "all">("all");
  const [platformFilter, setPlatformFilter] = useState<SocialPlatform | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const [selectedPosts, setSelectedPosts] = useState<Set<string>>(new Set());
  const [confirmAction, setConfirmAction] = useState<{ action: () => void; title: string; message: string } | null>(null);

  const queryParams = {
    page,
    page_size: 20,
    status: statusFilter === "all" ? undefined : statusFilter,
    platform: platformFilter === "all" ? undefined : platformFilter,
    search: searchQuery || undefined,
  };

  const { data, isLoading: loading } = useQuery({
    queryKey: ["social", "posts", queryParams],
    queryFn: () => api.social.posts(queryParams),
    staleTime: 30_000,
  });

  const posts = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = data?.pages ?? 1;

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.social.deletePost(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["social", "posts"] });
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) =>
      Promise.all(ids.map((id) => api.social.deletePost(id))),
    onSuccess: () => {
      setSelectedPosts(new Set());
      queryClient.invalidateQueries({ queryKey: ["social", "posts"] });
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const retryMutation = useMutation({
    mutationFn: (id: string) => api.social.retryFailed(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["social", "posts"] });
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const handleView = (id: string) => {
    router.push(`/social/posts/${id}`);
  };

  const handleEdit = (id: string) => {
    router.push(`/social/compose?edit=${id}`);
  };

  const handleDelete = (id: string) => {
    setConfirmAction({
      action: () => deleteMutation.mutate(id),
      title: "Delete Post",
      message: "Are you sure you want to delete this post? This action cannot be undone.",
    });
  };

  const handleRetry = (id: string) => {
    retryMutation.mutate(id);
  };

  const handleBulkDelete = () => {
    if (selectedPosts.size === 0) return;
    const count = selectedPosts.size;
    const ids = Array.from(selectedPosts);
    setConfirmAction({
      action: () => bulkDeleteMutation.mutate(ids),
      title: `Delete ${count} Post${count !== 1 ? "s" : ""}`,
      message: `Are you sure you want to delete ${count} post${count !== 1 ? "s" : ""}? This action cannot be undone.`,
    });
  };

  const toggleSelectPost = (id: string) => {
    const newSelected = new Set(selectedPosts);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedPosts(newSelected);
  };

  const exportToCSV = () => {
    const csv = [
      ["ID", "Content", "Platforms", "Status", "Scheduled At", "Published At"].join(","),
      ...posts.map((post) =>
        [
          post.id,
          `"${post.content.replace(/"/g, '""')}"`,
          getPostPlatforms(post).join(";"),
          post.status,
          post.scheduled_at,
          post.published_at || "",
        ].join(",")
      ),
    ].join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `social-posts-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
  };

  return (
    <TierGate minimum="starter" feature="Social Media">
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
      <div className="mb-6">
        <h1 className="text-2xl font-display font-bold text-text-primary flex items-center gap-3">
          <History className="h-8 w-8 text-primary-500" />
          Post History
        </h1>
        <p className="text-text-secondary mt-1">
          View and manage all your social media posts
        </p>
      </div>

      {/* Filters */}
      <div className="bg-surface rounded-xl border border-surface-tertiary p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <Input
              placeholder="Search posts..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              leftIcon={<Search className="h-4 w-4" />}
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as SocialPostStatus | "all");
              setPage(1);
            }}
            className="px-4 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="queued">Queued</option>
            <option value="posting">Posting</option>
            <option value="posted">Posted</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>

          {/* Platform Filter */}
          <select
            value={platformFilter}
            onChange={(e) => {
              setPlatformFilter(e.target.value as SocialPlatform | "all");
              setPage(1);
            }}
            className="px-4 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Platforms</option>
            <option value="twitter">Twitter</option>
            <option value="linkedin">LinkedIn</option>
            <option value="facebook">Facebook</option>
            <option value="instagram">Instagram</option>
          </select>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-1 bg-surface-secondary rounded-lg p-1">
            <button
              onClick={() => setViewMode("list")}
              className={cn(
                "p-2 rounded-md transition-colors",
                viewMode === "list"
                  ? "bg-surface shadow-sm"
                  : "text-text-secondary hover:text-text-primary"
              )}
              aria-label="List view"
            >
              <List className="h-5 w-5" />
            </button>
            <button
              onClick={() => setViewMode("grid")}
              className={cn(
                "p-2 rounded-md transition-colors",
                viewMode === "grid"
                  ? "bg-surface shadow-sm"
                  : "text-text-secondary hover:text-text-primary"
              )}
              aria-label="Grid view"
            >
              <Grid className="h-5 w-5" />
            </button>
          </div>

          {/* Export */}
          <Button
            variant="outline"
            size="sm"
            onClick={exportToCSV}
            leftIcon={<Download className="h-4 w-4" />}
            disabled={posts.length === 0}
          >
            Export
          </Button>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedPosts.size > 0 && (
        <div className="bg-primary-50 border border-primary-200 rounded-lg p-4 mb-4 flex items-center justify-between">
          <p className="text-sm font-medium">
            {selectedPosts.size} post{selectedPosts.size > 1 ? "s" : ""} selected
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectedPosts(new Set())}
            >
              Clear
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleBulkDelete}
              leftIcon={<Trash2 className="h-4 w-4" />}
            >
              Delete Selected
            </Button>
          </div>
        </div>
      )}

      {/* Posts List */}
      {loading ? (
        <div className="flex items-center justify-center h-64 bg-surface rounded-xl border border-surface-tertiary">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-text-secondary">Loading posts...</p>
          </div>
        </div>
      ) : posts.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 bg-surface rounded-xl border border-surface-tertiary">
          <History className="h-12 w-12 text-text-secondary mb-4" />
          <p className="text-lg font-medium text-text-secondary">No posts found</p>
          <p className="text-sm text-text-secondary mt-1">
            Try adjusting your filters or create a new post
          </p>
          <Button
            className="mt-4"
            onClick={() => router.push("/social/compose")}
          >
            Create New Post
          </Button>
        </div>
      ) : (
        <div
          className={cn(
            viewMode === "list" ? "space-y-4" : "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          )}
        >
          {posts.map((post) => (
            <div key={post.id} className="relative">
              {/* Checkbox for selection */}
              <input
                type="checkbox"
                checked={selectedPosts.has(post.id)}
                onChange={() => toggleSelectPost(post.id)}
                className="absolute top-6 left-6 z-10 w-4 h-4 rounded border-surface-tertiary"
              />
              <PostListItem
                post={post}
                onView={handleView}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onRetry={handleRetry}
              />
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-between">
          <p className="text-sm text-text-secondary">
            Showing {(page - 1) * 20 + 1} to {Math.min(page * 20, total)} of {total} posts
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(page - 1)}
              disabled={page === 1}
            >
              Previous
            </Button>
            <span className="text-sm">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(page + 1)}
              disabled={page === totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
    </TierGate>
  );
}
