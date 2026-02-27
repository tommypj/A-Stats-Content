"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { api, SocialAccount, parseApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PlatformSelector } from "@/components/social/platform-selector";
import { PostPreview } from "@/components/social/post-preview";
import { SchedulePicker } from "@/components/social/schedule-picker";
import {
  Image as ImageIcon,
  X,
  AlertCircle,
  CheckCircle,
  Upload,
} from "lucide-react";
import { toast } from "sonner";

const DRAFT_KEY = "social_compose_draft";

export default function ComposePage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [content, setContent] = useState("");
  const [mediaUrls, setMediaUrls] = useState<string[]>([]);
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>([]);
  const [scheduledAt, setScheduledAt] = useState(
    new Date(Date.now() + 3600000).toISOString() // Default to 1 hour from now
  );
  const [timezone, setTimezone] = useState(() => {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch {
      return "America/New_York";
    }
  });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const blobUrlsRef = useRef<string[]>([]);

  // Revoke all blob URLs on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      blobUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    };
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
        // selectedAccountIds restored after accounts load
        toast.info("Draft restored");
      }
    } catch {
      // ignore corrupt draft
    }
  }, []);

  // Auto-save draft to localStorage (debounced 500ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (!content && selectedAccountIds.length === 0) return;
      try {
        localStorage.setItem(
          DRAFT_KEY,
          JSON.stringify({ content, selectedAccountIds, scheduledAt, timezone })
        );
      } catch {
        // storage full — ignore
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [content, selectedAccountIds, scheduledAt, timezone]);

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      setLoading(true);
      const res = await api.social.accounts();
      const connected = res.accounts.filter((a) => a.is_connected);
      setAccounts(connected);

      // Restore draft account selection, or auto-select all connected
      const connectedIds = connected.map((a) => a.id);
      try {
        const raw = localStorage.getItem(DRAFT_KEY);
        if (raw) {
          const draft = JSON.parse(raw);
          if (Array.isArray(draft.selectedAccountIds)) {
            const valid = draft.selectedAccountIds.filter((id: string) => connectedIds.includes(id));
            if (valid.length > 0) {
              setSelectedAccountIds(valid);
              return;
            }
          }
        }
      } catch {
        // ignore
      }
      setSelectedAccountIds(connectedIds);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    // Validation
    if (!content.trim()) {
      setError("Please enter some content for your post");
      return;
    }

    if (selectedAccountIds.length === 0) {
      setError("Please select at least one platform");
      return;
    }

    try {
      setSubmitting(true);

      // Filter out blob: URLs — only send actual remote URLs to the backend
      const remoteMediaUrls = mediaUrls.filter((url) => !url.startsWith("blob:"));
      const blobCount = mediaUrls.length - remoteMediaUrls.length;
      if (blobCount > 0) {
        toast.error("Image upload failed — post will be sent without images");
      }

      await api.social.createPost({
        content,
        media_urls: remoteMediaUrls.length > 0 ? remoteMediaUrls : undefined,
        scheduled_at: scheduledAt,
        platforms: accounts
          .filter((a) => selectedAccountIds.includes(a.id))
          .map((a) => a.platform),
        account_ids: selectedAccountIds,
      });

      localStorage.removeItem(DRAFT_KEY);
      setSuccess(true);
      setTimeout(() => {
        router.push("/social");
      }, 2000);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleMediaUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    if (mediaUrls.length + files.length > 4) {
      setError("Maximum 4 media files allowed");
      return;
    }

    // Create object URLs for preview display
    // Note: blob URLs are for local preview only and are filtered out before API submission
    const urls = Array.from(files).map((file) => URL.createObjectURL(file));
    blobUrlsRef.current.push(...urls);
    setMediaUrls([...mediaUrls, ...urls]);
  };

  const handleRemoveMedia = (index: number) => {
    const removed = mediaUrls[index];
    if (removed?.startsWith("blob:")) {
      URL.revokeObjectURL(removed);
    }
    setMediaUrls(mediaUrls.filter((_, i) => i !== index));
  };

  const getSelectedAccount = () => {
    if (selectedAccountIds.length === 0) return null;
    return accounts.find((a) => a.id === selectedAccountIds[0]);
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-10 bg-surface-secondary rounded w-1/3" />
          <div className="h-64 bg-surface-secondary rounded-xl" />
        </div>
      </div>
    );
  }

  if (accounts.length === 0) {
    return (
      <div className="container mx-auto p-6">
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
    <div className="container mx-auto p-6">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-text-primary">Create Post</h1>
            <p className="text-text-secondary mt-1">
              Compose and schedule your social media post
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
            <Button type="submit" isLoading={submitting}>
              {submitting ? "Publishing..." : "Schedule Post"}
            </Button>
          </div>
        </div>

        {/* Success Message */}
        {success && (
          <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-xl flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-green-500" />
            <div>
              <p className="text-green-600 font-medium">Post scheduled successfully!</p>
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
              {mediaUrls.length > 0 && (
                <div className="grid grid-cols-2 gap-4 mb-4">
                  {mediaUrls.map((url, index) => (
                    <div key={url} className="relative group">
                      <img
                        src={url}
                        alt={`Media ${index + 1}`}
                        className="w-full h-48 object-cover rounded-xl"
                      />
                      <button
                        type="button"
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
              <label className="flex items-center justify-center gap-2 p-4 border-2 border-dashed border-surface-tertiary rounded-xl hover:bg-surface-secondary transition-colors cursor-pointer">
                <input
                  type="file"
                  accept="image/*,video/*"
                  multiple
                  onChange={handleMediaUpload}
                  className="hidden"
                />
                <Upload className="h-5 w-5 text-text-secondary" />
                <span className="text-text-secondary">
                  Click to upload images or videos
                </span>
              </label>
              <p className="text-xs text-text-tertiary mt-2">
                Supported: JPG, PNG, GIF, MP4 (max 4 files)
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
                        mediaUrls={mediaUrls}
                        accountName={account.display_name}
                        accountUsername={account.username}
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
  );
}
