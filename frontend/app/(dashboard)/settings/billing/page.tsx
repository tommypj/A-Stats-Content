"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  CreditCard,
  Check,
  Loader2,
  Crown,
  Zap,
  Building2,
} from "lucide-react";

interface PricingPlan {
  name: string;
  description: string;
  monthlyPrice: string;
  yearlyPrice: string;
  icon: typeof Crown;
  features: string[];
  tier: string;
  popular?: boolean;
}

const plans: PricingPlan[] = [
  {
    name: "Free",
    description: "Get started with AI content",
    monthlyPrice: "$0",
    yearlyPrice: "$0",
    icon: Zap,
    tier: "free",
    features: [
      "10 articles/month",
      "20 outlines/month",
      "5 images/month",
      "Basic SEO optimization",
      "1 project member",
    ],
  },
  {
    name: "Starter",
    description: "For growing content creators",
    monthlyPrice: "$19",
    yearlyPrice: "$190",
    icon: Crown,
    tier: "starter",
    popular: true,
    features: [
      "50 articles/month",
      "100 outlines/month",
      "25 images/month",
      "Advanced SEO tools",
      "Social media scheduling",
      "3 project members",
      "Knowledge Vault (100MB)",
    ],
  },
  {
    name: "Professional",
    description: "For agencies and teams",
    monthlyPrice: "$49",
    yearlyPrice: "$490",
    icon: Crown,
    tier: "professional",
    features: [
      "200 articles/month",
      "Unlimited outlines",
      "100 images/month",
      "Full analytics suite",
      "Social media automation",
      "10 project members",
      "Knowledge Vault (1GB)",
      "Priority support",
    ],
  },
  {
    name: "Enterprise",
    description: "Custom solutions at scale",
    monthlyPrice: "$149",
    yearlyPrice: "$1,490",
    icon: Building2,
    tier: "enterprise",
    features: [
      "Unlimited articles",
      "Unlimited outlines",
      "Unlimited images",
      "Custom AI training",
      "Unlimited project members",
      "Knowledge Vault (10GB)",
      "Dedicated support",
      "SLA guarantee",
    ],
  },
];

export default function BillingPage() {
  const [currentTier, setCurrentTier] = useState("free");
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "yearly">("monthly");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSubscription();
  }, []);

  const loadSubscription = async () => {
    try {
      const profile = await api.auth.me();
      setCurrentTier(profile.subscription_tier || "free");
    } catch {
      // Default to free
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (tier: string) => {
    try {
      const { checkout_url } = await api.billing.checkout(tier, billingPeriod);
      if (checkout_url) {
        window.location.href = checkout_url;
      }
    } catch {
      alert("Failed to start checkout. Please try again.");
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
          const isCurrent = currentTier === plan.tier;
          return (
            <Card
              key={plan.name}
              className={`p-6 relative ${
                plan.popular ? "ring-2 ring-primary-500" : ""
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary-500 text-white text-xs px-3 py-1 rounded-full font-medium">
                  Most Popular
                </div>
              )}
              <div className="h-10 w-10 rounded-xl bg-primary-50 flex items-center justify-center mb-4">
                <plan.icon className="h-5 w-5 text-primary-500" />
              </div>
              <h3 className="text-lg font-display font-bold text-text-primary">{plan.name}</h3>
              <p className="text-sm text-text-secondary mt-1">{plan.description}</p>
              <div className="mt-4 mb-6">
                <span className="text-3xl font-bold text-text-primary">
                  {billingPeriod === "monthly" ? plan.monthlyPrice : plan.yearlyPrice}
                </span>
                <span className="text-text-muted text-sm">
                  /{billingPeriod === "monthly" ? "mo" : "yr"}
                </span>
              </div>
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
                  variant={plan.popular ? "primary" : "outline"}
                  onClick={() => handleUpgrade(plan.tier)}
                >
                  {plan.tier === "free" ? "Downgrade" : "Upgrade"}
                </Button>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
