"use client";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { ProjectSubscription } from "@/lib/api";
import { CreditCard, TrendingUp, ExternalLink } from "lucide-react";

interface ProjectBillingCardProps {
  subscription: ProjectSubscription;
  onUpgrade: () => void;
  onManageBilling: () => void;
  onCancel: () => void;
}

const tierLabels = {
  free: "Free",
  starter: "Starter",
  professional: "Professional",
  enterprise: "Enterprise",
};

const tierColors = {
  free: "bg-gray-100 text-gray-800",
  starter: "bg-blue-100 text-blue-800",
  professional: "bg-purple-100 text-purple-800",
  enterprise: "bg-orange-100 text-orange-800",
};

export function ProjectBillingCard({
  subscription,
  onUpgrade,
  onManageBilling,
  onCancel,
}: ProjectBillingCardProps) {
  const isFreePlan = subscription.subscription_tier === "free";
  const hasActiveSubscription = subscription.subscription_status === "active";

  const getUsagePercentage = (used: number, limit: number) => {
    if (limit === 0) return 0;
    return Math.min((used / limit) * 100, 100);
  };

  const getUsageColor = (percentage: number) => {
    if (percentage < 75) return "text-green-600";
    if (percentage < 90) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <div className="space-y-6">
      {/* Current Plan */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary">Current Plan</h3>
          <Badge className={tierColors[subscription.subscription_tier]}>
            {tierLabels[subscription.subscription_tier]}
          </Badge>
        </div>

        <div className="space-y-4">
          <div>
            <p className="text-sm text-text-secondary mb-1">Status</p>
            <p className="font-medium text-text-primary capitalize">
              {subscription.subscription_status}
            </p>
            {subscription.subscription_expires && (
              <p className="text-sm text-text-muted mt-1">
                Expires: {new Date(subscription.subscription_expires).toLocaleDateString()}
              </p>
            )}
          </div>

          {isFreePlan && (
            <div className="p-4 rounded-lg bg-primary-50 border border-primary-200">
              <div className="flex items-start gap-3">
                <TrendingUp className="h-5 w-5 text-primary-600 mt-0.5" />
                <div>
                  <p className="font-medium text-primary-800 mb-1">Upgrade to unlock more</p>
                  <p className="text-sm text-primary-700">
                    Get unlimited access to all features with a paid plan
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="flex gap-2 pt-2">
            {isFreePlan ? (
              <Button onClick={onUpgrade} className="flex-1">
                Upgrade Plan
              </Button>
            ) : (
              <>
                {subscription.can_manage && (
                  <>
                    <Button variant="outline" onClick={onManageBilling} leftIcon={<ExternalLink className="h-4 w-4" />}>
                      Manage Billing
                    </Button>
                    {hasActiveSubscription && (
                      <Button variant="destructive" onClick={onCancel}>
                        Cancel Subscription
                      </Button>
                    )}
                  </>
                )}
              </>
            )}
          </div>
        </div>
      </Card>

      {/* Usage Tracking */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-6">
          <CreditCard className="h-5 w-5 text-primary-500" />
          <h3 className="text-lg font-semibold text-text-primary">Usage This Month</h3>
        </div>

        <div className="space-y-6">
          {/* Articles */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-text-secondary">Articles</span>
              <span className={`text-sm font-semibold ${getUsageColor(
                getUsagePercentage(subscription.usage.articles_used, subscription.limits.articles_per_month)
              )}`}>
                {subscription.usage.articles_used} / {subscription.limits.articles_per_month === -1 ? "∞" : subscription.limits.articles_per_month}
              </span>
            </div>
            <Progress
              value={getUsagePercentage(subscription.usage.articles_used, subscription.limits.articles_per_month)}
            />
          </div>

          {/* Outlines */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-text-secondary">Outlines</span>
              <span className={`text-sm font-semibold ${getUsageColor(
                getUsagePercentage(subscription.usage.outlines_used, subscription.limits.outlines_per_month)
              )}`}>
                {subscription.usage.outlines_used} / {subscription.limits.outlines_per_month === -1 ? "∞" : subscription.limits.outlines_per_month}
              </span>
            </div>
            <Progress
              value={getUsagePercentage(subscription.usage.outlines_used, subscription.limits.outlines_per_month)}
            />
          </div>

          {/* Images */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-text-secondary">Images</span>
              <span className={`text-sm font-semibold ${getUsageColor(
                getUsagePercentage(subscription.usage.images_used, subscription.limits.images_per_month)
              )}`}>
                {subscription.usage.images_used} / {subscription.limits.images_per_month === -1 ? "∞" : subscription.limits.images_per_month}
              </span>
            </div>
            <Progress
              value={getUsagePercentage(subscription.usage.images_used, subscription.limits.images_per_month)}
            />
          </div>
        </div>

        {subscription.usage.articles_used >= subscription.limits.articles_per_month && subscription.limits.articles_per_month !== -1 && (
          <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200">
            <p className="text-sm text-red-800">
              You've reached your article limit for this month. Upgrade to continue creating content.
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
