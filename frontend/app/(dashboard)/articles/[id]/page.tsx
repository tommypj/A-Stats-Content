"use client";

import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
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
  Share2,
  Bold,
  Italic,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  Link as LinkIcon,
  Link2,
  Quote,
  Search,
  History,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  XCircle,
  TrendingUp,
  Download,
} from "lucide-react";
import { api, Article, ArticleRevision, ArticleRevisionDetail, LinkSuggestion } from "@/lib/api";
import { calculateSEOScore, SEOScore } from "@/lib/seo-score";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import PublishToWordPressModal from "@/components/publish-to-wordpress-modal";
import SocialPostsModal from "@/components/social-posts-modal";
import { clsx } from "clsx";
import { toast } from "sonner";
import DOMPurify from "dompurify";
import { marked } from "marked";

// ---------------------------------------------------------------------------
// Word Count Widget — live word count, optional target + progress bar
// ---------------------------------------------------------------------------

interface WordCountWidgetProps {
  content: string;
  target: number | "";
  onTargetChange: (value: number | "") => void;
}

function getWordCount(text: string): number {
  return text.trim() === "" ? 0 : text.trim().split(/\s+/).length;
}

function getProgressColor(pct: number): string {
  if (pct >= 100) return "bg-blue-500";
  if (pct >= 75) return "bg-green-500";
  if (pct >= 50) return "bg-yellow-500";
  if (pct >= 25) return "bg-orange-500";
  return "bg-red-500";
}

function getProgressTextColor(pct: number): string {
  if (pct >= 100) return "text-blue-600";
  if (pct >= 75) return "text-green-600";
  if (pct >= 50) return "text-yellow-600";
  if (pct >= 25) return "text-orange-600";
  return "text-red-600";
}

function WordCountWidget({ content, target, onTargetChange }: WordCountWidgetProps) {
  const wordCount = getWordCount(content);
  const readingTime = Math.max(1, Math.round(wordCount / 200));
  const hasTarget = target !== "" && target > 0;
  const pct = hasTarget ? Math.round((wordCount / (target as number)) * 100) : 0;
  const clampedPct = Math.min(pct, 100);

  return (
    <div className="bg-white rounded-xl border border-surface-tertiary p-4 space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-text-primary">Word Count</p>
        <span className="text-xs text-text-muted">{readingTime} min read</span>
      </div>

      {/* Current count */}
      <div className="flex items-baseline gap-1.5">
        <span className={clsx("text-2xl font-bold tabular-nums", hasTarget ? getProgressTextColor(pct) : "text-text-primary")}>
          {wordCount.toLocaleString()}
        </span>
        {hasTarget && (
          <span className="text-sm text-text-muted">
            / {(target as number).toLocaleString()} words
          </span>
        )}
        {!hasTarget && (
          <span className="text-sm text-text-muted">words</span>
        )}
      </div>

      {/* Progress bar */}
      {hasTarget && (
        <div className="space-y-1">
          <div className="w-full h-2 bg-surface-secondary rounded-full overflow-hidden">
            <div
              className={clsx("h-full rounded-full transition-all duration-300", getProgressColor(pct))}
              style={{ width: `${clampedPct}%` }}
            />
          </div>
          <p className="text-xs text-text-muted tabular-nums">
            {pct}% of target
            {pct >= 100 && <span className="ml-1 text-blue-600 font-medium">— target reached!</span>}
          </p>
        </div>
      )}

      {/* Target input */}
      <div>
        <label className="block text-xs font-medium text-text-secondary mb-1">
          Target word count
        </label>
        <input
          type="number"
          min={0}
          placeholder="e.g. 1500"
          value={target}
          onChange={(e) => {
            const val = e.target.value;
            onTargetChange(val === "" ? "" : Math.max(0, parseInt(val, 10) || 0));
          }}
          className="w-full px-3 py-1.5 rounded-lg border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all text-sm"
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SERP Preview — purely visual, no API calls
// ---------------------------------------------------------------------------
const TITLE_LIMIT = 60;
const DESC_LIMIT = 160;
const DESC_WARN_MIN = 120;

function highlightKeyword(text: string, keyword: string): React.ReactNode {
  if (!keyword.trim()) return text;
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, "gi"));
  return parts.map((part, i) =>
    part.toLowerCase() === keyword.toLowerCase() ? (
      <span key={i} className="font-semibold">
        {part}
      </span>
    ) : (
      part
    )
  );
}

interface SerpPreviewProps {
  title: string;
  slug: string;
  metaDescription: string;
  keyword: string;
}

function SerpPreview({ title, slug, metaDescription, keyword }: SerpPreviewProps) {
  const displayTitle = title.length > TITLE_LIMIT ? title.slice(0, TITLE_LIMIT) + "..." : title;
  const titleLen = title.length;
  const titleOver = titleLen > TITLE_LIMIT;

  const displayDesc =
    metaDescription.length > DESC_LIMIT
      ? metaDescription.slice(0, DESC_LIMIT) + "..."
      : metaDescription;
  const descLen = metaDescription.length;
  const descOver = descLen > DESC_LIMIT;
  const descUnder = descLen > 0 && descLen < DESC_WARN_MIN;

  const breadcrumb = `yoursite.com › blog › ${slug || "article-slug"}`;

  return (
    <div className="bg-white rounded-xl border border-surface-tertiary p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Eye className="h-4 w-4 text-text-muted flex-shrink-0" />
        <div>
          <p className="text-sm font-medium text-text-primary leading-tight">SERP Preview</p>
          <p className="text-xs text-text-muted leading-tight">
            How your article may appear in Google search results
          </p>
        </div>
      </div>

      {/* Decorative search bar */}
      <div className="flex items-center gap-2 px-3 py-2 rounded-full border border-surface-tertiary bg-surface-secondary">
        <Search className="h-3.5 w-3.5 text-text-muted flex-shrink-0" />
        <span className="text-xs text-text-muted truncate">{keyword || "search query..."}</span>
      </div>

      {/* Google-style result card */}
      <div className="rounded-lg border border-surface-tertiary bg-white px-4 py-3 space-y-0.5 shadow-sm">
        {/* URL breadcrumb */}
        <p className="text-xs text-green-700 truncate">{breadcrumb}</p>

        {/* Title */}
        <p className="text-base font-medium text-blue-700 leading-snug line-clamp-2">
          {displayTitle
            ? highlightKeyword(displayTitle, keyword)
            : <span className="text-text-muted italic">No title yet</span>}
        </p>

        {/* Meta description */}
        <p className="text-xs text-text-secondary leading-relaxed line-clamp-2 mt-0.5">
          {displayDesc
            ? highlightKeyword(displayDesc, keyword)
            : <span className="text-text-muted italic">No meta description yet</span>}
        </p>
      </div>

      {/* Character counters */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-muted">Title length</span>
          <span className={clsx("font-medium tabular-nums", titleOver ? "text-red-500" : titleLen >= 50 ? "text-green-600" : "text-text-secondary")}>
            {titleLen} / {TITLE_LIMIT}
            {titleOver && <span className="ml-1">— too long</span>}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-muted">Description length</span>
          <span className={clsx(
            "font-medium tabular-nums",
            descOver
              ? "text-red-500"
              : descUnder
              ? "text-yellow-600"
              : descLen >= DESC_WARN_MIN
              ? "text-green-600"
              : "text-text-secondary"
          )}>
            {descLen} / {DESC_LIMIT}
            {descOver && <span className="ml-1">— too long</span>}
            {descUnder && <span className="ml-1">— too short</span>}
          </span>
        </div>
      </div>
    </div>
  );
}

function getSeoScoreColor(score: number) {
  if (score >= 80) return "text-green-600 bg-green-100";
  if (score >= 60) return "text-yellow-600 bg-yellow-100";
  return "text-red-600 bg-red-100";
}

// ---------------------------------------------------------------------------
// Live SEO Score Panel — client-side, no API calls, debounced 500 ms
// ---------------------------------------------------------------------------

function getLiveScoreRingColor(score: number): string {
  if (score >= 80) return "stroke-green-500";
  if (score >= 50) return "stroke-yellow-500";
  return "stroke-red-500";
}

function getLiveScoreTextColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 50) return "text-yellow-600";
  return "text-red-600";
}

function getLiveScoreLabel(score: number): string {
  if (score >= 80) return "Great";
  if (score >= 50) return "Needs work";
  return "Poor";
}

interface LiveSeoPanelProps {
  seoScore: SEOScore;
}

function LiveSeoPanel({ seoScore }: LiveSeoPanelProps) {
  const [expanded, setExpanded] = useState(true);

  const { overall, checks } = seoScore;
  const passedCount = checks.filter((c) => c.passed).length;
  const total = checks.length;

  // SVG ring — 80 px circle, r=34 gives circumference ≈ 213.6
  const RADIUS = 34;
  const CIRC = 2 * Math.PI * RADIUS;
  const offset = CIRC - (overall / 100) * CIRC;

  return (
    <Card className="p-4">
      {/* Collapsible header */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-text-secondary" />
          <span className="font-medium text-text-primary text-sm">Live SEO Score</span>
          <span
            className={clsx(
              "text-xs font-semibold px-1.5 py-0.5 rounded-full",
              overall >= 80
                ? "bg-green-100 text-green-700"
                : overall >= 50
                ? "bg-yellow-100 text-yellow-700"
                : "bg-red-100 text-red-700"
            )}
          >
            {overall}
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-text-muted flex-shrink-0" />
        ) : (
          <ChevronDown className="h-4 w-4 text-text-muted flex-shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="mt-4 space-y-4">
          {/* Score ring */}
          <div className="flex items-center gap-4">
            <div className="relative flex-shrink-0">
              <svg width="80" height="80" viewBox="0 0 80 80">
                {/* Track */}
                <circle
                  cx="40"
                  cy="40"
                  r={RADIUS}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="8"
                  className="text-surface-secondary"
                />
                {/* Progress arc */}
                <circle
                  cx="40"
                  cy="40"
                  r={RADIUS}
                  fill="none"
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray={CIRC}
                  strokeDashoffset={offset}
                  className={clsx("transition-all duration-500", getLiveScoreRingColor(overall))}
                  transform="rotate(-90 40 40)"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className={clsx("text-xl font-bold leading-none", getLiveScoreTextColor(overall))}>
                  {overall}
                </span>
                <span className="text-xs text-text-muted leading-none mt-0.5">/ 100</span>
              </div>
            </div>

            <div className="flex-1 min-w-0">
              <p className={clsx("text-sm font-semibold", getLiveScoreTextColor(overall))}>
                {getLiveScoreLabel(overall)}
              </p>
              <p className="text-xs text-text-muted mt-0.5">
                {passedCount} of {total} checks passed
              </p>
              {/* Mini progress bar */}
              <div className="mt-2 h-1.5 bg-surface-secondary rounded-full overflow-hidden">
                <div
                  className={clsx(
                    "h-full rounded-full transition-all duration-500",
                    overall >= 80
                      ? "bg-green-500"
                      : overall >= 50
                      ? "bg-yellow-500"
                      : "bg-red-500"
                  )}
                  style={{ width: `${overall}%` }}
                />
              </div>
            </div>
          </div>

          {/* Checklist */}
          <div className="space-y-2">
            {checks.map((check, i) => (
              <div key={i}>
                <div className="flex items-start gap-2">
                  {check.passed ? (
                    <CheckCircle className="h-3.5 w-3.5 text-green-500 flex-shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 text-red-400 flex-shrink-0 mt-0.5" />
                  )}
                  <span
                    className={clsx(
                      "text-xs leading-snug",
                      check.passed ? "text-text-secondary" : "text-text-primary font-medium"
                    )}
                  >
                    {check.label}
                  </span>
                </div>
                {/* Tip shown only for failed checks */}
                {!check.passed && check.tip && (
                  <p className="ml-5 text-xs text-text-muted leading-snug mt-0.5">
                    {check.tip}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

function formatRevisionType(revisionType: string): string {
  const labels: Record<string, string> = {
    manual_edit: "Manual Edit",
    before_ai_improve_seo: "Before AI Improve (SEO)",
    before_ai_improve_readability: "Before AI Improve (Readability)",
    before_ai_improve_engagement: "Before AI Improve (Engagement)",
    before_ai_improve_grammar: "Before AI Improve (Grammar)",
    restore: "Restore Backup",
  };
  return labels[revisionType] ?? revisionType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
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

  // Social posts modal state
  const [showSocialModal, setShowSocialModal] = useState(false);
  const [featuredImageUrl, setFeaturedImageUrl] = useState<string | undefined>(undefined);

  // WordPress modal state
  const [showWpModal, setShowWpModal] = useState(false);
  const [wpConnected, setWpConnected] = useState(false);
  const [checkingWpConnection, setCheckingWpConnection] = useState(true);

  // Editable fields
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [metaDescription, setMetaDescription] = useState("");
  const [keyword, setKeyword] = useState("");

  // Word count target (UI-only, not persisted)
  const [wordCountTarget, setWordCountTarget] = useState<number | "">("");

  // Markdown toolbar
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lastSavedContentRef = useRef<string>("");
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [autoSaveStatus, setAutoSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  // Version history panel state
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [revisions, setRevisions] = useState<ArticleRevision[]>([]);
  const [revisionsTotal, setRevisionsTotal] = useState(0);
  const [loadingRevisions, setLoadingRevisions] = useState(false);
  const [previewRevision, setPreviewRevision] = useState<ArticleRevisionDetail | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [restoringRevisionId, setRestoringRevisionId] = useState<string | null>(null);

  // Internal link suggestions panel state
  const [showLinkSuggestions, setShowLinkSuggestions] = useState(false);
  const [linkSuggestions, setLinkSuggestions] = useState<LinkSuggestion[]>([]);
  const [loadingLinks, setLoadingLinks] = useState(false);

  // Export dropdown state
  const [showExportMenu, setShowExportMenu] = useState(false);

  // Confirmation dialog state
  const [confirmAction, setConfirmAction] = useState<{ action: () => void; title: string; message: string; confirmLabel?: string; variant?: "danger" | "warning" | "default" } | null>(null);

  // Live SEO score — debounced 500 ms to avoid recalculating on every keystroke
  const [debouncedSeoInput, setDebouncedSeoInput] = useState({ title: "", content: "", keyword: "", metaDescription: "" });
  const seoDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (seoDebounceRef.current) clearTimeout(seoDebounceRef.current);
    seoDebounceRef.current = setTimeout(() => {
      setDebouncedSeoInput({ title, content, keyword, metaDescription });
    }, 500);
    return () => {
      if (seoDebounceRef.current) clearTimeout(seoDebounceRef.current);
    };
  }, [title, content, keyword, metaDescription]);

  const liveSeoScore = useMemo(
    () =>
      calculateSEOScore({
        title: debouncedSeoInput.title,
        content: debouncedSeoInput.content,
        keyword: debouncedSeoInput.keyword,
        meta_description: debouncedSeoInput.metaDescription,
      }),
    [debouncedSeoInput]
  );

  // Escape key exits preview mode
  useEffect(() => {
    if (viewMode !== "preview") return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setViewMode("edit");
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [viewMode]);

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
      lastSavedContentRef.current = data.content || "";

      // Fetch featured image URL if article has one
      if (data.featured_image_id) {
        try {
          const image = await api.images.get(data.featured_image_id);
          setFeaturedImageUrl(image.url);
        } catch {
          // Non-critical — featured image preview is optional
        }
      }
    } catch (error) {
      toast.error("Failed to load article. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function checkWordPressConnection() {
    try {
      setCheckingWpConnection(true);
      const status = await api.wordpress.status();
      setWpConnected(status.is_connected);
    } catch (error) {
      toast.error("Failed to check WordPress connection.");
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
      toast.error("Failed to save changes.");
    } finally {
      setSaving(false);
    }
  }

  // Keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: "s",
      ctrl: true,
      handler: () => {
        if (article && !saving) handleSave();
      },
    },
    {
      key: "p",
      ctrl: true,
      shift: true,
      handler: () => {
        if (wpConnected) setShowWpModal(true);
      },
    },
  ]);

  async function handleImprove(type: string) {
    if (!article) return;

    setImproving(true);
    try {
      const updated = await api.articles.improve(article.id, type);
      setArticle(updated);
      setContent(updated.content || "");
    } catch (error) {
      toast.error("AI improvement failed. Please try again.");
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
      toast.error("SEO analysis failed. Please try again.");
    }
  }

  function handleDelete() {
    if (!article) return;
    setConfirmAction({
      action: async () => {
        try {
          await api.articles.delete(article.id);
          router.push("/articles");
        } catch (error) {
          toast.error("Failed to delete article");
        }
      },
      title: "Delete Article",
      message: "Are you sure you want to delete this article? This cannot be undone.",
      confirmLabel: "Delete",
      variant: "danger",
    });
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard!");
  }

  // Markdown toolbar helpers
  const insertMarkdown = useCallback((prefix: string, suffix: string) => {
    const ta = textareaRef.current;
    if (!ta) return;

    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const selected = content.slice(start, end);
    const placeholder = selected || "text";
    const replacement = prefix + placeholder + suffix;

    const newContent =
      content.slice(0, start) + replacement + content.slice(end);
    setContent(newContent);

    // Restore cursor: if no selection, place cursor inside the inserted syntax
    const cursorStart = start + prefix.length;
    const cursorEnd = cursorStart + placeholder.length;
    requestAnimationFrame(() => {
      ta.focus();
      ta.setSelectionRange(cursorStart, cursorEnd);
    });
  }, [content]);

  const insertLinePrefix = useCallback((prefix: string) => {
    const ta = textareaRef.current;
    if (!ta) return;

    const pos = ta.selectionStart;
    // Find the beginning of the current line
    const lineStart = content.lastIndexOf("\n", pos - 1) + 1;

    const newContent =
      content.slice(0, lineStart) + prefix + content.slice(lineStart);
    setContent(newContent);

    const newCursor = pos + prefix.length;
    requestAnimationFrame(() => {
      ta.focus();
      ta.setSelectionRange(newCursor, newCursor);
    });
  }, [content]);

  // Auto-save: debounce 3 s after last keystroke (tracks all editable fields)
  const lastSavedSnapshotRef = useRef("");
  useEffect(() => {
    if (!article) return;
    const snapshot = JSON.stringify({ content, title, metaDescription, keyword });
    if (snapshot === lastSavedSnapshotRef.current) return;

    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }

    autoSaveTimerRef.current = setTimeout(async () => {
      const currentSnapshot = JSON.stringify({ content, title, metaDescription, keyword });
      if (currentSnapshot === lastSavedSnapshotRef.current) return;
      setAutoSaveStatus("saving");
      try {
        await api.articles.update(article.id, {
          title,
          content,
          meta_description: metaDescription,
          keyword,
        });
        lastSavedSnapshotRef.current = currentSnapshot;
        lastSavedContentRef.current = content;
        setAutoSaveStatus("saved");
        setTimeout(() => setAutoSaveStatus("idle"), 2000);
      } catch {
        setAutoSaveStatus("error");
        setTimeout(() => setAutoSaveStatus("idle"), 3000);
      }
    }, 3000);

    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, [content, article, title, metaDescription, keyword]);

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

  async function handleToggleVersionHistory() {
    const nextOpen = !showVersionHistory;
    setShowVersionHistory(nextOpen);
    // Lazy-load the first page of revisions when opening for the first time
    if (nextOpen && revisions.length === 0) {
      await loadRevisions();
    }
  }

  async function loadRevisions() {
    if (!article) return;
    setLoadingRevisions(true);
    try {
      const data = await api.articles.listRevisions(article.id, { page: 1, page_size: 20 });
      setRevisions(data.items);
      setRevisionsTotal(data.total);
    } catch (error) {
      toast.error("Failed to load version history");
    } finally {
      setLoadingRevisions(false);
    }
  }

  async function handlePreviewRevision(revisionId: string) {
    if (!article) return;
    // Toggle off if already previewing this revision
    if (previewRevision?.id === revisionId) {
      setPreviewRevision(null);
      return;
    }
    setLoadingPreview(true);
    try {
      const detail = await api.articles.getRevision(article.id, revisionId);
      setPreviewRevision(detail);
    } catch (error) {
      toast.error("Failed to load revision content");
    } finally {
      setLoadingPreview(false);
    }
  }

  function handleRestoreRevision(revisionId: string) {
    if (!article) return;
    setConfirmAction({
      action: async () => {
        setRestoringRevisionId(revisionId);
        try {
          const updated = await api.articles.restoreRevision(article.id, revisionId);
          setArticle(updated);
          setTitle(updated.title);
          setContent(updated.content || "");
          setMetaDescription(updated.meta_description || "");
          lastSavedContentRef.current = updated.content || "";
          setPreviewRevision(null);
          // Refresh revision list to include the new "restore" backup revision
          await loadRevisions();
          toast.success("Article restored to selected version");
        } catch (error) {
          toast.error("Failed to restore revision");
        } finally {
          setRestoringRevisionId(null);
        }
      },
      title: "Restore Version",
      message: "Restore this version? The current content will be saved as a backup revision first.",
      confirmLabel: "Restore",
      variant: "warning",
    });
  }

  async function handleToggleLinkSuggestions() {
    const nextOpen = !showLinkSuggestions;
    setShowLinkSuggestions(nextOpen);
    // Lazy-load suggestions only when opening for the first time
    if (nextOpen && linkSuggestions.length === 0) {
      setLoadingLinks(true);
      try {
        const data = await api.articles.linkSuggestions(articleId);
        setLinkSuggestions(data.suggestions);
      } catch (error) {
        toast.error("Failed to load link suggestions");
      } finally {
        setLoadingLinks(false);
      }
    }
  }

  function handleInsertLink(suggestion: LinkSuggestion) {
    const slug = suggestion.slug || suggestion.id;
    insertMarkdown(`[${suggestion.title}](/${slug})`, "");
  }

  async function handleExport(format: "markdown" | "html" | "csv") {
    if (!article) return;
    setShowExportMenu(false);
    try {
      const response = await api.articles.exportOne(article.id, format);
      const ext = format === "markdown" ? "md" : format;
      const safeTitle = article.title.replace(/[^\w\-]/g, "_").slice(0, 80);
      const filename = `${safeTitle}.${ext}`;
      const url = window.URL.createObjectURL(response.data as Blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success(`Article exported as ${format.toUpperCase()}`);
    } catch {
      toast.error("Failed to export article");
    }
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
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="flex items-start gap-4 min-w-0">
          <Link
            href="/articles"
            className="p-2 rounded-lg hover:bg-surface-secondary transition-colors flex-shrink-0"
          >
            <ArrowLeft className="h-5 w-5 text-text-secondary" />
          </Link>
          <div className="min-w-0">
            <h1 className="text-2xl font-display font-bold text-text-primary line-clamp-2">
              {article.title}
            </h1>
            <div className="flex flex-wrap items-center gap-2 mt-2 text-sm text-text-secondary">
              <span className="px-2 py-0.5 bg-surface-secondary rounded-md">
                {article.keyword}
              </span>
              <span>{article.word_count} words</span>
              {article.read_time && <span>{article.read_time} min read</span>}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:flex-shrink-0">
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

          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSocialModal(true)}
            disabled={!article.published_url && !article.wordpress_post_url}
            title={!article.published_url && !article.wordpress_post_url ? "Publish to WordPress first" : "Share on social media"}
            leftIcon={<Share2 className="h-4 w-4" />}
          >
            Share
          </Button>

          {/* Export dropdown */}
          <div className="relative">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowExportMenu((prev) => !prev)}
              leftIcon={<Download className="h-4 w-4" />}
            >
              Export
              <ChevronDown className="h-3 w-3 ml-1" />
            </Button>
            {showExportMenu && (
              <div className="absolute right-0 top-full mt-1 z-50 w-40 rounded-xl border border-surface-tertiary bg-surface shadow-lg py-1">
                <button
                  onClick={() => handleExport("markdown")}
                  className="w-full text-left px-4 py-2 text-sm text-text-primary hover:bg-surface-secondary transition-colors"
                >
                  Markdown (.md)
                </button>
                <button
                  onClick={() => handleExport("html")}
                  className="w-full text-left px-4 py-2 text-sm text-text-primary hover:bg-surface-secondary transition-colors"
                >
                  HTML (.html)
                </button>
                <button
                  onClick={() => handleExport("csv")}
                  className="w-full text-left px-4 py-2 text-sm text-text-primary hover:bg-surface-secondary transition-colors"
                >
                  CSV (.csv)
                </button>
              </div>
            )}
          </div>

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
              <div>
                {/* Markdown toolbar */}
                <div className="flex items-center gap-1 p-2 bg-surface-secondary rounded-t-xl border border-surface-tertiary border-b-0">
                  {/* Inline formatting group */}
                  <button
                    type="button"
                    title="Bold"
                    onClick={() => insertMarkdown("**", "**")}
                    className="p-1.5 rounded-lg hover:bg-surface-tertiary text-text-secondary hover:text-text-primary transition-colors"
                  >
                    <Bold className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    title="Italic"
                    onClick={() => insertMarkdown("*", "*")}
                    className="p-1.5 rounded-lg hover:bg-surface-tertiary text-text-secondary hover:text-text-primary transition-colors"
                  >
                    <Italic className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    title="Inline Code"
                    onClick={() => insertMarkdown("`", "`")}
                    className="p-1.5 rounded-lg hover:bg-surface-tertiary text-text-secondary hover:text-text-primary transition-colors"
                  >
                    <Code className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    title="Link"
                    onClick={() => insertMarkdown("[", "](url)")}
                    className="p-1.5 rounded-lg hover:bg-surface-tertiary text-text-secondary hover:text-text-primary transition-colors"
                  >
                    <LinkIcon className="h-4 w-4" />
                  </button>

                  <div className="w-px h-5 bg-surface-tertiary mx-1" />

                  {/* Block / heading group */}
                  <button
                    type="button"
                    title="Heading 2"
                    onClick={() => insertLinePrefix("## ")}
                    className="p-1.5 rounded-lg hover:bg-surface-tertiary text-text-secondary hover:text-text-primary transition-colors"
                  >
                    <Heading2 className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    title="Heading 3"
                    onClick={() => insertLinePrefix("### ")}
                    className="p-1.5 rounded-lg hover:bg-surface-tertiary text-text-secondary hover:text-text-primary transition-colors"
                  >
                    <Heading3 className="h-4 w-4" />
                  </button>

                  <div className="w-px h-5 bg-surface-tertiary mx-1" />

                  {/* List group */}
                  <button
                    type="button"
                    title="Bullet List"
                    onClick={() => insertLinePrefix("- ")}
                    className="p-1.5 rounded-lg hover:bg-surface-tertiary text-text-secondary hover:text-text-primary transition-colors"
                  >
                    <List className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    title="Numbered List"
                    onClick={() => insertLinePrefix("1. ")}
                    className="p-1.5 rounded-lg hover:bg-surface-tertiary text-text-secondary hover:text-text-primary transition-colors"
                  >
                    <ListOrdered className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    title="Blockquote"
                    onClick={() => insertLinePrefix("> ")}
                    className="p-1.5 rounded-lg hover:bg-surface-tertiary text-text-secondary hover:text-text-primary transition-colors"
                  >
                    <Quote className="h-4 w-4" />
                  </button>

                  {/* Auto-save status — pushed to far right */}
                  <div className="ml-auto flex items-center gap-1.5 text-xs text-text-muted pr-1 select-none">
                    {autoSaveStatus === "saving" && (
                      <>
                        <Loader2 className="h-3 w-3 animate-spin" />
                        <span>Saving...</span>
                      </>
                    )}
                    {autoSaveStatus === "saved" && (
                      <>
                        <CheckCircle className="h-3 w-3 text-green-500" />
                        <span className="text-green-600">Saved</span>
                      </>
                    )}
                    {autoSaveStatus === "error" && (
                      <span className="text-red-500">Save failed</span>
                    )}
                  </div>
                </div>

                {/* Textarea — top corners removed because toolbar sits above */}
                <textarea
                  ref={textareaRef}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="w-full min-h-[500px] px-4 py-3 rounded-b-xl rounded-t-none border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all resize-none font-mono text-sm leading-relaxed"
                  placeholder="Write your article content in Markdown format..."
                />
              </div>
            ) : (
              <div className="prose prose-lg max-w-none min-h-[500px] px-4 py-3">
                {content ? (
                  <div dangerouslySetInnerHTML={{
                    __html: DOMPurify.sanitize(
                      marked.parse(content, { async: false }) as string
                    )
                  }} />
                ) : (
                  <p className="text-text-muted">No content to preview</p>
                )}
              </div>
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
          {/* Word Count Widget */}
          <WordCountWidget
            content={content}
            target={wordCountTarget}
            onTargetChange={setWordCountTarget}
          />

          {/* SERP Preview */}
          <SerpPreview
            title={title}
            slug={article.slug || ""}
            metaDescription={metaDescription}
            keyword={keyword}
          />

          {/* Live SEO Score — updates as the user types (debounced 500 ms) */}
          <LiveSeoPanel seoScore={liveSeoScore} />

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

          {/* Version History */}
          <Card className="p-4">
            <button
              type="button"
              onClick={handleToggleVersionHistory}
              className="w-full flex items-center justify-between text-left"
            >
              <div className="flex items-center gap-2">
                <History className="h-4 w-4 text-text-secondary" />
                <span className="font-medium text-text-primary text-sm">Version History</span>
                {revisionsTotal > 0 && (
                  <span className="text-xs text-text-muted bg-surface-secondary px-1.5 py-0.5 rounded-full">
                    {revisionsTotal}
                  </span>
                )}
              </div>
              {showVersionHistory ? (
                <ChevronUp className="h-4 w-4 text-text-muted" />
              ) : (
                <ChevronDown className="h-4 w-4 text-text-muted" />
              )}
            </button>

            {showVersionHistory && (
              <div className="mt-3 space-y-2">
                {loadingRevisions ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="h-4 w-4 animate-spin text-text-muted" />
                  </div>
                ) : revisions.length === 0 ? (
                  <p className="text-xs text-text-muted text-center py-3">
                    No saved versions yet. Versions are saved automatically before AI improvements and manual edits.
                  </p>
                ) : (
                  <>
                    {revisions.map((rev) => (
                      <div
                        key={rev.id}
                        className={clsx(
                          "rounded-lg border p-2.5 transition-colors",
                          previewRevision?.id === rev.id
                            ? "border-primary-300 bg-primary-50"
                            : "border-surface-tertiary bg-white hover:bg-surface-secondary"
                        )}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="text-xs font-medium text-text-primary truncate">
                              {formatRevisionType(rev.revision_type)}
                            </p>
                            <p className="text-xs text-text-muted mt-0.5">
                              {new Date(rev.created_at).toLocaleString(undefined, {
                                month: "short",
                                day: "numeric",
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                              {" · "}
                              {rev.word_count.toLocaleString()} words
                            </p>
                          </div>
                          <button
                            type="button"
                            title="Restore this version"
                            onClick={() => handleRestoreRevision(rev.id)}
                            disabled={restoringRevisionId === rev.id}
                            className="flex-shrink-0 p-1 rounded hover:bg-surface-tertiary text-text-muted hover:text-text-primary transition-colors"
                          >
                            {restoringRevisionId === rev.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <RotateCcw className="h-3.5 w-3.5" />
                            )}
                          </button>
                        </div>

                        {/* Preview toggle */}
                        <button
                          type="button"
                          onClick={() => handlePreviewRevision(rev.id)}
                          className="mt-1.5 text-xs text-primary-600 hover:text-primary-700 transition-colors"
                        >
                          {previewRevision?.id === rev.id ? "Hide preview" : "Preview"}
                          {loadingPreview && previewRevision?.id !== rev.id && " ..."}
                        </button>

                        {/* Inline content preview */}
                        {previewRevision?.id === rev.id && (
                          <div className="mt-2 p-2 rounded bg-surface-secondary border border-surface-tertiary max-h-40 overflow-y-auto">
                            <p className="text-xs font-medium text-text-secondary mb-1 truncate">
                              {previewRevision.title}
                            </p>
                            <p className="text-xs text-text-muted whitespace-pre-wrap font-mono leading-relaxed line-clamp-6">
                              {previewRevision.content?.slice(0, 600) || "(no content)"}
                              {(previewRevision.content?.length ?? 0) > 600 && "…"}
                            </p>
                          </div>
                        )}
                      </div>
                    ))}

                    {revisionsTotal > revisions.length && (
                      <p className="text-xs text-text-muted text-center pt-1">
                        Showing {revisions.length} of {revisionsTotal} versions
                      </p>
                    )}
                  </>
                )}
              </div>
            )}
          </Card>

          {/* Internal Links */}
          <Card className="p-4">
            <button
              type="button"
              onClick={handleToggleLinkSuggestions}
              className="w-full flex items-center justify-between text-left"
            >
              <div className="flex items-center gap-2">
                <Link2 className="h-4 w-4 text-text-secondary" />
                <span className="font-medium text-text-primary text-sm">Internal Links</span>
              </div>
              {showLinkSuggestions ? (
                <ChevronUp className="h-4 w-4 text-text-muted" />
              ) : (
                <ChevronDown className="h-4 w-4 text-text-muted" />
              )}
            </button>

            {showLinkSuggestions && (
              <div className="mt-3 space-y-2">
                {loadingLinks ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="h-4 w-4 animate-spin text-text-muted" />
                  </div>
                ) : linkSuggestions.length === 0 ? (
                  <p className="text-xs text-text-muted text-center py-3">
                    No related articles found. Try publishing more articles with overlapping keywords.
                  </p>
                ) : (
                  linkSuggestions.map((suggestion) => (
                    <div
                      key={suggestion.id}
                      className="flex items-start gap-2 p-2 rounded-lg border border-surface-tertiary bg-white hover:bg-surface-secondary transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-text-primary leading-snug line-clamp-2">
                          {suggestion.title}
                        </p>
                        <div className="flex items-center gap-1.5 mt-1">
                          <span className="text-xs px-1.5 py-0.5 bg-primary-50 text-primary-700 rounded truncate max-w-[120px]">
                            {suggestion.keyword}
                          </span>
                          {/* Relevance dots: 1-3 filled based on score */}
                          <span className="flex items-center gap-0.5 flex-shrink-0" title={`Relevance: ${suggestion.relevance_score}`}>
                            {[1, 2, 3].map((dot) => (
                              <span
                                key={dot}
                                className={clsx(
                                  "w-1.5 h-1.5 rounded-full",
                                  suggestion.relevance_score >= dot * 4
                                    ? "bg-primary-400"
                                    : "bg-surface-tertiary"
                                )}
                              />
                            ))}
                          </span>
                        </div>
                      </div>
                      <button
                        type="button"
                        title="Insert link at cursor"
                        onClick={() => handleInsertLink(suggestion)}
                        className="flex-shrink-0 px-2 py-1 rounded text-xs font-medium text-primary-600 border border-primary-200 hover:bg-primary-50 transition-colors"
                      >
                        Insert
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
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

      {/* Social Posts Modal */}
      <SocialPostsModal
        articleId={articleId}
        articleTitle={article.title}
        articleUrl={article.published_url || article.wordpress_post_url}
        imageUrl={featuredImageUrl}
        isOpen={showSocialModal}
        onClose={() => setShowSocialModal(false)}
      />
    </div>
  );
}
