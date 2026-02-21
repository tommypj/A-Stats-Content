"use client";

import { SocialAnalytics } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Heart, MessageCircle, Share2, Eye, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface PostAnalyticsCardProps {
  analytics: SocialAnalytics[];
  className?: string;
}

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  subValue?: string;
  trend?: "up" | "down" | "neutral";
  className?: string;
}

function MetricCard({ icon, label, value, subValue, trend, className }: MetricCardProps) {
  return (
    <div className={cn("flex items-start gap-3 p-4 bg-surface-secondary rounded-lg", className)}>
      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center text-primary-500">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-text-secondary mb-1">{label}</p>
        <p className="text-2xl font-bold">{value.toLocaleString()}</p>
        {subValue && (
          <p className="text-xs text-text-secondary mt-1">{subValue}</p>
        )}
        {trend && (
          <div
            className={cn(
              "inline-flex items-center gap-1 text-xs mt-1",
              trend === "up" && "text-green-600",
              trend === "down" && "text-red-600",
              trend === "neutral" && "text-text-secondary"
            )}
          >
            {trend === "up" && <TrendingUp className="h-3 w-3" />}
            {trend === "down" && <TrendingUp className="h-3 w-3 rotate-180" />}
            {trend !== "neutral" && <span>{trend === "up" ? "Increasing" : "Decreasing"}</span>}
          </div>
        )}
      </div>
    </div>
  );
}

export function PostAnalyticsCard({ analytics, className }: PostAnalyticsCardProps) {
  // Aggregate analytics from all platforms
  const totalLikes = analytics.reduce((sum, a) => sum + a.likes, 0);
  const totalComments = analytics.reduce((sum, a) => sum + a.comments, 0);
  const totalShares = analytics.reduce((sum, a) => sum + a.shares, 0);
  const totalImpressions = analytics.reduce((sum, a) => sum + a.impressions, 0);
  const avgEngagementRate =
    analytics.length > 0
      ? analytics.reduce((sum, a) => sum + a.engagement_rate, 0) / analytics.length
      : 0;

  if (analytics.length === 0) {
    return (
      <Card className={cn("p-6", className)}>
        <p className="text-center text-text-secondary">No analytics available yet</p>
      </Card>
    );
  }

  return (
    <Card className={cn("p-6", className)}>
      <h3 className="text-lg font-semibold mb-4">Engagement Metrics</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          icon={<Heart className="h-5 w-5" />}
          label="Total Likes"
          value={totalLikes}
        />
        <MetricCard
          icon={<MessageCircle className="h-5 w-5" />}
          label="Total Comments"
          value={totalComments}
        />
        <MetricCard
          icon={<Share2 className="h-5 w-5" />}
          label="Total Shares"
          value={totalShares}
        />
        <MetricCard
          icon={<Eye className="h-5 w-5" />}
          label="Total Impressions"
          value={totalImpressions}
        />
        <MetricCard
          icon={<TrendingUp className="h-5 w-5" />}
          label="Engagement Rate"
          value={parseFloat(avgEngagementRate.toFixed(2))}
          subValue={`${avgEngagementRate.toFixed(2)}%`}
        />
        <MetricCard
          icon={<TrendingUp className="h-5 w-5" />}
          label="Total Engagement"
          value={totalLikes + totalComments + totalShares}
          subValue={`Across ${analytics.length} platform${analytics.length > 1 ? "s" : ""}`}
        />
      </div>

      {/* Platform Breakdown */}
      <div className="mt-6">
        <h4 className="text-sm font-semibold text-text-secondary mb-3">Platform Breakdown</h4>
        <div className="space-y-2">
          {analytics.map((platformAnalytics) => (
            <div
              key={platformAnalytics.platform}
              className="flex items-center justify-between p-3 bg-surface-secondary rounded-lg"
            >
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium capitalize">
                  {platformAnalytics.platform}
                </span>
              </div>
              <div className="flex items-center gap-6 text-sm text-text-secondary">
                <div className="flex items-center gap-1">
                  <Heart className="h-4 w-4" />
                  <span>{platformAnalytics.likes}</span>
                </div>
                <div className="flex items-center gap-1">
                  <MessageCircle className="h-4 w-4" />
                  <span>{platformAnalytics.comments}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Share2 className="h-4 w-4" />
                  <span>{platformAnalytics.shares}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Eye className="h-4 w-4" />
                  <span>{platformAnalytics.impressions}</span>
                </div>
                <div className="font-medium text-primary-500">
                  {platformAnalytics.engagement_rate.toFixed(2)}%
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
