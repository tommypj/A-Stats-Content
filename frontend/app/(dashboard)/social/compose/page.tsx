"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, SocialAccount, parseApiError } from "@/lib/api";
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
              disabled={submitting || anyUploading}
              isLoading={submitting && !createPostMutation.variables?.publish_now}
              leftIcon={<Clock className="h-4 w-4" />}
            >
              Schedule Post
            </Button>
            <Button
              type="button"
              onClick={handlePublishNow}
              disabled={submitting || anyUploading}
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
