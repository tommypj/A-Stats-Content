"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";

interface Integration {
  id: string;
  name: string;
  description: string;
  icon: string;
  connected: boolean;
}

export default function IntegrationsSettingsPage() {
  const t = useTranslations("settings.integrations");
  const [integrations, setIntegrations] = useState<Integration[]>([
    {
      id: "wordpress",
      name: "WordPress",
      description: t("wordpress.description"),
      icon: "W",
      connected: false,
    },
    {
      id: "gsc",
      name: "Google Search Console",
      description: t("gsc.description"),
      icon: "G",
      connected: false,
    },
  ]);

  const handleConnect = async (id: string) => {
    // TODO: Implement OAuth flow
    toast.info("Integration coming soon!");
  };

  const handleDisconnect = async (id: string) => {
    setIntegrations((prev) =>
      prev.map((i) => (i.id === id ? { ...i, connected: false } : i))
    );
    toast.success("Integration disconnected");
  };

  return (
    <div className="card">
      <div className="p-6 border-b border-surface-tertiary">
        <h2 className="font-display text-lg font-semibold text-text-primary">
          {t("title")}
        </h2>
        <p className="mt-1 text-sm text-text-secondary">{t("description")}</p>
      </div>

      <div className="p-6 space-y-4">
        {integrations.map((integration) => (
          <div
            key={integration.id}
            className="flex items-center justify-between p-4 rounded-xl border border-surface-tertiary"
          >
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-xl bg-surface-secondary flex items-center justify-center">
                <span className="text-lg font-bold text-text-primary">
                  {integration.icon}
                </span>
              </div>
              <div>
                <p className="font-medium text-text-primary">
                  {integration.name}
                </p>
                <p className="text-sm text-text-secondary">
                  {integration.description}
                </p>
              </div>
            </div>
            {integration.connected ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDisconnect(integration.id)}
              >
                {t(`${integration.id}.disconnect`)}
              </Button>
            ) : (
              <Button
                variant="primary"
                size="sm"
                onClick={() => handleConnect(integration.id)}
              >
                {t(`${integration.id}.connect`)}
              </Button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
