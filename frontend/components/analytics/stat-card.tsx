"use client";

import { LucideIcon, TrendingUp, TrendingDown } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: LucideIcon;
  trend?: "up" | "down" | "neutral";
  isLoading?: boolean;
}

export function StatCard({
  title,
  value,
  change,
  icon: Icon,
  trend = "neutral",
  isLoading = false,
}: StatCardProps) {
  const isPositive = trend === "up";
  const isNegative = trend === "down";

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-text-secondary">{title}</p>
            {isLoading ? (
              <div className="mt-2 h-8 w-24 bg-surface-tertiary animate-pulse rounded" />
            ) : (
              <p className="mt-2 text-3xl font-display font-semibold text-text-primary">
                {value}
              </p>
            )}
            {change !== undefined && !isLoading && (
              <div className="mt-2 flex items-center gap-1">
                {isPositive && (
                  <TrendingUp className="h-4 w-4 text-green-600" />
                )}
                {isNegative && (
                  <TrendingDown className="h-4 w-4 text-red-600" />
                )}
                <span
                  className={cn(
                    "text-sm font-medium",
                    isPositive && "text-green-600",
                    isNegative && "text-red-600",
                    !isPositive && !isNegative && "text-text-muted"
                  )}
                >
                  {change > 0 ? "+" : ""}
                  {change.toFixed(1)}%
                </span>
                <span className="text-xs text-text-muted ml-1">vs last period</span>
              </div>
            )}
          </div>
          <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center">
            <Icon className="h-6 w-6 text-white" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
