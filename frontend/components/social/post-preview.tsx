"use client";

import { SocialPlatform } from "@/lib/api";
import { Twitter, Linkedin, Facebook, Instagram, Heart, MessageCircle, Repeat2, Share } from "lucide-react";
import { Card } from "@/components/ui/card";

interface PostPreviewProps {
  platform: SocialPlatform;
  content: string;
  mediaUrls?: string[];
  accountName: string;
  accountUsername: string;
  profileImageUrl?: string;
}

export function PostPreview({
  platform,
  content,
  mediaUrls = [],
  accountName,
  accountUsername,
  profileImageUrl,
}: PostPreviewProps) {
  const getPlatformIcon = () => {
    switch (platform) {
      case "twitter":
        return <Twitter className="h-4 w-4 text-blue-500" />;
      case "linkedin":
        return <Linkedin className="h-4 w-4 text-blue-700" />;
      case "facebook":
        return <Facebook className="h-4 w-4 text-blue-600" />;
      case "instagram":
        return <Instagram className="h-4 w-4 text-pink-500" />;
    }
  };

  const getPlatformName = () => {
    return platform.charAt(0).toUpperCase() + platform.slice(1);
  };

  const renderTwitterPreview = () => (
    <div className="border border-surface-tertiary rounded-xl overflow-hidden max-w-md">
      {/* Header */}
      <div className="p-4 flex items-start gap-3">
        <div className="h-12 w-12 rounded-full bg-surface-tertiary flex items-center justify-center overflow-hidden flex-shrink-0">
          {profileImageUrl ? (
            <img src={profileImageUrl} alt={accountName} className="h-full w-full object-cover" />
          ) : (
            <span className="text-text-tertiary font-medium">{accountName[0]}</span>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="font-semibold text-text-primary">{accountName}</p>
            <Twitter className="h-4 w-4 text-blue-500" />
          </div>
          <p className="text-sm text-text-secondary">@{accountUsername}</p>
        </div>
      </div>

      {/* Content */}
      <div className="px-4 pb-3">
        <p className="text-text-primary whitespace-pre-wrap break-words">
          {content.slice(0, 280)}
          {content.length > 280 && <span className="text-text-tertiary">...</span>}
        </p>
      </div>

      {/* Media */}
      {mediaUrls.length > 0 && (
        <div className="px-4 pb-3">
          <div className={`grid gap-2 ${mediaUrls.length === 1 ? 'grid-cols-1' : 'grid-cols-2'}`}>
            {mediaUrls.slice(0, 4).map((url) => (
              <div key={url} className="aspect-video bg-surface-tertiary rounded-xl overflow-hidden">
                <img src={url} alt="Post media" className="w-full h-full object-cover" />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="px-4 py-3 border-t border-surface-tertiary flex items-center gap-6 text-text-secondary">
        <button className="flex items-center gap-2 hover:text-blue-500 transition-colors">
          <MessageCircle className="h-4 w-4" />
          <span className="text-sm">Reply</span>
        </button>
        <button className="flex items-center gap-2 hover:text-green-500 transition-colors">
          <Repeat2 className="h-4 w-4" />
          <span className="text-sm">Retweet</span>
        </button>
        <button className="flex items-center gap-2 hover:text-red-500 transition-colors">
          <Heart className="h-4 w-4" />
          <span className="text-sm">Like</span>
        </button>
        <button className="flex items-center gap-2 hover:text-blue-500 transition-colors">
          <Share className="h-4 w-4" />
          <span className="text-sm">Share</span>
        </button>
      </div>
    </div>
  );

  const renderLinkedInPreview = () => (
    <div className="border border-surface-tertiary rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 flex items-start gap-3">
        <div className="h-12 w-12 rounded-full bg-surface-tertiary flex items-center justify-center overflow-hidden flex-shrink-0">
          {profileImageUrl ? (
            <img src={profileImageUrl} alt={accountName} className="h-full w-full object-cover" />
          ) : (
            <span className="text-text-tertiary font-medium">{accountName[0]}</span>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-text-primary">{accountName}</p>
          <p className="text-xs text-text-secondary">Professional Account</p>
          <p className="text-xs text-text-tertiary">Just now</p>
        </div>
      </div>

      {/* Content */}
      <div className="px-4 pb-3">
        <p className="text-text-primary whitespace-pre-wrap break-words">
          {content.slice(0, 3000)}
        </p>
      </div>

      {/* Media */}
      {mediaUrls.length > 0 && (
        <div className="mt-3">
          <img src={mediaUrls[0]} alt="Post media" className="w-full object-cover max-h-64 sm:max-h-96" />
        </div>
      )}

      {/* Actions */}
      <div className="px-4 py-3 border-t border-surface-tertiary flex items-center gap-4">
        <button className="flex items-center gap-2 text-text-secondary hover:text-blue-700 transition-colors">
          <Linkedin className="h-4 w-4" />
          <span className="text-sm">Like</span>
        </button>
        <button className="flex items-center gap-2 text-text-secondary hover:text-blue-700 transition-colors">
          <MessageCircle className="h-4 w-4" />
          <span className="text-sm">Comment</span>
        </button>
        <button className="flex items-center gap-2 text-text-secondary hover:text-blue-700 transition-colors">
          <Repeat2 className="h-4 w-4" />
          <span className="text-sm">Repost</span>
        </button>
        <button className="flex items-center gap-2 text-text-secondary hover:text-blue-700 transition-colors">
          <Share className="h-4 w-4" />
          <span className="text-sm">Send</span>
        </button>
      </div>
    </div>
  );

  const renderFacebookPreview = () => (
    <div className="border border-surface-tertiary rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 flex items-start gap-3">
        <div className="h-10 w-10 rounded-full bg-surface-tertiary flex items-center justify-center overflow-hidden flex-shrink-0">
          {profileImageUrl ? (
            <img src={profileImageUrl} alt={accountName} className="h-full w-full object-cover" />
          ) : (
            <span className="text-text-tertiary font-medium">{accountName[0]}</span>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-text-primary">{accountName}</p>
          <p className="text-xs text-text-tertiary">Just now · 🌎</p>
        </div>
      </div>

      {/* Content */}
      <div className="px-4 pb-3">
        <p className="text-text-primary whitespace-pre-wrap break-words">{content}</p>
      </div>

      {/* Media */}
      {mediaUrls.length > 0 && (
        <div>
          <img src={mediaUrls[0]} alt="Post media" className="w-full object-cover max-h-64 sm:max-h-96" />
        </div>
      )}

      {/* Actions */}
      <div className="px-4 py-3 border-t border-surface-tertiary flex items-center gap-6 text-text-secondary">
        <button className="flex items-center gap-2 hover:text-blue-600 transition-colors">
          <Heart className="h-4 w-4" />
          <span className="text-sm">Like</span>
        </button>
        <button className="flex items-center gap-2 hover:text-blue-600 transition-colors">
          <MessageCircle className="h-4 w-4" />
          <span className="text-sm">Comment</span>
        </button>
        <button className="flex items-center gap-2 hover:text-blue-600 transition-colors">
          <Share className="h-4 w-4" />
          <span className="text-sm">Share</span>
        </button>
      </div>
    </div>
  );

  const renderInstagramPreview = () => (
    <div className="border border-surface-tertiary rounded-xl overflow-hidden max-w-md mx-auto">
      {/* Header */}
      <div className="p-3 flex items-center gap-3 border-b border-surface-tertiary">
        <div className="h-8 w-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 p-0.5">
          <div className="h-full w-full rounded-full bg-white flex items-center justify-center overflow-hidden">
            {profileImageUrl ? (
              <img src={profileImageUrl} alt={accountName} className="h-full w-full object-cover" />
            ) : (
              <span className="text-text-tertiary text-xs font-medium">{accountName[0]}</span>
            )}
          </div>
        </div>
        <p className="font-semibold text-text-primary text-sm">{accountUsername}</p>
      </div>

      {/* Media */}
      {mediaUrls.length > 0 ? (
        <div className="aspect-square bg-surface-tertiary">
          <img src={mediaUrls[0]} alt="Post media" className="w-full h-full object-cover" />
        </div>
      ) : (
        <div className="aspect-square bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center">
          <Instagram className="h-16 w-16 text-text-tertiary" />
        </div>
      )}

      {/* Actions */}
      <div className="p-3">
        <div className="flex items-center gap-4 mb-3">
          <Heart className="h-6 w-6 text-text-secondary" />
          <MessageCircle className="h-6 w-6 text-text-secondary" />
          <Share className="h-6 w-6 text-text-secondary" />
        </div>

        {/* Caption */}
        <p className="text-sm">
          <span className="font-semibold text-text-primary">{accountUsername}</span>{" "}
          <span className="text-text-primary">
            {content.slice(0, 2200)}
            {content.length > 2200 && "..."}
          </span>
        </p>
      </div>
    </div>
  );

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        {getPlatformIcon()}
        <h3 className="text-sm font-medium text-text-primary">
          {getPlatformName()} Preview
        </h3>
      </div>

      {platform === "twitter" && renderTwitterPreview()}
      {platform === "linkedin" && renderLinkedInPreview()}
      {platform === "facebook" && renderFacebookPreview()}
      {platform === "instagram" && renderInstagramPreview()}
    </div>
  );
}
