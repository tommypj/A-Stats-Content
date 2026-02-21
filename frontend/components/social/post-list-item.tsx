"use client";

import { SocialPost, SocialPlatform } from "@/lib/api";
import { PostStatusBadge } from "./post-status-badge";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Twitter, Linkedin, Facebook, Instagram, Eye, Edit, Trash2, RotateCw } from "lucide-react";
import { format, parseISO } from "date-fns";
import { cn } from "@/lib/utils";

interface PostListItemProps {
  post: SocialPost;
  onView: (id: string) => void;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
  onRetry?: (id: string) => void;
}

const PLATFORM_ICONS: Record<SocialPlatform, React.ReactNode> = {
  twitter: <Twitter className="h-4 w-4 text-[#1DA1F2]" />,
  linkedin: <Linkedin className="h-4 w-4 text-[#0A66C2]" />,
  facebook: <Facebook className="h-4 w-4 text-[#1877F2]" />,
  instagram: <Instagram className="h-4 w-4 text-[#E4405F]" />,
};

export function PostListItem({
  post,
  onView,
  onEdit,
  onDelete,
  onRetry,
}: PostListItemProps) {
  const scheduledDate = parseISO(post.scheduled_at);
  const isPosted = post.status === "posted";
  const isFailed = post.status === "failed";
  const canEdit = post.status === "pending" || post.status === "failed";

  return (
    <Card className="p-4 hover:shadow-md transition-shadow">
      <div className="flex gap-4">
        {/* Media Preview */}
        {post.media_urls && post.media_urls.length > 0 && (
          <div className="flex-shrink-0">
            <img
              src={post.media_urls[0]}
              alt="Post media"
              className="w-16 h-16 object-cover rounded-lg"
            />
          </div>
        )}

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4 mb-2">
            <div className="flex-1">
              <p className="text-sm line-clamp-2 mb-2">{post.content}</p>
              <div className="flex items-center gap-3 text-xs text-text-secondary">
                <span>
                  {isPosted ? "Posted" : "Scheduled"} {format(scheduledDate, "MMM d, yyyy 'at' h:mm a")}
                </span>
                {isPosted && post.published_at && (
                  <span className="text-green-600">
                    Published {format(parseISO(post.published_at), "MMM d, h:mm a")}
                  </span>
                )}
              </div>
            </div>
            <PostStatusBadge status={post.status as any} />
          </div>

          {/* Platforms and Actions */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {post.platforms.map((platform) => (
                <span
                  key={platform}
                  className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-surface-secondary"
                  title={platform}
                >
                  {PLATFORM_ICONS[platform as SocialPlatform]}
                </span>
              ))}
              {post.targets && post.targets.length > 0 && (
                <span className="text-xs text-text-secondary ml-2">
                  {post.targets.filter((t) => t.status === "posted").length}/{post.targets.length} accounts
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onView(post.id)}
                leftIcon={<Eye className="h-4 w-4" />}
              >
                View
              </Button>
              {canEdit && onEdit && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onEdit(post.id)}
                  leftIcon={<Edit className="h-4 w-4" />}
                >
                  Edit
                </Button>
              )}
              {isFailed && onRetry && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onRetry(post.id)}
                  leftIcon={<RotateCw className="h-4 w-4" />}
                >
                  Retry
                </Button>
              )}
              {onDelete && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onDelete(post.id)}
                  leftIcon={<Trash2 className="h-4 w-4" />}
                  className="text-red-500 hover:text-red-600"
                >
                  Delete
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
