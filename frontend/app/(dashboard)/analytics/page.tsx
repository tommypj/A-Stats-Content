"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  MousePointerClick,
  Eye,
  TrendingUp,
  Target,
  RefreshCw,
  ArrowRight,
} from "lucide-react";
import { toast } from "sonner";

import { api, parseApiError, AnalyticsSummary, DailyAnalyticsData } from "@/lib/api";
import { StatCard } from "@/components/analytics/stat-card";
import { PerformanceChart } from "@/components/analytics/performance-chart";
import { DateRangePicker } from "@/components/analytics/date-range-picker";
import { GscConnectBanner } from "@/components/analytics/gsc-connect-banner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AnalyticsPage() {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [dateRange, setDateRange] = useState(28);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [dailyData, setDailyData] = useState<DailyAnalyticsData[]>([]);
  const [lastSync, setLastSync] = useState<string | null>(null);

  useEffect(() => {
    checkStatus();
  }, []);

  useEffect(() => {
    if (isConnected) {
      loadAnalytics();
    }
  }, [isConnected, dateRange]);

  async function checkStatus() {
    try {
      setIsLoading(true);
      const status = await api.analytics.status();
      setIsConnected(status.connected);
      setLastSync(status.last_sync || null);
    } catch (error) {
      console.error("Failed to check analytics status:", error);
    } finally {
      setIsLoading(false);
    }
  }

  async function loadAnalytics() {
    try {
      const [summaryData, dailyResponse] = await Promise.all([
        api.analytics.summary(),
        api.analytics.daily({ page: 1, page_size: dateRange }),
      ]);
      setSummary(summaryData);
      setDailyData(dailyResponse.items);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to load analytics data");
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

  async function handleSync() {
    try {
      setIsSyncing(true);
      await api.analytics.sync();
      toast.success("Analytics data synced successfully!");
      await loadAnalytics();
      await checkStatus();
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to sync analytics data");
    } finally {
      setIsSyncing(false);
    }
  }

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("en-US").format(Math.round(num));
  };

  const formatPercentage = (num: number) => {
    return `${(num * 100).toFixed(2)}%`;
  };

  const formatPosition = (num: number) => {
    return num.toFixed(1);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
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
          <h1 className="font-display text-3xl font-bold text-text-primary">Analytics</h1>
          <p className="mt-2 text-text-secondary">
            Track your website performance with Google Search Console
          </p>
        </div>
        <GscConnectBanner onConnect={handleConnect} isLoading={isConnecting} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-text-primary">Analytics</h1>
          <p className="mt-2 text-text-secondary">
            Track your search performance and rankings
            {lastSync && (
              <span className="ml-2 text-xs">
                Last synced: {new Date(lastSync).toLocaleDateString()}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <DateRangePicker value={dateRange} onChange={setDateRange} />
          <Button
            variant="outline"
            onClick={handleSync}
            isLoading={isSyncing}
            leftIcon={<RefreshCw className="h-4 w-4" />}
          >
            Sync Data
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Clicks"
          value={summary ? formatNumber(summary.total_clicks) : "0"}
          change={summary?.clicks_trend?.change_percent}
          icon={MousePointerClick}
          trend={summary?.clicks_trend?.trend || "neutral"}
        />
        <StatCard
          title="Total Impressions"
          value={summary ? formatNumber(summary.total_impressions) : "0"}
          change={summary?.impressions_trend?.change_percent}
          icon={Eye}
          trend={summary?.impressions_trend?.trend || "neutral"}
        />
        <StatCard
          title="Average CTR"
          value={summary ? formatPercentage(summary.avg_ctr) : "0%"}
          change={summary?.ctr_trend?.change_percent}
          icon={TrendingUp}
          trend={summary?.ctr_trend?.trend || "neutral"}
        />
        <StatCard
          title="Average Position"
          value={summary ? formatPosition(summary.avg_position) : "0"}
          change={summary?.position_trend?.change_percent}
          icon={Target}
          trend={
            summary?.position_trend?.trend
              ? summary.position_trend.trend === "down"
                ? "up"
                : summary.position_trend.trend === "up"
                ? "down"
                : "neutral"
              : "neutral"
          }
        />
      </div>

      {/* Performance Chart */}
      <PerformanceChart data={dailyData} />

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <Link href="/analytics/keywords">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Keyword Rankings
                <ArrowRight className="h-5 w-5 text-text-muted" />
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-text-secondary">
                View detailed keyword performance, rankings, and opportunities
              </p>
            </CardContent>
          </Link>
        </Card>

        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <Link href="/analytics/pages">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Page Performance
                <ArrowRight className="h-5 w-5 text-text-muted" />
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-text-secondary">
                Analyze which pages are performing best and identify improvements
              </p>
            </CardContent>
          </Link>
        </Card>
      </div>
    </div>
  );
}
