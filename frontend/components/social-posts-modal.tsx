"use client";

import { useState, useEffect, useRef } from "react";
import {
  X,
  Loader2,
  Sparkles,
  Copy,
  Share2,
  Check,
  RefreshCw,
  Download,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { api, parseApiError, SocialPostsData, getImageUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

type Platform = "twitter" | "linkedin" | "facebook" | "instagram";

const PLATFORMS: { key: Platform; label: string; maxChars: number; color: string }[] = [
  { key: "twitter", label: "Twitter / X", maxChars: 280, color: "bg-sky-500" },
  { key: "linkedin", label: "LinkedIn", maxChars: 3000, color: "bg-blue-700" },
  { key: "facebook", label: "Facebook", maxChars: 500, color: "bg-blue-600" },
  { key: "instagram", label: "Instagram", maxChars: 2200, color: "bg-gradient-to-r from-purple-500 to-pink-500" },
];

interface SocialPostsModalProps {
  articleId: string;
  articleTitle: string;
  articleUrl?: string;
  imageUrl?: string;
  isOpen: boolean;
  onClose: () => void;
}

export default function SocialPostsModal({
  articleId,
  articleTitle,
  articleUrl,
  imageUrl,
  isOpen,
  onClose,
}: SocialPostsModalProps) {
  const [activePlatform, setActivePlatform] = useState<Platform>("twitter");
  const [socialPosts, setSocialPosts] = useState<SocialPostsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editedTexts, setEditedTexts] = useState<Record<string, string>>({});
  const [copiedPlatform, setCopiedPlatform] = useState<string | null>(null);
  const copyTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clean up timeout on unmount
  useEffect(() => {
    return () => {
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (isOpen) {
      loadSocialPosts();
      setEditedTexts({});
      setCopiedPlatform(null);
    }
  }, [isOpen, articleId]);

  async function loadSocialPosts() {
    setLoading(true);
    try {
      const data = await api.articles.getSocialPosts(articleId);
      setSocialPosts(data);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to load social posts");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerate() {
    setGenerating(true);
    try {
      const data = await api.articles.generateSocialPosts(articleId);
      setSocialPosts(data);
      setEditedTexts({});
      toast.success("Social posts generated!");
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to generate social posts");
    } finally {
      setGenerating(false);
    }
  }

  async function handleSave(platform: Platform) {
    const text = editedTexts[platform];
    if (text === undefined) return;

    setSaving(true);
    try {
      const data = await api.articles.updateSocialPost(articleId, platform, text);
      setSocialPosts(data);
      setEditedTexts((prev) => {
        const next = { ...prev };
        delete next[platform];
        return next;
      });
      toast.success("Post updated!");
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  function getPostText(platform: Platform): string {
    if (editedTexts[platform] !== undefined) return editedTexts[platform];
    const post = socialPosts?.[platform];
    return post?.text || "";
  }

  function handleTextChange(platform: Platform, text: string) {
    setEditedTexts((prev) => ({ ...prev, [platform]: text }));
  }

  async function handleCopy(platform: Platform) {
    const text = getPostText(platform);
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedPlatform(platform);
      toast.success("Copied to clipboard!");
      if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
      copyTimeoutRef.current = setTimeout(() => setCopiedPlatform(null), 2000);
    } catch {
      toast.error("Failed to copy");
    }
  }

  async function handleShare(platform: Platform) {
    const text = getPostText(platform);
    if (!text) return;

    if (navigator.share) {
      // Try sharing with image file if available
      if (imageUrl) {
        const fullUrl = getImageUrl(imageUrl);
        try {
          const response = await fetch(fullUrl);
          const blob = await response.blob();
          const fileName = fullUrl.split("/").pop() || "featured-image.jpg";
          const imageFile = new File([blob], fileName, { type: blob.type || "image/jpeg" });

          if (navigator.canShare && navigator.canShare({ files: [imageFile] })) {
            await navigator.share({
              files: [imageFile],
              title: articleTitle,
              text,
            });
            return;
          }
        } catch {
          // File fetch or share failed — fall through to text share
        }
      }

      try {
        await navigator.share({
          title: articleTitle,
          text,
          url: articleUrl,
        });
      } catch (err: unknown) {
        // User cancelled share — ignore AbortError
        if (err instanceof Error && err.name !== "AbortError") {
          handleCopy(platform);
        }
      }
    } else {
      handleCopy(platform);
    }
  }

  async function handleDownloadImage() {
    if (!imageUrl) return;
    const fullUrl = getImageUrl(imageUrl);
    try {
      const response = await fetch(fullUrl);
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = fullUrl.split("/").pop() || "featured-image.jpg";
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(objectUrl);
    } catch {
      toast.error("Failed to download image");
    }
  }

  const hasPosts = socialPosts && Object.values(socialPosts).some((p) => p?.text);
  const currentText = getPostText(activePlatform);
  const currentPlatformInfo = PLATFORMS.find((p) => p.key === activePlatform)!;
  const charCount = currentText.length;
  const isOverLimit = charCount > currentPlatformInfo.maxChars;
  const isEdited = editedTexts[activePlatform] !== undefined;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-surface rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-surface border-b border-surface-tertiary p-6 flex items-start justify-between z-10">
          <div className="flex-1">
            <h2 className="text-xl font-display font-bold text-text-primary">
              Share on Social Media
            </h2>
            <p className="text-sm text-text-secondary mt-1 line-clamp-1">
              {articleTitle}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-secondary transition-colors"
          >
            <X className="h-5 w-5 text-text-secondary" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* Generate / Regenerate Button */}
          <div className="flex justify-center">
            <Button
              onClick={handleGenerate}
              isLoading={generating}
              leftIcon={hasPosts ? <RefreshCw className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
            >
              {generating
                ? "Generating..."
                : hasPosts
                ? "Regenerate All Posts"
                : "Generate Social Posts"}
            </Button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
            </div>
          ) : !hasPosts && !generating ? (
            <div className="text-center py-8">
              <Share2 className="h-12 w-12 mx-auto text-text-muted mb-3" />
              <p className="text-text-secondary">
                No social posts generated yet. Click the button above to create platform-specific posts.
              </p>
            </div>
          ) : hasPosts ? (
            <>
              {/* Featured Image Preview */}
              {imageUrl && (
                <div className="border border-surface-tertiary rounded-xl overflow-hidden">
                  <img
                    src={getImageUrl(imageUrl)}
                    alt="Featured image"
                    className="w-full object-cover rounded-t-xl"
                    style={{ maxHeight: "200px" }}
                  />
                  <div className="px-3 py-2 flex justify-end bg-surface-secondary">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleDownloadImage}
                      leftIcon={<Download className="h-4 w-4" />}
                    >
                      Download Image
                    </Button>
                  </div>
                </div>
              )}

              {/* Platform Tabs */}
              <div className="flex gap-1 bg-surface-secondary p-1 rounded-xl">
                {PLATFORMS.map((platform) => {
                  const hasContent = !!socialPosts?.[platform.key]?.text;
                  return (
                    <button
                      key={platform.key}
                      onClick={() => setActivePlatform(platform.key)}
                      className={cn(
                        "flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all relative",
                        activePlatform === platform.key
                          ? "bg-surface text-text-primary shadow-sm"
                          : "text-text-secondary hover:text-text-primary"
                      )}
                    >
                      {platform.label}
                      {hasContent && (
                        <span className={cn(
                          "absolute top-1 right-1 w-2 h-2 rounded-full",
                          platform.color
                        )} />
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Post Editor */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-text-secondary">
                    {currentPlatformInfo.label}
                  </span>
                  <span
                    className={cn(
                      "text-xs font-mono",
                      isOverLimit ? "text-red-500 font-bold" : charCount > currentPlatformInfo.maxChars * 0.9 ? "text-yellow-600" : "text-text-muted"
                    )}
                  >
                    {charCount} / {currentPlatformInfo.maxChars}
                  </span>
                </div>

                <textarea
                  value={currentText}
                  onChange={(e) => handleTextChange(activePlatform, e.target.value)}
                  rows={activePlatform === "linkedin" ? 10 : activePlatform === "instagram" ? 8 : 5}
                  className={cn(
                    "w-full px-4 py-3 rounded-xl border focus:ring-2 outline-none transition-all resize-none text-sm leading-relaxed",
                    isOverLimit
                      ? "border-red-300 focus:border-red-400 focus:ring-red-100"
                      : "border-surface-tertiary focus:border-primary-400 focus:ring-primary-100"
                  )}
                  placeholder={`Write your ${currentPlatformInfo.label} post...`}
                />

                {isOverLimit && (
                  <p className="text-xs text-red-500">
                    Post exceeds the {currentPlatformInfo.maxChars} character limit for {currentPlatformInfo.label}.
                  </p>
                )}

                {/* Action Buttons */}
                <div className="flex gap-2">
                  {isEdited && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleSave(activePlatform)}
                      isLoading={saving}
                    >
                      Save Changes
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleShare(activePlatform)}
                    disabled={!currentText}
                    leftIcon={<Share2 className="h-4 w-4" />}
                  >
                    Share
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleCopy(activePlatform)}
                    disabled={!currentText}
                    leftIcon={
                      copiedPlatform === activePlatform ? (
                        <Check className="h-4 w-4 text-green-600" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )
                    }
                  >
                    {copiedPlatform === activePlatform ? "Copied!" : "Copy"}
                  </Button>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
