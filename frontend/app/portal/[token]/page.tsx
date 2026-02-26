"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import {
  BarChart3,
  MousePointerClick,
  Eye,
  TrendingUp,
  Target,
  AlertCircle,
} from "lucide-react";
import { api, PortalData } from "@/lib/api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatNumber(value: unknown): string {
  const n = typeof value === "number" ? value : Number(value);
  if (isNaN(n)) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function formatPercent(value: unknown): string {
  const n = typeof value === "number" ? value : Number(value);
  if (isNaN(n)) return "—";
  return `${n.toFixed(2)}%`;
}

function formatPosition(value: unknown): string {
  const n = typeof value === "number" ? value : Number(value);
  if (isNaN(n)) return "—";
  return n.toFixed(1);
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  accentColor: string;
}

function StatCard({ icon, label, value, accentColor }: StatCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-start gap-4 shadow-sm">
      <div
        className="flex-shrink-0 h-10 w-10 rounded-lg flex items-center justify-center"
        style={{ backgroundColor: `${accentColor}18`, color: accentColor }}
      >
        {icon}
      </div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-semibold text-gray-900 mt-0.5">{value}</p>
      </div>
    </div>
  );
}

interface SectionCardProps {
  title: string;
  accentColor: string;
  children: React.ReactNode;
}

function SectionCard({ title, accentColor, children }: SectionCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div
        className="px-6 py-4 border-b border-gray-100"
        style={{ borderLeftWidth: 4, borderLeftColor: accentColor }}
      >
        <h2 className="text-base font-semibold text-gray-900">{title}</h2>
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function ClientPortalPage() {
  const params = useParams();
  const token = typeof params.token === "string" ? params.token : Array.isArray(params.token) ? params.token[0] : "";

  const [data, setData] = useState<PortalData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!token) {
      setError(true);
      setIsLoading(false);
      return;
    }

    let cancelled = false;

    async function loadPortal() {
      try {
        const result = await api.agency.portal(token);
        if (!cancelled) {
          setData(result);
        }
      } catch {
        if (!cancelled) {
          setError(true);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadPortal();

    return () => {
      cancelled = true;
    };
  }, [token]);

  // Derive brand accent color (falls back to a neutral indigo)
  const accentColor =
    data?.brand_colors?.primary ||
    data?.brand_colors?.accent ||
    Object.values(data?.brand_colors ?? {})[0] ||
    "#4f46e5";

  const allowsAnalytics = data?.allowed_features?.analytics !== false;
  const allowsContent = data?.allowed_features?.content !== false;

  // Analytics summary extraction
  const summary = data?.analytics_summary ?? {};
  const totalClicks = summary.total_clicks ?? summary.clicks ?? null;
  const totalImpressions = summary.total_impressions ?? summary.impressions ?? null;
  const avgCtr = summary.avg_ctr ?? summary.ctr ?? null;
  const avgPosition = summary.avg_position ?? summary.position ?? null;
  const articleCount = (summary.article_count ?? summary.articles ?? null) as number | null;
  const recentArticles = Array.isArray(summary.recent_articles)
    ? (summary.recent_articles as Array<{ title: string; published_at?: string }>)
    : [];

  // ---------------------------------------------------------------------------
  // Loading state
  // ---------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div
            className="h-10 w-10 rounded-full border-4 border-t-transparent animate-spin"
            style={{ borderColor: `#e5e7eb`, borderTopColor: "transparent" }}
          >
            <span className="sr-only">Loading portal…</span>
          </div>
          <p className="text-sm text-gray-500">Loading your report…</p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Error / not found state
  // ---------------------------------------------------------------------------
  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center max-w-sm">
          <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h1 className="text-xl font-semibold text-gray-900 mb-2">
            Portal Not Found or Disabled
          </h1>
          <p className="text-sm text-gray-500">
            This client portal link is invalid or has been disabled by the
            agency. Please contact your account manager for a new link.
          </p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* ------------------------------------------------------------------ */}
      {/* Header */}
      {/* ------------------------------------------------------------------ */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex items-center gap-4">
          {/* Agency logo */}
          {data.agency_logo_url ? (
            <img
              src={data.agency_logo_url}
              alt={`${data.agency_name} logo`}
              className="h-10 w-auto object-contain"
            />
          ) : (
            <div
              className="h-10 w-10 rounded-lg flex items-center justify-center text-white font-bold text-lg select-none"
              style={{ backgroundColor: accentColor }}
            >
              {data.agency_name.charAt(0).toUpperCase()}
            </div>
          )}

          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium uppercase tracking-wider text-gray-400">
              Prepared by
            </p>
            <h1 className="text-lg font-semibold text-gray-900 truncate">
              {data.agency_name}
            </h1>
          </div>

          {/* Client badge */}
          <div className="flex-shrink-0 text-right">
            <p className="text-xs text-gray-400">Report for</p>
            <p className="text-sm font-semibold text-gray-800">{data.client_name}</p>
          </div>

          {/* Client logo (if different from agency logo) */}
          {data.client_logo_url && (
            <img
              src={data.client_logo_url}
              alt={`${data.client_name} logo`}
              className="h-8 w-auto object-contain ml-2"
            />
          )}
        </div>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* Main content */}
      {/* ------------------------------------------------------------------ */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

        {/* Welcome banner */}
        <div
          className="rounded-xl px-6 py-5 text-white"
          style={{ background: `linear-gradient(135deg, ${accentColor}, ${accentColor}cc)` }}
        >
          <h2 className="text-xl font-semibold">
            Welcome, {data.client_name}
          </h2>
          <p className="text-sm mt-1 opacity-80">
            Here is your latest SEO performance overview prepared by{" "}
            {data.agency_name}.
          </p>
        </div>

        {/* ---------------------------------------------------------------- */}
        {/* Analytics section */}
        {/* ---------------------------------------------------------------- */}
        {allowsAnalytics && (
          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400 mb-4">
              Analytics Overview
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                icon={<MousePointerClick className="h-5 w-5" />}
                label="Total Clicks"
                value={totalClicks !== null ? formatNumber(totalClicks) : "—"}
                accentColor={accentColor}
              />
              <StatCard
                icon={<Eye className="h-5 w-5" />}
                label="Total Impressions"
                value={totalImpressions !== null ? formatNumber(totalImpressions) : "—"}
                accentColor={accentColor}
              />
              <StatCard
                icon={<TrendingUp className="h-5 w-5" />}
                label="Avg. CTR"
                value={avgCtr !== null ? formatPercent(avgCtr) : "—"}
                accentColor={accentColor}
              />
              <StatCard
                icon={<Target className="h-5 w-5" />}
                label="Avg. Position"
                value={avgPosition !== null ? formatPosition(avgPosition) : "—"}
                accentColor={accentColor}
              />
            </div>
          </section>
        )}

        {/* ---------------------------------------------------------------- */}
        {/* Content section */}
        {/* ---------------------------------------------------------------- */}
        {allowsContent && (
          <SectionCard title="Content Summary" accentColor={accentColor}>
            <div className="space-y-4">
              {/* Article count */}
              <div className="flex items-center gap-3">
                <div
                  className="h-9 w-9 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ backgroundColor: `${accentColor}18`, color: accentColor }}
                >
                  <BarChart3 className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs text-gray-500">Published Articles</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {articleCount !== null ? formatNumber(articleCount) : "—"}
                  </p>
                </div>
              </div>

              {/* Recent articles list */}
              {recentArticles.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                    Recent Articles
                  </p>
                  <ul className="divide-y divide-gray-100">
                    {recentArticles.map((article, idx) => (
                      <li
                        key={idx}
                        className="flex items-center justify-between py-2.5"
                      >
                        <span className="text-sm text-gray-800 truncate flex-1 pr-4">
                          {article.title}
                        </span>
                        {article.published_at && (
                          <span className="text-xs text-gray-400 flex-shrink-0">
                            {new Date(article.published_at).toLocaleDateString("en-US", {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                            })}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {recentArticles.length === 0 && articleCount === null && (
                <p className="text-sm text-gray-400">
                  No content data available for this period.
                </p>
              )}
            </div>
          </SectionCard>
        )}

        {/* Fallback when no features are enabled */}
        {!allowsAnalytics && !allowsContent && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-10 text-center">
            <BarChart3 className="h-10 w-10 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">
              No data sections have been enabled for this portal. Please
              contact {data.agency_name} for access.
            </p>
          </div>
        )}
      </main>

      {/* ------------------------------------------------------------------ */}
      {/* Footer */}
      {/* ------------------------------------------------------------------ */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-sm text-gray-500">
            {data.agency_name
              ? `${data.agency_name} — Client Analytics Portal`
              : "Client Analytics Portal"}
          </p>

          <div className="flex flex-col sm:flex-row items-center gap-4 text-sm text-gray-400">
            {/* Custom footer text from agency profile */}
            {data.footer_text && (
              <span className="text-center sm:text-right">{data.footer_text}</span>
            )}

            {/* Contact email */}
            {data.contact_email && (
              <a
                href={`mailto:${data.contact_email}`}
                className="hover:underline"
                style={{ color: accentColor }}
              >
                {data.contact_email}
              </a>
            )}
          </div>
        </div>
      </footer>
    </div>
  );
}
