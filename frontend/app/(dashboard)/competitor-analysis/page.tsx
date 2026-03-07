"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import {
  Search,
  Globe,
  Loader2,
  Trash2,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  BarChart2,
  ArrowLeft,
  AlertCircle,
  Target,
  Plus,
} from "lucide-react";
import { api, CompetitorAnalysis, CompetitorAnalysisDetail, KeywordAggregation, KeywordGapItem } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { clsx } from "clsx";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function parseApiError(err: unknown): { message: string } {
  if (err && typeof err === "object") {
    const e = err as Record<string, unknown>;
    if (typeof e.message === "string") return { message: e.message };
    if (e.response && typeof e.response === "object") {
      const r = e.response as Record<string, unknown>;
      if (r.data && typeof r.data === "object") {
        const d = r.data as Record<string, unknown>;
        if (typeof d.detail === "string") return { message: d.detail };
      }
    }
  }
  return { message: "An unexpected error occurred." };
}

function statusBadge(status: string) {
  const classes = clsx(
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
    status === "completed" && "bg-green-100 text-green-700",
    status === "failed" && "bg-red-100 text-red-700",
    status === "pending" && "bg-surface-tertiary text-text-secondary",
    (status === "processing" || status === "scraping" || status === "analyzing") &&
      "bg-yellow-100 text-yellow-700"
  );
  const label =
    status === "completed"
      ? "Completed"
      : status === "failed"
      ? "Failed"
      : status === "pending"
      ? "Pending"
      : status === "processing"
      ? "Processing"
      : status === "scraping"
      ? "Scraping"
      : status === "analyzing"
      ? "Analyzing"
      : status;
  return <span className={classes}>{label}</span>;
}

function isInProgress(status: string) {
  return ["pending", "processing", "scraping", "analyzing"].includes(status);
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

type Tab = "keywords" | "gaps" | "articles";

function KeywordsTab({ analysisId }: { analysisId: string }) {
  const [keywords, setKeywords] = useState<KeywordAggregation[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    setLoading(true);
    api.competitors
      .keywords(analysisId)
      .then((data) => setKeywords(data.keywords))
      .catch((err) => toast.error(parseApiError(err).message))
      .finally(() => setLoading(false));
  }, [analysisId]);

  function toggle(keyword: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(keyword)) {
        next.delete(keyword);
      } else {
        next.add(keyword);
      }
      return next;
    });
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
      </div>
    );
  }

  if (keywords.length === 0) {
    return (
      <p className="text-center text-text-secondary py-12">No keywords extracted yet.</p>
    );
  }

  return (
    <div className="divide-y divide-surface-tertiary">
      {keywords.map((kw) => {
        const isOpen = expanded.has(kw.keyword);
        return (
          <div key={kw.keyword}>
            <button
              onClick={() => toggle(kw.keyword)}
              className="w-full flex items-center gap-3 px-4 py-3 hover:bg-surface-secondary transition-colors text-left"
            >
              {isOpen ? (
                <ChevronDown className="h-4 w-4 text-text-muted shrink-0" />
              ) : (
                <ChevronRight className="h-4 w-4 text-text-muted shrink-0" />
              )}
              <span className="flex-1 text-sm font-medium text-text-primary">{kw.keyword}</span>
              <span className="text-xs text-text-secondary bg-surface-secondary px-2 py-0.5 rounded-full">
                {kw.article_count} {kw.article_count === 1 ? "article" : "articles"}
              </span>
            </button>
            {isOpen && (
              <div className="bg-surface-secondary/50 px-4 pb-3 pt-1">
                <ul className="space-y-1 ml-7">
                  {kw.articles.map((a) => (
                    <li key={a.url} className="flex items-center gap-2">
                      <a
                        href={a.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-primary-600 hover:underline flex items-center gap-1 truncate"
                      >
                        {a.title || a.url}
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function GapsTab({ analysisId }: { analysisId: string }) {
  const [gaps, setGaps] = useState<KeywordGapItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.competitors
      .gaps(analysisId)
      .then((data) => setGaps(data.gaps))
      .catch((err) => toast.error(parseApiError(err).message))
      .finally(() => setLoading(false));
  }, [analysisId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
      </div>
    );
  }

  if (gaps.length === 0) {
    return (
      <p className="text-center text-text-secondary py-12">No keyword gaps found.</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-surface-tertiary">
            <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
              Keyword
            </th>
            <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
              Competitor Articles
            </th>
            <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
              Action
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-tertiary">
          {gaps.map((gap) => (
            <tr key={gap.keyword} className="hover:bg-surface-secondary/50 transition-colors">
              <td className="px-4 py-3 font-medium text-text-primary">{gap.keyword}</td>
              <td className="px-4 py-3 text-text-secondary">{gap.competitor_articles}</td>
              <td className="px-4 py-3">
                <Link
                  href={`/outlines?keyword=${encodeURIComponent(gap.keyword)}`}
                  className="inline-flex items-center gap-1 text-xs font-medium text-primary-600 hover:text-primary-700 hover:underline"
                >
                  <Plus className="h-3 w-3" />
                  Create Outline
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ArticlesTab({ detail }: { detail: CompetitorAnalysisDetail }) {
  const articles = detail.articles;

  if (articles.length === 0) {
    return (
      <p className="text-center text-text-secondary py-12">No articles found.</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-surface-tertiary">
            <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
              Title
            </th>
            <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
              Keyword
            </th>
            <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
              Confidence
            </th>
            <th className="text-left px-4 py-3 text-xs font-semibold text-text-secondary uppercase tracking-wide">
              Word Count
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-tertiary">
          {articles.map((article) => {
            const confidence =
              article.keyword_confidence != null
                ? Math.round(article.keyword_confidence * 100)
                : null;
            return (
              <tr key={article.id} className="hover:bg-surface-secondary/50 transition-colors">
                <td className="px-4 py-3 max-w-xs">
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-primary-600 hover:underline truncate"
                  >
                    <span className="truncate">{article.title || article.url}</span>
                    <ExternalLink className="h-3 w-3 shrink-0" />
                  </a>
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {article.extracted_keyword || <span className="text-text-muted italic">—</span>}
                </td>
                <td className="px-4 py-3">
                  {confidence != null ? (
                    <span
                      className={clsx(
                        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
                        confidence >= 80
                          ? "bg-green-100 text-green-700"
                          : confidence >= 50
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-surface-tertiary text-text-secondary"
                      )}
                    >
                      {confidence}%
                    </span>
                  ) : (
                    <span className="text-text-muted italic text-xs">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {article.word_count != null ? article.word_count.toLocaleString() : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function CompetitorAnalysisPage() {
  // History list
  const [analyses, setAnalyses] = useState<CompetitorAnalysis[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  // Input state
  const [domain, setDomain] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Selected analysis
  const [selected, setSelected] = useState<CompetitorAnalysisDetail | null>(null);
  const [selectedLoading, setSelectedLoading] = useState(false);

  // Active tab in results view
  const [activeTab, setActiveTab] = useState<Tab>("keywords");

  // Poll ref
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------

  const loadHistory = useCallback(async () => {
    try {
      const data = await api.competitors.list(1, 20);
      setAnalyses(data.items);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const loadDetail = useCallback(async (id: string) => {
    setSelectedLoading(true);
    try {
      const data = await api.competitors.get(id);
      setSelected(data);
      return data;
    } catch (err) {
      toast.error(parseApiError(err).message);
      return null;
    } finally {
      setSelectedLoading(false);
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Polling for in-progress analyses
  // ---------------------------------------------------------------------------

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (id: string) => {
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const data = await api.competitors.get(id);
          setSelected(data);
          // Update status in history list too
          setAnalyses((prev) =>
            prev.map((a) => (a.id === id ? { ...a, status: data.status, scraped_urls: data.scraped_urls } : a))
          );
          if (!isInProgress(data.status)) {
            stopPolling();
            if (data.status === "completed") {
              setActiveTab("keywords");
            }
          }
        } catch {
          // silent poll failure
        }
      }, 3000);
    },
    [stopPolling]
  );

  useEffect(() => {
    if (selected && isInProgress(selected.status)) {
      startPolling(selected.id);
    } else {
      stopPolling();
    }
    return () => stopPolling();
  }, [selected?.id, selected?.status, startPolling, stopPolling]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  async function handleAnalyze(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = domain.trim();
    if (!trimmed) return;
    setSubmitting(true);
    try {
      const analysis = await api.competitors.analyze(trimmed);
      toast.success(`Analysis started for ${trimmed}`);
      setDomain("");
      setAnalyses((prev) => [analysis, ...prev]);
      const detail = await loadDetail(analysis.id);
      if (detail) {
        setActiveTab("keywords");
      }
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await api.competitors.delete(id);
      setAnalyses((prev) => prev.filter((a) => a.id !== id));
      if (selected?.id === id) {
        setSelected(null);
        stopPolling();
      }
      toast.success("Analysis deleted.");
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  }

  async function handleSelectAnalysis(analysis: CompetitorAnalysis) {
    setActiveTab("keywords");
    await loadDetail(analysis.id);
  }

  function handleBack() {
    setSelected(null);
    stopPolling();
    loadHistory();
  }

  // ---------------------------------------------------------------------------
  // Render: State 2 — In Progress
  // ---------------------------------------------------------------------------

  if (selected && isInProgress(selected.status)) {
    const progress =
      selected.total_urls > 0
        ? Math.round((selected.scraped_urls / selected.total_urls) * 100)
        : 0;

    return (
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleBack}
            className="p-2 rounded-xl hover:bg-surface-secondary transition-colors"
            aria-label="Back"
          >
            <ArrowLeft className="h-5 w-5 text-text-secondary" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
              <Globe className="h-6 w-6 text-primary-500" />
              {selected.domain}
            </h1>
            <p className="text-sm text-text-secondary mt-0.5">Analysis in progress</p>
          </div>
        </div>

        <Card className="p-6 space-y-5">
          <div className="flex items-center gap-3">
            {statusBadge(selected.status)}
            <Loader2 className="h-4 w-4 animate-spin text-primary-500" />
            <span className="text-sm text-text-secondary">Scanning competitor content...</span>
          </div>

          {selected.total_urls > 0 && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm text-text-secondary">
                <span>URLs scraped</span>
                <span>
                  {selected.scraped_urls} / {selected.total_urls}
                </span>
              </div>
              <div className="h-2 bg-surface-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-500 rounded-full transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs text-text-muted">{progress}% complete</p>
            </div>
          )}

          {selected.total_urls === 0 && (
            <div className="h-2 bg-surface-secondary rounded-full overflow-hidden">
              <div className="h-full bg-primary-400 rounded-full animate-pulse w-1/3" />
            </div>
          )}

          <p className="text-xs text-text-muted">
            This usually takes 1–5 minutes. You can navigate away and come back.
          </p>
        </Card>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render: State 3 — Results
  // ---------------------------------------------------------------------------

  if (selected && selected.status === "completed") {
    const tabs: { key: Tab; label: string }[] = [
      { key: "keywords", label: "Keywords" },
      { key: "gaps", label: "Gaps" },
      { key: "articles", label: "Articles" },
    ];

    return (
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleBack}
            className="p-2 rounded-xl hover:bg-surface-secondary transition-colors"
            aria-label="Back"
          >
            <ArrowLeft className="h-5 w-5 text-text-secondary" />
          </button>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
              <Globe className="h-6 w-6 text-primary-500" />
              {selected.domain}
            </h1>
            <p className="text-sm text-text-secondary mt-0.5">
              {selected.completed_at ? `Completed ${formatDate(selected.completed_at)}` : ""}
            </p>
          </div>
          {statusBadge(selected.status)}
        </div>

        {/* Summary stat cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="p-4 flex items-center gap-4">
            <div className="h-10 w-10 rounded-xl bg-blue-50 flex items-center justify-center shrink-0">
              <BarChart2 className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-text-secondary">Total Articles</p>
              <p className="text-2xl font-bold text-text-primary">{selected.total_urls}</p>
            </div>
          </Card>

          <Card className="p-4 flex items-center gap-4">
            <div className="h-10 w-10 rounded-xl bg-purple-50 flex items-center justify-center shrink-0">
              <Search className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-xs text-text-secondary">Unique Keywords</p>
              <p className="text-2xl font-bold text-text-primary">{selected.total_keywords}</p>
            </div>
          </Card>

          <GapCountCard analysisId={selected.id} />
        </div>

        {/* Tabs */}
        <Card className="overflow-hidden">
          <div className="flex border-b border-surface-tertiary">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={clsx(
                  "px-5 py-3 text-sm font-medium transition-colors border-b-2 -mb-px",
                  activeTab === tab.key
                    ? "border-primary-500 text-primary-600"
                    : "border-transparent text-text-secondary hover:text-text-primary"
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="min-h-[300px]">
            {activeTab === "keywords" && <KeywordsTab analysisId={selected.id} />}
            {activeTab === "gaps" && <GapsTab analysisId={selected.id} />}
            {activeTab === "articles" && <ArticlesTab detail={selected} />}
          </div>
        </Card>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render: State 1 — failed result (show inline in State 1 area)
  // ---------------------------------------------------------------------------

  // ---------------------------------------------------------------------------
  // Render: State 1 — Input + History
  // ---------------------------------------------------------------------------

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
          <Target className="h-6 w-6 text-primary-500" />
          Competitor Analysis
        </h1>
        <p className="text-text-secondary mt-1">
          Enter a competitor domain to extract their content strategy and find keyword gaps.
        </p>
      </div>

      {/* Failed state inline banner (when a failed analysis is selected) */}
      {selected && selected.status === "failed" && (
        <Card className="p-4 border-red-200 bg-red-50 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-800">
              Analysis failed for {selected.domain}
            </p>
            {selected.error_message && (
              <p className="text-xs text-red-600 mt-0.5">{selected.error_message}</p>
            )}
          </div>
          <button
            onClick={() => setSelected(null)}
            className="text-xs text-red-600 hover:text-red-800"
          >
            Dismiss
          </button>
        </Card>
      )}

      {/* Domain input form */}
      <Card className="p-6">
        <h2 className="text-base font-semibold text-text-primary mb-4">Analyze a Competitor</h2>
        <form onSubmit={handleAnalyze} className="flex gap-3">
          <div className="relative flex-1">
            <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="e.g. competitor.com"
              className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-surface-tertiary bg-surface text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 transition-colors"
              disabled={submitting}
            />
          </div>
          <Button type="submit" disabled={submitting || !domain.trim()}>
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Analyzing...
              </>
            ) : (
              <>
                <Search className="h-4 w-4 mr-2" />
                Analyze
              </>
            )}
          </Button>
        </form>
      </Card>

      {/* History */}
      <div>
        <h2 className="text-base font-semibold text-text-primary mb-3">Previous Analyses</h2>

        {historyLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
          </div>
        ) : analyses.length === 0 ? (
          <Card className="p-8 text-center">
            <Globe className="h-10 w-10 text-surface-tertiary mx-auto mb-3" />
            <p className="text-text-secondary text-sm">
              No competitor analyses yet. Enter a domain above to get started.
            </p>
          </Card>
        ) : (
          <div className="space-y-3">
            {analyses.map((analysis) => (
              <Card
                key={analysis.id}
                className={clsx(
                  "p-4 flex items-center gap-4 cursor-pointer hover:bg-surface-secondary/50 transition-colors",
                  selectedLoading && "opacity-60 pointer-events-none"
                )}
                onClick={() => handleSelectAnalysis(analysis)}
              >
                <div className="h-10 w-10 rounded-xl bg-primary-50 flex items-center justify-center shrink-0">
                  <Globe className="h-5 w-5 text-primary-500" />
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-text-primary truncate">
                    {analysis.domain}
                  </p>
                  <p className="text-xs text-text-muted mt-0.5">
                    {formatDate(analysis.created_at)}
                    {analysis.total_keywords > 0 &&
                      ` · ${analysis.total_keywords} keywords`}
                    {analysis.total_urls > 0 &&
                      ` · ${analysis.total_urls} articles`}
                  </p>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {statusBadge(analysis.status)}
                  <button
                    onClick={(e) => handleDelete(analysis.id, e)}
                    aria-label={`Delete analysis for ${analysis.domain}`}
                    className="p-1.5 rounded-lg text-text-muted hover:text-red-500 hover:bg-red-50 transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Small helper component to fetch gap count for summary card
// ---------------------------------------------------------------------------

function GapCountCard({ analysisId }: { analysisId: string }) {
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    api.competitors
      .gaps(analysisId)
      .then((data) => setCount(data.total_gaps))
      .catch(() => setCount(null));
  }, [analysisId]);

  return (
    <Card className="p-4 flex items-center gap-4">
      <div className="h-10 w-10 rounded-xl bg-amber-50 flex items-center justify-center shrink-0">
        <Target className="h-5 w-5 text-amber-600" />
      </div>
      <div>
        <p className="text-xs text-text-secondary">Keyword Gaps</p>
        <p className="text-2xl font-bold text-text-primary">
          {count != null ? count : <span className="text-base text-text-muted">—</span>}
        </p>
      </div>
    </Card>
  );
}
