"use client";

import { Card, CardContent } from "@/components/ui/card";
import { TrendData } from "@/lib/api";
import { LucideIcon, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatsCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: TrendData;
  loading?: boolean;
  colorClass?: string;
}

export function StatsCard({
  title,
  value,
  icon: Icon,
  trend,
  loading,
  colorClass = "bg-primary-500",
}: StatsCardProps) {
  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="h-4 bg-surface-tertiary rounded w-24 mb-2 animate-pulse" />
              <div className="h-8 bg-surface-tertiary rounded w-32 animate-pulse" />
            </div>
            <div className={cn("h-12 w-12 rounded-lg bg-surface-tertiary animate-pulse")} />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-text-secondary">{title}</p>
            <h3 className="text-3xl font-bold text-text-primary mt-1">{value}</h3>
            {trend && (
              <div className="flex items-center gap-1 mt-2">
                {trend.trend === "up" && (
                  <TrendingUp className="h-4 w-4 text-green-600" />
                )}
                {trend.trend === "down" && (
                  <TrendingDown className="h-4 w-4 text-red-600" />
                )}
                {trend.trend === "stable" && (
                  <Minus className="h-4 w-4 text-text-muted" />
                )}
                <span
                  className={cn(
                    "text-sm font-medium",
                    trend.trend === "up" && "text-green-600",
                    trend.trend === "down" && "text-red-600",
                    trend.trend === "stable" && "text-text-muted"
                  )}
                >
                  {trend.change_percent > 0 ? "+" : ""}
                  {trend.change_percent.toFixed(1)}%
                </span>
                <span className="text-xs text-text-muted ml-1">vs last period</span>
              </div>
            )}
          </div>
          <div
            className={cn(
              "h-12 w-12 rounded-lg flex items-center justify-center",
              colorClass
            )}
          >
            <Icon className="h-6 w-6 text-white" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
