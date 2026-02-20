"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { User, Lock, Bell, CreditCard, Plug, Globe } from "lucide-react";
import { clsx } from "clsx";

const settingsNav = [
  { name: "profile", href: "/settings", icon: User },
  { name: "password", href: "/settings/password", icon: Lock },
  { name: "notifications", href: "/settings/notifications", icon: Bell },
  { name: "billing", href: "/settings/billing", icon: CreditCard },
  { name: "integrations", href: "/settings/integrations", icon: Plug },
  { name: "language", href: "/settings/language", icon: Globe },
];

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const t = useTranslations("settings");
  const pathname = usePathname();

  // Remove locale prefix for comparison
  const pathWithoutLocale = pathname.replace(/^\/[a-z]{2}(?=\/|$)/, "");

  return (
    <div className="animate-in">
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-text-primary">
          {t("title")}
        </h1>
      </div>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Settings navigation */}
        <nav className="lg:w-64 flex-shrink-0">
          <div className="card p-2">
            {settingsNav.map((item) => {
              const isActive =
                pathWithoutLocale === item.href ||
                (item.href === "/settings" && pathWithoutLocale === "/settings");

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={clsx(
                    "flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary-50 text-primary-600"
                      : "text-text-secondary hover:bg-surface-secondary hover:text-text-primary"
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  {t(`${item.name}.title`)}
                </Link>
              );
            })}
          </div>
        </nav>

        {/* Settings content */}
        <div className="flex-1 min-w-0">{children}</div>
      </div>
    </div>
  );
}
