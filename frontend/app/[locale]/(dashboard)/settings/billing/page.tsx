"use client";

import { useTranslations } from "next-intl";
import { CreditCard, FileText, ArrowUpRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth";

const plans = {
  free: {
    name: "Free",
    price: "$0",
    features: ["5 articles/month", "10 outlines/month", "2 images/month"],
  },
  starter: {
    name: "Starter",
    price: "$29",
    features: ["10 articles/month", "20 outlines/month", "5 images/month"],
  },
  professional: {
    name: "Professional",
    price: "$79",
    features: ["50 articles/month", "100 outlines/month", "25 images/month"],
  },
  enterprise: {
    name: "Enterprise",
    price: "$199",
    features: ["Unlimited articles", "Unlimited outlines", "Unlimited images"],
  },
};

export default function BillingSettingsPage() {
  const t = useTranslations("settings.billing");
  const { user } = useAuthStore();
  const currentPlan = user?.subscription_tier || "free";
  const planInfo = plans[currentPlan as keyof typeof plans] || plans.free;

  return (
    <div className="space-y-6">
      {/* Current Plan */}
      <div className="card">
        <div className="p-6 border-b border-surface-tertiary">
          <h2 className="font-display text-lg font-semibold text-text-primary">
            {t("title")}
          </h2>
          <p className="mt-1 text-sm text-text-secondary">{t("description")}</p>
        </div>

        <div className="p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-text-muted">{t("currentPlan")}</p>
              <p className="text-2xl font-display font-bold text-text-primary mt-1">
                {planInfo.name}
              </p>
              <p className="text-lg text-primary-500 font-medium">
                {planInfo.price}
                <span className="text-sm text-text-muted">/month</span>
              </p>
            </div>
            <Button variant="primary">
              {t("upgrade")}
              <ArrowUpRight className="ml-2 h-4 w-4" />
            </Button>
          </div>

          <div className="mt-6 pt-6 border-t border-surface-tertiary">
            <p className="text-sm font-medium text-text-primary mb-3">
              Plan includes:
            </p>
            <ul className="space-y-2">
              {planInfo.features.map((feature, index) => (
                <li key={index} className="flex items-center gap-2 text-sm text-text-secondary">
                  <span className="h-1.5 w-1.5 rounded-full bg-healing-sage" />
                  {feature}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Payment Method */}
      <div className="card">
        <div className="p-6 border-b border-surface-tertiary">
          <h3 className="font-display font-semibold text-text-primary">
            {t("paymentMethod")}
          </h3>
        </div>

        <div className="p-6">
          <div className="flex items-center justify-between p-4 rounded-xl border border-surface-tertiary">
            <div className="flex items-center gap-4">
              <div className="h-10 w-10 rounded-lg bg-surface-secondary flex items-center justify-center">
                <CreditCard className="h-5 w-5 text-text-secondary" />
              </div>
              <div>
                <p className="text-sm font-medium text-text-primary">
                  No payment method
                </p>
                <p className="text-xs text-text-muted">
                  Add a card to upgrade your plan
                </p>
              </div>
            </div>
            <Button variant="secondary" size="sm">
              {t("updatePayment")}
            </Button>
          </div>
        </div>
      </div>

      {/* Invoices */}
      <div className="card">
        <div className="p-6 border-b border-surface-tertiary flex items-center justify-between">
          <h3 className="font-display font-semibold text-text-primary">
            {t("invoices")}
          </h3>
          <button className="text-sm text-primary-500 hover:text-primary-600">
            {t("viewInvoices")}
          </button>
        </div>

        <div className="p-6">
          <div className="text-center py-8">
            <div className="h-12 w-12 rounded-xl bg-surface-secondary flex items-center justify-center mx-auto mb-3">
              <FileText className="h-6 w-6 text-text-muted" />
            </div>
            <p className="text-sm text-text-secondary">No invoices yet</p>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="card border-red-200">
        <div className="p-6 border-b border-red-100">
          <h3 className="font-display font-semibold text-red-600">
            {t("cancel")}
          </h3>
        </div>

        <div className="p-6">
          <p className="text-sm text-text-secondary mb-4">
            Canceling your subscription will downgrade you to the Free plan at the end of your billing period.
          </p>
          <Button variant="outline" className="border-red-200 text-red-600 hover:bg-red-50">
            Cancel Subscription
          </Button>
        </div>
      </div>
    </div>
  );
}
