import React from "react";
import { AlertTriangle, AlertCircle, TrendingUp, ExternalLink } from "lucide-react";
import { clsx } from "clsx";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import Link from "next/link";

interface UsageLimitWarningProps {
  resource: "articles" | "outlines" | "images" | "storage";
  used: number;
  limit: number;
  unit?: string;
  isProject?: boolean;
  showUpgrade?: boolean;
  className?: string;
}

export function UsageLimitWarning({
  resource,
  used,
  limit,
  unit = "items",
  isProject = false,
  showUpgrade = true,
  className,
}: UsageLimitWarningProps) {
  const percentage = limit > 0 ? (used / limit) * 100 : (used > 0 ? 100 : 0);
  const isWarning = percentage >= 80 && percentage < 100;
  const isAtLimit = percentage >= 100;

  // Don't show anything if usage is below 80%
  if (percentage < 80) {
    return null;
  }

  const resourceLabel = {
    articles: "Articles",
    outlines: "Outlines",
    images: "Images",
    storage: "Storage",
  }[resource];

  const Icon = isAtLimit ? AlertCircle : AlertTriangle;

  return (
    <div
      className={clsx(
        "rounded-lg border p-4",
        isAtLimit
          ? "bg-red-50 border-red-200"
          : "bg-yellow-50 border-yellow-200",
        className
      )}
    >
      <div className="flex items-start gap-3">
        <Icon
          className={clsx(
            "h-5 w-5 flex-shrink-0 mt-0.5",
            isAtLimit ? "text-red-600" : "text-yellow-600"
          )}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-4 mb-2">
            <h4
              className={clsx(
                "text-sm font-medium",
                isAtLimit ? "text-red-800" : "text-yellow-800"
              )}
            >
              {isAtLimit
                ? `${resourceLabel} Limit Reached`
                : `Approaching ${resourceLabel} Limit`}
            </h4>
            <span
              className={clsx(
                "text-xs font-medium whitespace-nowrap",
                isAtLimit ? "text-red-700" : "text-yellow-700"
              )}
            >
              {used} / {limit} {unit}
            </span>
          </div>

          <Progress
            value={Math.min(percentage, 100)}
            className="mb-3"
          />

          <p
            className={clsx(
              "text-sm mb-3",
              isAtLimit ? "text-red-700" : "text-yellow-700"
            )}
          >
            {isAtLimit ? (
              <>
                You've reached your {resourceLabel.toLowerCase()} limit for{" "}
                {isProject ? "this project" : "your account"}.{" "}
                {showUpgrade && (
                  <>
                    Upgrade to continue creating {resourceLabel.toLowerCase()}.
                  </>
                )}
              </>
            ) : (
              <>
                You're using {Math.round(percentage)}% of your{" "}
                {resourceLabel.toLowerCase()} limit. Consider upgrading before
                you reach the limit.
              </>
            )}
          </p>

          {showUpgrade && (
            <div className="flex items-center gap-3">
              <Link
                href="/settings/billing"
              >
                <Button
                  size="sm"
                  variant={isAtLimit ? "primary" : "outline"}
                  leftIcon={<TrendingUp className="h-4 w-4" />}
                >
                  {isAtLimit ? "Upgrade Now" : "View Plans"}
                </Button>
              </Link>
              {!isProject && (
                <Link href="/settings/billing">
                  <Button
                    size="sm"
                    variant="ghost"
                    leftIcon={<ExternalLink className="h-4 w-4" />}
                  >
                    Manage Subscription
                  </Button>
                </Link>
              )}
            </div>
          )}

          {isProject && (
            <p className="text-xs text-text-muted mt-2">
              Project owners and admins can manage project subscriptions
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

interface UsageLimitBannerProps {
  resource: "articles" | "outlines" | "images";
  used: number;
  limit: number;
  isProject?: boolean;
  projectName?: string;
}

export function UsageLimitBanner({
  resource,
  used,
  limit,
  isProject = false,
  projectName,
}: UsageLimitBannerProps) {
  const percentage = limit > 0 ? (used / limit) * 100 : (used > 0 ? 100 : 0);

  // Don't show anything if usage is below 90% for banner
  if (percentage < 90) {
    return null;
  }

  const isAtLimit = percentage >= 100;

  const resourceLabel = {
    articles: "articles",
    outlines: "outlines",
    images: "images",
  }[resource];

  return (
    <div
      className={clsx(
        "mb-6 rounded-lg border p-3",
        isAtLimit
          ? "bg-red-50 border-red-200"
          : "bg-yellow-50 border-yellow-200"
      )}
    >
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {isAtLimit ? (
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
          ) : (
            <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0" />
          )}
          <div>
            <p
              className={clsx(
                "text-sm font-medium",
                isAtLimit ? "text-red-800" : "text-yellow-800"
              )}
            >
              {isAtLimit
                ? `Cannot create more ${resourceLabel}`
                : `${Math.round(percentage)}% of ${resourceLabel} limit used`}
            </p>
            <p
              className={clsx(
                "text-xs mt-0.5",
                isAtLimit ? "text-red-700" : "text-yellow-700"
              )}
            >
              {used} / {limit} {resourceLabel} this month
              {isProject && projectName && ` for ${projectName}`}
            </p>
          </div>
        </div>
        <Link
          href="/settings/billing"
        >
          <Button
            size="sm"
            variant={isAtLimit ? "primary" : "outline"}
          >
            {isAtLimit ? "Upgrade Plan" : "View Plans"}
          </Button>
        </Link>
      </div>
    </div>
  );
}
