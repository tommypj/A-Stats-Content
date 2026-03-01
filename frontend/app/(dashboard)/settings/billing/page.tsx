"use client";

import { useEffect, useState } from "react";
import { api, parseApiError, PlanInfo, SubscriptionStatus } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  CreditCard,
  Check,
  Loader2,
  Crown,
  Zap,
  Building2,
  AlertTriangle,
} from "lucide-react";

const tierIcons: Record<string, typeof Crown> = {
  free: Zap,
  starter: Crown,
  professional: Crown,
  enterprise: Building2,
};

export default function BillingPage() {
  const { user } = useAuthStore();
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
        <p className="mt-1 text-text-secondary">Choose the right plan for your content needs.</p>
      </div>

      {/* Current subscription info */}
      {currentTier !== "free" && subscription && (
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary">Current Plan</p>
              <p className="text-lg font-semibold text-text-primary capitalize">{currentTier}</p>
              {subscription.subscription_expires && (
                <p className="text-xs text-text-muted mt-1">
                  Renews {new Date(subscription.subscription_expires).toLocaleDateString()}
                </p>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={cancelling}
              isLoading={cancelling}
              leftIcon={<AlertTriangle className="h-4 w-4" />}
            >
              Cancel Subscription
            </Button>
          </div>
        </Card>
      )}

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
          const isPopular = plan.id === "professional";
          const displayPrice = billingPeriod === "monthly"
            ? plan.price_monthly
            : Math.round(plan.price_yearly / 12);
          return (
            <Card
              key={plan.id}
              className={`p-6 relative ${isPopular ? "ring-2 ring-primary-500" : ""}`}
            >
              {isPopular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary-500 text-white text-xs px-3 py-1 rounded-full font-medium">
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
                <p className="text-xs text-primary-600 mb-5">Billed annually (${plan.price_yearly}/yr)</p>
              )}
              {(billingPeriod === "monthly" || plan.price_monthly === 0) && <div className="mb-6" />}
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
                  variant={isPopular ? "primary" : "outline"}
                  onClick={() => handleUpgrade(plan.id)}
                >
                  {plan.id === "free" ? "Downgrade" : "Upgrade"}
                </Button>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
