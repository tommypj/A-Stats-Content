"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Loader2,
  Save,
  Sparkles,
  RefreshCw,
  BarChart2,
  CheckCircle,
  AlertCircle,
  Copy,
  Eye,
  Code,
  Upload,
  ExternalLink,
  Trash2,
} from "lucide-react";
import { api, Article } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import PublishToWordPressModal from "@/components/publish-to-wordpress-modal";
import { clsx } from "clsx";
import { toast } from "sonner";

function getSeoScoreColor(score: number) {
  if (score >= 80) return "text-green-600 bg-green-100";
  if (score >= 60) return "text-yellow-600 bg-yellow-100";
  return "text-red-600 bg-red-100";
}

export default function ArticleEditorPage() {
  const params = useParams();
  const router = useRouter();
  const articleId = params.id as string;

  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [improving, setImproving] = useState(false);
  const [viewMode, setViewMode] = useState<"edit" | "preview">("edit");

  // WordPress modal state
  const [showWpModal, setShowWpModal] = useState(false);
  const [wpConnected, setWpConnected] = useState(false);
  const [checkingWpConnection, setCheckingWpConnection] = useState(true);

  // Editable fields
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [metaDescription, setMetaDescription] = useState("");
  const [keyword, setKeyword] = useState("");

  useEffect(() => {
    loadArticle();
    checkWordPressConnection();
  }, [articleId]);

  async function loadArticle() {
    try {
      setLoading(true);
      const data = await api.articles.get(articleId);
      setArticle(data);
      setTitle(data.title);
      setContent(data.content || "");
      setMetaDescription(data.meta_description || "");
      setKeyword(data.keyword);
    } catch (error) {
      console.error("Failed to load article:", error);
    } finally {
      setLoading(false);
    }
  }

  async function checkWordPressConnection() {
    try {
      setCheckingWpConnection(true);
      const status = await api.wordpress.status();
      setWpConnected(status.connected);
    } catch (error) {
      console.error("Failed to check WordPress connection:", error);
      setWpConnected(false);
    } finally {
      setCheckingWpConnection(false);
    }
  }

  async function handleSave() {
    if (!article) return;

    setSaving(true);
    try {
      const updated = await api.articles.update(article.id, {
        title,
        content,
        meta_description: metaDescription,
        keyword,
      });
      setArticle(updated);
    } catch (error) {
      console.error("Failed to save article:", error);
    } finally {
      setSaving(false);
    }
  }

  async function handleImprove(type: string) {
    if (!article) return;

    setImproving(true);
    try {
      const updated = await api.articles.improve(article.id, type);
      setArticle(updated);
      setContent(updated.content || "");
    } catch (error) {
      console.error("Failed to improve article:", error);
    } finally {
      setImproving(false);
    }
  }

  async function handleAnalyzeSeo() {
    if (!article) return;

    try {
      const updated = await api.articles.analyzeSeo(article.id);
      setArticle(updated);
    } catch (error) {
      console.error("Failed to analyze SEO:", error);
    }
  }

  async function handleDelete() {
    if (!article) return;
    if (!confirm("Are you sure you want to delete this article? This cannot be undone.")) return;

    try {
      await api.articles.delete(article.id);
      router.push("/articles");
    } catch (error) {
      console.error("Failed to delete article:", error);
      toast.error("Failed to delete article");
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard!");
  }

  function handlePublishToWordPress() {
    if (!wpConnected) {
      toast.error("Please connect to WordPress first", {
        description: "Go to Settings → Integrations to connect your WordPress site",
      });
      return;
    }
    setShowWpModal(true);
  }

  function handleWordPressPublishSuccess(postUrl: string) {
    // Reload article to get updated wordpress_post_id
    loadArticle();
    setShowWpModal(false);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!article) {
    return (
      <div className="text-center py-12">
        <p className="text-text-secondary">Article not found</p>
        <Link href="/articles" className="text-primary-600 hover:underline mt-2 inline-block">
          Back to articles
        </Link>
      </div>
    );
  }

  const seo = article.seo_analysis;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <Link
            href="/articles"
            className="p-2 rounded-lg hover:bg-surface-secondary transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-text-secondary" />
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-text-primary line-clamp-1">
              {article.title}
            </h1>
            <div className="flex items-center gap-3 mt-2 text-sm text-text-secondary">
              <span className="px-2 py-0.5 bg-surface-secondary rounded-md">
                {article.keyword}
              </span>
              <span>{article.word_count} words</span>
              {article.read_time && <span>{article.read_time} min read</span>}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* WordPress Status/Action */}
          {article.wordpress_post_url ? (
            <a
              href={article.wordpress_post_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-green-600 bg-green-50 hover:bg-green-100 transition-colors"
            >
              <CheckCircle className="h-4 w-4" />
              View on WordPress
              <ExternalLink className="h-3 w-3" />
            </a>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={handlePublishToWordPress}
              disabled={checkingWpConnection}
              leftIcon={<Upload className="h-4 w-4" />}
            >
              Publish to WordPress
            </Button>
          )}

          <div className="flex rounded-lg border border-surface-tertiary overflow-hidden">
            <button
              onClick={() => setViewMode("edit")}
              className={clsx(
                "px-3 py-1.5 text-sm font-medium transition-colors",
                viewMode === "edit"
                  ? "bg-primary-50 text-primary-600"
                  : "text-text-secondary hover:bg-surface-secondary"
              )}
            >
              <Code className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode("preview")}
              className={clsx(
                "px-3 py-1.5 text-sm font-medium transition-colors",
                viewMode === "preview"
                  ? "bg-primary-50 text-primary-600"
                  : "text-text-secondary hover:bg-surface-secondary"
              )}
            >
              <Eye className="h-4 w-4" />
            </button>
          </div>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            Save
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Editor */}
        <div className="lg:col-span-2 space-y-4">
          <Card className="p-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">
                Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all text-lg font-medium"
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">
                  Target Keyword
                </label>
                <input
                  type="text"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">
                  Meta Description
                  <span className="text-text-muted ml-2">
                    ({metaDescription.length}/160)
                  </span>
                </label>
                <input
                  type="text"
                  value={metaDescription}
                  onChange={(e) => setMetaDescription(e.target.value)}
                  maxLength={160}
                  className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
                />
              </div>
            </div>
          </Card>

          <Card className="p-4">
            {viewMode === "edit" ? (
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="w-full min-h-[500px] px-4 py-3 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all resize-none font-mono text-sm leading-relaxed"
                placeholder="Write your article content in Markdown format..."
              />
            ) : (
              <div
                className="prose prose-lg max-w-none min-h-[500px] px-4 py-3"
                dangerouslySetInnerHTML={{ __html: article.content_html || "" }}
              />
            )}
          </Card>

          {/* AI Improvement Tools */}
          <Card className="p-4">
            <h3 className="font-medium text-text-primary mb-3">AI Improvements</h3>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleImprove("seo")}
                disabled={improving}
              >
                {improving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                Improve SEO
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleImprove("readability")}
                disabled={improving}
              >
                {improving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                Improve Readability
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleImprove("engagement")}
                disabled={improving}
              >
                {improving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                Boost Engagement
              </Button>
            </div>
          </Card>
        </div>

        {/* SEO Sidebar */}
        <div className="space-y-4">
          {/* SEO Score */}
          <Card className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium text-text-primary">SEO Score</h3>
              <Button variant="ghost" size="sm" onClick={handleAnalyzeSeo}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>

            {article.seo_score !== undefined ? (
              <div className="text-center">
                <div className={clsx("inline-flex items-center justify-center w-20 h-20 rounded-full text-2xl font-bold", getSeoScoreColor(article.seo_score))}>
                  {Math.round(article.seo_score)}
                </div>
                <p className="text-sm text-text-secondary mt-2">
                  {article.seo_score >= 80
                    ? "Great SEO optimization!"
                    : article.seo_score >= 60
                    ? "Good, but can be improved"
                    : "Needs improvement"}
                </p>
              </div>
            ) : (
              <p className="text-sm text-text-muted text-center py-4">
                Click refresh to analyze SEO
              </p>
            )}
          </Card>

          {/* SEO Analysis Details */}
          {seo && (
            <Card className="p-4">
              <h3 className="font-medium text-text-primary mb-3">SEO Analysis</h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Keyword Density</span>
                  <span className={clsx(
                    "font-medium",
                    seo.keyword_density >= 1 && seo.keyword_density <= 3
                      ? "text-green-600"
                      : "text-yellow-600"
                  )}>
                    {seo.keyword_density.toFixed(1)}%
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Title Has Keyword</span>
                  {seo.title_has_keyword ? (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-yellow-600" />
                  )}
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Meta Description</span>
                  <span className={clsx(
                    "font-medium",
                    seo.meta_description_length >= 120 && seo.meta_description_length <= 160
                      ? "text-green-600"
                      : "text-yellow-600"
                  )}>
                    {seo.meta_description_length} chars
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Headings</span>
                  <span className="text-text-primary">
                    {seo.h2_count} H2, {seo.h3_count} H3
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Links</span>
                  <span className="text-text-primary">
                    {seo.internal_links} internal, {seo.external_links} external
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Readability</span>
                  <span className={clsx(
                    "font-medium",
                    seo.readability_score >= 60 ? "text-green-600" : "text-yellow-600"
                  )}>
                    {seo.readability_score.toFixed(0)}
                  </span>
                </div>
              </div>
            </Card>
          )}

          {/* Suggestions */}
          {seo?.suggestions && seo.suggestions.length > 0 && (
            <Card className="p-4">
              <h3 className="font-medium text-text-primary mb-3">Suggestions</h3>
              <ul className="space-y-2">
                {seo.suggestions.map((suggestion, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm text-text-secondary">
                    <AlertCircle className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                    {suggestion}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* Quick Actions */}
          <Card className="p-4">
            <h3 className="font-medium text-text-primary mb-3">Quick Actions</h3>
            <div className="space-y-2">
              <button
                onClick={() => copyToClipboard(content)}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-text-secondary hover:bg-surface-secondary transition-colors"
              >
                <Copy className="h-4 w-4" />
                Copy Content
              </button>
              <button
                onClick={() => copyToClipboard(article.content_html || "")}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-text-secondary hover:bg-surface-secondary transition-colors"
              >
                <Code className="h-4 w-4" />
                Copy HTML
              </button>
              <button
                onClick={handleDelete}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-red-600 hover:bg-red-50 transition-colors"
              >
                <Trash2 className="h-4 w-4" />
                Delete Article
              </button>
            </div>
          </Card>
        </div>
      </div>

      {/* WordPress Publish Modal */}
      {article && (
        <PublishToWordPressModal
          article={article}
          isOpen={showWpModal}
          onClose={() => setShowWpModal(false)}
          onSuccess={handleWordPressPublishSuccess}
        />
      )}
    </div>
  );
}
