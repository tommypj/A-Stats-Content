"use client";

import { useRouter } from "next/navigation";
import { clsx } from "clsx";
import { User, CreditCard, Plug, Bell } from "lucide-react";

const TABS = [
  { id: "profile", label: "Profile", icon: User },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "integrations", label: "Integrations", icon: Plug },
  { id: "notifications", label: "Notifications", icon: Bell },
] as const;

type TabId = (typeof TABS)[number]["id"];

const TAB_ROUTES: Record<TabId, string> = {
  profile: "/settings#profile",
  billing: "/settings/billing",
  integrations: "/settings/integrations",
  notifications: "/settings/notifications",
};

interface SettingsTabsProps {
  activeTab: TabId;
}

export function SettingsTabs({ activeTab }: SettingsTabsProps) {
  const router = useRouter();

  const handleTabChange = (tabId: TabId) => {
    if (tabId === activeTab) return;
    router.push(TAB_ROUTES[tabId]);
  };

  return (
    <div className="inline-flex gap-1 p-1 bg-surface-secondary rounded-xl">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => handleTabChange(tab.id)}
          className={clsx(
            "flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
            tab.id === activeTab
              ? "bg-surface text-text-primary shadow-sm"
              : "text-text-secondary hover:text-text-primary"
          )}
        >
          <tab.icon className="h-4 w-4" />
          {tab.label}
        </button>
      ))}
    </div>
  );
}
