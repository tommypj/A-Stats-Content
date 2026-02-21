"use client";

import { useEffect, useState } from "react";
import { api, parseApiError } from "@/lib/api";
import type { AdminUserAnalytics, AdminContentAnalytics, AdminRevenueAnalytics, AdminAnalyticsParams } from "@/lib/api";
import { Calendar, TrendingUp, DollarSign, Users, FileText } from "lucide-react";
import { UserGrowthChart } from "@/components/admin/charts/user-growth-chart";
import { ContentChart } from "@/components/admin/charts/content-chart";
import { RevenueChart } from "@/components/admin/charts/revenue-chart";
import { SubscriptionChart } from "@/components/admin/charts/subscription-chart";

export default function AdminAnalyticsPage() {
  const [userAnalytics, setUserAnalytics] = useState<AdminUserAnalytics | null>(null);
  const [contentAnalytics, setContentAnalytics] = useState<AdminContentAnalytics | null>(null);
  const [revenueAnalytics, setRevenueAnalytics] = useState<AdminRevenueAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<{ start_date: string; end_date: string }>({
    start_date: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
    end_date: new Date().toISOString().split("T")[0],
  });

  useEffect(() => {
    loadAnalytics();
  }, [dateRange]);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: AdminAnalyticsParams = {
        start_date: dateRange.start_date,
        end_date: dateRange.end_date,
      };

      const [users, content, revenue] = await Promise.all([
        api.admin.analytics.users(params),
        api.admin.analytics.content(params),
        api.admin.analytics.revenue(params),
      ]);

      setUserAnalytics(users);
      setContentAnalytics(content);
      setRevenueAnalytics(revenue);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Analytics</h1>
          <p className="text-text-muted mt-1">
            Detailed platform analytics and insights
          </p>
        </div>
        <button
          onClick={loadAnalytics}
          className="px-4 py-2 bg-white border border-surface-tertiary rounded-lg hover:bg-surface-secondary text-sm font-medium"
        >
          Refresh
        </button>
      </div>

      {/* Date Range Selector */}
      <div className="bg-white rounded-xl border border-surface-tertiary p-4">
        <div className="flex items-center gap-4">
          <Calendar className="h-5 w-5 text-text-secondary" />
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-text-secondary">From:</label>
            <input
              type="date"
              value={dateRange.start_date}
              onChange={(e) => setDateRange({ ...dateRange, start_date: e.target.value })}
              className="px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <label className="text-sm font-medium text-text-secondary">To:</label>
            <input
              type="date"
              value={dateRange.end_date}
              onChange={(e) => setDateRange({ ...dateRange, end_date: e.target.value })}
              className="px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-red-600">{error}</p>
          <button
            onClick={loadAnalytics}
            className="mt-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
          >
            Retry
          </button>
        </div>
      )}

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-xl border border-surface-tertiary p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 rounded-lg bg-blue-50">
              <Users className="h-6 w-6 text-blue-600" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-text-primary mb-1">
            {loading ? "—" : userAnalytics?.total_users.toLocaleString()}
          </h3>
          <p className="text-sm text-text-muted">Total Users</p>
          {userAnalytics && (
            <p className="text-xs text-green-600 mt-2">
              +{userAnalytics.new_users} new
            </p>
          )}
        </div>

        <div className="bg-white rounded-xl border border-surface-tertiary p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 rounded-lg bg-green-50">
              <FileText className="h-6 w-6 text-green-600" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-text-primary mb-1">
            {loading ? "—" : contentAnalytics?.total_articles.toLocaleString()}
          </h3>
          <p className="text-sm text-text-muted">Total Articles</p>
          {contentAnalytics && (
            <p className="text-xs text-text-muted mt-2">
              Avg: {contentAnalytics.avg_articles_per_user.toFixed(1)} per user
            </p>
          )}
        </div>

        <div className="bg-white rounded-xl border border-surface-tertiary p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 rounded-lg bg-purple-50">
              <DollarSign className="h-6 w-6 text-purple-600" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-text-primary mb-1">
            {loading ? "—" : `$${revenueAnalytics?.total_revenue.toLocaleString()}`}
          </h3>
          <p className="text-sm text-text-muted">Total Revenue</p>
          {revenueAnalytics && (
            <p className="text-xs text-text-muted mt-2">
              MRR: ${revenueAnalytics.monthly_recurring_revenue.toLocaleString()}
            </p>
          )}
        </div>

        <div className="bg-white rounded-xl border border-surface-tertiary p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 rounded-lg bg-orange-50">
              <TrendingUp className="h-6 w-6 text-orange-600" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-text-primary mb-1">
            {loading ? "—" : `${userAnalytics?.retention_rate.toFixed(1)}%`}
          </h3>
          <p className="text-sm text-text-muted">Retention Rate</p>
          {revenueAnalytics && (
            <p className="text-xs text-text-muted mt-2">
              LTV: ${revenueAnalytics.lifetime_value.toFixed(0)}
            </p>
          )}
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* User Growth */}
        <div className="bg-white rounded-xl border border-surface-tertiary p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">
            User Growth
          </h2>
          {loading ? (
            <div className="h-[300px] flex items-center justify-center">
              <div className="h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : userAnalytics && userAnalytics.users_by_month.length > 0 ? (
            <UserGrowthChart data={userAnalytics.users_by_month} />
          ) : (
            <div className="h-[300px] flex items-center justify-center">
              <p className="text-text-muted">No data available</p>
            </div>
          )}
        </div>

        {/* Content Creation */}
        <div className="bg-white rounded-xl border border-surface-tertiary p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">
            Content Creation
          </h2>
          {loading ? (
            <div className="h-[300px] flex items-center justify-center">
              <div className="h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : contentAnalytics && contentAnalytics.content_by_month.length > 0 ? (
            <ContentChart data={contentAnalytics.content_by_month} />
          ) : (
            <div className="h-[300px] flex items-center justify-center">
              <p className="text-text-muted">No data available</p>
            </div>
          )}
        </div>

        {/* Revenue Trend */}
        <div className="bg-white rounded-xl border border-surface-tertiary p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">
            Revenue Trend
          </h2>
          {loading ? (
            <div className="h-[300px] flex items-center justify-center">
              <div className="h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : revenueAnalytics && revenueAnalytics.revenue_by_month.length > 0 ? (
            <RevenueChart data={revenueAnalytics.revenue_by_month} />
          ) : (
            <div className="h-[300px] flex items-center justify-center">
              <p className="text-text-muted">No data available</p>
            </div>
          )}
        </div>

        {/* Subscription Distribution */}
        <div className="bg-white rounded-xl border border-surface-tertiary p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">
            Users by Tier
          </h2>
          {loading ? (
            <div className="h-[300px] flex items-center justify-center">
              <div className="h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : userAnalytics && userAnalytics.users_by_tier.length > 0 ? (
            <SubscriptionChart data={userAnalytics.users_by_tier} />
          ) : (
            <div className="h-[300px] flex items-center justify-center">
              <p className="text-text-muted">No data available</p>
            </div>
          )}
        </div>
      </div>

      {/* Top Creators */}
      {contentAnalytics && contentAnalytics.top_creators.length > 0 && (
        <div className="bg-white rounded-xl border border-surface-tertiary p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">
            Top Content Creators
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-secondary">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                    Rank
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                    User
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-text-secondary uppercase">
                    Articles
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-tertiary">
                {contentAnalytics.top_creators.map((creator, index) => (
                  <tr key={creator.user_id} className="hover:bg-surface-secondary">
                    <td className="px-4 py-3 text-sm text-text-secondary">
                      #{index + 1}
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-text-primary">
                        {creator.user_name}
                      </p>
                      <p className="text-xs text-text-muted">
                        ID: {creator.user_id.substring(0, 8)}...
                      </p>
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-text-primary">
                      {creator.article_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
