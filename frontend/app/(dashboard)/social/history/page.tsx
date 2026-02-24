"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { PostListItem } from "@/components/social/post-list-item";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { api, SocialPost, SocialPostStatus, SocialPlatform } from "@/lib/api";
import { History, Search, Filter, Download, Trash2, List, Grid } from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

export default function SocialHistoryPage() {
  const router = useRouter();
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  // Filters
  const [statusFilter, setStatusFilter] = useState<SocialPostStatus | "all">("all");
  const [platformFilter, setPlatformFilter] = useState<SocialPlatform | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const [selectedPosts, setSelectedPosts] = useState<Set<string>>(new Set());
  const [confirmAction, setConfirmAction] = useState<{ action: () => void; title: string; message: string } | null>(null);

  useEffect(() => {
    loadPosts();
  }, [page, statusFilter, platformFilter, searchQuery]);

  const loadPosts = async () => {
    setLoading(true);
    try {
      const response = await api.social.posts({
        page,
        page_size: 20,
        status: statusFilter === "all" ? undefined : statusFilter,
        platform: platformFilter === "all" ? undefined : platformFilter,
        search: searchQuery || undefined,
      });

      setPosts(response.items);
      setTotal(response.total);
      setTotalPages(response.pages);
    } catch (error) {
      console.error("Failed to load posts:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleView = (id: string) => {
    router.push(`/social/posts/${id}`);
  };

  const handleEdit = (id: string) => {
    router.push(`/social/compose?edit=${id}`);
  };

  const handleDelete = (id: string) => {
    setConfirmAction({
      action: async () => {
        try {
          await api.social.deletePost(id);
          loadPosts();
        } catch (error) {
          console.error("Failed to delete post:", error);
          toast.error("Failed to delete post");
        }
      },
      title: "Delete Post",
      message: "Are you sure you want to delete this post? This action cannot be undone.",
    });
  };

  const handleRetry = async (id: string) => {
    try {
      await api.social.retryFailed(id);
      loadPosts();
    } catch (error) {
      console.error("Failed to retry post:", error);
      toast.error("Failed to retry post");
    }
  };

  const handleBulkDelete = () => {
    if (selectedPosts.size === 0) return;
    const count = selectedPosts.size;
    setConfirmAction({
      action: async () => {
        try {
          await Promise.all(
            Array.from(selectedPosts).map((id) => api.social.deletePost(id))
          );
          setSelectedPosts(new Set());
          loadPosts();
        } catch (error) {
          console.error("Failed to delete posts:", error);
          toast.error("Failed to delete some posts");
        }
      },
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
          post.platforms.join(";"),
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
    <div className="container mx-auto px-4 py-8 max-w-7xl">
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
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <History className="h-8 w-8 text-primary-500" />
          Post History
        </h1>
        <p className="text-text-secondary mt-1">
          View and manage all your social media posts
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-surface-tertiary p-4 mb-6">
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
            className="px-4 py-2 border border-surface-tertiary rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
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
            className="px-4 py-2 border border-surface-tertiary rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
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
                  ? "bg-white shadow-sm"
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
                  ? "bg-white shadow-sm"
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
        <div className="flex items-center justify-center h-64 bg-white rounded-xl border border-surface-tertiary">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-text-secondary">Loading posts...</p>
          </div>
        </div>
      ) : posts.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 bg-white rounded-xl border border-surface-tertiary">
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
  );
}
