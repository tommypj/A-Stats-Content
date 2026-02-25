"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Check, Sparkles, Zap, Rocket, Building2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api, parseApiError, PlanInfo } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { toast } from "sonner";

export default function PricingPage() {
  const t = useTranslations("pricing");
  const router = useRouter();
  const { isAuthenticated, user } = useAuthStore();
  const [billingCycle, setBillingCycle] = useState<"monthly" | "yearly">("monthly");
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchPricing();
  }, []);

  const fetchPricing = async () => {
    try {
      setLoading(true);
      const response = await api.billing.pricing();
      setPlans(response.plans);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPlan = async (planId: string) => {
    if (!isAuthenticated) {
      router.push("/login?redirect=/pricing");
      return;
    }

    if (planId === "free") {
      toast.info("You are already on the free plan");
      return;
    }

    try {
      setCheckoutLoading(planId);
      const response = await api.billing.checkout(planId, billingCycle);
      window.open(response.checkout_url, "_blank");
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message);
    } finally {
      setCheckoutLoading(null);
    }
  };

  const getPlanIcon = (planId: string) => {
    switch (planId) {
      case "free":
        return <Sparkles className="h-6 w-6" />;
      case "starter":
        return <Zap className="h-6 w-6" />;
      case "professional":
        return <Rocket className="h-6 w-6" />;
      case "enterprise":
        return <Building2 className="h-6 w-6" />;
      default:
        return <Sparkles className="h-6 w-6" />;
    }
  };

  const calculateYearlySavings = (monthly: number, yearly: number) => {
    const yearlyTotal = monthly * 12;
    const savings = ((yearlyTotal - yearly) / yearlyTotal) * 100;
    return Math.round(savings);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-surface to-surface-secondary flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-surface to-surface-secondary">
      {/* Header */}
      <div className="container mx-auto px-4 py-16 text-center">
        <h1 className="font-display text-4xl md:text-5xl font-bold text-text-primary mb-4">
          Simple, transparent pricing
        </h1>
        <p className="text-lg text-text-secondary max-w-2xl mx-auto mb-8">
          Choose the perfect plan for your content creation needs. Upgrade or downgrade at any time.
        </p>

        {/* Billing Toggle */}
        <div className="inline-flex items-center gap-3 p-1 bg-surface-secondary rounded-xl border border-surface-tertiary">
          <button
            onClick={() => setBillingCycle("monthly")}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${
              billingCycle === "monthly"
                ? "bg-primary-500 text-white shadow-sm"
                : "text-text-secondary hover:text-text-primary"
            }`}
          >
            Monthly
          </button>
          <button
            onClick={() => setBillingCycle("yearly")}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${
              billingCycle === "yearly"
                ? "bg-primary-500 text-white shadow-sm"
                : "text-text-secondary hover:text-text-primary"
            }`}
          >
            Yearly
            {plans.length > 0 && plans[1] && (
              <Badge variant="success" className="ml-2">
                Save {calculateYearlySavings(plans[1].price_monthly, plans[1].price_yearly)}%
              </Badge>
            )}
          </button>
        </div>
      </div>

      {/* Pricing Cards */}
      <div className="container mx-auto px-4 pb-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-7xl mx-auto">
          {plans.map((plan) => {
            const price = billingCycle === "monthly" ? plan.price_monthly : plan.price_yearly;
            const isCurrentPlan = user?.subscription_tier === plan.id;
            const isProfessional = plan.id === "professional";

            return (
              <div
                key={plan.id}
                className={`relative rounded-2xl border shadow-lg transition-all hover:shadow-xl ${
                  isProfessional
                    ? "border-primary-500 bg-gradient-to-br from-primary-50 to-surface scale-105"
                    : "border-surface-tertiary bg-surface"
                }`}
              >
                {isProfessional && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge variant="default" className="shadow-md">
                      Most Popular
                    </Badge>
                  </div>
                )}

                {isCurrentPlan && (
                  <div className="absolute -top-3 right-4">
                    <Badge variant="success">Current Plan</Badge>
                  </div>
                )}

                <div className="p-6">
                  {/* Plan Icon & Name */}
                  <div
                    className={`inline-flex items-center justify-center w-12 h-12 rounded-xl mb-4 ${
                      isProfessional
                        ? "bg-primary-500 text-white"
                        : "bg-surface-secondary text-primary-500"
                    }`}
                  >
                    {getPlanIcon(plan.id)}
                  </div>
                  <h3 className="font-display text-2xl font-bold text-text-primary mb-2">
                    {plan.name}
                  </h3>

                  {/* Price */}
                  <div className="mb-6">
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl font-display font-bold text-text-primary">
                        ${price}
                      </span>
                      <span className="text-text-muted">
                        /{billingCycle === "monthly" ? "mo" : "yr"}
                      </span>
                    </div>
                    {billingCycle === "yearly" && plan.price_monthly > 0 && (
                      <p className="text-sm text-text-secondary mt-1">
                        ${(price / 12).toFixed(2)}/month billed yearly
                      </p>
                    )}
                  </div>

                  {/* CTA Button */}
                  <Button
                    variant={isProfessional ? "primary" : "secondary"}
                    className="w-full mb-6"
                    onClick={() => handleSelectPlan(plan.id)}
                    isLoading={checkoutLoading === plan.id}
                    disabled={isCurrentPlan}
                  >
                    {isCurrentPlan
                      ? "Current Plan"
                      : plan.id === "free"
                      ? "Get Started"
                      : "Upgrade Now"}
                  </Button>

                  {/* Features */}
                  <div className="space-y-3">
                    <p className="text-sm font-medium text-text-primary">
                      {plan.id === "free" ? "Includes:" : "Everything in Free, plus:"}
                    </p>
                    <ul className="space-y-2">
                      <li className="flex items-start gap-2 text-sm text-text-secondary">
                        <Check className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                        <span>
                          {plan.limits.articles_per_month === -1
                            ? "Unlimited"
                            : plan.limits.articles_per_month}{" "}
                          articles/month
                        </span>
                      </li>
                      <li className="flex items-start gap-2 text-sm text-text-secondary">
                        <Check className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                        <span>
                          {plan.limits.outlines_per_month === -1
                            ? "Unlimited"
                            : plan.limits.outlines_per_month}{" "}
                          outlines/month
                        </span>
                      </li>
                      <li className="flex items-start gap-2 text-sm text-text-secondary">
                        <Check className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                        <span>
                          {plan.limits.images_per_month === -1
                            ? "Unlimited"
                            : plan.limits.images_per_month}{" "}
                          images/month
                        </span>
                      </li>
                      {plan.features.map((feature) => (
                        <li
                          key={feature}
                          className="flex items-start gap-2 text-sm text-text-secondary"
                        >
                          <Check className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Feature Comparison Table */}
      <div className="container mx-auto px-4 pb-16">
        <div className="max-w-4xl mx-auto">
          <h2 className="font-display text-3xl font-bold text-text-primary text-center mb-8">
            Compare all features
          </h2>
          <div className="bg-surface rounded-2xl border border-surface-tertiary overflow-hidden">
            <table className="w-full">
              <thead className="bg-surface-secondary border-b border-surface-tertiary">
                <tr>
                  <th className="text-left p-4 text-sm font-semibold text-text-primary">
                    Feature
                  </th>
                  {plans.map((plan) => (
                    <th
                      key={plan.id}
                      className="text-center p-4 text-sm font-semibold text-text-primary"
                    >
                      {plan.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-surface-tertiary">
                  <td className="p-4 text-sm text-text-secondary">Articles per month</td>
                  {plans.map((plan) => (
                    <td key={plan.id} className="text-center p-4 text-sm text-text-primary">
                      {plan.limits.articles_per_month === -1
                        ? "Unlimited"
                        : plan.limits.articles_per_month}
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-surface-tertiary">
                  <td className="p-4 text-sm text-text-secondary">Outlines per month</td>
                  {plans.map((plan) => (
                    <td key={plan.id} className="text-center p-4 text-sm text-text-primary">
                      {plan.limits.outlines_per_month === -1
                        ? "Unlimited"
                        : plan.limits.outlines_per_month}
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-surface-tertiary">
                  <td className="p-4 text-sm text-text-secondary">Images per month</td>
                  {plans.map((plan) => (
                    <td key={plan.id} className="text-center p-4 text-sm text-text-primary">
                      {plan.limits.images_per_month === -1
                        ? "Unlimited"
                        : plan.limits.images_per_month}
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-surface-tertiary">
                  <td className="p-4 text-sm text-text-secondary">SEO Analysis</td>
                  {plans.map((plan) => (
                    <td key={plan.id} className="text-center p-4">
                      <Check className="h-5 w-5 text-green-500 mx-auto" />
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-surface-tertiary">
                  <td className="p-4 text-sm text-text-secondary">WordPress Integration</td>
                  {plans.map((plan) => (
                    <td key={plan.id} className="text-center p-4">
                      <Check className="h-5 w-5 text-green-500 mx-auto" />
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="p-4 text-sm text-text-secondary">Priority Support</td>
                  {plans.map((plan) => (
                    <td key={plan.id} className="text-center p-4">
                      {plan.id === "professional" || plan.id === "enterprise" ? (
                        <Check className="h-5 w-5 text-green-500 mx-auto" />
                      ) : (
                        <span className="text-text-muted">-</span>
                      )}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
