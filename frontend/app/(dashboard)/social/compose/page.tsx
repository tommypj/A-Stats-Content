"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, SocialAccount, SocialPlatform, SocialPostsData, GeneratedImage, parseApiError, getImageUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PlatformSelector } from "@/components/social/platform-selector";
import { PostPreview } from "@/components/social/post-preview";
import { SchedulePicker } from "@/components/social/schedule-picker";
import {
  X,
  AlertCircle,
  CheckCircle,
  Upload,
  Send,
  Clock,
  Loader2,
  FileText,
  Sparkles,
  Image as ImageIcon,
} from "lucide-react";
import { toast } from "sonner";
import { TierGate } from "@/components/ui/tier-gate";

const DRAFT_KEY = "social_compose_draft";

interface MediaItem {
  previewUrl: string; // blob URL for display
  remoteUrl: string | null; // uploaded URL from backend (null while uploading)
  uploading: boolean;
  error: string | null;
}

export default function ComposePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [content, setContent] = useState("");
  const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>([]);
  const [scheduledAt, setScheduledAt] = useState(
    new Date(Date.now() + 3600000).toISOString()
  );
  const [timezone, setTimezone] = useState(() => {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch {
      return "America/New_York";
    }
  });
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [accountsInitialised, setAccountsInitialised] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- Article-to-social state ---
  const [selectedArticleId, setSelectedArticleId] = useState("");
  const [generatedPosts, setGeneratedPosts] = useState<SocialPostsData | null>(null);
  const [activePlatformTab, setActivePlatformTab] = useState<SocialPlatform>("facebook");
  const [generating, setGenerating] = useState(false);
  const [articleImageAttached, setArticleImageAttached] = useState(false);

  // Revoke all blob URLs on unmount
  useEffect(() => {
    return () => {
      mediaItems.forEach((item) => URL.revokeObjectURL(item.previewUrl));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Restore draft from localStorage on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(DRAFT_KEY);
      if (raw) {
        const draft = JSON.parse(raw);
        if (draft.content) setContent(draft.content);
        if (draft.scheduledAt) setScheduledAt(draft.scheduledAt);
        if (draft.timezone) setTimezone(draft.timezone);
        toast.info("Draft restored");
      }
    } catch {
      // ignore corrupt draft
    }
  }, []);

  // Auto-save draft (debounced 500ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (!content && selectedAccountIds.length === 0) return;
      try {
        localStorage.setItem(
          DRAFT_KEY,
          JSON.stringify({ content, selectedAccountIds, scheduledAt, timezone })
        );
      } catch {
        // storage full
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [content, selectedAccountIds, scheduledAt, timezone]);

  // --- React Query: fetch accounts ---

  const { data: accountsData, isLoading: loading } = useQuery({
    queryKey: ["social", "accounts"],
    queryFn: () => api.social.accounts(),
    staleTime: 30_000,
    select: (res) => res.accounts.filter((a) => a.is_active),
  });

  const accounts: SocialAccount[] = accountsData ?? [];

  // --- React Query: fetch articles for selector ---

  const { data: articlesData, isLoading: loadingArticles } = useQuery({
    queryKey: ["articles", "list", { page_size: 100 }],
    queryFn: () => api.articles.list({ page_size: 100 }),
    staleTime: 30_000,
  });

  const articles = useMemo(
    () => (articlesData?.items ?? []).filter(
      (a) => a.status === "completed" || a.status === "published"
    ),
    [articlesData]
  );

  const selectedArticle = useMemo(
    () => articles.find((a) => a.id === selectedArticleId),
    [articles, selectedArticleId]
  );

  // Initialise selectedAccountIds once accounts arrive
  useEffect(() => {
    if (accountsInitialised || accounts.length === 0) return;
    setAccountsInitialised(true);

    const connectedIds = accounts.map((a) => a.id);
    try {
      const raw = localStorage.getItem(DRAFT_KEY);
      if (raw) {
        const draft = JSON.parse(raw);
        if (Array.isArray(draft.selectedAccountIds)) {
          const valid = draft.selectedAccountIds.filter((id: string) => connectedIds.includes(id));
          if (valid.length > 0) {
            setSelectedAccountIds(valid);
            if (valid.length < draft.selectedAccountIds.length) {
              toast.warning("Some accounts from your draft are no longer connected and were removed.");
            }
            return;
          }
        }
      }
    } catch {
      // ignore
    }
    setSelectedAccountIds(connectedIds);
  }, [accounts, accountsInitialised]);

  // --- React Query: fetch article images when article is selected ---

  const { data: articleImagesData } = useQuery({
    queryKey: ["images", "article", selectedArticleId],
    queryFn: () => api.images.list({ article_id: selectedArticleId, page_size: 20 }),
    enabled: !!selectedArticleId,
    staleTime: 30_000,
  });

  const articleImages = useMemo(
    () => (articleImagesData?.items ?? []).filter((img) => img.status === "completed" && img.url),
    [articleImagesData]
  );

  // --- Handle article selection: generate posts ---

  const handleArticleSelect = async (articleId: string) => {
    setSelectedArticleId(articleId);
    setGeneratedPosts(null);
    setArticleImageAttached(false);
    setMediaItems([]);

    if (!articleId) return;

    const article = articles.find((a) => a.id === articleId);
    if (!article) return;

    // Generate AI social posts
    setGenerating(true);
    setError(null);
    try {
      let posts: SocialPostsData;
      const existing = article.social_posts;
      if (existing && (existing.twitter?.text || existing.linkedin?.text || existing.facebook?.text)) {
        posts = existing;
        toast.info("Loaded existing social posts for this article");
      } else {
        posts = await api.articles.generateSocialPosts(articleId);
        toast.success("Social posts generated from article!");
      }
      setGeneratedPosts(posts);

      const firstPlatform = (["facebook", "twitter", "linkedin", "instagram"] as SocialPlatform[])
        .find((p) => posts[p]?.text);
      if (firstPlatform) {
        setContent(posts[firstPlatform]!.text);
        setActivePlatformTab(firstPlatform);
      }
    } catch (err) {
      const msg = parseApiError(err).message;
      setError(`Failed to generate social posts: ${msg}`);
      toast.error(msg);
    } finally {
      setGenerating(false);
    }
  };

  const handleSelectArticleImage = (image: GeneratedImage) => {
    // Check if this image is already attached
    const resolvedUrl = getImageUrl(image.local_path || image.url);
    if (mediaItems.some((item) => item.remoteUrl === resolvedUrl)) {
      toast.info("This image is already attached");
      return;
    }
    if (mediaItems.length >= 4) {
      toast.warning("Maximum 4 images allowed");
      return;
    }
    setMediaItems((prev) => [
      ...prev,
      {
        previewUrl: resolvedUrl,
        remoteUrl: resolvedUrl,
        uploading: false,
        error: null,
      },
    ]);
    setArticleImageAttached(true);
    toast.success("Image attached to post");
  };

  // Switch content when platform tab changes (only in article mode)
  const handlePlatformTabChange = (platform: SocialPlatform) => {
    setActivePlatformTab(platform);
    if (generatedPosts && generatedPosts[platform]?.text) {
      setContent(generatedPosts[platform]!.text);
    }
  };

  // --- React Query: create post mutation ---

  const createPostMutation = useMutation({
    mutationFn: (data: Parameters<typeof api.social.createPost>[0]) =>
      api.social.createPost(data),
  });

  const submitting = createPostMutation.isPending;
  const anyUploading = mediaItems.some((item) => item.uploading);

  const validate = (): boolean => {
    setError(null);
    if (!content.trim()) {
      setError("Please enter some content for your post");
      return false;
    }
    if (selectedAccountIds.length === 0) {
      setError("Please select at least one platform");
      return false;
    }
    if (anyUploading) {
      setError("Please wait for images to finish uploading");
      return false;
    }
    const failedUploads = mediaItems.filter((item) => item.error);
    if (failedUploads.length > 0) {
      setError("Some images failed to upload. Remove them or try re-uploading.");
      return false;
    }
    return true;
  };

  const submitPost = (publishNow: boolean) => {
    if (!validate()) return;
    setSuccess(null);

    const remoteUrls = mediaItems
      .map((item) => item.remoteUrl)
      .filter((url): url is string => url !== null);

    createPostMutation.mutate(
      {
        content,
        media_urls: remoteUrls.length > 0 ? remoteUrls : undefined,
        scheduled_at: publishNow ? undefined : scheduledAt,
        publish_now: publishNow,
        platforms: accounts
          .filter((a) => selectedAccountIds.includes(a.id))
          .map((a) => a.platform),
        account_ids: selectedAccountIds,
      },
      {
        onSuccess: (post) => {
          localStorage.removeItem(DRAFT_KEY);
          queryClient.invalidateQueries({ queryKey: ["social"] });
          if (publishNow) {
            const failed = post.status === "failed";
            if (failed) {
              setError("Post failed to publish. Check the post details for more information.");
              router.push(`/social/posts/${post.id}`);
            } else {
              setSuccess("Post published successfully!");
              setTimeout(() => router.push("/social"), 2000);
            }
          } else {
            setSuccess("Post scheduled successfully!");
            setTimeout(() => router.push("/social"), 2000);
          }
        },
        onError: (err) => {
          setError(parseApiError(err).message);
        },
      }
    );
  };

  const handleSchedule = (e: React.FormEvent) => {
    e.preventDefault();
    submitPost(false);
  };

  const handlePublishNow = () => {
    submitPost(true);
  };

  const handleMediaUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    if (mediaItems.length + files.length > 4) {
      setError("Maximum 4 images allowed");
      return;
    }

    for (const file of Array.from(files)) {
      const previewUrl = URL.createObjectURL(file);
      const newItem: MediaItem = {
        previewUrl,
        remoteUrl: null,
        uploading: true,
        error: null,
      };

      setMediaItems((prev) => [...prev, newItem]);

      // Upload in background
      try {
        const result = await api.social.uploadMedia(file);
        setMediaItems((prev) =>
          prev.map((item) =>
            item.previewUrl === previewUrl
              ? { ...item, remoteUrl: result.url, uploading: false }
              : item
          )
        );
      } catch (err) {
        const message = parseApiError(err).message;
        setMediaItems((prev) =>
          prev.map((item) =>
            item.previewUrl === previewUrl
              ? { ...item, uploading: false, error: message }
              : item
          )
        );
        toast.error(`Failed to upload ${file.name}: ${message}`);
      }
    }

    // Reset file input so the same file can be re-selected
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleRemoveMedia = (index: number) => {
    const removed = mediaItems[index];
    if (removed) {
      URL.revokeObjectURL(removed.previewUrl);
    }
    setMediaItems(mediaItems.filter((_, i) => i !== index));
    if (articleImageAttached && index === 0) {
      setArticleImageAttached(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse space-y-6">
          <div className="h-10 bg-surface-secondary rounded w-1/3" />
          <div className="h-64 bg-surface-secondary rounded-xl" />
        </div>
      </div>
    );
  }

  if (accounts.length === 0) {
    return (
      <div className="space-y-6">
        <Card className="p-8 text-center">
          <AlertCircle className="h-12 w-12 text-text-tertiary mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-text-primary mb-2">
            No Connected Accounts
          </h2>
          <p className="text-text-secondary mb-4">
            You need to connect at least one social media account before you can
            create posts.
          </p>
          <Button onClick={() => router.push("/social/accounts")}>
            Connect an Account
          </Button>
        </Card>
      </div>
    );
  }

  const PLATFORM_TABS: { key: SocialPlatform; label: string }[] = [
    { key: "facebook", label: "Facebook" },
    { key: "twitter", label: "Twitter/X" },
    { key: "linkedin", label: "LinkedIn" },
    { key: "instagram", label: "Instagram" },
  ];

  return (
    <TierGate minimum="starter" feature="Social Media">
    <div className="space-y-6">
      <form onSubmit={handleSchedule} className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-display font-bold text-text-primary">Create Post</h1>
            <p className="text-text-secondary mt-1">
              Compose and publish or schedule your social media post
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.push("/social")}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="outline"
              disabled={submitting || anyUploading || generating}
              isLoading={submitting && !createPostMutation.variables?.publish_now}
              leftIcon={<Clock className="h-4 w-4" />}
            >
              Schedule Post
            </Button>
            <Button
              type="button"
              onClick={handlePublishNow}
              disabled={submitting || anyUploading || generating}
              isLoading={submitting && createPostMutation.variables?.publish_now === true}
              leftIcon={<Send className="h-4 w-4" />}
            >
              Publish Now
            </Button>
          </div>
        </div>

        {/* Success Message */}
        {success && (
          <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-xl flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-green-500" />
            <div>
              <p className="text-green-600 font-medium">{success}</p>
              <p className="text-green-500 text-sm">
                Redirecting to dashboard...
              </p>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-red-500 font-medium">Error</p>
              <p className="text-red-400 text-sm mt-1">{error}</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Composer */}
          <div className="lg:col-span-2 space-y-6">
            {/* Article Selector */}
            <Card className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <FileText className="h-5 w-5 text-primary-500" />
                <h2 className="text-lg font-semibold text-text-primary">
                  Generate from Article
                </h2>
              </div>
              <p className="text-sm text-text-secondary mb-3">
                Select an article to auto-generate platform-optimized social posts with the article&apos;s featured image.
              </p>
              <select
                value={selectedArticleId}
                onChange={(e) => handleArticleSelect(e.target.value)}
                disabled={loadingArticles || generating}
                className="w-full px-4 py-3 border border-surface-tertiary rounded-xl bg-surface-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">Write manually (no article)</option>
                {articles.map((article) => (
                  <option key={article.id} value={article.id}>
                    {article.title}
                  </option>
                ))}
              </select>
              {loadingArticles && (
                <div className="flex items-center gap-2 mt-2 text-sm text-text-secondary">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading articles...
                </div>
              )}
              {generating && (
                <div className="flex items-center gap-2 mt-3 p-3 bg-primary-500/5 border border-primary-500/20 rounded-lg">
                  <Loader2 className="h-4 w-4 animate-spin text-primary-500" />
                  <span className="text-sm text-primary-600 font-medium">
                    Generating social posts from article...
                  </span>
                </div>
              )}

              {/* Article Image Picker */}
              {selectedArticleId && articleImages.length > 0 && (
                <div className="mt-4">
                  <div className="flex items-center gap-2 mb-3">
                    <ImageIcon className="h-4 w-4 text-text-secondary" />
                    <h3 className="text-sm font-medium text-text-primary">
                      Select an Image ({articleImages.length} available)
                    </h3>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    {articleImages.map((image) => {
                      const resolvedUrl = getImageUrl(image.local_path || image.url);
                      const isSelected = mediaItems.some((item) => item.remoteUrl === resolvedUrl);
                      return (
                        <button
                          key={image.id}
                          type="button"
                          onClick={() => handleSelectArticleImage(image)}
                          className={`relative group rounded-lg overflow-hidden border-2 transition-all ${
                            isSelected
                              ? "border-primary-500 ring-2 ring-primary-500/30"
                              : "border-surface-tertiary hover:border-primary-300"
                          }`}
                        >
                          <img
                            src={resolvedUrl}
                            alt={image.alt_text || image.prompt}
                            className="w-full h-24 object-cover"
                          />
                          {isSelected && (
                            <div className="absolute inset-0 bg-primary-500/20 flex items-center justify-center">
                              <CheckCircle className="h-6 w-6 text-primary-500 drop-shadow" />
                            </div>
                          )}
                          {!isSelected && (
                            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
                              <span className="text-white text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                                Select
                              </span>
                            </div>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
              {selectedArticleId && articleImages.length === 0 && !generating && (
                <p className="mt-3 text-xs text-text-tertiary">
                  No generated images found for this article. You can upload images manually below.
                </p>
              )}
            </Card>

            {/* Platform Tabs (when article is selected) */}
            {generatedPosts && (
              <Card className="p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles className="h-5 w-5 text-primary-500" />
                  <h2 className="text-lg font-semibold text-text-primary">
                    Generated Posts
                  </h2>
                </div>
                <p className="text-xs text-text-secondary mb-3">
                  Switch between platforms to see and edit each generated post. The content below updates when you switch tabs.
                </p>
                <div className="flex gap-2 flex-wrap">
                  {PLATFORM_TABS.map(({ key, label }) => {
                    const hasContent = !!generatedPosts[key]?.text;
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => handlePlatformTabChange(key)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                          activePlatformTab === key
                            ? "bg-primary-500 text-white"
                            : hasContent
                            ? "bg-surface-secondary text-text-primary hover:bg-surface-tertiary"
                            : "bg-surface-secondary text-text-tertiary"
                        }`}
                      >
                        {label}
                        {hasContent && activePlatformTab !== key && (
                          <span className="ml-2 inline-block w-2 h-2 rounded-full bg-green-500" />
                        )}
                      </button>
                    );
                  })}
                </div>
              </Card>
            )}

            {/* Content Input */}
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">
                Post Content
              </h2>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="What's on your mind?"
                rows={10}
                className="w-full px-4 py-3 border border-surface-tertiary rounded-xl bg-surface-primary text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
              />
              <div className="mt-2 flex items-center justify-between">
                <p className="text-sm text-text-secondary">
                  {content.length} characters
                </p>
              </div>
            </Card>

            {/* Media Upload */}
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">
                Media
              </h2>

              {/* Media Preview */}
              {mediaItems.length > 0 && (
                <div className="grid grid-cols-2 gap-4 mb-4">
                  {mediaItems.map((item, index) => (
                    <div key={item.previewUrl} className="relative group">
                      <img
                        src={item.previewUrl}
                        alt={`Media ${index + 1}`}
                        className="w-full h-48 object-cover rounded-xl"
                      />
                      {/* Upload overlay */}
                      {item.uploading && (
                        <div className="absolute inset-0 bg-black/40 rounded-xl flex items-center justify-center">
                          <Loader2 className="h-8 w-8 text-white animate-spin" />
                        </div>
                      )}
                      {/* Error overlay */}
                      {item.error && (
                        <div className="absolute inset-0 bg-red-500/20 rounded-xl flex items-center justify-center">
                          <div className="text-center px-2">
                            <AlertCircle className="h-6 w-6 text-red-500 mx-auto mb-1" />
                            <p className="text-xs text-red-600 font-medium">Upload failed</p>
                          </div>
                        </div>
                      )}
                      {/* Success indicator */}
                      {item.remoteUrl && !item.uploading && (
                        <div className="absolute top-2 left-2">
                          <CheckCircle className="h-5 w-5 text-green-500 drop-shadow" />
                        </div>
                      )}
                      {/* Article image badge */}
                      {articleImageAttached && index === 0 && (
                        <div className="absolute bottom-2 left-2 px-2 py-1 bg-black/60 rounded text-xs text-white">
                          Article image
                        </div>
                      )}
                      <button
                        type="button"
                        aria-label="Remove media"
                        onClick={() => handleRemoveMedia(index)}
                        className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Upload Button */}
              {mediaItems.length < 4 && (
                <label className="flex items-center justify-center gap-2 p-4 border-2 border-dashed border-surface-tertiary rounded-xl hover:bg-surface-secondary transition-colors cursor-pointer">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/gif,image/webp"
                    multiple
                    onChange={handleMediaUpload}
                    className="hidden"
                  />
                  <Upload className="h-5 w-5 text-text-secondary" />
                  <span className="text-text-secondary">
                    Click to upload images
                  </span>
                </label>
              )}
              <p className="text-xs text-text-tertiary mt-2">
                Supported: JPG, PNG, GIF, WebP (max 4 images, 10 MB each)
              </p>
            </Card>

            {/* Preview */}
            {content && selectedAccountIds.length > 0 && (
              <Card className="p-6">
                <h2 className="text-lg font-semibold text-text-primary mb-4">
                  Preview
                </h2>
                <div className="space-y-6">
                  {accounts
                    .filter((a) => selectedAccountIds.includes(a.id))
                    .slice(0, 2)
                    .map((account) => (
                      <PostPreview
                        key={account.id}
                        platform={account.platform}
                        content={content}
                        mediaUrls={mediaItems.map((item) => item.previewUrl)}
                        accountName={account.platform_display_name}
                        accountUsername={account.platform_username}
                        profileImageUrl={account.profile_image_url}
                      />
                    ))}
                  {selectedAccountIds.length > 2 && (
                    <p className="text-sm text-text-secondary text-center">
                      + {selectedAccountIds.length - 2} more platform(s)
                    </p>
                  )}
                </div>
              </Card>
            )}
          </div>

          {/* Right Column - Settings */}
          <div className="space-y-6">
            {/* Platform Selection */}
            <Card className="p-6">
              <PlatformSelector
                accounts={accounts}
                selectedAccountIds={selectedAccountIds}
                onSelectionChange={setSelectedAccountIds}
                content={content}
              />
            </Card>

            {/* Schedule */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4">
                Schedule
              </h3>
              <p className="text-xs text-text-secondary mb-3">
                Set a date and time for scheduled posting, or use &quot;Publish Now&quot; to post immediately.
              </p>
              <SchedulePicker
                selectedDate={scheduledAt}
                onDateChange={setScheduledAt}
                timezone={timezone}
                onTimezoneChange={setTimezone}
              />
            </Card>

            {/* Tips */}
            <Card className="p-4 bg-blue-500/5 border-blue-500/20">
              <h4 className="text-sm font-medium text-text-primary mb-2">
                Tips for Better Engagement
              </h4>
              <ul className="text-xs text-text-secondary space-y-1 list-disc list-inside">
                <li>Use relevant hashtags (2-5 optimal)</li>
                <li>Ask questions to encourage comments</li>
                <li>Include eye-catching visuals</li>
                <li>Post during peak hours (9 AM, 12 PM, 3 PM, 6 PM)</li>
                <li>Keep it concise and valuable</li>
              </ul>
            </Card>
          </div>
        </div>
      </form>
    </div>
    </TierGate>
  );
}
