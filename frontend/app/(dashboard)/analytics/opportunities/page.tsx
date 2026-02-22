"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Zap,
  TrendingUp,
  AlertCircle,
  Lightbulb,
  Sparkles,
  CheckCircle2,
  ArrowRight,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";

import {
  api,
  parseApiError,
  KeywordOpportunity,
  ContentOpportunitiesResponse,
  ContentSuggestion,
} from "@/lib/api";
import { StatCard } from "@/components/analytics/stat-card";
import { DateRangePicker } from "@/components/analytics/date-range-picker";
import { GscConnectBanner } from "@/components/analytics/gsc-connect-banner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type Tab = "quick_wins" | "content_gaps" | "rising";

export default function ContentOpportunitiesPage() {
  const router = useRouter();
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);
  const [data, setData] = useState<ContentOpportunitiesResponse | null>(null);
  const [dateRange, setDateRange] = useState(28);
  const [activeTab, setActiveTab] = useState<Tab>("quick_wins");

  // Selection & AI suggestions
  const [selectedKeywords, setSelectedKeywords] = useState<Set<string>>(new Set());
  const [suggestions, setSuggestions] = useState<ContentSuggestion[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    checkStatus();
  }, []);

  useEffect(() => {
    if (isConnected) {
      loadData();
    }
  }, [isConnected, dateRange]);

  async function checkStatus() {
    try {
      setIsLoading(true);
      const status = await api.analytics.status();
      setIsConnected(status.connected && !!status.site_url);
    } catch (error) {
      console.error("Failed to check analytics status:", error);
    } finally {
      setIsLoading(false);
    }
  }

  async function loadData() {
    try {
      setIsLoading(true);
      const endDate = new Date().toISOString().split("T")[0];
      const startDate = new Date(Date.now() - dateRange * 86400000).toISOString().split("T")[0];

      const response = await api.analytics.opportunities({
        start_date: startDate,
        end_date: endDate,
      });
      setData(response);
      setSelectedKeywords(new Set());
      setSuggestions([]);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to load opportunities");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleConnect() {
    try {
      setIsConnecting(true);
      const response = await api.analytics.getAuthUrl();
      window.location.href = response.auth_url;
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to initiate Google connection");
      setIsConnecting(false);
    }
  }

  async function handleGenerateSuggestions() {
    if (selectedKeywords.size === 0) {
      toast.error("Select at least one keyword");
      return;
    }

    try {
      setIsGenerating(true);
      const response = await api.analytics.suggestContent(
        Array.from(selectedKeywords),
        Math.min(selectedKeywords.size * 2, 10),
      );
      setSuggestions(response.suggestions);
      toast.success(`Generated ${response.suggestions.length} content suggestions`);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to generate suggestions");
    } finally {
      setIsGenerating(false);
    }
  }

  function toggleKeyword(keyword: string) {
    setSelectedKeywords((prev) => {
      const next = new Set(prev);
      if (next.has(keyword)) {
        next.delete(keyword);
      } else if (next.size < 20) {
        next.add(keyword);
      } else {
        toast.error("Maximum 20 keywords can be selected");
      }
      return next;
    });
  }

  function navigateToOutline(keyword: string) {
    router.push(`/outlines?keyword=${encodeURIComponent(keyword)}`);
  }

  const formatNumber = (num: number) => new Intl.NumberFormat("en-US").format(Math.round(num));

  function getActiveItems(): KeywordOpportunity[] {
    if (!data) return [];
    switch (activeTab) {
      case "quick_wins": return data.quick_wins;
      case "content_gaps": return data.content_gaps;
      case "rising": return data.rising_keywords;
    }
  }

  if (isLoading && !isConnected) {
    return (
      <div className="space-y-6">
        <div className="h-32 bg-surface-tertiary animate-pulse rounded-2xl" />
      </div>
    );
  }

  if (!isConnected) {
    return (
      <div className="space-y-6">
        <div>
          <Link href="/analytics" className="text-sm text-primary-600 hover:text-primary-700 mb-4 inline-block">
            ← Back to Analytics
          </Link>
          <h1 className="font-display text-3xl font-bold text-text-primary">Content Opportunities</h1>
          <p className="mt-2 text-text-secondary">
            Connect Google Search Console to discover content opportunities
          </p>
        </div>
        <GscConnectBanner onConnect={handleConnect} isLoading={isConnecting} />
      </div>
    );
  }

  const tabs: { key: Tab; label: string; icon: typeof Zap; count: number }[] = [
    { key: "quick_wins", label: "Quick Wins", icon: Zap, count: data?.quick_wins.length || 0 },
    { key: "content_gaps", label: "Content Gaps", icon: AlertCircle, count: data?.content_gaps.length || 0 },
    { key: "rising", label: "Rising Keywords", icon: TrendingUp, count: data?.rising_keywords.length || 0 },
  ];

  const activeItems = getActiveItems();

  const difficultyColors = {
    easy: "bg-green-50 text-green-700 border-green-200",
    medium: "bg-amber-50 text-amber-700 border-amber-200",
    hard: "bg-red-50 text-red-700 border-red-200",
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link href="/analytics" className="text-sm text-primary-600 hover:text-primary-700 mb-4 inline-block">
          ← Back to Analytics
        </Link>
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-text-primary">Content Opportunities</h1>
            <p className="mt-2 text-text-secondary">
              Discover keyword opportunities and get AI-powered content suggestions
            </p>
          </div>
          <DateRangePicker value={dateRange} onChange={setDateRange} />
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Opportunities"
          value={data ? formatNumber(data.total_opportunities) : "0"}
          icon={Lightbulb}
          trend="neutral"
        />
        <StatCard
          title="Quick Wins"
          value={data ? formatNumber(data.quick_wins.length) : "0"}
          icon={Zap}
          trend="neutral"
        />
        <StatCard
          title="Content Gaps"
          value={data ? formatNumber(data.content_gaps.length) : "0"}
          icon={AlertCircle}
          trend="neutral"
        />
        <StatCard
          title="Rising Keywords"
          value={data ? formatNumber(data.rising_keywords.length) : "0"}
          icon={TrendingUp}
          trend="neutral"
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-surface-tertiary">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              "flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors -mb-px",
              activeTab === tab.key
                ? "border-primary-600 text-primary-600"
                : "border-transparent text-text-muted hover:text-text-primary hover:border-surface-tertiary"
            )}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
            <span className={cn(
              "px-1.5 py-0.5 text-xs rounded-full",
              activeTab === tab.key
                ? "bg-primary-100 text-primary-700"
                : "bg-surface-tertiary text-text-muted"
            )}>
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* Action Bar */}
      {selectedKeywords.size > 0 && (
        <div className="flex items-center justify-between p-4 bg-primary-50 border border-primary-200 rounded-xl">
          <span className="text-sm font-medium text-primary-700">
            {selectedKeywords.size} keyword{selectedKeywords.size > 1 ? "s" : ""} selected
          </span>
          <Button
            onClick={handleGenerateSuggestions}
            isLoading={isGenerating}
            leftIcon={<Sparkles className="h-4 w-4" />}
          >
            Get AI Suggestions
          </Button>
        </div>
      )}

      {/* Opportunities Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-surface-tertiary">
                <tr>
                  <th className="w-10 p-4">
                    <span className="sr-only">Select</span>
                  </th>
                  <th className="text-left p-4 text-sm font-semibold text-text-primary">Keyword</th>
                  <th className="text-right p-4 text-sm font-semibold text-text-primary">Impressions</th>
                  <th className="text-right p-4 text-sm font-semibold text-text-primary">Clicks</th>
                  <th className="text-right p-4 text-sm font-semibold text-text-primary">CTR</th>
                  <th className="text-right p-4 text-sm font-semibold text-text-primary">Position</th>
                  <th className="text-center p-4 text-sm font-semibold text-text-primary">Article?</th>
                  <th className="text-right p-4 text-sm font-semibold text-text-primary">Action</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-b border-surface-tertiary">
                      {Array.from({ length: 8 }).map((_, j) => (
                        <td key={j} className="p-4">
                          <div className="h-4 bg-surface-tertiary animate-pulse rounded w-16" />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : activeItems.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-text-muted">
                      No {activeTab === "quick_wins" ? "quick win" : activeTab === "content_gaps" ? "content gap" : "rising keyword"} opportunities found for this period.
                    </td>
                  </tr>
                ) : (
                  activeItems.map((item) => (
                    <tr
                      key={item.keyword}
                      className={cn(
                        "border-b border-surface-tertiary hover:bg-surface-secondary transition-colors",
                        selectedKeywords.has(item.keyword) && "bg-primary-50/50"
                      )}
                    >
                      <td className="p-4">
                        <input
                          type="checkbox"
                          checked={selectedKeywords.has(item.keyword)}
                          onChange={() => toggleKeyword(item.keyword)}
                          className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                      </td>
                      <td className="p-4 text-sm font-medium text-text-primary max-w-xs truncate">
                        {item.keyword}
                      </td>
                      <td className="p-4 text-sm text-text-primary text-right">
                        {formatNumber(item.impressions)}
                      </td>
                      <td className="p-4 text-sm text-text-primary text-right">
                        {formatNumber(item.clicks)}
                      </td>
                      <td className="p-4 text-sm text-text-primary text-right">
                        {(item.ctr * 100).toFixed(2)}%
                      </td>
                      <td className="p-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <span className="text-sm text-text-primary">{item.position.toFixed(1)}</span>
                          {item.position_change !== 0 && (
                            <span className={cn(
                              "text-xs font-medium",
                              item.position_change > 0 ? "text-green-600" : "text-red-600"
                            )}>
                              {item.position_change > 0 ? "+" : ""}{item.position_change.toFixed(1)}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="p-4 text-center">
                        {item.has_existing_article ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500 mx-auto" />
                        ) : (
                          <span className="text-xs text-text-muted">—</span>
                        )}
                      </td>
                      <td className="p-4 text-right">
                        {!item.has_existing_article ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => navigateToOutline(item.keyword)}
                          >
                            Create Article
                          </Button>
                        ) : item.existing_article_id ? (
                          <Link
                            href={`/articles`}
                            className="text-sm text-primary-600 hover:text-primary-700"
                          >
                            View
                          </Link>
                        ) : null}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* AI Suggestions Panel */}
      {suggestions.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-amber-500" />
            <h2 className="font-display text-xl font-bold text-text-primary">AI Content Suggestions</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {suggestions.map((suggestion, index) => (
              <Card key={index} className="hover:shadow-lg transition-shadow">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-base leading-snug">{suggestion.suggested_title}</CardTitle>
                    <span className={cn(
                      "px-2 py-0.5 text-xs font-medium rounded-full border whitespace-nowrap",
                      difficultyColors[suggestion.estimated_difficulty]
                    )}>
                      {suggestion.estimated_difficulty}
                    </span>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <p className="text-xs font-semibold uppercase text-text-muted mb-1">Target Keyword</p>
                    <p className="text-sm text-text-primary">{suggestion.target_keyword}</p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase text-text-muted mb-1">Content Angle</p>
                    <p className="text-sm text-text-secondary">{suggestion.content_angle}</p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase text-text-muted mb-1">Rationale</p>
                    <p className="text-sm text-text-secondary">{suggestion.rationale}</p>
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-surface-tertiary">
                    <span className="text-xs text-text-muted">~{formatNumber(suggestion.estimated_word_count)} words</span>
                    <Button
                      size="sm"
                      onClick={() => navigateToOutline(suggestion.target_keyword)}
                      rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
                    >
                      Create Outline
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
