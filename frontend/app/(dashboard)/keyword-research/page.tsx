"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Search,
  Loader2,
  AlertCircle,
  ArrowRight,
  Lightbulb,
  Clock,
} from "lucide-react";
import {
  api,
  KeywordSuggestion,
  KeywordSuggestionsResponse,
  KeywordHistoryEntry,
} from "@/lib/api";

// Badge color helpers
function intentBadgeClass(intent: KeywordSuggestion["intent"]): string {
  switch (intent) {
    case "informational":
      return "bg-blue-100 text-blue-700 border-blue-200";
    case "commercial":
      return "bg-green-100 text-green-700 border-green-200";
    case "transactional":
      return "bg-orange-100 text-orange-700 border-orange-200";
    case "navigational":
      return "bg-purple-100 text-purple-700 border-purple-200";
    default:
      return "bg-gray-100 text-gray-600 border-gray-200";
  }
}

function difficultyBadgeClass(difficulty: KeywordSuggestion["difficulty"]): string {
  switch (difficulty) {
    case "low":
      return "bg-green-100 text-green-700 border-green-200";
    case "medium":
      return "bg-yellow-100 text-yellow-700 border-yellow-200";
    case "high":
      return "bg-red-100 text-red-700 border-red-200";
    default:
      return "bg-gray-100 text-gray-600 border-gray-200";
  }
}

function intentLabel(intent: KeywordSuggestion["intent"]): string {
  return intent.charAt(0).toUpperCase() + intent.slice(1);
}

function difficultyLabel(difficulty: KeywordSuggestion["difficulty"]): string {
  return difficulty.charAt(0).toUpperCase() + difficulty.slice(1);
}

export default function KeywordResearchPage() {
  const [seedKeyword, setSeedKeyword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<KeywordSuggestionsResponse | null>(null);
  const [history, setHistory] = useState<KeywordHistoryEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  useEffect(() => {
    api.articles.keywordHistory()
      .then((data) => setHistory(data.history))
      .catch(() => {}) // history is non-critical; silent fail
      .finally(() => setHistoryLoading(false));
  }, []);

  async function handleSubmit(e?: React.FormEvent) {
    if (e) e.preventDefault();
    const trimmed = seedKeyword.trim();
    if (!trimmed) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await api.articles.keywordSuggestions(trimmed, 10);
      setResult(data);

      // Prepend to history if not already cached
      if (!data.cached) {
        setHistory((prev) => [
          {
            seed_keyword: data.seed_keyword,
            searched_at: new Date().toISOString(),
            expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
            result: data,
          },
          ...prev.filter((h) => h.seed_keyword.toLowerCase() !== data.seed_keyword.toLowerCase()),
        ]);
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to generate keyword suggestions";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold text-text-primary">Keyword Research</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Discover content ideas powered by AI. Enter a seed keyword to get related
          keyword suggestions with intent, difficulty, and content angles.
        </p>
      </div>

      {/* Search bar */}
      <div className="bg-surface rounded-xl border border-surface-tertiary p-6">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-5 w-5 text-text-tertiary pointer-events-none" />
            <input
              type="text"
              value={seedKeyword}
              onChange={(e) => setSeedKeyword(e.target.value)}
              placeholder="Enter a seed keyword (e.g. content marketing)"
              className="w-full pl-11 pr-4 py-3 rounded-lg bg-surface-secondary border border-surface-tertiary text-text-primary placeholder:text-text-tertiary text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition"
              disabled={isLoading}
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !seedKeyword.trim()}
            className="inline-flex items-center gap-2 px-5 py-3 rounded-lg bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Lightbulb className="h-4 w-4" />
                Get Suggestions
              </>
            )}
          </button>
        </form>
        <p className="mt-2 text-xs text-text-tertiary">
          AI generates up to 10 related keyword ideas. Rate limited to 10 requests per minute.
        </p>
      </div>

      {/* Error state */}
      {error && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700">
          <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium">Failed to generate suggestions</p>
            <p className="text-sm opacity-80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Recent searches history */}
      {!isLoading && !historyLoading && history.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-text-secondary mb-2">Recent searches</h3>
          <div className="flex flex-wrap gap-2">
            {history.map((entry) => (
              <button
                key={entry.seed_keyword}
                onClick={() => {
                  setSeedKeyword(entry.seed_keyword);
                  setResult(entry.result);
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm bg-surface-secondary border border-surface-tertiary text-text-secondary hover:border-primary-300 hover:text-primary-600 transition-colors"
              >
                <Clock className="h-3.5 w-3.5" />
                {entry.seed_keyword}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="card p-5 animate-pulse space-y-3"
            >
              <div className="h-5 bg-surface-tertiary rounded w-3/4" />
              <div className="flex gap-2">
                <div className="h-5 bg-surface-tertiary rounded w-24" />
                <div className="h-5 bg-surface-tertiary rounded w-16" />
              </div>
              <div className="h-4 bg-surface-tertiary rounded w-full" />
              <div className="h-4 bg-surface-tertiary rounded w-2/3" />
            </div>
          ))}
        </div>
      )}

      {/* Results */}
      {!isLoading && result && result.suggestions.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-text-secondary">
              <span className="font-medium text-text-primary">{result.suggestions.length} suggestions</span>
              {" "}for &ldquo;<span className="italic">{result.seed_keyword}</span>&rdquo;
            </p>
          </div>

          {result.cached && (
            <div className="flex items-center gap-1.5 text-xs text-text-muted mb-3">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-surface-secondary border border-surface-tertiary text-text-secondary text-xs">
                Served from cache · saves AI tokens
              </span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {result.suggestions.map((item) => (
              <div
                key={item.keyword}
                className="card p-5 flex flex-col gap-3 hover:shadow-md transition-shadow"
              >
                {/* Keyword */}
                <p className="text-base font-semibold text-text-primary leading-snug">
                  {item.keyword}
                </p>

                {/* Badges */}
                <div className="flex flex-wrap gap-2">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${intentBadgeClass(item.intent)}`}
                  >
                    {intentLabel(item.intent)}
                  </span>
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${difficultyBadgeClass(item.difficulty)}`}
                  >
                    {difficultyLabel(item.difficulty)} difficulty
                  </span>
                </div>

                {/* Content angle */}
                <p className="text-sm text-text-secondary leading-relaxed flex-1">
                  {item.content_angle}
                </p>

                {/* Action */}
                <Link
                  href={`/outlines?keyword=${encodeURIComponent(item.keyword)}`}
                  className="mt-1 inline-flex items-center gap-1.5 text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors self-start"
                >
                  Create Outline
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state (no search yet or empty results) */}
      {!isLoading && !error && !result && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="h-14 w-14 rounded-full bg-primary-50 flex items-center justify-center mb-4">
            <Search className="h-7 w-7 text-primary-400" />
          </div>
          <h3 className="text-base font-medium text-text-primary mb-1">
            Enter a keyword to discover content opportunities
          </h3>
          <p className="text-sm text-text-secondary max-w-sm">
            Type a seed keyword above and click &ldquo;Get Suggestions&rdquo; to receive AI-generated
            keyword ideas with intent classification, difficulty, and content angles.
          </p>
        </div>
      )}

      {/* Empty results state */}
      {!isLoading && result && result.suggestions.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertCircle className="h-10 w-10 text-text-tertiary mb-3" />
          <p className="text-sm text-text-secondary">
            No suggestions were returned for &ldquo;{result.seed_keyword}&rdquo;. Try a different keyword.
          </p>
        </div>
      )}
    </div>
  );
}
