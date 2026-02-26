"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  FileText,
  Sparkles,
  Image as ImageIcon,
  TrendingUp,
  ArrowRight,
  Plus,
  Clock,
  CheckCircle2,
  Loader2,
  BarChart2,
  XCircle,
  Rocket,
  X,
  Circle,
  Activity,
} from "lucide-react";
import { api, Article, Outline, PlanInfo, UserResponse, ContentHealthSummary } from "@/lib/api";
import { toast } from "sonner";

const quickActions = [
  {
    name: "Create Outline",
    description: "Start with AI-generated structure",
    icon: FileText,
    href: "/outlines/new",
    color: "bg-healing-sage",
  },
  {
    name: "Write Article",
    description: "Generate SEO-optimized content",
    icon: Sparkles,
    href: "/articles/new",
    color: "bg-healing-lavender",
  },
  {
    name: "Generate Image",
    description: "Create custom AI images",
    icon: ImageIcon,
    href: "/images/generate",
    color: "bg-healing-sky",
  },
];

const statusIcons: Record<string, typeof CheckCircle2> = {
  completed: CheckCircle2,
  published: CheckCircle2,
  draft: FileText,
  generating: Loader2,
  failed: XCircle,
};

const statusColors: Record<string, string> = {
  completed: "text-green-600",
  published: "text-blue-600",
  draft: "text-text-muted",
  generating: "text-yellow-600",
  failed: "text-red-600",
};

interface OnboardingChecklistProps {
  user: UserResponse | null;
  totalArticles: number;
  totalOutlines: number;
  onDismiss: () => void;
}

function OnboardingChecklist({
  user,
  totalArticles,
  totalOutlines,
  onDismiss,
}: OnboardingChecklistProps) {
  const steps = [
    {
      id: "profile",
      label: "Complete your profile",
      description: "Add your name so we can personalise your experience.",
      done: Boolean(user?.name && user.name.trim().length > 0),
      href: "/settings",
    },
    {
      id: "wordpress",
      label: "Connect WordPress",
      description: "Publish articles directly to your WordPress site.",
      done: false, // not available from user object — link-only step
      href: "/settings",
      linkOnly: true,
    },
    {
      id: "gsc",
      label: "Connect Google Search Console",
      description: "Track keyword rankings and content performance.",
      done: false, // not available from user object — link-only step
      href: "/analytics",
      linkOnly: true,
    },
    {
      id: "outline",
      label: "Create your first outline",
      description: "Generate an AI-structured content plan for any keyword.",
      done: totalOutlines > 0,
      href: "/outlines/new",
    },
    {
      id: "article",
      label: "Generate your first article",
      description: "Turn an outline into a full SEO-optimised article.",
      done: totalArticles > 0,
      href: "/articles/new",
    },
  ];

  const completedCount = steps.filter((s) => s.done).length;
  const progressPercent = Math.round((completedCount / steps.length) * 100);

  return (
    <div className="card p-5">
      {/* Header row */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-primary-50 flex items-center justify-center shrink-0">
            <Rocket className="h-5 w-5 text-primary-500" />
          </div>
          <div>
            <h2 className="font-display font-semibold text-text-primary leading-tight">
              Get Started
            </h2>
            <p className="text-sm text-text-muted">
              {completedCount} of {steps.length} complete
            </p>
          </div>
        </div>
        <button
          onClick={onDismiss}
          aria-label="Dismiss onboarding checklist"
          className="p-1.5 rounded-lg hover:bg-surface-secondary text-text-muted hover:text-text-secondary transition-colors shrink-0"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-surface-tertiary rounded-full overflow-hidden mb-5">
        <div
          className="h-full bg-primary-500 rounded-full transition-all duration-500"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {steps.map((step) => (
          <div
            key={step.id}
            className="flex items-center gap-3 group"
          >
            {/* Status icon */}
            <div className="shrink-0">
              {step.done ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : (
                <Circle className="h-5 w-5 text-surface-tertiary" />
              )}
            </div>

            {/* Text */}
            <div className="flex-1 min-w-0">
              <p
                className={`text-sm font-medium leading-tight ${
                  step.done
                    ? "line-through text-text-muted"
                    : "text-text-primary"
                }`}
              >
                {step.label}
                {step.linkOnly && !step.done && (
                  <span className="ml-1.5 text-xs font-normal text-text-muted">
                    (set up)
                  </span>
                )}
              </p>
              <p
                className={`text-xs mt-0.5 ${
                  step.done ? "text-text-muted" : "text-text-secondary"
                }`}
              >
                {step.description}
              </p>
            </div>

            {/* Arrow link */}
            {!step.done && (
              <Link
                href={step.href}
                className="shrink-0 flex items-center gap-1 text-xs font-medium text-primary-500 hover:text-primary-600 transition-colors group-hover:translate-x-0.5"
                aria-label={`Go to ${step.label}`}
              >
                <ArrowRight className="h-4 w-4" />
              </Link>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<UserResponse | null>(null);
  const [recentArticles, setRecentArticles] = useState<Article[]>([]);
  const [recentOutlines, setRecentOutlines] = useState<Outline[]>([]);
  const [totalArticles, setTotalArticles] = useState(0);
  const [totalOutlines, setTotalOutlines] = useState(0);
  const [totalImages, setTotalImages] = useState(0);
  const [avgSeoScore, setAvgSeoScore] = useState<number | null>(null);
  const [planLimits, setPlanLimits] = useState<PlanInfo | null>(null);
  const [contentHealth, setContentHealth] = useState<ContentHealthSummary | null>(null);
  const [onboardingDismissed, setOnboardingDismissed] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setOnboardingDismissed(
        localStorage.getItem("onboarding_dismissed") === "true"
      );
    }
  }, []);

  function dismissOnboarding() {
    if (typeof window !== "undefined") {
      localStorage.setItem("onboarding_dismissed", "true");
    }
    setOnboardingDismissed(true);
  }

  useEffect(() => {
    loadDashboardData();
  }, []);

  async function loadDashboardData() {
    try {
      setLoading(true);

      const [userRes, articlesRes, outlinesRes, imagesRes, pricingRes, healthRes] =
        await Promise.all([
          api.auth.me(),
          api.articles.list({ page: 1, page_size: 5 }).catch(() => ({ items: [], total: 0 })),
          api.outlines.list({ page: 1, page_size: 5 }).catch(() => ({ items: [], total: 0 })),
          api.images.list({ page: 1, page_size: 1 }).catch(() => ({ items: [], total: 0 })),
          api.billing.pricing().catch(() => null),
          api.articles.healthSummary().catch(() => null),
        ]);

      setUser(userRes);
      setRecentArticles(articlesRes.items);
      setTotalArticles(articlesRes.total);
      setRecentOutlines(outlinesRes.items);
      setTotalOutlines(outlinesRes.total);
      setTotalImages(imagesRes.total);
      setContentHealth(healthRes);

      // Calculate average SEO score from articles that have one
      const articlesWithSeo = articlesRes.items.filter(
        (a) => a.seo_score !== undefined && a.seo_score !== null
      );
      if (articlesWithSeo.length > 0) {
        const avg =
          articlesWithSeo.reduce((sum, a) => sum + (a.seo_score || 0), 0) /
          articlesWithSeo.length;
        setAvgSeoScore(Math.round(avg));
      }

      // Find the user's current plan limits
      if (pricingRes) {
        const currentPlan = pricingRes.plans.find(
          (p) => p.id === userRes.subscription_tier
        );
        if (currentPlan) {
          setPlanLimits(currentPlan);
        }
      }
    } catch (error) {
      toast.error("Failed to load dashboard data. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const articlesUsed = user?.articles_generated_this_month ?? 0;
  const outlinesUsed = user?.outlines_generated_this_month ?? 0;
  const imagesUsed = user?.images_generated_this_month ?? 0;

  const articlesLimit = planLimits?.limits.articles_per_month ?? 10;
  const outlinesLimit = planLimits?.limits.outlines_per_month ?? 20;
  const imagesLimit = planLimits?.limits.images_per_month ?? 5;

  function formatLimit(used: number, limit: number) {
    return `${used} / ${limit === -1 ? "∞" : limit}`;
  }

  function usagePercent(used: number, limit: number) {
    if (limit === -1) return Math.min(used * 5, 100); // show some progress for unlimited
    return Math.min((used / limit) * 100, 100);
  }

  function getSeoScoreColor(score: number | null) {
    if (score === null) return "text-text-muted";
    if (score >= 80) return "text-green-600";
    if (score >= 60) return "text-yellow-600";
    return "text-red-600";
  }

  const stats = [
    { name: "Total Articles", value: totalArticles.toString(), icon: FileText, change: `${articlesUsed} this month` },
    { name: "Outlines Created", value: totalOutlines.toString(), icon: Sparkles, change: `${outlinesUsed} this month` },
    { name: "Images Generated", value: totalImages.toString(), icon: ImageIcon, change: `${imagesUsed} this month` },
    {
      name: "SEO Score Avg",
      value: avgSeoScore !== null ? avgSeoScore.toString() : "N/A",
      icon: TrendingUp,
      change: avgSeoScore !== null && avgSeoScore >= 80 ? "Good" : avgSeoScore !== null && avgSeoScore >= 60 ? "Fair" : avgSeoScore !== null ? "Needs work" : "",
      changeColor: getSeoScoreColor(avgSeoScore),
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in min-w-0">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          Welcome back{user?.name ? `, ${user.name.split(" ")[0]}` : ""}!
        </h1>
        <p className="mt-1 text-text-secondary">
          Here's an overview of your content creation activity.
        </p>
      </div>

      {/* Onboarding checklist — shown only to new users who haven't dismissed it */}
      {!onboardingDismissed && totalArticles === 0 && totalOutlines === 0 && (
        <OnboardingChecklist
          user={user}
          totalArticles={totalArticles}
          totalOutlines={totalOutlines}
          onDismiss={dismissOnboarding}
        />
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div key={stat.name} className="card p-5">
            <div className="flex items-center justify-between">
              <div className="h-10 w-10 rounded-xl bg-primary-50 flex items-center justify-center">
                <stat.icon className="h-5 w-5 text-primary-500" />
              </div>
              <span className={`text-xs font-medium ${"changeColor" in stat ? stat.changeColor : "text-text-muted"}`}>
                {stat.change}
              </span>
            </div>
            <div className="mt-4">
              <p className="text-2xl font-display font-bold text-text-primary">
                {stat.value}
              </p>
              <p className="text-sm text-text-muted">{stat.name}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div>
        <h2 className="text-lg font-display font-semibold text-text-primary mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {quickActions.map((action) => (
            <Link
              key={action.name}
              href={action.href}
              className="card p-5 hover:shadow-md transition-all group"
            >
              <div
                className={`h-12 w-12 rounded-xl ${action.color} flex items-center justify-center mb-4`}
              >
                <action.icon className="h-6 w-6 text-white" />
              </div>
              <h3 className="font-display font-semibold text-text-primary group-hover:text-primary-600 transition-colors">
                {action.name}
              </h3>
              <p className="text-sm text-text-secondary mt-1">
                {action.description}
              </p>
              <div className="flex items-center gap-1 mt-3 text-sm text-primary-500 font-medium">
                <span>Get started</span>
                <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent activity */}
      <div className="grid lg:grid-cols-2 gap-6 min-w-0">
        {/* Recent outlines */}
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between p-5 border-b border-surface-tertiary">
            <h2 className="font-display font-semibold text-text-primary">
              Recent Outlines
            </h2>
            <Link
              href="/outlines"
              className="text-sm text-primary-500 hover:text-primary-600 font-medium"
            >
              View all
            </Link>
          </div>
          <div className="p-5">
            {recentOutlines.length === 0 ? (
              <div className="text-center py-8">
                <div className="h-12 w-12 rounded-xl bg-surface-secondary flex items-center justify-center mx-auto mb-3">
                  <FileText className="h-6 w-6 text-text-muted" />
                </div>
                <p className="text-text-secondary text-sm">No outlines yet</p>
                <Link
                  href="/outlines/new"
                  className="inline-flex items-center gap-1 mt-3 text-sm text-primary-500 hover:text-primary-600 font-medium"
                >
                  <Plus className="h-4 w-4" />
                  Create your first outline
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {recentOutlines.map((outline) => {
                  const StatusIcon = statusIcons[outline.status] || FileText;
                  return (
                    <Link
                      key={outline.id}
                      href={`/outlines/${outline.id}`}
                      className="flex items-center gap-3 p-2 -mx-2 rounded-lg hover:bg-surface-secondary transition-colors"
                    >
                      <StatusIcon
                        className={`h-4 w-4 flex-shrink-0 ${statusColors[outline.status] || "text-text-muted"} ${outline.status === "generating" ? "animate-spin" : ""}`}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-text-primary truncate">
                          {outline.title}
                        </p>
                        <p className="text-xs text-text-muted">
                          {outline.keyword} · {new Date(outline.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Recent articles */}
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between p-5 border-b border-surface-tertiary">
            <h2 className="font-display font-semibold text-text-primary">
              Recent Articles
            </h2>
            <Link
              href="/articles"
              className="text-sm text-primary-500 hover:text-primary-600 font-medium"
            >
              View all
            </Link>
          </div>
          <div className="p-5">
            {recentArticles.length === 0 ? (
              <div className="text-center py-8">
                <div className="h-12 w-12 rounded-xl bg-surface-secondary flex items-center justify-center mx-auto mb-3">
                  <Sparkles className="h-6 w-6 text-text-muted" />
                </div>
                <p className="text-text-secondary text-sm">No articles yet</p>
                <Link
                  href="/articles/new"
                  className="inline-flex items-center gap-1 mt-3 text-sm text-primary-500 hover:text-primary-600 font-medium"
                >
                  <Plus className="h-4 w-4" />
                  Create your first article
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {recentArticles.map((article) => {
                  const StatusIcon = statusIcons[article.status] || FileText;
                  return (
                    <Link
                      key={article.id}
                      href={`/articles/${article.id}`}
                      className="flex items-center gap-3 p-2 -mx-2 rounded-lg hover:bg-surface-secondary transition-colors"
                    >
                      <StatusIcon
                        className={`h-4 w-4 flex-shrink-0 ${statusColors[article.status] || "text-text-muted"} ${article.status === "generating" ? "animate-spin" : ""}`}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-text-primary truncate">
                          {article.title}
                        </p>
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-text-muted">
                          <span className="truncate max-w-[120px]">{article.keyword}</span>
                          {article.seo_score !== undefined && (
                            <>
                              <span>·</span>
                              <span className={getSeoScoreColor(article.seo_score)}>
                                SEO {Math.round(article.seo_score)}
                              </span>
                            </>
                          )}
                          <span>·</span>
                          <span className="whitespace-nowrap">{new Date(article.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      {article.word_count > 0 && (
                        <span className="text-xs text-text-muted flex-shrink-0">
                          {article.word_count.toLocaleString()} words
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Usage & Plan */}
      <div className="card p-5">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
          <h2 className="font-display font-semibold text-text-primary">
            Usage This Month
          </h2>
          <Link
            href="/settings/billing"
            className="text-sm text-primary-500 hover:text-primary-600 font-medium"
          >
            Upgrade Plan
          </Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-text-secondary">Articles</span>
              <span className="text-text-primary font-medium">
                {formatLimit(articlesUsed, articlesLimit)}
              </span>
            </div>
            <div className="h-2 bg-surface-tertiary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 rounded-full transition-all duration-500"
                style={{ width: `${usagePercent(articlesUsed, articlesLimit)}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-text-secondary">Outlines</span>
              <span className="text-text-primary font-medium">
                {formatLimit(outlinesUsed, outlinesLimit)}
              </span>
            </div>
            <div className="h-2 bg-surface-tertiary rounded-full overflow-hidden">
              <div
                className="h-full bg-healing-sage rounded-full transition-all duration-500"
                style={{ width: `${usagePercent(outlinesUsed, outlinesLimit)}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-text-secondary">Images</span>
              <span className="text-text-primary font-medium">
                {formatLimit(imagesUsed, imagesLimit)}
              </span>
            </div>
            <div className="h-2 bg-surface-tertiary rounded-full overflow-hidden">
              <div
                className="h-full bg-healing-lavender rounded-full transition-all duration-500"
                style={{ width: `${usagePercent(imagesUsed, imagesLimit)}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Content Health */}
      {contentHealth && contentHealth.total_articles > 0 && (
        <div className="card p-5">
          {/* Header */}
          <div className="flex flex-wrap items-center justify-between gap-2 mb-5">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-primary-50 flex items-center justify-center shrink-0">
                <Activity className="h-5 w-5 text-primary-500" />
              </div>
              <div>
                <h2 className="font-display font-semibold text-text-primary leading-tight">
                  Content Health
                </h2>
                <p className="text-xs text-text-muted">
                  {contentHealth.total_articles} completed article{contentHealth.total_articles !== 1 ? "s" : ""} analysed
                </p>
              </div>
            </div>
            {contentHealth.avg_seo_score !== null && (
              <div className="text-right">
                <p className={`text-2xl font-display font-bold ${getSeoScoreColor(contentHealth.avg_seo_score)}`}>
                  {contentHealth.avg_seo_score}
                </p>
                <p className="text-xs text-text-muted">avg SEO score</p>
              </div>
            )}
          </div>

          {/* Score distribution bar */}
          {(() => {
            const total =
              contentHealth.excellent_count +
              contentHealth.good_count +
              contentHealth.needs_work_count +
              contentHealth.no_score_count;
            if (total === 0) return null;
            const excellentPct = (contentHealth.excellent_count / total) * 100;
            const goodPct = (contentHealth.good_count / total) * 100;
            const needsWorkPct = (contentHealth.needs_work_count / total) * 100;
            const noScorePct = (contentHealth.no_score_count / total) * 100;
            return (
              <div className="mb-4">
                <div className="h-3 rounded-full overflow-hidden flex mb-2">
                  {excellentPct > 0 && (
                    <div
                      className="bg-green-500 transition-all duration-500"
                      style={{ width: `${excellentPct}%` }}
                      title={`Excellent (≥80): ${contentHealth.excellent_count}`}
                    />
                  )}
                  {goodPct > 0 && (
                    <div
                      className="bg-yellow-400 transition-all duration-500"
                      style={{ width: `${goodPct}%` }}
                      title={`Good (60–79): ${contentHealth.good_count}`}
                    />
                  )}
                  {needsWorkPct > 0 && (
                    <div
                      className="bg-red-400 transition-all duration-500"
                      style={{ width: `${needsWorkPct}%` }}
                      title={`Needs Work (<60): ${contentHealth.needs_work_count}`}
                    />
                  )}
                  {noScorePct > 0 && (
                    <div
                      className="bg-surface-tertiary transition-all duration-500"
                      style={{ width: `${noScorePct}%` }}
                      title={`No Score: ${contentHealth.no_score_count}`}
                    />
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-text-muted">
                  {contentHealth.excellent_count > 0 && (
                    <span className="flex items-center gap-1">
                      <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
                      Excellent ({contentHealth.excellent_count})
                    </span>
                  )}
                  {contentHealth.good_count > 0 && (
                    <span className="flex items-center gap-1">
                      <span className="inline-block h-2 w-2 rounded-full bg-yellow-400" />
                      Good ({contentHealth.good_count})
                    </span>
                  )}
                  {contentHealth.needs_work_count > 0 && (
                    <span className="flex items-center gap-1">
                      <span className="inline-block h-2 w-2 rounded-full bg-red-400" />
                      Needs Work ({contentHealth.needs_work_count})
                    </span>
                  )}
                  {contentHealth.no_score_count > 0 && (
                    <span className="flex items-center gap-1">
                      <span className="inline-block h-2 w-2 rounded-full bg-surface-tertiary border border-surface-secondary" />
                      No Score ({contentHealth.no_score_count})
                    </span>
                  )}
                </div>
              </div>
            );
          })()}

          {/* Needs Improvement list */}
          {contentHealth.needs_work.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-3">
                Needs Improvement
              </h3>
              <div className="space-y-2">
                {contentHealth.needs_work.map((article) => (
                  <div
                    key={article.id}
                    className="flex items-center gap-3 p-2 -mx-2 rounded-lg hover:bg-surface-secondary transition-colors"
                  >
                    {/* Score badge */}
                    <span
                      className={`shrink-0 inline-flex items-center justify-center w-10 h-6 rounded text-xs font-bold ${
                        article.seo_score !== undefined && article.seo_score >= 60
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      {article.seo_score !== undefined ? Math.round(article.seo_score) : "—"}
                    </span>

                    {/* Title + keyword */}
                    <div className="flex-1 min-w-0">
                      <Link
                        href={`/articles/${article.id}`}
                        className="text-sm font-medium text-text-primary hover:text-primary-600 truncate block"
                      >
                        {article.title}
                      </Link>
                      <p className="text-xs text-text-muted truncate">{article.keyword}</p>
                    </div>

                    {/* Improve link */}
                    <Link
                      href={`/articles/${article.id}`}
                      className="shrink-0 text-xs font-medium text-primary-500 hover:text-primary-600 transition-colors"
                    >
                      Improve
                      <ArrowRight className="inline h-3 w-3 ml-0.5" />
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No score articles notice */}
          {contentHealth.no_score.length > 0 && contentHealth.needs_work.length === 0 && (
            <p className="text-sm text-text-muted mt-2">
              {contentHealth.no_score_count} article{contentHealth.no_score_count !== 1 ? "s" : ""} have not been analysed yet.{" "}
              <Link href="/articles" className="text-primary-500 hover:text-primary-600 font-medium">
                View articles
              </Link>
            </p>
          )}

          {/* All good state */}
          {contentHealth.needs_work.length === 0 && contentHealth.no_score.length === 0 && (
            <div className="flex items-center gap-2 text-sm text-green-600">
              <CheckCircle2 className="h-4 w-4" />
              All articles are in good health.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
