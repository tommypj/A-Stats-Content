"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, parseApiError, SocialPlatform, getPostPlatforms, getTargetStatus } from "@/lib/api";
import { toast } from "sonner";
import { PostStatusBadge } from "@/components/social/post-status-badge";
import { PostAnalyticsCard } from "@/components/social/post-analytics-card";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  ArrowLeft,
  Edit,
  Trash2,
  RotateCw,
  Send,
  ExternalLink,
  Twitter,
  Linkedin,
  Facebook,
  Instagram,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { cn } from "@/lib/utils";
import { TierGate } from "@/components/ui/tier-gate";

const PLATFORM_ICONS: Record<SocialPlatform, React.ReactNode> = {
  twitter: <Twitter className="h-5 w-5 text-[#1DA1F2]" />,
  linkedin: <Linkedin className="h-5 w-5 text-[#0A66C2]" />,
  facebook: <Facebook className="h-5 w-5 text-[#1877F2]" />,
  instagram: <Instagram className="h-5 w-5 text-[#E4405F]" />,
};

export default function PostDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const rawId = params.id;
  const postId = Array.isArray(rawId) ? rawId[0] : (rawId ?? "");

  const [confirmAction, setConfirmAction] = useState<{ action: () => void; title: string; message: string; confirmLabel?: string; variant?: "danger" | "warning" | "default" } | null>(null);

  // --- React Query hooks ---

  const { data: post, isLoading: loading } = useQuery({
    queryKey: ["social", "post", postId],
    queryFn: () => api.social.getPost(postId),
    enabled: !!postId,
    staleTime: 60_000,
    meta: { onError: true },
  });

  const { data: analyticsData, isLoading: analyticsLoading } = useQuery({
    queryKey: ["social", "analytics", postId],
    queryFn: () => api.social.analytics(postId),
    enabled: !!postId && (post?.status === "published" || post?.status === "partially_published"),
    staleTime: 60_000,
  });

  const analytics = analyticsData ? [analyticsData] : [];

  // --- Mutations ---

  const deleteMutation = useMutation({
    mutationFn: () => api.social.deletePost(postId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["social"] });
      router.push("/social/history");
    },
    onError: (error) => {
      toast.error(parseApiError(error).message);
    },
  });

  const publishNowMutation = useMutation({
    mutationFn: () => api.social.publishNow(postId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["social", "post", postId] });
      queryClient.invalidateQueries({ queryKey: ["social", "analytics", postId] });
    },
    onError: (error) => {
      toast.error(parseApiError(error).message);
    },
  });

  const retryMutation = useMutation({
    mutationFn: (targetIds?: string[]) => api.social.retryFailed(postId, targetIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["social", "post", postId] });
    },
    onError: (error) => {
      toast.error(parseApiError(error).message);
    },
  });

  // --- Handlers ---

  const handleEdit = () => {
    router.push(`/social/compose?edit=${postId}`);
  };

  const handleDelete = () => {
    setConfirmAction({
      action: () => deleteMutation.mutate(),
      title: "Delete Post",
      message: "Are you sure you want to delete this post? This action cannot be undone.",
      confirmLabel: "Delete",
      variant: "danger",
    });
  };

  const handlePublishNow = () => {
    setConfirmAction({
      action: () => publishNowMutation.mutate(),
      title: "Publish Now",
      message: "Are you sure you want to publish this post now?",
      confirmLabel: "Publish",
      variant: "default",
    });
  };

  const handleRetry = (targetIds?: string[]) => {
    retryMutation.mutate(targetIds);
  };

  if (!postId) {
    return <div>Invalid post ID</div>;
  }

  if (loading) {
    return (
      <div className="space-y-6 max-w-5xl">
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-text-secondary">Loading post...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!post) {
    return (
      <div className="space-y-6 max-w-5xl">
        <div className="text-center">
          <p className="text-lg text-text-secondary">Post not found</p>
          <Button className="mt-4" onClick={() => router.push("/social/history")}>
            Back to History
          </Button>
        </div>
      </div>
    );
  }

  const canEdit = post.status === "draft" || post.status === "scheduled" || post.status === "failed";
  const canPublishNow = post.status === "draft" || post.status === "scheduled";
  const hasFailed = post.status === "failed" || post.targets?.some((t) => getTargetStatus(t) === "failed");

  return (
    <TierGate minimum="starter" feature="Social Media">
    <div className="space-y-6 max-w-5xl">
      <ConfirmDialog
        isOpen={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        onConfirm={() => { confirmAction?.action(); setConfirmAction(null); }}
        title={confirmAction?.title ?? ""}
        message={confirmAction?.message ?? ""}
        variant={confirmAction?.variant ?? "default"}
        confirmLabel={confirmAction?.confirmLabel ?? "Confirm"}
      />

      {/* Header */}
      <div className="mb-6">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.back()}
          leftIcon={<ArrowLeft className="h-4 w-4" />}
          className="mb-4"
        >
          Back
        </Button>

        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-display font-bold text-text-primary">Post Details</h1>
              <PostStatusBadge status={post.status} />
            </div>
            <div className="flex items-center gap-4 text-sm text-text-secondary">
              <span className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                {post.scheduled_at ? `Scheduled: ${format(parseISO(post.scheduled_at), "MMM d, yyyy 'at' h:mm a")}` : "Published immediately"}
              </span>
              {post.published_at && (
                <span className="flex items-center gap-1 text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  Published: {format(parseISO(post.published_at), "MMM d, yyyy 'at' h:mm a")}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {canEdit && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleEdit}
                leftIcon={<Edit className="h-4 w-4" />}
              >
                Edit
              </Button>
            )}
            {canPublishNow && (
              <Button
                variant="primary"
                size="sm"
                onClick={handlePublishNow}
                leftIcon={<Send className="h-4 w-4" />}
              >
                Publish Now
              </Button>
            )}
            {hasFailed && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleRetry()}
                leftIcon={<RotateCw className="h-4 w-4" />}
              >
                Retry Failed
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleDelete}
              leftIcon={<Trash2 className="h-4 w-4" />}
              className="text-red-500 hover:text-red-600"
            >
              Delete
            </Button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Post Content */}
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4">Content</h2>
            <p className="text-base whitespace-pre-wrap leading-relaxed">{post.content}</p>

            {/* Media */}
            {post.media_urls && post.media_urls.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-text-secondary mb-3">Attached Media</h3>
                <div className="grid grid-cols-2 gap-4">
                  {post.media_urls.map((url, index) => (
                    <img
                      key={url}
                      src={url}
                      alt={`Media ${index + 1}`}
                      className="w-full h-48 object-cover rounded-lg border border-surface-tertiary"
                    />
                  ))}
                </div>
              </div>
            )}
          </Card>

          {/* Platform Targets */}
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4">Target Accounts</h2>
            <div className="space-y-3">
              {post.targets && post.targets.length > 0 ? (
                post.targets.map((target) => (
                  <div
                    key={target.id}
                    className="flex items-center justify-between p-4 bg-surface-secondary rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <span className="flex items-center justify-center w-10 h-10 rounded-full bg-surface">
                        {PLATFORM_ICONS[target.platform]}
                      </span>
                      <div>
                        <p className="font-medium capitalize">{target.platform}</p>
                        {target.published_at && (
                          <p className="text-xs text-text-secondary">
                            Posted {format(parseISO(target.published_at), "MMM d, h:mm a")}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {getTargetStatus(target) === "posted" && (
                        <>
                          <Badge variant="success">Posted</Badge>
                          {target.platform_post_url && (
                            <a
                              href={target.platform_post_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-primary-500 hover:text-primary-600"
                            >
                              <ExternalLink className="h-5 w-5" />
                            </a>
                          )}
                        </>
                      )}
                      {getTargetStatus(target) === "failed" && (
                        <div className="flex items-center gap-2">
                          <Badge variant="danger">Failed</Badge>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleRetry([target.id])}
                          >
                            Retry
                          </Button>
                        </div>
                      )}
                      {getTargetStatus(target) === "pending" && <Badge variant="warning">Pending</Badge>}
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-text-secondary text-center py-4">No target accounts configured</p>
              )}
            </div>

            {/* Error Messages */}
            {post.targets?.some((t) => t.publish_error) && (
              <div className="mt-4 space-y-2">
                <h3 className="text-sm font-semibold text-red-600 flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  Errors
                </h3>
                {post.targets
                  .filter((t) => t.publish_error)
                  .map((target) => (
                    <div
                      key={target.id}
                      className="p-3 bg-red-50 border border-red-200 rounded-lg"
                    >
                      <p className="text-sm font-medium capitalize">{target.platform}</p>
                      <p className="text-sm text-red-700 mt-1">{target.publish_error}</p>
                    </div>
                  ))}
              </div>
            )}
          </Card>

          {/* Analytics */}
          {(post.status === "published" || post.status === "partially_published") && (
            <div>
              {analyticsLoading ? (
                <Card className="p-6">
                  <div className="text-center py-8">
                    <div className="w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-text-secondary">Loading analytics...</p>
                  </div>
                </Card>
              ) : analytics.length > 0 ? (
                <PostAnalyticsCard analytics={analytics} />
              ) : (
                <Card className="p-6">
                  <p className="text-center text-text-secondary">
                    Analytics not available yet. Check back later.
                  </p>
                </Card>
              )}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Platforms */}
          <Card className="p-6">
            <h3 className="text-sm font-semibold text-text-secondary mb-3">Platforms</h3>
            <div className="flex flex-wrap gap-2">
              {getPostPlatforms(post).map((platform) => (
                <Badge key={platform} variant="default" className="capitalize">
                  {platform}
                </Badge>
              ))}
            </div>
          </Card>

          {/* Metadata */}
          <Card className="p-6">
            <h3 className="text-sm font-semibold text-text-secondary mb-3">Metadata</h3>
            <div className="space-y-2 text-sm">
              <div>
                <span className="text-text-secondary">Created:</span>
                <p className="font-medium">{format(parseISO(post.created_at), "MMM d, yyyy h:mm a")}</p>
              </div>
              <div>
                <span className="text-text-secondary">Last Updated:</span>
                <p className="font-medium">{format(parseISO(post.updated_at), "MMM d, yyyy h:mm a")}</p>
              </div>
              <div>
                <span className="text-text-secondary">Post ID:</span>
                <p className="font-mono text-xs">{post.id}</p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
    </TierGate>
  );
}
