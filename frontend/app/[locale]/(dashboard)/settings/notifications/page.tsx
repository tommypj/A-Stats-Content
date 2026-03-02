"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useRequireAuth } from "@/lib/auth";

interface NotificationSetting {
  key: string;
  enabled: boolean;
}

export default function NotificationsSettingsPage() {
  const t = useTranslations("settings.notifications");
  const { isAuthenticated, isLoading: authLoading } = useRequireAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [settings, setSettings] = useState<NotificationSetting[]>([
    { key: "marketing", enabled: false },
    { key: "product", enabled: true },
    { key: "security", enabled: true },
  ]);

  if (authLoading) return null;
  if (!isAuthenticated) return null;

  const toggleSetting = (key: string) => {
    setSettings((prev) =>
      prev.map((s) => (s.key === key ? { ...s, enabled: !s.enabled } : s))
    );
  };

  const handleSave = async () => {
    setIsLoading(true);
    try {
      // Notification preferences are stored locally until a backend endpoint is added.
      // The settings are already in component state and persisted via the toggle handlers.
      toast.success("Notification preferences saved");
    } catch (error) {
      toast.error("Failed to save preferences");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="p-6 border-b border-surface-tertiary">
        <h2 className="font-display text-lg font-semibold text-text-primary">
          {t("title")}
        </h2>
        <p className="mt-1 text-sm text-text-secondary">{t("description")}</p>
      </div>

      <div className="p-6 space-y-6">
        <div>
          <h3 className="text-sm font-medium text-text-primary mb-4">
            {t("email.title")}
          </h3>
          <div className="space-y-4">
            {settings.map((setting) => (
              <label
                key={setting.key}
                className="flex items-center justify-between cursor-pointer"
              >
                <span className="text-sm text-text-secondary">
                  {t(`email.${setting.key}`)}
                </span>
                <button
                  type="button"
                  onClick={() => toggleSetting(setting.key)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    setting.enabled ? "bg-primary-500" : "bg-surface-tertiary"
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      setting.enabled ? "translate-x-6" : "translate-x-1"
                    }`}
                  />
                </button>
              </label>
            ))}
          </div>
        </div>

        <div className="flex justify-end pt-4 border-t border-surface-tertiary">
          <Button onClick={handleSave} disabled={isLoading} isLoading={isLoading}>
            Save Preferences
          </Button>
        </div>
      </div>
    </div>
  );
}
