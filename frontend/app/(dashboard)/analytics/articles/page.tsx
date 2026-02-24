"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  TrendingUp,
  TrendingDown,
  Minus,
  FileText,
  MousePointerClick,
  Eye,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";

import {
  api,
  parseApiError,
  ArticlePerformanceItem,
  ArticlePerformanceListResponse,
} from "@/lib/api";
import { StatCard } from "@/components/analytics/stat-card";
import { DateRangePicker } from "@/components/analytics/date-range-picker";
import { GscConnectBanner } from "@/components/analytics/gsc-connect-banner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type SortField = "total_clicks" | "total_impressions" | "avg_position" | "avg_ctr" | "published_at";
type SortOrder = "asc" | "desc";

export default function ArticlePerformancePage() {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);
  const [data, setData] = useState<ArticlePerformanceListResponse | null>(null);
  const [dateRange, setDateRange] = useState(28);
  const [sortField, setSortField] = useState<SortField>("total_clicks");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  useEffect(() => {
    checkStatus();
  }, []);

  useEffect(() => {
    if (isConnected) {
      loadData();
    }
  }, [isConnected, dateRange, sortField, sortOrder, currentPage]);

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

      const response = await api.analytics.articlePerformance({
        page: currentPage,
        page_size: pageSize,
        start_date: startDate,
        end_date: endDate,
        sort_by: sortField,
        sort_order: sortOrder,
      });
      setData(response);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to load article performance");
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

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
    setCurrentPage(1);
  }

  function SortIcon({ field }: { field: SortField }) {
    if (sortField !== field) return <ArrowUpDown className="h-4 w-4 opacity-30" />;
    return sortOrder === "asc" ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />;
  }

  function StatusBadge({ status }: { status: string }) {
    const styles = {
      improving: "bg-green-50 text-green-700 border-green-200",
      declining: "bg-red-50 text-red-700 border-red-200",
      neutral: "bg-gray-50 text-gray-700 border-gray-200",
      new: "bg-blue-50 text-blue-700 border-blue-200",
    };
    return (
      <span className={cn("px-2 py-0.5 text-xs font-medium rounded-full border", styles[status as keyof typeof styles] || styles.neutral)}>
        {status}
      </span>
    );
  }

  const formatNumber = (num: number) => new Intl.NumberFormat("en-US").format(Math.round(num));

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
          <h1 className="font-display text-3xl font-bold text-text-primary">Article Performance</h1>
          <p className="mt-2 text-text-secondary">
            Connect Google Search Console to track your published articles
          </p>
        </div>
        <GscConnectBanner onConnect={handleConnect} isLoading={isConnecting} />
      </div>
    );
  }

  const bestPerformer = data?.items.reduce((best, item) =>
    item.total_clicks > (best?.total_clicks || 0) ? item : best
  , data.items[0]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link href="/analytics" className="text-sm text-primary-600 hover:text-primary-700 mb-4 inline-block">
          ← Back to Analytics
        </Link>
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-text-primary">Article Performance</h1>
            <p className="mt-2 text-text-secondary">
              Track how your published articles perform in search
            </p>
          </div>
          <DateRangePicker value={dateRange} onChange={(v) => { setDateRange(v); setCurrentPage(1); }} />
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title="Total Published"
          value={data ? formatNumber(data.total_published_articles) : "0"}
          icon={FileText}
          trend="neutral"
        />
        <StatCard
          title="With GSC Data"
          value={data ? formatNumber(data.articles_with_data) : "0"}
          icon={Eye}
          trend="neutral"
        />
        <StatCard
          title="Best Performer"
          value={bestPerformer ? formatNumber(bestPerformer.total_clicks) + " clicks" : "N/A"}
          icon={MousePointerClick}
          trend="neutral"
        />
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-surface-tertiary">
                <tr>
                  <th className="text-left p-4 text-sm font-semibold text-text-primary">Title</th>
                  <th className="text-left p-4 text-sm font-semibold text-text-primary">Keyword</th>
                  <th className="text-right p-4 text-sm font-semibold text-text-primary">
                    <button onClick={() => handleSort("total_clicks")} className="flex items-center gap-2 hover:text-primary-600 ml-auto">
                      Clicks <SortIcon field="total_clicks" />
                    </button>
                  </th>
                  <th className="text-right p-4 text-sm font-semibold text-text-primary">
                    <button onClick={() => handleSort("total_impressions")} className="flex items-center gap-2 hover:text-primary-600 ml-auto">
                      Impressions <SortIcon field="total_impressions" />
                    </button>
                  </th>
                  <th className="text-right p-4 text-sm font-semibold text-text-primary">
                    <button onClick={() => handleSort("avg_ctr")} className="flex items-center gap-2 hover:text-primary-600 ml-auto">
                      CTR <SortIcon field="avg_ctr" />
                    </button>
                  </th>
                  <th className="text-right p-4 text-sm font-semibold text-text-primary">
                    <button onClick={() => handleSort("avg_position")} className="flex items-center gap-2 hover:text-primary-600 ml-auto">
                      Position <SortIcon field="avg_position" />
                    </button>
                  </th>
                  <th className="text-center p-4 text-sm font-semibold text-text-primary">Trend</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-b border-surface-tertiary">
                      {Array.from({ length: 7 }).map((_, j) => (
                        <td key={j} className="p-4">
                          <div className="h-4 bg-surface-tertiary animate-pulse rounded w-20" />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : !data?.items.length ? (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-text-muted">
                      No published articles found. Publish articles to WordPress to see performance data.
                    </td>
                  </tr>
                ) : (
                  data.items.map((article) => (
                    <tr
                      key={article.article_id}
                      className="border-b border-surface-tertiary hover:bg-surface-secondary transition-colors"
                    >
                      <td className="p-4 max-w-xs">
                        <Link
                          href={`/analytics/articles/${article.article_id}`}
                          className="text-sm font-medium text-text-primary hover:text-primary-600 line-clamp-2"
                        >
                          {article.title}
                        </Link>
                        {article.published_at && (
                          <p className="text-xs text-text-muted mt-1">
                            {new Date(article.published_at).toLocaleDateString("en-US")}
                          </p>
                        )}
                      </td>
                      <td className="p-4 text-sm text-text-secondary max-w-[150px] truncate">
                        {article.keyword}
                      </td>
                      <td className="p-4 text-sm text-text-primary text-right font-medium">
                        {formatNumber(article.total_clicks)}
                      </td>
                      <td className="p-4 text-sm text-text-primary text-right">
                        {formatNumber(article.total_impressions)}
                      </td>
                      <td className="p-4 text-sm text-text-primary text-right">
                        {(article.avg_ctr * 100).toFixed(2)}%
                      </td>
                      <td className="p-4 text-sm text-text-primary text-right">
                        {article.avg_position.toFixed(1)}
                      </td>
                      <td className="p-4 text-center">
                        <StatusBadge status={article.performance_status} />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div className="flex items-center justify-between p-4 border-t border-surface-tertiary">
              <div className="text-sm text-text-muted">
                Page {data.page} of {data.pages}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  leftIcon={<ChevronLeft className="h-4 w-4" />}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.min(data.pages, p + 1))}
                  disabled={currentPage === data.pages}
                  rightIcon={<ChevronRight className="h-4 w-4" />}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
