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
  Zap,
  Bot,
} from "lucide-react";
import { api, Article, ArticleRevision, ArticleRevisionDetail, LinkSuggestion, AEOScore } from "@/lib/api";
import { ErrorBoundary } from "@/components/ui/error-boundary";
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
  // FE-CONTENT-19: Word count also computed in lib/seo-score.ts — keep in sync
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

// ---------------------------------------------------------------------------
// AI Answer Preview — shows how content may appear when cited by AI engines
// ---------------------------------------------------------------------------

interface AiAnswerPreviewProps {
  title: string;
  content: string;
  keyword: string;
  url?: string;
}

type AiEngine = "chatgpt" | "perplexity" | "gemini";

function extractAnswerSnippet(content: string): string {
  if (!content.trim()) return "";

  // Strip markdown formatting: headings, bold, italic, links, code, list markers
  const stripped = content
    .replace(/```[\s\S]*?```/g, "")       // fenced code blocks
    .replace(/`[^`]+`/g, "")              // inline code
    .replace(/!\[.*?\]\(.*?\)/g, "")      // images
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // links → text
    .replace(/^#{1,6}\s+/gm, "")          // headings
    .replace(/[*_]{1,2}([^*_]+)[*_]{1,2}/g, "$1") // bold/italic
    .replace(/^[-*+]\s+/gm, "")           // unordered list markers
    .replace(/^\d+\.\s+/gm, "")           // ordered list markers
    .replace(/^>\s+/gm, "")               // blockquotes
    .replace(/\n{2,}/g, "\n")             // collapse blank lines
    .trim();

  const lines = stripped.split("\n").map((l) => l.trim()).filter(Boolean);
  const originalLines = content.split("\n").map((l) => l.trim());

  // Try to find heading with FAQ/what-is/how-to and use the paragraph right after it
  for (let i = 0; i < originalLines.length - 1; i++) {
    const heading = originalLines[i];
    if (/^#{1,3}\s.*(what is|how to|why|faq|definition)/i.test(heading)) {
      // Look for the next non-empty, non-heading paragraph
      for (let j = i + 1; j < originalLines.length; j++) {
        const candidate = originalLines[j]
          .replace(/^#{1,6}\s+/, "")
          .replace(/[*_]{1,2}([^*_]+)[*_]{1,2}/g, "$1")
          .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
          .trim();
        if (candidate.length >= 50 && candidate.length <= 300 && !candidate.startsWith("#")) {
          return candidate.length > 200 ? candidate.slice(0, 197) + "..." : candidate;
        }
      }
    }
  }

  // Otherwise find the first qualifying paragraph
  for (const line of lines) {
    if (
      line.length >= 50 &&
      line.length <= 300 &&
      !line.endsWith("?")
    ) {
      return line.length > 200 ? line.slice(0, 197) + "..." : line;
    }
  }

  // Fallback: first substantial line, trimmed
  const fallback = lines.find((l) => l.length >= 20) ?? "";
  return fallback.length > 200 ? fallback.slice(0, 197) + "..." : fallback;
}

function calcSnippetQuality(snippet: string, keyword: string): number {
  if (!snippet) return 0;
  let score = 0;

  // Has a concise direct answer (not starting with "In this article...")
  if (!/^in this (article|post|guide)/i.test(snippet)) score += 30;

  // Answer is 50-200 chars
  if (snippet.length >= 50 && snippet.length <= 200) score += 20;
  else if (snippet.length > 20) score += 8; // partial credit

  // Contains the keyword
  if (keyword && snippet.toLowerCase().includes(keyword.toLowerCase())) score += 20;

  // Starts with a factual statement (not a question)
  if (!snippet.trim().endsWith("?") && /^[A-Z]/.test(snippet.trim())) score += 15;

  // Has structured data hints: numbers, definitions, or lists embedded
  if (/\d+|:\s|e\.g\.|i\.e\.|such as|including|for example/i.test(snippet)) score += 15;

  return Math.min(score, 100);
}

function AiAnswerPreview({ title, content, keyword, url }: AiAnswerPreviewProps) {
  const [activeEngine, setActiveEngine] = useState<AiEngine>("chatgpt");

  const snippet = useMemo(() => extractAnswerSnippet(content), [content]);
  const qualityScore = useMemo(() => calcSnippetQuality(snippet, keyword), [snippet, keyword]);

  const displayUrl = url
    ? url.replace(/^https?:\/\//, "").replace(/\/$/, "")
    : "yoursite.com";

  const engines: { id: AiEngine; label: string }[] = [
    { id: "chatgpt", label: "ChatGPT" },
    { id: "perplexity", label: "Perplexity" },
    { id: "gemini", label: "Gemini" },
  ];

  const qualityLabel =
    qualityScore >= 80 ? "Excellent" :
    qualityScore >= 60 ? "Good" :
    qualityScore >= 40 ? "Fair" :
    "Needs work";

  const qualityColor =
    qualityScore >= 80 ? "bg-green-500" :
    qualityScore >= 60 ? "bg-yellow-500" :
    qualityScore >= 40 ? "bg-orange-500" :
    "bg-red-500";

  const qualityTextColor =
    qualityScore >= 80 ? "text-green-600" :
    qualityScore >= 60 ? "text-yellow-600" :
    qualityScore >= 40 ? "text-orange-600" :
    "text-red-600";

  const snippetText = snippet || "Add content to your article to see an AI answer preview.";
  const hasSnippet = snippet.length > 0;

  return (
    <div className="bg-white rounded-xl border border-surface-tertiary p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Bot className="h-4 w-4 text-purple-500 flex-shrink-0" />
        <div>
          <p className="text-sm font-medium text-text-primary leading-tight">AI Answer Preview</p>
          <p className="text-xs text-text-muted leading-tight">
            How your content may appear in AI search results
          </p>
        </div>
      </div>

      {/* Engine tab pills */}
      <div className="flex items-center gap-1.5">
        {engines.map((engine) => (
          <button
            key={engine.id}
            type="button"
            onClick={() => setActiveEngine(engine.id)}
            className={clsx(
              "px-2 py-1 rounded-lg text-xs font-medium transition-colors",
              activeEngine === engine.id
                ? "bg-purple-100 text-purple-700"
                : "text-text-muted hover:bg-surface-secondary"
            )}
          >
            {engine.label}
          </button>
        ))}
      </div>

      {/* Preview panel */}
      <div className="rounded-lg bg-surface-secondary border border-surface-tertiary p-3 space-y-2">
        {activeEngine === "chatgpt" && (
          <>
            {/* ChatGPT style */}
            <p className="text-xs text-text-secondary leading-relaxed">
              {hasSnippet ? snippetText : <span className="italic text-text-muted">{snippetText}</span>}
            </p>
            {hasSnippet && (
              <div className="pt-1.5 border-t border-surface-tertiary space-y-1">
                <p className="text-xs font-semibold text-text-secondary">Sources</p>
                <div className="flex items-center gap-1.5 text-xs text-purple-600">
                  <span className="bg-purple-100 text-purple-700 rounded px-1 font-mono font-bold">1</span>
                  <span className="font-medium truncate">{title || "Untitled article"}</span>
                  <span className="text-text-muted">—</span>
                  <span className="text-text-muted truncate">{displayUrl}</span>
                  <ExternalLink className="h-3 w-3 flex-shrink-0 text-text-muted" />
                </div>
              </div>
            )}
          </>
        )}

        {activeEngine === "perplexity" && (
          <>
            {/* Perplexity style — inline citation */}
            <p className="text-xs text-text-secondary leading-relaxed">
              {hasSnippet ? (
                <>
                  {snippetText.length > 20
                    ? snippetText.slice(0, Math.floor(snippetText.length * 0.6))
                    : snippetText}
                  <sup className="text-purple-600 font-bold ml-0.5 text-[10px]">[1]</sup>
                  {snippetText.length > 20
                    ? snippetText.slice(Math.floor(snippetText.length * 0.6))
                    : ""}
                </>
              ) : (
                <span className="italic text-text-muted">{snippetText}</span>
              )}
            </p>
            {hasSnippet && (
              <div className="mt-2 flex items-center gap-2 bg-white rounded-lg border border-surface-tertiary px-2.5 py-1.5">
                <div className="w-4 h-4 rounded-sm bg-purple-200 flex items-center justify-center flex-shrink-0">
                  <span className="text-[8px] font-bold text-purple-700">S</span>
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-medium text-text-primary truncate">{title || "Untitled article"}</p>
                  <p className="text-[10px] text-text-muted truncate">{displayUrl}</p>
                </div>
              </div>
            )}
          </>
        )}

        {activeEngine === "gemini" && (
          <>
            {/* Gemini style — minimal, "Learn more" link */}
            <p className="text-xs text-text-secondary leading-relaxed">
              {hasSnippet ? snippetText : <span className="italic text-text-muted">{snippetText}</span>}
            </p>
            {hasSnippet && (
              <div className="pt-1.5 border-t border-surface-tertiary flex items-center gap-1 text-xs text-purple-600">
                <ExternalLink className="h-3 w-3 flex-shrink-0" />
                <span className="font-medium">Learn more</span>
                <span className="text-text-muted">· {displayUrl}</span>
              </div>
            )}
          </>
        )}
      </div>

      {/* Snippet quality score */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-muted font-medium">Snippet quality</span>
          <span className={clsx("font-semibold tabular-nums", qualityTextColor)}>
            {qualityScore}% — {qualityLabel}
          </span>
        </div>
        <div className="w-full h-1.5 bg-surface-secondary rounded-full overflow-hidden">
          <div
            className={clsx("h-full rounded-full transition-all duration-500", qualityColor)}
            style={{ width: `${qualityScore}%` }}
          />
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
            {checks.map((check) => (
              <div key={check.label}>
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
  const rawArticleId = params.id;
  const articleId = Array.isArray(rawArticleId) ? rawArticleId[0] : (rawArticleId ?? "");

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
  const autoSaveStatusTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [autoSaveStatus, setAutoSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  // FE-CONTENT-13: prevent auto-save firing concurrently with a revision restore
  const isRestoringRef = useRef(false);

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
  const [linkSuggestionsError, setLinkSuggestionsError] = useState(false);

  // Export dropdown state
  const [showExportMenu, setShowExportMenu] = useState(false);

  // AEO score state
  const [aeoScore, setAeoScore] = useState<AEOScore | null>(null);
  const [aeoLoading, setAeoLoading] = useState(false);

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

  const loadArticle = useCallback(async () => {
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
  }, [articleId]);

  const checkWordPressConnection = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    loadArticle();
    checkWordPressConnection();
  }, [loadArticle, checkWordPressConnection]);

  useEffect(() => {
    if (params.id) handleLoadAeo();
  }, [params.id]);

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
    // Formatting shortcuts
    { key: "b", ctrl: true, handler: () => insertMarkdown("**", "**") },
    { key: "i", ctrl: true, handler: () => insertMarkdown("*", "*") },
    { key: "k", ctrl: true, handler: () => insertMarkdown("[", "](url)") },
    { key: "e", ctrl: true, handler: () => insertMarkdown("`", "`") },
    // View shortcuts
    { key: "\\", ctrl: true, handler: () => setViewMode((m) => m === "edit" ? "preview" : "edit") },
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

  async function copyToClipboard(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Copied to clipboard!");
    } catch {
      toast.error("Failed to copy to clipboard");
    }
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
  const lastSavedSnapshotRef = useRef<string | null>("");
  // FE-CONTENT-04: Reset snapshot ref on unmount to prevent stale comparisons
  useEffect(() => {
    return () => {
      lastSavedSnapshotRef.current = null;
    };
  }, []);
  useEffect(() => {
    if (!article) return;
    const snapshot = JSON.stringify({ content, title, metaDescription, keyword });
    if (snapshot === lastSavedSnapshotRef.current) return;

    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }

    autoSaveTimerRef.current = setTimeout(async () => {
      // FE-CONTENT-13: skip auto-save if a revision restore is in progress
      if (isRestoringRef.current) return;
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
        autoSaveStatusTimerRef.current = setTimeout(() => setAutoSaveStatus("idle"), 2000);
      } catch {
        setAutoSaveStatus("error");
        autoSaveStatusTimerRef.current = setTimeout(() => setAutoSaveStatus("idle"), 3000);
      }
    }, 3000);

    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
      if (autoSaveStatusTimerRef.current) {
        clearTimeout(autoSaveStatusTimerRef.current);
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
        isRestoringRef.current = true;
        setRestoringRevisionId(revisionId);
        try {
          const updated = await api.articles.restoreRevision(article.id, revisionId);
          if (!updated) {
            toast.error("Failed to restore revision");
            return;
          }
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
          isRestoringRef.current = false;
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
    if (nextOpen && linkSuggestions.length === 0 && !linkSuggestionsError) {
      setLoadingLinks(true);
      try {
        const data = await api.articles.linkSuggestions(articleId);
        setLinkSuggestions(data.suggestions);
      } catch (error) {
        toast.error("Failed to load link suggestions");
        setLinkSuggestionsError(true);
      } finally {
        setLoadingLinks(false);
      }
    }
  }

  function handleInsertLink(suggestion: LinkSuggestion) {
    // WordPress suggestions have a full absolute URL; platform articles use slug path
    const href = suggestion.url || `/${suggestion.slug || suggestion.id}`;
    insertMarkdown(`[${suggestion.title}](${href})`, "");
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

  const handleLoadAeo = async () => {
    if (!params.id) return;
    try {
      setAeoLoading(true);
      const data = await api.articles.getAeoScore(params.id as string);
      setAeoScore(data);
    } catch {
      // Silent — AEO is optional
    } finally {
      setAeoLoading(false);
    }
  };

  const handleRefreshAeo = async () => {
    if (!params.id) return;
    try {
      setAeoLoading(true);
      const data = await api.articles.refreshAeoScore(params.id as string);
      setAeoScore(data);
      toast.success("AEO score updated");
    } catch {
      toast.error("Failed to refresh AEO score");
    } finally {
      setAeoLoading(false);
    }
  };

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
    <ErrorBoundary>
    <div className="space-y-6 min-w-0">
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
              onKeyDown={(e) => { if (e.key === "Escape") setShowExportMenu(false); }}
              aria-haspopup="menu"
              aria-expanded={showExportMenu}
              leftIcon={<Download className="h-4 w-4" />}
            >
              Export
              <ChevronDown className="h-3 w-3 ml-1" />
            </Button>
            {showExportMenu && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowExportMenu(false)} />
                <div
                  role="menu"
                  className="absolute right-0 top-full mt-1 z-50 w-40 rounded-xl border border-surface-tertiary bg-surface shadow-lg py-1"
                  onKeyDown={(e) => { if (e.key === "Escape") setShowExportMenu(false); }}
                >
                  <button
                    role="menuitem"
                    onClick={() => { handleExport("markdown"); setShowExportMenu(false); }}
                    className="w-full text-left px-4 py-2 text-sm text-text-primary hover:bg-surface-secondary transition-colors"
                  >
                    Markdown (.md)
                  </button>
                  <button
                    role="menuitem"
                    onClick={() => { handleExport("html"); setShowExportMenu(false); }}
                    className="w-full text-left px-4 py-2 text-sm text-text-primary hover:bg-surface-secondary transition-colors"
                  >
                    HTML (.html)
                  </button>
                  <button
                    role="menuitem"
                    onClick={() => { handleExport("csv"); setShowExportMenu(false); }}
                    className="w-full text-left px-4 py-2 text-sm text-text-primary hover:bg-surface-secondary transition-colors"
                  >
                    CSV (.csv)
                  </button>
                </div>
              </>
            )}
          </div>

          <div className="flex rounded-lg border border-surface-tertiary overflow-hidden">
            <button
              onClick={() => setViewMode("edit")}
              aria-label="Edit mode"
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
              aria-label="Preview mode"
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

      <div className="grid gap-6 lg:grid-cols-3 min-w-0">
        {/* Main Editor */}
        <div className="lg:col-span-2 space-y-4 min-w-0">
          <Card className="p-4 space-y-4 overflow-hidden">
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

          <Card className="p-4 overflow-hidden">
            {viewMode === "edit" ? (
              <div>
                {/* Markdown toolbar */}
                <div className="flex flex-wrap items-center gap-1 p-2 bg-surface-secondary rounded-t-xl border border-surface-tertiary border-b-0">
                  {/* Inline formatting group */}
                  <button
                    type="button"
                    title="Bold (Ctrl+B)"
                    onClick={() => insertMarkdown("**", "**")}
                    className="p-1.5 rounded-lg hover:bg-surface-tertiary text-text-secondary hover:text-text-primary transition-colors"
                  >
                    <Bold className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    title="Italic (Ctrl+I)"
                    onClick={() => insertMarkdown("*", "*")}
                    className="p-1.5 rounded-lg hover:bg-surface-tertiary text-text-secondary hover:text-text-primary transition-colors"
                  >
                    <Italic className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    title="Inline Code (Ctrl+E)"
                    onClick={() => insertMarkdown("`", "`")}
                    className="p-1.5 rounded-lg hover:bg-surface-tertiary text-text-secondary hover:text-text-primary transition-colors"
                  >
                    <Code className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    title="Link (Ctrl+K)"
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
              <div className="prose prose-lg max-w-none min-h-[500px] px-4 py-3 overflow-x-auto break-words">
                {content ? (
                  <div dangerouslySetInnerHTML={{
                    __html: DOMPurify.sanitize(
                      marked.parse(content, { async: false, breaks: true, gfm: true }) as string,
                      {
                        ALLOWED_TAGS: ['h1','h2','h3','h4','h5','h6','p','br','strong','em','u','s','ul','ol','li','a','blockquote','code','pre','hr','img','table','thead','tbody','tr','th','td'],
                        ALLOWED_ATTR: ['href','src','alt','title','class','target','rel'],
                        FORBID_TAGS: ['script','iframe','object','embed','form','input'],
                        FORBID_ATTR: ['onerror','onload','onclick','onmouseover'],
                      }
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
        <div className="space-y-4 min-w-0">
          {/* Word Count Widget */}
          <WordCountWidget
            content={content}
            target={wordCountTarget}
            onTargetChange={setWordCountTarget}
          />

          {/* SERP Preview */}
          <SerpPreview
            title={title}
            slug={article.slug || article.title?.toLowerCase().replace(/\s+/g, "-") || "article"}
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

          {/* AEO Score */}
          <Card className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium text-text-primary flex items-center gap-1.5">
                <Zap className="h-4 w-4 text-purple-500" />
                AEO Score
              </h3>
              <Button variant="ghost" size="sm" onClick={handleRefreshAeo} disabled={aeoLoading}>
                <RefreshCw className={`h-4 w-4 ${aeoLoading ? "animate-spin" : ""}`} />
              </Button>
            </div>

            {aeoScore ? (
              <div>
                <div className="text-center mb-3">
                  <div className={clsx(
                    "inline-flex items-center justify-center w-20 h-20 rounded-full text-2xl font-bold",
                    aeoScore.aeo_score >= 80 ? "bg-green-100 text-green-700" :
                    aeoScore.aeo_score >= 50 ? "bg-yellow-100 text-yellow-700" :
                    "bg-red-100 text-red-700"
                  )}>
                    {aeoScore.aeo_score}
                  </div>
                  <p className="text-sm text-text-secondary mt-2">
                    {aeoScore.aeo_score >= 80 ? "Great AI readability!" :
                     aeoScore.aeo_score >= 50 ? "Good, can be improved" :
                     "Needs improvement"}
                  </p>
                  {aeoScore.previous_score !== null && aeoScore.previous_score !== undefined && (
                    <p className="text-xs text-text-muted mt-1">
                      Previous: {aeoScore.previous_score}
                    </p>
                  )}
                </div>

                {aeoScore.score_breakdown && (
                  <div className="space-y-2 text-sm">
                    {Object.entries(aeoScore.score_breakdown).map(([key, value]) => {
                      const max = key === "entity_score" || key === "citation_readiness" ? 15 : key === "schema_score" ? 10 : 20;
                      const pct = Math.round((Number(value) / max) * 100);
                      return (
                        <div key={key} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-text-secondary capitalize">{key.replace(/_/g, " ")}</span>
                            <span className="text-text-primary font-medium">{value}/{max}</span>
                          </div>
                          <div className="h-1.5 bg-surface-secondary rounded-full overflow-hidden">
                            <div
                              className={clsx(
                                "h-full rounded-full",
                                pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-500" : "bg-red-500"
                              )}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {aeoScore.suggestions && aeoScore.suggestions.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-surface-tertiary">
                    <p className="text-xs font-semibold text-text-secondary mb-2">Suggestions</p>
                    <ul className="space-y-1.5">
                      {aeoScore.suggestions.slice(0, 3).map((s, i) => (
                        <li key={i} className="text-xs text-text-secondary flex items-start gap-1.5">
                          <span className="text-primary-500 mt-0.5 shrink-0">•</span>
                          <span className="break-words min-w-0">{typeof s === "string" ? s : s.action || s.description}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-sm text-text-muted">
                  {aeoLoading ? "Calculating..." : "Click refresh to calculate AEO score"}
                </p>
              </div>
            )}
          </Card>

          {/* AI Answer Preview */}
          <AiAnswerPreview
            title={title}
            content={content}
            keyword={keyword}
            url={article?.published_url ?? undefined}
          />

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
                {seo.suggestions.map((suggestion) => (
                  <li key={suggestion} className="flex items-start gap-2 text-sm text-text-secondary">
                    <AlertCircle className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                    <span className="break-words min-w-0">{suggestion}</span>
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
                            aria-label="Restore this version"
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
                ) : linkSuggestionsError ? (
                  <div className="text-center py-3 space-y-2">
                    <p className="text-xs text-red-500">Failed to load link suggestions.</p>
                    <button
                      type="button"
                      onClick={() => { setLinkSuggestionsError(false); handleToggleLinkSuggestions(); }}
                      className="text-xs text-primary-600 hover:underline"
                    >
                      Retry
                    </button>
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
                          {suggestion.source === "wordpress" ? (
                            <span className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded flex-shrink-0">
                              WP
                            </span>
                          ) : suggestion.keyword ? (
                            <span className="text-xs px-1.5 py-0.5 bg-primary-50 text-primary-700 rounded truncate max-w-[120px]">
                              {suggestion.keyword}
                            </span>
                          ) : null}
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
    </ErrorBoundary>
  );
}
