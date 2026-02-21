"use client";

import { useState, useEffect } from "react";
import { api, AdminDashboardStats } from "@/lib/api";
import { StatsCard } from "@/components/admin/stats-card";
import { ActivityFeed } from "@/components/admin/activity-feed";
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

const SUBSCRIPTION_COLORS = {
  free: "#94a3b8",
  starter: "#3b82f6",
  professional: "#8b5cf6",
  enterprise: "#f59e0b",
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
      console.error("Failed to load dashboard stats:", err);
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
          value={stats ? formatNumber(stats.total_users) : "0"}
          icon={Users}
          trend={stats?.users_trend}
          loading={loading}
          colorClass="bg-blue-500"
        />
        <StatsCard
          title="Total Articles"
          value={stats ? formatNumber(stats.total_articles) : "0"}
          icon={FileText}
          trend={stats?.articles_trend}
          loading={loading}
          colorClass="bg-green-500"
        />
        <StatsCard
          title="Monthly Revenue"
          value={stats ? formatCurrency(stats.total_revenue) : "$0"}
          icon={DollarSign}
          trend={stats?.revenue_trend}
          loading={loading}
          colorClass="bg-purple-500"
        />
        <StatsCard
          title="Active Subscriptions"
          value={stats ? formatNumber(stats.active_subscriptions) : "0"}
          icon={CreditCard}
          trend={stats?.subscriptions_trend}
          loading={loading}
          colorClass="bg-orange-500"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* New Users Chart */}
        <Card>
          <CardHeader>
            <CardTitle>New Users (Last 7 Days)</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="h-64 flex items-center justify-center">
                <div className="h-8 w-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : stats && stats.new_users_7d.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={stats.new_users_7d}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="date"
                    stroke="#6b7280"
                    fontSize={12}
                    tickFormatter={(value) => {
                      const date = new Date(value);
                      return `${date.getMonth() + 1}/${date.getDate()}`;
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
                    stroke="#8b5cf6"
                    strokeWidth={2}
                    dot={{ fill: "#8b5cf6", r: 4 }}
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
            ) : stats && stats.subscription_distribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={stats.subscription_distribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ tier, percentage }) =>
                      `${tier}: ${percentage.toFixed(1)}%`
                    }
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {stats.subscription_distribution.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={
                          SUBSCRIPTION_COLORS[
                            entry.tier.toLowerCase() as keyof typeof SUBSCRIPTION_COLORS
                          ] || "#94a3b8"
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

      {/* Activity Feed and Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ActivityFeed
          activities={stats?.recent_activity || []}
          loading={loading}
        />
        <QuickActions />
      </div>
    </div>
  );
}
