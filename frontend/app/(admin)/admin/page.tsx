"use client";

import { useState, useEffect } from "react";
import { api, AdminDashboardStats } from "@/lib/api";
import { StatsCard } from "@/components/admin/stats-card";
import { QuickActions } from "@/components/admin/quick-actions";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Users,
  FileText,
  DollarSign,
  CreditCard,
} from "lucide-react";
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const SUBSCRIPTION_COLORS: Record<string, string> = {
  free: "#94a3b8",
  starter: "#627862",
  professional: "#a17d66",
  enterprise: "#bc7a5c",
};

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardStats();
  }, []);

  const loadDashboardStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.admin.dashboard();
      setStats(data);
    } catch (err) {
      setError("Failed to load dashboard statistics");
    } finally {
      setLoading(false);
    }
  };

  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Format number with commas
  const formatNumber = (value: number) => {
    return new Intl.NumberFormat("en-US").format(value);
  };

  // Build subscription distribution for pie chart
  // FE-ADMIN-02: Guard against null/undefined fields to prevent PieChart crash
  const subscriptionDistribution = (stats
    ? [
        { tier: "Free", count: stats.subscriptions?.free_tier ?? 0 },
        { tier: "Starter", count: stats.subscriptions?.starter_tier ?? 0 },
        { tier: "Professional", count: stats.subscriptions?.professional_tier ?? 0 },
        { tier: "Enterprise", count: stats.subscriptions?.enterprise_tier ?? 0 },
      ].filter((d) => d.count > 0)
    : []).filter(Boolean);

  const totalSubscribers = subscriptionDistribution.reduce((sum, d) => sum + d.count, 0);

  // Build usage chart data
  const usageChartData = stats
    ? stats.platform_usage_7d.map((d) => ({ date: d.date, count: d.value }))
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Admin Dashboard</h1>
          <p className="text-text-secondary mt-1">
            System overview and key metrics
          </p>
        </div>
        <Button
          onClick={loadDashboardStats}
          variant="outline"
          size="md"
        >
          Refresh
        </Button>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-600">{error}</p>
          <Button
            onClick={loadDashboardStats}
            variant="destructive"
            size="sm"
            className="mt-2"
          >
            Retry
          </Button>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Users"
          value={stats ? formatNumber(stats.users.total_users) : "0"}
          icon={Users}
          loading={loading}
          colorClass="bg-blue-500"
        />
        <StatsCard
          title="Total Articles"
          value={stats ? formatNumber(stats.content.total_articles) : "0"}
          icon={FileText}
          loading={loading}
          colorClass="bg-green-500"
        />
        <StatsCard
          title="Monthly Revenue"
          value={stats ? formatCurrency(stats.revenue.monthly_recurring_revenue) : "$0"}
          icon={DollarSign}
          loading={loading}
          colorClass="bg-purple-500"
        />
        <StatsCard
          title="Active Subscriptions"
          value={stats ? formatNumber(stats.subscriptions.active_subscriptions) : "0"}
          icon={CreditCard}
          loading={loading}
          colorClass="bg-orange-500"
        />
      </div>

      {/* Secondary Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-text-secondary">New Users (Week)</p>
              <p className="text-xl font-bold text-text-primary mt-1">{formatNumber(stats.users.new_users_this_week)}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-text-secondary">Articles (Month)</p>
              <p className="text-xl font-bold text-text-primary mt-1">{formatNumber(stats.content.articles_this_month)}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-text-secondary">Outlines (Month)</p>
              <p className="text-xl font-bold text-text-primary mt-1">{formatNumber(stats.content.outlines_this_month)}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-text-secondary">Images (Month)</p>
              <p className="text-xl font-bold text-text-primary mt-1">{formatNumber(stats.content.images_this_month)}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Users Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Active Users (Last 7 Days)</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="h-64 flex items-center justify-center">
                <div className="h-8 w-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : usageChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={usageChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="date"
                    stroke="#6b7280"
                    fontSize={12}
                    tickFormatter={(value) => {
                      try {
                        return new Date(value).toLocaleDateString();
                      } catch {
                        return value;
                      }
                    }}
                  />
                  <YAxis stroke="#6b7280" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#fff",
                      border: "1px solid #e5e7eb",
                      borderRadius: "8px",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="count"
                    stroke="#627862"
                    strokeWidth={2}
                    dot={{ fill: "#627862", r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex items-center justify-center">
                <p className="text-text-muted">No data available</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Subscription Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Subscription Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="h-64 flex items-center justify-center">
                <div className="h-8 w-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : subscriptionDistribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={subscriptionDistribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ tier, count }) =>
                      `${tier}: ${totalSubscribers > 0 ? ((count / totalSubscribers) * 100).toFixed(1) : 0}%`
                    }
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {subscriptionDistribution.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={
                          SUBSCRIPTION_COLORS[entry.tier.toLowerCase()] || "#94a3b8"
                        }
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#fff",
                      border: "1px solid #e5e7eb",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex items-center justify-center">
                <p className="text-text-muted">No data available</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <QuickActions />
    </div>
  );
}
