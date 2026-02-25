"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  CreditCard,
  ArrowUpRight,
  ExternalLink,
  AlertTriangle,
  TrendingUp,
  CheckCircle,
  XCircle,
  Clock,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useAuthStore } from "@/stores/auth";
import { api, parseApiError, SubscriptionStatus, PlanInfo } from "@/lib/api";
import { toast } from "sonner";

export default function BillingSettingsPage() {
  const t = useTranslations("settings.billing");
  const router = useRouter();
  const { user } = useAuthStore();
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    fetchData();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    };
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [subData, pricingData] = await Promise.all([
        api.billing.subscription(),
        api.billing.pricing(),
      ]);
      setSubscription(subData);
      setPlans(pricingData.plans);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (planId: string) => {
    try {
      setActionLoading(true);
      const response = await api.billing.checkout(planId, "monthly");
      window.open(response.checkout_url, "_blank");

      // Poll for subscription changes after checkout
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const subData = await api.billing.subscription();
          if (subData.subscription_tier !== subscription?.subscription_tier) {
            setSubscription(subData);
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
            toast.success("Subscription updated successfully!");
          }
        } catch (error) {
          // Ignore polling errors
        }
      }, 3000);

      // Stop polling after 5 minutes
      pollTimeoutRef.current = setTimeout(() => {
        if (pollRef.current) clearInterval(pollRef.current);
        pollRef.current = null;
      }, 300000);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleManageSubscription = async () => {
    try {
      setActionLoading(true);
      const response = await api.billing.portal();
      window.open(response.portal_url, "_blank");
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelSubscription = async () => {
    try {
      setActionLoading(true);
      await api.billing.cancel();
      toast.success("Subscription cancelled. You'll have access until the end of your billing period.");
      await fetchData();
      setShowCancelDialog(false);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message);
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return (
          <Badge variant="success" className="flex items-center gap-1">
            <CheckCircle className="h-3 w-3" />
            Active
          </Badge>
        );
      case "cancelled":
        return (
          <Badge variant="warning" className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Cancelled
          </Badge>
        );
      case "expired":
        return (
          <Badge variant="danger" className="flex items-center gap-1">
            <XCircle className="h-3 w-3" />
            Expired
          </Badge>
        );
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const calculateUsagePercentage = (used: number, limit: number) => {
    if (limit === -1) return 0; // Unlimited
    return Math.min((used / limit) * 100, 100);
  };

  const getCurrentPlan = () => {
    return plans.find((p) => p.id === subscription?.subscription_tier) || plans[0];
  };

  const currentPlan = getCurrentPlan();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Current Plan */}
      <div className="card">
        <div className="p-6 border-b border-surface-tertiary">
          <h2 className="font-display text-lg font-semibold text-text-primary">
            Current Plan
          </h2>
          <p className="mt-1 text-sm text-text-secondary">
            Manage your subscription and billing information
          </p>
        </div>

        <div className="p-6">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <p className="text-2xl font-display font-bold text-text-primary">
                  {currentPlan?.name || "Free"}
                </p>
                {subscription && getStatusBadge(subscription.subscription_status)}
              </div>
              <p className="text-lg text-primary-500 font-medium">
                ${currentPlan?.price_monthly || 0}
                <span className="text-sm text-text-muted">/month</span>
              </p>
              {subscription?.subscription_expires && (
                <p className="text-sm text-text-secondary mt-1">
                  {subscription.subscription_status === "cancelled"
                    ? `Access until ${formatDate(subscription.subscription_expires)}`
                    : `Renews on ${formatDate(subscription.subscription_expires)}`}
                </p>
              )}
            </div>
            <div className="flex gap-2">
              {subscription?.can_manage && (
                <Button
                  variant="secondary"
                  onClick={handleManageSubscription}
                  isLoading={actionLoading}
                >
                  Manage Subscription
                  <ExternalLink className="ml-2 h-4 w-4" />
                </Button>
              )}
              <Button variant="primary" onClick={() => router.push("/pricing")}>
                {subscription?.subscription_tier === "free" ? "Upgrade Plan" : "Change Plan"}
                <ArrowUpRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>

          {currentPlan && (
            <div className="mt-6 pt-6 border-t border-surface-tertiary">
              <p className="text-sm font-medium text-text-primary mb-3">Plan includes:</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="flex items-center gap-2 text-sm text-text-secondary">
                  <div className="h-1.5 w-1.5 rounded-full bg-healing-sage" />
                  <span>
                    {currentPlan.limits.articles_per_month === -1
                      ? "Unlimited"
                      : currentPlan.limits.articles_per_month}{" "}
                    articles/month
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm text-text-secondary">
                  <div className="h-1.5 w-1.5 rounded-full bg-healing-sage" />
                  <span>
                    {currentPlan.limits.outlines_per_month === -1
                      ? "Unlimited"
                      : currentPlan.limits.outlines_per_month}{" "}
                    outlines/month
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm text-text-secondary">
                  <div className="h-1.5 w-1.5 rounded-full bg-healing-sage" />
                  <span>
                    {currentPlan.limits.images_per_month === -1
                      ? "Unlimited"
                      : currentPlan.limits.images_per_month}{" "}
                    images/month
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Usage Section */}
      {subscription && currentPlan && (
        <div className="card">
          <div className="p-6 border-b border-surface-tertiary">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display font-semibold text-text-primary">Usage This Month</h3>
                <p className="text-sm text-text-secondary mt-1">
                  Track your resource consumption
                </p>
              </div>
              <TrendingUp className="h-5 w-5 text-primary-500" />
            </div>
          </div>

          <div className="p-6 space-y-6">
            {/* Articles Usage */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-text-primary">Articles</span>
                <span className="text-sm text-text-secondary">
                  {subscription.articles_generated_this_month} /{" "}
                  {currentPlan.limits.articles_per_month === -1
                    ? "Unlimited"
                    : currentPlan.limits.articles_per_month}
                </span>
              </div>
              <Progress
                value={subscription.articles_generated_this_month}
                max={currentPlan.limits.articles_per_month === -1 ? 100 : currentPlan.limits.articles_per_month}
              />
              {calculateUsagePercentage(
                subscription.articles_generated_this_month,
                currentPlan.limits.articles_per_month
              ) >= 80 && currentPlan.limits.articles_per_month !== -1 && (
                <p className="text-xs text-yellow-600 mt-1">
                  You're approaching your limit. Consider upgrading for more articles.
                </p>
              )}
            </div>

            {/* Outlines Usage */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-text-primary">Outlines</span>
                <span className="text-sm text-text-secondary">
                  {subscription.outlines_generated_this_month} /{" "}
                  {currentPlan.limits.outlines_per_month === -1
                    ? "Unlimited"
                    : currentPlan.limits.outlines_per_month}
                </span>
              </div>
              <Progress
                value={subscription.outlines_generated_this_month}
                max={currentPlan.limits.outlines_per_month === -1 ? 100 : currentPlan.limits.outlines_per_month}
              />
            </div>

            {/* Images Usage */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-text-primary">Images</span>
                <span className="text-sm text-text-secondary">
                  {subscription.images_generated_this_month} /{" "}
                  {currentPlan.limits.images_per_month === -1
                    ? "Unlimited"
                    : currentPlan.limits.images_per_month}
                </span>
              </div>
              <Progress
                value={subscription.images_generated_this_month}
                max={currentPlan.limits.images_per_month === -1 ? 100 : currentPlan.limits.images_per_month}
              />
            </div>
          </div>
        </div>
      )}

      {/* Plan Comparison */}
      <div className="card">
        <div className="p-6 border-b border-surface-tertiary">
          <h3 className="font-display font-semibold text-text-primary">Available Plans</h3>
          <p className="text-sm text-text-secondary mt-1">
            Compare plans and upgrade for more features
          </p>
        </div>

        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {plans.map((plan) => {
              const isCurrent = plan.id === subscription?.subscription_tier;
              const canUpgrade =
                plans.findIndex((p) => p.id === subscription?.subscription_tier) <
                plans.findIndex((p) => p.id === plan.id);

              return (
                <div
                  key={plan.id}
                  className={`p-4 rounded-xl border ${
                    isCurrent
                      ? "border-primary-500 bg-primary-50"
                      : "border-surface-tertiary bg-surface-secondary"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-text-primary">{plan.name}</h4>
                    {isCurrent && <Badge variant="success">Current</Badge>}
                  </div>
                  <p className="text-2xl font-bold text-text-primary mb-3">
                    ${plan.price_monthly}
                    <span className="text-sm text-text-muted">/mo</span>
                  </p>
                  <div className="space-y-1 mb-4 text-xs text-text-secondary">
                    <p>
                      {plan.limits.articles_per_month === -1
                        ? "Unlimited"
                        : plan.limits.articles_per_month}{" "}
                      articles
                    </p>
                    <p>
                      {plan.limits.outlines_per_month === -1
                        ? "Unlimited"
                        : plan.limits.outlines_per_month}{" "}
                      outlines
                    </p>
                    <p>
                      {plan.limits.images_per_month === -1
                        ? "Unlimited"
                        : plan.limits.images_per_month}{" "}
                      images
                    </p>
                  </div>
                  {!isCurrent && canUpgrade && (
                    <Button
                      variant="secondary"
                      size="sm"
                      className="w-full"
                      onClick={() => handleUpgrade(plan.id)}
                      isLoading={actionLoading}
                    >
                      Upgrade
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Cancel Subscription */}
      {subscription?.subscription_tier !== "free" &&
        subscription?.subscription_status === "active" && (
          <div className="card border-red-200">
            <div className="p-6 border-b border-red-100">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-red-600" />
                <h3 className="font-display font-semibold text-red-600">Danger Zone</h3>
              </div>
            </div>

            <div className="p-6">
              {!showCancelDialog ? (
                <>
                  <p className="text-sm text-text-secondary mb-4">
                    Canceling your subscription will downgrade you to the Free plan at the end of
                    your billing period. You'll lose access to:
                  </p>
                  <ul className="list-disc list-inside text-sm text-text-secondary mb-4 space-y-1">
                    <li>Higher content generation limits</li>
                    <li>Priority support</li>
                    <li>Advanced features</li>
                  </ul>
                  <Button
                    variant="outline"
                    className="border-red-200 text-red-600 hover:bg-red-50"
                    onClick={() => setShowCancelDialog(true)}
                  >
                    Cancel Subscription
                  </Button>
                </>
              ) : (
                <div className="space-y-4">
                  <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm font-medium text-red-800 mb-2">
                      Are you sure you want to cancel?
                    </p>
                    <p className="text-sm text-red-700">
                      You'll continue to have access until{" "}
                      {formatDate(subscription.subscription_expires)}. After that, you'll be
                      downgraded to the Free plan.
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="destructive"
                      onClick={handleCancelSubscription}
                      isLoading={actionLoading}
                    >
                      Yes, Cancel Subscription
                    </Button>
                    <Button variant="secondary" onClick={() => setShowCancelDialog(false)}>
                      Keep Subscription
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
    </div>
  );
}
