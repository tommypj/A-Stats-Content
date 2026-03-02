"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight, Home } from "lucide-react";

const PATH_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  articles: "Articles",
  outlines: "Outlines",
  images: "Images",
  projects: "Projects",
  knowledge: "Knowledge Vault",
  analytics: "Analytics",
  social: "Social Media",
  bulk: "Bulk Content",
  settings: "Settings",
  billing: "Billing",
  integrations: "Integrations",
  notifications: "Notifications",
  help: "Help",
  new: "New",
  compose: "Compose",
  calendar: "Calendar",
  accounts: "Accounts",
  history: "History",
  query: "Query",
  agency: "Agency",
  clients: "Clients",
  reports: "Reports",
  branding: "Branding",
  keywords: "Keywords",
  pages: "Pages",
  opportunities: "Opportunities",
  "content-health": "Content Health",
  aeo: "AEO Scores",
  revenue: "Revenue",
  "brand-voice": "Brand Voice",
  password: "Password",
  language: "Language",
  "content-calendar": "Content Calendar",
  "keyword-research": "Keyword Research",
};

export function Breadcrumb() {
  const pathname = usePathname();

  // Strip locale prefix (e.g., /en/dashboard -> /dashboard)
  const cleanPath = pathname.replace(/^\/[a-z]{2}(?:\/|$)/, "/");

  // Skip on dashboard home
  if (cleanPath === "/" || cleanPath === "/dashboard") return null;

  const segments = cleanPath.split("/").filter(Boolean);

  // Build breadcrumb items, skip UUIDs (long alphanumeric segments)
  const filteredSegments = segments.filter((seg) => seg.length < 30);

  const crumbs = filteredSegments.map((seg, i) => {
    // Build href using original segments up to this filtered segment's position
    const originalIndex = segments.indexOf(seg, i);
    return {
      label: PATH_LABELS[seg] || seg.charAt(0).toUpperCase() + seg.slice(1),
      href: "/" + segments.slice(0, originalIndex + 1).join("/"),
      isLast: i === filteredSegments.length - 1,
    };
  });

  if (crumbs.length <= 1) return null;

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-sm text-text-muted mb-4">
      <Link href="/dashboard" className="hover:text-text-primary transition-colors">
        <Home className="h-3.5 w-3.5" />
      </Link>
      {crumbs.map((crumb) => (
        <span key={crumb.href} className="flex items-center gap-1">
          <ChevronRight className="h-3.5 w-3.5 flex-shrink-0" />
          {crumb.isLast ? (
            <span className="text-text-primary font-medium">{crumb.label}</span>
          ) : (
            <Link href={crumb.href} className="hover:text-text-primary transition-colors">
              {crumb.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  );
}
