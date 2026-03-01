"use client";

import { useEffect, useState } from "react";
import { api, parseApiError, PlanInfo, SubscriptionStatus } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Check,
  Loader2,
  Crown,
  Zap,
  Building2,
  AlertTriangle,
  FileText,
  Sparkles,
  Image as ImageIcon,
  Share2,
  Search,
  RefreshCw,
} from "lucide-react";

const tierIcons: Record<string, typeof Crown> = {
  free: Zap,
  starter: Crown,
  professional: Crown,
  enterprise: Building2,
};

const TIER_COLORS: Record<string, string> = {
  free: "bg-surface-secondary text-text-secondary",
  starter: "bg-blue-100 text-blue-700",
  professional: "bg-primary-100 text-primary-700",
  enterprise: "bg-purple-100 text-purple-700",
};

const TIER_ORDER: Record<string, number> = {
  free: 0,
  starter: 1,
  professional: 2,
  enterprise: 3,
};

interface UsageBarProps {
  label: string;
  icon: React.ElementType;
  used: number;
  limit: number;
  color: string;
}

function UsageBar({ label, icon: Icon, used, limit, color }: UsageBarProps) {
  const isUnlimited = limit === -1;
  const pct = isUnlimited
    ? Math.min(used * 2, 100)
    : Math.min((used / limit) * 100, 100);
  const isNearLimit = !isUnlimited && pct >= 80;
  const isAtLimit = !isUnlimited && used >= limit;

  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1.5">
        <span className="flex items-center gap-1.5 text-text-secondary">
          <Icon className="h-3.5 w-3.5" />
          {label}
        </span>
        <span
          className={`font-medium tabular-nums ${
            isAtLimit
              ? "text-red-600"
              : isNearLimit
              ? "text-yellow-600"
              : "text-text-primary"
          }`}
        >
          {used} / {isUnlimited ? "∞" : limit}
        </span>
      </div>
      <div className="h-2 bg-surface-tertiary rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isAtLimit ? "bg-red-500" : isNearLimit ? "bg-yellow-400" : color
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function BillingPage() {
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [currentTier, setCurrentTier] = useState("free");
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "yearly">("monthly");
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);

  useEffect(() => {
    loadBillingData();
  }, []);

  async function loadBillingData() {
    try {
      setLoading(true);
      const [pricingRes, profileRes, subRes] = await Promise.all([
        api.billing.pricing().catch(() => null),
        api.auth.me().catch(() => null),
        api.billing.subscription().catch(() => null),
      ]);

      if (pricingRes?.plans) {
        setPlans(pricingRes.plans);
      }
      if (profileRes) {
        setCurrentTier(profileRes.subscription_tier || "free");
      }
      if (subRes) {
        setSubscription(subRes);
      }
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to load billing data");
    } finally {
      setLoading(false);
    }
  }

  const handleUpgrade = async (tier: string) => {
    try {
      const { checkout_url } = await api.billing.checkout(tier, billingPeriod);
      if (checkout_url) {
        window.location.href = checkout_url;
      }
    } catch {
      toast.error("Failed to start checkout. Please try again.");
    }
  };

  const handleCancel = async () => {
    try {
      setCancelling(true);
      const result = await api.billing.cancel();
      toast.success(result.message || "Subscription cancelled");
      await loadBillingData();
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to cancel subscription");
    } finally {
      setCancelling(false);
    }
  };

  // Derive current plan limits
  const currentPlan = plans.find((p) => p.id === currentTier);
  const limits = currentPlan?.limits;

  const articlesUsed = subscription?.articles_generated_this_month ?? 0;
  const outlinesUsed = subscription?.outlines_generated_this_month ?? 0;
  const imagesUsed = subscription?.images_generated_this_month ?? 0;
  const socialUsed = subscription?.social_posts_generated_this_month ?? 0;

  const resetDate = subscription?.usage_reset_date
    ? new Date(subscription.usage_reset_date).toLocaleDateString(undefined, {
        month: "long",
        day: "numeric",
      })
    : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in">
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Billing & Plans</h1>
        <p className="mt-1 text-text-secondary">Manage your subscription and track your usage.</p>
      </div>

      {/* Current plan + usage */}
      <Card className="p-5 space-y-5">
        {/* Plan header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            {(() => {
              const PlanIcon = tierIcons[currentTier] || Zap;
              return (
                <div className="h-10 w-10 rounded-xl bg-primary-50 flex items-center justify-center shrink-0">
                  <PlanIcon className="h-5 w-5 text-primary-500" />
                </div>
              );
            })()}
            <div>
              <div className="flex items-center gap-2">
                <p className="text-lg font-semibold text-text-primary capitalize">{currentTier}</p>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    TIER_COLORS[currentTier] || TIER_COLORS.free
                  }`}
                >
                  {subscription?.subscription_status === "active" ? "Active" : currentTier === "free" ? "Free" : subscription?.subscription_status || "Active"}
                </span>
              </div>
              {currentTier !== "free" && subscription?.subscription_expires && (
                <p className="text-xs text-text-muted mt-0.5">
                  Renews {new Date(subscription.subscription_expires).toLocaleDateString()}
                </p>
              )}
              {currentTier === "free" && (
                <p className="text-xs text-text-muted mt-0.5">No credit card required</p>
              )}
            </div>
          </div>

          {currentTier !== "free" && subscription && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={cancelling}
              isLoading={cancelling}
              leftIcon={<AlertTriangle className="h-4 w-4" />}
            >
              Cancel
            </Button>
          )}
        </div>

        {/* Divider */}
        <div className="border-t border-surface-tertiary" />

        {/* Usage bars */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-text-primary">Usage This Month</h3>
            {resetDate && (
              <span className="flex items-center gap-1 text-xs text-text-muted">
                <RefreshCw className="h-3 w-3" />
                Resets {resetDate}
              </span>
            )}
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <UsageBar
              label="Articles"
              icon={Sparkles}
              used={articlesUsed}
              limit={limits?.articles_per_month ?? 0}
              color="bg-primary-500"
            />
            <UsageBar
              label="Outlines"
              icon={FileText}
              used={outlinesUsed}
              limit={limits?.outlines_per_month ?? 0}
              color="bg-healing-sage"
            />
            <UsageBar
              label="Images"
              icon={ImageIcon}
              used={imagesUsed}
              limit={limits?.images_per_month ?? 0}
              color="bg-healing-lavender"
            />
            <UsageBar
              label="Social Posts"
              icon={Share2}
              used={socialUsed}
              limit={limits?.social_posts_per_month ?? 0}
              color="bg-healing-sky"
            />
          </div>
          {limits && (
            <p className="text-xs text-text-muted mt-3">
              Keyword research: <span className="font-medium text-text-secondary">{limits.keyword_researches_per_month} searches/month</span>
            </p>
          )}
        </div>
      </Card>

      {/* Billing Toggle */}
      <div className="flex items-center justify-center gap-3">
        <button
          onClick={() => setBillingPeriod("monthly")}
          className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
            billingPeriod === "monthly"
              ? "bg-primary-500 text-white"
              : "bg-surface-secondary text-text-secondary hover:text-text-primary"
          }`}
        >
          Monthly
        </button>
        <button
          onClick={() => setBillingPeriod("yearly")}
          className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
            billingPeriod === "yearly"
              ? "bg-primary-500 text-white"
              : "bg-surface-secondary text-text-secondary hover:text-text-primary"
          }`}
        >
          Yearly <span className="text-xs opacity-75">Save 17%</span>
        </button>
      </div>

      {/* Plans Grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {plans.map((plan) => {
          const isCurrent = currentTier === plan.id;
          const PlanIcon = tierIcons[plan.id] || Zap;
          const currentLevel = TIER_ORDER[currentTier] ?? 0;
          const planLevel = TIER_ORDER[plan.id] ?? 0;
          const isUpgrade = planLevel > currentLevel;
          const isDowngrade = planLevel < currentLevel;
          // Only show "Most Popular" on Professional when it's above the user's current tier
          const isPopular = plan.id === "professional" && isUpgrade;
          const displayPrice =
            billingPeriod === "monthly"
              ? plan.price_monthly
              : Math.round(plan.price_yearly / 12);
          return (
            <Card
              key={plan.id}
              className={`p-6 relative ${
                isCurrent
                  ? "ring-2 ring-primary-500"
                  : isPopular
                  ? "ring-2 ring-primary-300"
                  : ""
              }`}
            >
              {isCurrent && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary-500 text-white text-xs px-3 py-1 rounded-full font-medium whitespace-nowrap">
                  Your Plan
                </div>
              )}
              {!isCurrent && isPopular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary-300 text-primary-900 text-xs px-3 py-1 rounded-full font-medium whitespace-nowrap">
                  Most Popular
                </div>
              )}
              <div className="h-10 w-10 rounded-xl bg-primary-50 flex items-center justify-center mb-4">
                <PlanIcon className="h-5 w-5 text-primary-500" />
              </div>
              <h3 className="text-lg font-display font-bold text-text-primary">{plan.name}</h3>
              <div className="mt-4 mb-1">
                {plan.price_monthly === 0 ? (
                  <span className="text-3xl font-bold text-text-primary">Free</span>
                ) : (
                  <>
                    <span className="text-3xl font-bold text-text-primary">${displayPrice}</span>
                    <span className="text-text-muted text-sm">/mo</span>
                  </>
                )}
              </div>
              {billingPeriod === "yearly" && plan.price_monthly > 0 && (
                <p className="text-xs text-primary-600 mb-5">
                  Billed annually (${plan.price_yearly}/yr)
                </p>
              )}
              {(billingPeriod === "monthly" || plan.price_monthly === 0) && (
                <div className="mb-6" />
              )}
              <ul className="space-y-2 mb-6">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2 text-sm">
                    <Check className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                    <span className="text-text-secondary">{feature}</span>
                  </li>
                ))}
              </ul>
              {isCurrent ? (
                <Button disabled className="w-full" variant="outline">
                  Current Plan
                </Button>
              ) : (
                <Button
                  className="w-full"
                  variant={isUpgrade && isPopular ? "primary" : "outline"}
                  onClick={() => handleUpgrade(plan.id)}
                >
                  {isDowngrade ? "Downgrade" : "Upgrade"}
                </Button>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
