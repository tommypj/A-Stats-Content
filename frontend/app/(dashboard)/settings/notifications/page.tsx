"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { clsx } from "clsx";
import { toast } from "sonner";
import {
  User,
  Lock,
  CreditCard,
  Plug,
  Bell,
  Loader2,
  Sparkles,
  AlertTriangle,
  TrendingDown,
  Mail,
  CreditCard as BillingIcon,
  Megaphone,
} from "lucide-react";
import { api, parseApiError, NotificationPreferences } from "@/lib/api";
import { Card } from "@/components/ui/card";

const TABS = [
  { id: "profile", label: "Profile", icon: User },
  { id: "password", label: "Password", icon: Lock },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "integrations", label: "Integrations", icon: Plug },
  { id: "notifications", label: "Notifications", icon: Bell },
] as const;

interface ToggleRowProps {
  label: string;
  description: string;
  icon: React.ElementType;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

function ToggleRow({ label, description, icon: Icon, checked, onChange, disabled }: ToggleRowProps) {
  return (
    <div className="flex items-start justify-between gap-4 py-4">
      <div className="flex items-start gap-3 min-w-0">
        <div className="h-9 w-9 rounded-lg bg-surface-secondary flex items-center justify-center flex-shrink-0 mt-0.5">
          <Icon className="h-4.5 w-4.5 text-text-secondary" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-text-primary">{label}</p>
          <p className="text-xs text-text-muted mt-0.5">{description}</p>
        </div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={clsx(
          "relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0",
          checked ? "bg-primary-500" : "bg-surface-tertiary",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <span
          className={clsx(
            "inline-block h-4 w-4 rounded-full bg-white transition-transform shadow-sm",
            checked ? "translate-x-6" : "translate-x-1"
          )}
        />
      </button>
    </div>
  );
}

export default function NotificationsSettingsPage() {
  const router = useRouter();
  const [prefs, setPrefs] = useState<NotificationPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadPreferences();
  }, []);

  async function loadPreferences() {
    try {
      setLoading(true);
      const data = await api.notifications.getPreferences();
      setPrefs(data);
    } catch (err) {
      toast.error(parseApiError(err).message || "Failed to load notification preferences");
    } finally {
      setLoading(false);
    }
  }

  async function handleToggle(field: keyof NotificationPreferences, value: boolean) {
    if (!prefs) return;

    // Optimistic update
    const prev = { ...prefs };
    setPrefs({ ...prefs, [field]: value });

    setSaving(true);
    try {
      const updated = await api.notifications.updatePreferences({ [field]: value });
      setPrefs(updated);
    } catch (err) {
      setPrefs(prev); // Rollback
      toast.error(parseApiError(err).message || "Failed to update preference");
    } finally {
      setSaving(false);
    }
  }

  const handleTabChange = (tabId: string) => {
    if (tabId === "notifications") return;
    if (tabId === "billing") {
      router.push("/settings/billing");
    } else if (tabId === "integrations") {
      router.push("/settings/integrations");
    } else {
      router.push(`/settings#${tabId}`);
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
    <div className="space-y-6 max-w-4xl animate-in">
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Settings</h1>
        <p className="mt-1 text-text-secondary">Manage your account settings and preferences.</p>
      </div>

      {/* Tab bar */}
      <div className="inline-flex gap-1 p-1 bg-surface-secondary rounded-xl">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
              tab.id === "notifications"
                ? "bg-surface text-text-primary shadow-sm"
                : "text-text-secondary hover:text-text-primary"
            )}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {prefs && (
        <div className="space-y-6">
          {/* Generation Alerts */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-2">
              <Sparkles className="h-5 w-5 text-primary-500" />
              <h2 className="text-lg font-display font-semibold text-text-primary">Generation Alerts</h2>
            </div>
            <p className="text-sm text-text-muted mb-2">
              Get notified when your AI-generated content is ready or if something went wrong.
            </p>
            <div className="divide-y divide-surface-tertiary">
              <ToggleRow
                label="Generation completed"
                description="Email me when an article, outline, or image finishes generating"
                icon={Sparkles}
                checked={prefs.email_generation_completed}
                onChange={(v) => handleToggle("email_generation_completed", v)}
                disabled={saving}
              />
              <ToggleRow
                label="Generation failed"
                description="Email me if a generation fails so I can retry"
                icon={AlertTriangle}
                checked={prefs.email_generation_failed}
                onChange={(v) => handleToggle("email_generation_failed", v)}
                disabled={saving}
              />
            </div>
          </Card>

          {/* Usage Alerts */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              <h2 className="text-lg font-display font-semibold text-text-primary">Usage Alerts</h2>
            </div>
            <p className="text-sm text-text-muted mb-2">
              Stay informed about your monthly quota so you never hit a wall unexpectedly.
            </p>
            <div className="divide-y divide-surface-tertiary">
              <ToggleRow
                label="80% usage warning"
                description="Heads up when you've used 80% of any monthly limit"
                icon={AlertTriangle}
                checked={prefs.email_usage_80_percent}
                onChange={(v) => handleToggle("email_usage_80_percent", v)}
                disabled={saving}
              />
              <ToggleRow
                label="Limit reached"
                description="Alert when you've hit a monthly generation limit"
                icon={AlertTriangle}
                checked={prefs.email_usage_limit_reached}
                onChange={(v) => handleToggle("email_usage_limit_reached", v)}
                disabled={saving}
              />
            </div>
          </Card>

          {/* Content & Performance */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-2">
              <TrendingDown className="h-5 w-5 text-red-500" />
              <h2 className="text-lg font-display font-semibold text-text-primary">Content & Performance</h2>
            </div>
            <p className="text-sm text-text-muted mb-2">
              Notifications about how your published content is performing over time.
            </p>
            <div className="divide-y divide-surface-tertiary">
              <ToggleRow
                label="Content decay alerts"
                description="Get notified when an article's search performance is declining"
                icon={TrendingDown}
                checked={prefs.email_content_decay}
                onChange={(v) => handleToggle("email_content_decay", v)}
                disabled={saving}
              />
              <ToggleRow
                label="Weekly digest"
                description="A weekly summary of your content activity and key metrics"
                icon={Mail}
                checked={prefs.email_weekly_digest}
                onChange={(v) => handleToggle("email_weekly_digest", v)}
                disabled={saving}
              />
            </div>
          </Card>

          {/* Billing & Product */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-2">
              <BillingIcon className="h-5 w-5 text-text-secondary" />
              <h2 className="text-lg font-display font-semibold text-text-primary">Billing & Product</h2>
            </div>
            <p className="text-sm text-text-muted mb-2">
              Subscription updates, payment reminders, and product news.
            </p>
            <div className="divide-y divide-surface-tertiary">
              <ToggleRow
                label="Billing alerts"
                description="Payment failures, renewal reminders, and subscription changes"
                icon={BillingIcon}
                checked={prefs.email_billing_alerts}
                onChange={(v) => handleToggle("email_billing_alerts", v)}
                disabled={saving}
              />
              <ToggleRow
                label="Product updates"
                description="New features, improvements, and occasional announcements"
                icon={Megaphone}
                checked={prefs.email_product_updates}
                onChange={(v) => handleToggle("email_product_updates", v)}
                disabled={saving}
              />
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
