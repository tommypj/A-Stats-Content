"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, SocialPost, SocialAnalytics, SocialPlatform } from "@/lib/api";
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

const PLATFORM_ICONS: Record<SocialPlatform, React.ReactNode> = {
  twitter: <Twitter className="h-5 w-5 text-[#1DA1F2]" />,
  linkedin: <Linkedin className="h-5 w-5 text-[#0A66C2]" />,
  facebook: <Facebook className="h-5 w-5 text-[#1877F2]" />,
  instagram: <Instagram className="h-5 w-5 text-[#E4405F]" />,
};

export default function PostDetailPage() {
  const params = useParams();
  const router = useRouter();
  const postId = params.id as string;

  const [post, setPost] = useState<SocialPost | null>(null);
  const [analytics, setAnalytics] = useState<SocialAnalytics[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{ action: () => void; title: string; message: string; confirmLabel?: string; variant?: "danger" | "warning" | "default" } | null>(null);

  useEffect(() => {
    loadPost();
  }, [postId]);

  const loadPost = async () => {
    setLoading(true);
    try {
      const data = await api.social.getPost(postId);
      setPost(data);

      // Load analytics if post is published
      if (data.status === "posted") {
        loadAnalytics();
      }
    } catch (error) {
      toast.error("Failed to load post");
      router.push("/social/history");
    } finally {
      setLoading(false);
    }
  };

  const loadAnalytics = async () => {
    setAnalyticsLoading(true);
    try {
      const data = await api.social.analytics(postId);
      setAnalytics([data]);
    } catch (error) {
      console.error("Failed to load analytics:", error);
    } finally {
      setAnalyticsLoading(false);
    }
  };

  const handleEdit = () => {
    router.push(`/social/compose?edit=${postId}`);
  };

  const handleDelete = () => {
    setConfirmAction({
      action: async () => {
        try {
          await api.social.deletePost(postId);
          router.push("/social/history");
        } catch (error) {
          toast.error("Failed to delete post");
        }
      },
      title: "Delete Post",
      message: "Are you sure you want to delete this post? This action cannot be undone.",
      confirmLabel: "Delete",
      variant: "danger",
    });
  };

  const handlePublishNow = () => {
    setConfirmAction({
      action: async () => {
        try {
          await api.social.publishNow(postId);
          loadPost();
        } catch (error) {
          toast.error("Failed to publish post");
        }
      },
      title: "Publish Now",
      message: "Are you sure you want to publish this post now?",
      confirmLabel: "Publish",
      variant: "default",
    });
  };

  const handleRetry = async (targetIds?: string[]) => {
    try {
      await api.social.retryFailed(postId, targetIds);
      loadPost();
    } catch (error) {
      toast.error("Failed to retry post");
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-5xl">
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
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="text-center">
          <p className="text-lg text-text-secondary">Post not found</p>
          <Button className="mt-4" onClick={() => router.push("/social/history")}>
            Back to History
          </Button>
        </div>
      </div>
    );
  }

  const canEdit = post.status === "pending" || post.status === "failed";
  const canPublishNow = post.status === "pending";
  const hasFailed = post.status === "failed" || post.targets?.some((t) => t.status === "failed");

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
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
              <h1 className="text-3xl font-bold">Post Details</h1>
              <PostStatusBadge status={post.status} />
            </div>
            <div className="flex items-center gap-4 text-sm text-text-secondary">
              <span className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                Scheduled: {format(parseISO(post.scheduled_at), "MMM d, yyyy 'at' h:mm a")}
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
                      key={index}
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
                      <span className="flex items-center justify-center w-10 h-10 rounded-full bg-white">
                        {PLATFORM_ICONS[target.platform]}
                      </span>
                      <div>
                        <p className="font-medium capitalize">{target.platform}</p>
                        {target.posted_at && (
                          <p className="text-xs text-text-secondary">
                            Posted {format(parseISO(target.posted_at), "MMM d, h:mm a")}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {target.status === "posted" && (
                        <>
                          <Badge variant="success">Posted</Badge>
                          {target.posted_url && (
                            <a
                              href={target.posted_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-primary-500 hover:text-primary-600"
                            >
                              <ExternalLink className="h-5 w-5" />
                            </a>
                          )}
                        </>
                      )}
                      {target.status === "failed" && (
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
                      {target.status === "pending" && <Badge variant="warning">Pending</Badge>}
                      {target.status === "posting" && <Badge variant="default">Posting...</Badge>}
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-text-secondary text-center py-4">No target accounts configured</p>
              )}
            </div>

            {/* Error Messages */}
            {post.targets?.some((t) => t.error_message) && (
              <div className="mt-4 space-y-2">
                <h3 className="text-sm font-semibold text-red-600 flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  Errors
                </h3>
                {post.targets
                  .filter((t) => t.error_message)
                  .map((target) => (
                    <div
                      key={target.id}
                      className="p-3 bg-red-50 border border-red-200 rounded-lg"
                    >
                      <p className="text-sm font-medium capitalize">{target.platform}</p>
                      <p className="text-sm text-red-700 mt-1">{target.error_message}</p>
                    </div>
                  ))}
              </div>
            )}
          </Card>

          {/* Analytics */}
          {post.status === "posted" && (
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
              {post.platforms.map((platform) => (
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
  );
}
