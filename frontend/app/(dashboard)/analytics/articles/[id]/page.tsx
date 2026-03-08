"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  MousePointerClick,
  Eye,
  TrendingUp,
  Target,
  ExternalLink,
  Edit3,
  Search,
  Loader2,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Smartphone,
  Clock,
} from "lucide-react";
import { toast } from "sonner";

import {
  api,
  parseApiError,
  ArticlePerformanceDetailResponse,
  URLInspectionResponse,
} from "@/lib/api";
import { StatCard } from "@/components/analytics/stat-card";
import { PerformanceChart } from "@/components/analytics/performance-chart";
import { DateRangePicker } from "@/components/analytics/date-range-picker";
import { GscConnectBanner } from "@/components/analytics/gsc-connect-banner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ArticlePerformanceDetailPage() {
  const params = useParams();
  const articleId = params.id as string;

  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);
  const [data, setData] = useState<ArticlePerformanceDetailResponse | null>(null);
  const [dateRange, setDateRange] = useState(28);
  const [indexStatus, setIndexStatus] = useState<URLInspectionResponse | null>(null);
  const [isCheckingIndex, setIsCheckingIndex] = useState(false);

  useEffect(() => {
    checkStatus();
  }, []);

  useEffect(() => {
    if (isConnected && articleId) {
      loadData();
    }
  }, [isConnected, articleId, dateRange]);

  async function checkStatus() {
    try {
      setIsLoading(true);
      const status = await api.analytics.status();
      setIsConnected(status.connected && !!status.site_url);
    } catch (error) {
      toast.error("Failed to check analytics status");
    } finally {
      setIsLoading(false);
    }
  }

  async function loadData() {
    try {
      setIsLoading(true);
      const endDate = new Date().toISOString().split("T")[0];
      const startDate = new Date(Date.now() - dateRange * 86400000).toISOString().split("T")[0];

      const response = await api.analytics.articlePerformanceDetail(articleId, {
        start_date: startDate,
        end_date: endDate,
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
      localStorage.setItem("gsc_oauth_state", response.state);
      localStorage.setItem("gsc_oauth_state_ts", Date.now().toString());
      window.location.href = response.auth_url;
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to initiate Google connection");
      setIsConnecting(false);
    }
  }

  async function checkIndexStatus() {
    try {
      setIsCheckingIndex(true);
      const result = await api.analytics.articleIndexStatus(articleId);
      setIndexStatus(result);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to check index status");
    } finally {
      setIsCheckingIndex(false);
    }
  }

  const formatNumber = (num: number) => new Intl.NumberFormat("en-US").format(Math.round(num));
  const formatPercentage = (num: number) => `${(num * 100).toFixed(2)}%`;
  const formatPosition = (num: number) => num.toFixed(1);

  if (isLoading && !data) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-surface-tertiary animate-pulse rounded w-48" />
        <div className="h-32 bg-surface-tertiary animate-pulse rounded-2xl" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-40 bg-surface-tertiary animate-pulse rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  if (!isConnected) {
    return (
      <div className="space-y-6">
        <div>
          <Link href="/analytics/articles" className="text-sm text-primary-600 hover:text-primary-700 mb-4 inline-block">
            ← Back to Article Performance
          </Link>
          <h1 className="font-display text-2xl font-bold text-text-primary">Article Detail</h1>
        </div>
        <GscConnectBanner onConnect={handleConnect} isLoading={isConnecting} />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-6">
        <Link href="/analytics/articles" className="text-sm text-primary-600 hover:text-primary-700 mb-4 inline-block">
          ← Back to Article Performance
        </Link>
        <div className="text-center py-12 text-text-muted">Article not found or has no published URL.</div>
      </div>
    );
  }

  // Transform daily_data to the format PerformanceChart expects
  const chartData = data.daily_data.map((d) => ({
    id: d.date,
    date: d.date,
    total_clicks: d.clicks,
    total_impressions: d.impressions,
    avg_ctr: d.ctr,
    avg_position: d.position,
    created_at: d.date,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link href="/analytics/articles" className="text-sm text-primary-600 hover:text-primary-700 mb-4 inline-block">
          ← Back to Article Performance
        </Link>
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div className="flex-1 min-w-0">
            <h1 className="font-display text-2xl font-bold text-text-primary">{data.title}</h1>
            <div className="mt-2 flex items-center gap-4 flex-wrap text-sm text-text-secondary">
              <span>Keyword: <span className="font-medium text-text-primary">{data.keyword}</span></span>
              {data.published_at && (
                <span>Published: {new Date(data.published_at).toLocaleDateString("en-US")}</span>
              )}
              {data.seo_score !== null && data.seo_score !== undefined && (
                <span>SEO Score: <span className="font-medium text-text-primary">{data.seo_score}</span></span>
              )}
            </div>
            <div className="mt-2 flex items-center gap-3">
              <a
                href={data.published_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-primary-600 hover:text-primary-700"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                View live article
              </a>
              <Link
                href={`/articles`}
                className="inline-flex items-center gap-1.5 text-sm text-primary-600 hover:text-primary-700"
              >
                <Edit3 className="h-3.5 w-3.5" />
                Edit article
              </Link>
            </div>
          </div>
          <DateRangePicker value={dateRange} onChange={setDateRange} />
        </div>
      </div>

      {/* Index Status */}
      <Card>
        <CardContent className="py-4">
          {!indexStatus && !isCheckingIndex ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Search className="h-5 w-5 text-text-muted" />
                <div>
                  <p className="text-sm font-medium text-text-primary">Google Index Status</p>
                  <p className="text-xs text-text-muted">Check if this page is indexed by Google</p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={checkIndexStatus}>
                Check Status
              </Button>
            </div>
          ) : isCheckingIndex ? (
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-primary-500" />
              <p className="text-sm text-text-secondary">Checking index status...</p>
            </div>
          ) : indexStatus ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {indexStatus.verdict === "PASS" ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : indexStatus.verdict === "FAIL" ? (
                    <XCircle className="h-5 w-5 text-red-500" />
                  ) : (
                    <AlertTriangle className="h-5 w-5 text-yellow-500" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-text-primary">
                      {indexStatus.verdict === "PASS"
                        ? "Indexed"
                        : indexStatus.verdict === "FAIL"
                        ? "Not Indexed"
                        : "Partially Indexed"}
                    </p>
                    {indexStatus.coverage_state && (
                      <p className="text-xs text-text-muted">{indexStatus.coverage_state}</p>
                    )}
                  </div>
                </div>
                <Button variant="ghost" size="sm" onClick={checkIndexStatus}>
                  Refresh
                </Button>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2 border-t border-surface-tertiary">
                {indexStatus.last_crawl_time && (
                  <div className="flex items-start gap-2">
                    <Clock className="h-4 w-4 text-text-muted mt-0.5" />
                    <div>
                      <p className="text-xs text-text-muted">Last Crawled</p>
                      <p className="text-sm font-medium text-text-primary">
                        {new Date(indexStatus.last_crawl_time).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </p>
                    </div>
                  </div>
                )}
                <div className="flex items-start gap-2">
                  <Smartphone className="h-4 w-4 text-text-muted mt-0.5" />
                  <div>
                    <p className="text-xs text-text-muted">Crawled As</p>
                    <p className="text-sm font-medium text-text-primary">
                      {indexStatus.crawled_as ? indexStatus.crawled_as.replace("_", " ") : "—"}
                    </p>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Mobile Usability</p>
                  <p className={`text-sm font-medium ${
                    indexStatus.mobile_usability_verdict === "PASS"
                      ? "text-green-600"
                      : indexStatus.mobile_usability_verdict === "FAIL"
                      ? "text-red-600"
                      : "text-text-muted"
                  }`}>
                    {indexStatus.mobile_usability_verdict === "PASS"
                      ? "Passed"
                      : indexStatus.mobile_usability_verdict === "FAIL"
                      ? "Issues Found"
                      : "—"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Rich Results</p>
                  <p className={`text-sm font-medium ${
                    indexStatus.rich_results_verdict === "PASS"
                      ? "text-green-600"
                      : indexStatus.rich_results_verdict === "FAIL"
                      ? "text-red-600"
                      : "text-text-muted"
                  }`}>
                    {indexStatus.rich_results_verdict === "PASS"
                      ? "Eligible"
                      : indexStatus.rich_results_verdict === "FAIL"
                      ? "Not Eligible"
                      : "—"}
                  </p>
                </div>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Clicks"
          value={formatNumber(data.total_clicks)}
          change={data.clicks_trend?.change_percent}
          icon={MousePointerClick}
          trend={data.clicks_trend?.trend || "neutral"}
        />
        <StatCard
          title="Total Impressions"
          value={formatNumber(data.total_impressions)}
          change={data.impressions_trend?.change_percent}
          icon={Eye}
          trend={data.impressions_trend?.trend || "neutral"}
        />
        <StatCard
          title="Average CTR"
          value={formatPercentage(data.avg_ctr)}
          change={data.ctr_trend?.change_percent}
          icon={TrendingUp}
          trend={data.ctr_trend?.trend || "neutral"}
        />
        <StatCard
          title="Average Position"
          value={formatPosition(data.avg_position)}
          change={data.position_trend?.change_percent}
          icon={Target}
          trend={
            data.position_trend?.trend
              ? data.position_trend.trend === "down" ? "up"
              : data.position_trend.trend === "up" ? "down"
              : "neutral"
              : "neutral"
          }
        />
      </div>

      {/* Performance Chart */}
      {chartData.length > 0 ? (
        <PerformanceChart data={chartData} />
      ) : (
        <Card>
          <CardContent className="py-12 text-center text-text-muted">
            No daily performance data available for this period.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
