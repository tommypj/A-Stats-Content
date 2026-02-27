"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Sparkles,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  RefreshCw,
  Zap,
  Target,
  FileText,
  List,
  MessageSquare,
  Layout,
} from "lucide-react";
import { toast } from "sonner";

import { api, parseApiError, AEOOverviewResponse, AEOArticleSummary } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const CATEGORY_ICONS: Record<string, typeof Sparkles> = {
  structure_score: Layout,
  faq_score: MessageSquare,
  entity_score: Target,
  conciseness_score: FileText,
  schema_score: List,
  citation_readiness: Zap,
};

const CATEGORY_LABELS: Record<string, string> = {
  structure_score: "Structure",
  faq_score: "FAQ Patterns",
  entity_score: "Entity Coverage",
  conciseness_score: "Conciseness",
  schema_score: "Schema Ready",
  citation_readiness: "Citation Ready",
};

const CATEGORY_MAX: Record<string, number> = {
  structure_score: 20,
  faq_score: 20,
  entity_score: 15,
  conciseness_score: 20,
  schema_score: 10,
  citation_readiness: 15,
};

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 80
      ? "bg-green-100 text-green-700"
      : score >= 50
        ? "bg-yellow-100 text-yellow-700"
        : "bg-red-100 text-red-700";
  return (
    <span className={`inline-flex items-center justify-center w-10 h-10 rounded-full font-bold text-sm ${color}`}>
      {score}
    </span>
  );
}

export default function AEOPage() {
  const [overview, setOverview] = useState<AEOOverviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadOverview = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await api.analytics.aeoOverview();
      setOverview(data);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const scoreColor = (score: number) =>
    score >= 80 ? "text-green-600" : score >= 50 ? "text-yellow-600" : "text-red-600";

  const scoreBg = (score: number) =>
    score >= 80 ? "bg-green-50 border-green-200" : score >= 50 ? "bg-yellow-50 border-yellow-200" : "bg-red-50 border-red-200";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">AEO Scores</h1>
          <p className="text-text-secondary mt-1">
            Answer Engine Optimization — how AI-ready your content is
          </p>
        </div>
        <Button onClick={loadOverview} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-1" />
          Refresh
        </Button>
      </div>

      {!overview || overview.total_scored === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <Sparkles className="h-12 w-12 text-primary-400 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-text-primary">No AEO Scores Yet</h3>
            <p className="text-text-secondary mt-1 max-w-md mx-auto">
              AEO scores are calculated when you open an article. Go to any article and check the AEO panel in the sidebar to get started.
            </p>
            <Link href="/articles">
              <Button variant="primary" size="sm" className="mt-4">
                Go to Articles
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <Card className={`${scoreBg(overview.average_score)} border`}>
              <CardContent className="p-4 text-center">
                <p className="text-sm text-text-secondary">Average Score</p>
                <p className={`text-4xl font-bold mt-1 ${scoreColor(overview.average_score)}`}>
                  {overview.average_score}
                </p>
                <p className="text-xs text-text-muted mt-1">out of 100</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-sm text-text-secondary">Articles Scored</p>
                <p className="text-2xl font-bold text-text-primary mt-1">
                  {overview.total_scored}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-sm text-text-secondary">Excellent (80+)</p>
                <p className="text-2xl font-bold text-green-600 mt-1">
                  {overview.excellent_count}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-sm text-text-secondary">Good (50-79)</p>
                <p className="text-2xl font-bold text-yellow-600 mt-1">
                  {overview.good_count}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-sm text-text-secondary">Needs Work (&lt;50)</p>
                <p className="text-2xl font-bold text-red-600 mt-1">
                  {overview.needs_work_count}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Score Distribution */}
          <Card>
            <CardHeader>
              <CardTitle>Score Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Object.entries(overview?.score_distribution ?? {}).map(([range, count]) => {
                  const maxCount = Math.max(...Object.values(overview?.score_distribution ?? {}), 1);
                  const pct = (count / maxCount) * 100;
                  const barColor =
                    range === "81-100" ? "bg-green-500" :
                    range === "61-80" ? "bg-green-400" :
                    range === "41-60" ? "bg-yellow-500" :
                    range === "21-40" ? "bg-orange-500" :
                    "bg-red-500";
                  return (
                    <div key={range} className="flex items-center gap-3">
                      <span className="text-sm text-text-secondary w-16 text-right">{range}</span>
                      <div className="flex-1 h-6 bg-surface-secondary rounded-full overflow-hidden">
                        <div
                          className={`h-full ${barColor} rounded-full transition-all duration-500`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-text-primary w-8">{count}</span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Top & Bottom Articles */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Performers */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-500" />
                  Top AEO Performers
                </CardTitle>
              </CardHeader>
              <CardContent>
                {overview.top_articles.length === 0 ? (
                  <p className="text-sm text-text-muted text-center py-4">No scored articles yet</p>
                ) : (
                  <div className="space-y-3">
                    {overview.top_articles.map((article) => (
                      <Link
                        key={article.article_id}
                        href={`/articles/${article.article_id}`}
                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-secondary transition-colors"
                      >
                        <ScoreBadge score={article.aeo_score} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-text-primary truncate">
                            {article.title}
                          </p>
                          <p className="text-xs text-text-muted truncate">{article.keyword}</p>
                        </div>
                        <ChevronRight className="h-4 w-4 text-text-muted shrink-0" />
                      </Link>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Needs Improvement */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-yellow-500" />
                  Needs Improvement
                </CardTitle>
              </CardHeader>
              <CardContent>
                {overview.bottom_articles.length === 0 ? (
                  <p className="text-sm text-text-muted text-center py-4">
                    <CheckCircle2 className="h-5 w-5 text-green-500 inline mr-1" />
                    All articles are performing well!
                  </p>
                ) : (
                  <div className="space-y-3">
                    {overview.bottom_articles.map((article) => (
                      <Link
                        key={article.article_id}
                        href={`/articles/${article.article_id}`}
                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-secondary transition-colors"
                      >
                        <ScoreBadge score={article.aeo_score} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-text-primary truncate">
                            {article.title}
                          </p>
                          <p className="text-xs text-text-muted truncate">{article.keyword}</p>
                        </div>
                        <ChevronRight className="h-4 w-4 text-text-muted shrink-0" />
                      </Link>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
