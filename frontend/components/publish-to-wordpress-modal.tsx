"use client";

import { useState, useEffect } from "react";
import { X, Loader2, CheckCircle, ExternalLink, AlertCircle } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { api, parseApiError, Article, WordPressCategory, WordPressTag } from "@/lib/api";
import { cn } from "@/lib/utils";

interface PublishToWordPressModalProps {
  article: Article;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (postUrl: string) => void;
}

export default function PublishToWordPressModal({
  article,
  isOpen,
  onClose,
  onSuccess,
}: PublishToWordPressModalProps) {
  const [status, setStatus] = useState<"draft" | "publish">("draft");
  const [selectedCategories, setSelectedCategories] = useState<number[]>([]);
  const [selectedTags, setSelectedTags] = useState<number[]>([]);

  const [categories, setCategories] = useState<WordPressCategory[]>([]);
  const [tags, setTags] = useState<WordPressTag[]>([]);

  const [loadingCategories, setLoadingCategories] = useState(false);
  const [loadingTags, setLoadingTags] = useState(false);
  const [publishing, setPublishing] = useState(false);

  const [published, setPublished] = useState(false);
  const [publishedUrl, setPublishedUrl] = useState("");

  useEffect(() => {
    if (isOpen) {
      loadCategories();
      loadTags();
      setPublished(false);
      setPublishedUrl("");
      setStatus("draft");
      setSelectedCategories([]);
      setSelectedTags([]);
    }
  }, [isOpen]);

  async function loadCategories() {
    setLoadingCategories(true);
    try {
      const data = await api.wordpress.categories();
      setCategories(data);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to load categories");
    } finally {
      setLoadingCategories(false);
    }
  }

  async function loadTags() {
    setLoadingTags(true);
    try {
      const data = await api.wordpress.tags();
      setTags(data);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to load tags");
    } finally {
      setLoadingTags(false);
    }
  }

  async function handlePublish() {
    setPublishing(true);
    try {
      const result = await api.wordpress.publish({
        article_id: article.id,
        status,
        categories: selectedCategories.length > 0 ? selectedCategories : undefined,
        tags: selectedTags.length > 0 ? selectedTags : undefined,
      });

      setPublished(true);
      setPublishedUrl(result.post_url);
      toast.success(
        status === "publish"
          ? "Article published to WordPress!"
          : "Article saved as draft on WordPress"
      );

      if (onSuccess) {
        onSuccess(result.post_url);
      }
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to publish to WordPress");
    } finally {
      setPublishing(false);
    }
  }

  function toggleCategory(id: number) {
    setSelectedCategories((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  }

  function toggleTag(id: number) {
    setSelectedTags((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]
    );
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-surface rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-surface border-b border-surface-tertiary p-6 flex items-start justify-between">
          <div className="flex-1">
            <h2 className="text-xl font-display font-bold text-text-primary">
              Publish to WordPress
            </h2>
            <p className="text-sm text-text-secondary mt-1">
              Configure and publish your article to WordPress
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
        <div className="p-6 space-y-6">
          {published ? (
            // Success State
            <div className="text-center py-8 space-y-4">
              <div className="flex justify-center">
                <div className="h-16 w-16 rounded-full bg-green-100 flex items-center justify-center">
                  <CheckCircle className="h-8 w-8 text-green-600" />
                </div>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-text-primary">
                  {status === "publish" ? "Published Successfully!" : "Saved as Draft"}
                </h3>
                <p className="text-sm text-text-secondary mt-1">
                  Your article has been {status === "publish" ? "published" : "saved"} on WordPress
                </p>
              </div>
              <a
                href={publishedUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary-50 text-primary-600 hover:bg-primary-100 transition-colors font-medium"
              >
                View on WordPress
                <ExternalLink className="h-4 w-4" />
              </a>
              <Button onClick={onClose} variant="outline" className="mt-4">
                Close
              </Button>
            </div>
          ) : (
            // Publishing Form
            <>
              {/* Article Preview */}
              <div className="p-4 rounded-xl border border-surface-tertiary bg-surface-secondary">
                <h3 className="font-semibold text-text-primary text-lg mb-2">
                  {article.title}
                </h3>
                {article.meta_description && (
                  <p className="text-sm text-text-secondary line-clamp-2">
                    {article.meta_description}
                  </p>
                )}
                <div className="flex items-center gap-3 mt-3 text-xs text-text-muted">
                  <span>{article.word_count} words</span>
                  {article.read_time && <span>{article.read_time} min read</span>}
                  <span className="px-2 py-0.5 bg-surface rounded-md">
                    {article.keyword}
                  </span>
                </div>
              </div>

              {/* Status Selector */}
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Publication Status
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => setStatus("draft")}
                    className={cn(
                      "p-4 rounded-xl border-2 transition-all text-left",
                      status === "draft"
                        ? "border-primary-500 bg-primary-50"
                        : "border-surface-tertiary hover:border-surface-tertiary/80"
                    )}
                  >
                    <div className="font-medium text-text-primary">Draft</div>
                    <div className="text-xs text-text-secondary mt-1">
                      Save as draft for review
                    </div>
                  </button>
                  <button
                    onClick={() => setStatus("publish")}
                    className={cn(
                      "p-4 rounded-xl border-2 transition-all text-left",
                      status === "publish"
                        ? "border-primary-500 bg-primary-50"
                        : "border-surface-tertiary hover:border-surface-tertiary/80"
                    )}
                  >
                    <div className="font-medium text-text-primary">Publish</div>
                    <div className="text-xs text-text-secondary mt-1">
                      Publish immediately
                    </div>
                  </button>
                </div>
              </div>

              {/* Categories */}
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Categories (Optional)
                </label>
                {loadingCategories ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
                  </div>
                ) : categories.length === 0 ? (
                  <div className="p-4 rounded-xl border border-surface-tertiary text-center text-sm text-text-muted">
                    No categories available
                  </div>
                ) : (
                  <div className="max-h-48 overflow-y-auto p-4 rounded-xl border border-surface-tertiary space-y-2">
                    {categories.map((category) => (
                      <label
                        key={category.id}
                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-secondary cursor-pointer transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={selectedCategories.includes(category.id)}
                          onChange={() => toggleCategory(category.id)}
                          className="h-4 w-4 rounded border-surface-tertiary text-primary-500 focus:ring-primary-500"
                        />
                        <span className="text-sm text-text-primary flex-1">
                          {category.name}
                        </span>
                        <span className="text-xs text-text-muted">
                          {category.count}
                        </span>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* Tags */}
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Tags (Optional)
                </label>
                {loadingTags ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
                  </div>
                ) : tags.length === 0 ? (
                  <div className="p-4 rounded-xl border border-surface-tertiary text-center text-sm text-text-muted">
                    No tags available
                  </div>
                ) : (
                  <div className="max-h-48 overflow-y-auto p-4 rounded-xl border border-surface-tertiary">
                    <div className="flex flex-wrap gap-2">
                      {tags.map((tag) => (
                        <button
                          key={tag.id}
                          onClick={() => toggleTag(tag.id)}
                          className={cn(
                            "px-3 py-1.5 rounded-lg text-sm font-medium transition-all",
                            selectedTags.includes(tag.id)
                              ? "bg-primary-500 text-white"
                              : "bg-surface-secondary text-text-primary hover:bg-surface-tertiary"
                          )}
                        >
                          {tag.name}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Info Notice */}
              <div className="p-4 rounded-xl bg-blue-50 border border-blue-200">
                <div className="flex gap-3">
                  <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0" />
                  <div className="text-sm text-blue-900">
                    <p className="font-medium">Publishing Information</p>
                    <ul className="mt-2 space-y-1 text-xs">
                      <li>The article content will be published in HTML format</li>
                      <li>Featured images must be set separately in WordPress</li>
                      <li>You can edit the post in WordPress after publishing</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <Button
                  variant="outline"
                  onClick={onClose}
                  disabled={publishing}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handlePublish}
                  isLoading={publishing}
                  className="flex-1"
                >
                  {status === "publish" ? "Publish Now" : "Save as Draft"}
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
