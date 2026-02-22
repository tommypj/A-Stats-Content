"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Plus,
  FileText,
  Loader2,
  MoreVertical,
  Trash2,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Clock,
  Sparkles,
  BarChart2,
  Filter,
  User,
  Users,
} from "lucide-react";
import { api, Article } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { clsx } from "clsx";
import { useTeam } from "@/contexts/TeamContext";
import { ContentOwnershipBadge } from "@/components/team/content-ownership-badge";
import { UsageLimitBanner } from "@/components/team/usage-limit-warning";

const statusConfig = {
  draft: { label: "Draft", color: "bg-gray-100 text-gray-700", icon: FileText },
  generating: { label: "Generating", color: "bg-yellow-100 text-yellow-700", icon: Loader2 },
  completed: { label: "Completed", color: "bg-green-100 text-green-700", icon: CheckCircle2 },
  published: { label: "Published", color: "bg-blue-100 text-blue-700", icon: ExternalLink },
  failed: { label: "Failed", color: "bg-red-100 text-red-700", icon: XCircle },
};

type ContentFilter = "all" | "personal" | "team";

function getSeoScoreColor(score: number | undefined) {
  if (!score) return "text-text-muted";
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  return "text-red-600";
}

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const [contentFilter, setContentFilter] = useState<ContentFilter>("all");

  const {
    currentTeam,
    isPersonalWorkspace,
    canCreate,
    canEdit,
    isViewer,
    usage,
    limits,
    isAtLimit,
  } = useTeam();

  useEffect(() => {
    loadArticles();
  }, [currentTeam, contentFilter]);

  async function loadArticles() {
    try {
      setLoading(true);
      const params: any = { page_size: 50 };

      // Apply team context
      if (!isPersonalWorkspace && currentTeam) {
        params.team_id = currentTeam.id;
      }

      // Apply content filter
      if (contentFilter === "personal") {
        delete params.team_id;
      } else if (contentFilter === "team" && currentTeam) {
        params.team_id = currentTeam.id;
      }

      const response = await api.articles.list(params);
      setArticles(response.items);
    } catch (error) {
      console.error("Failed to load articles:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Are you sure you want to delete this article?")) return;

    try {
      await api.articles.delete(id);
      setArticles(articles.filter((a) => a.id !== id));
    } catch (error) {
      console.error("Failed to delete article:", error);
    }
    setActiveMenu(null);
  }

  const showCreateButton = canCreate && !isAtLimit("articles");
  const articlesUsed = usage?.articles_used || 0;
  const articlesLimit = limits?.articles_per_month || Infinity;

  return (
    <div className="space-y-6">
      {/* Usage Limit Warning */}
      {!isPersonalWorkspace && currentTeam && usage && limits && (
        <UsageLimitBanner
          resource="articles"
          used={articlesUsed}
          limit={articlesLimit}
          isTeam={true}
          teamName={currentTeam.name}
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-text-primary">
            Articles
          </h1>
          <p className="text-text-secondary mt-1">
            {isPersonalWorkspace
              ? "Manage and edit your generated articles"
              : `Managing articles for ${currentTeam?.name}`}
          </p>
        </div>
        <div className="flex gap-2">
          {/* Content Filter (only show in team context) */}
          {!isPersonalWorkspace && currentTeam && (
            <div className="flex items-center gap-1 bg-surface-secondary rounded-lg p-1">
              <button
                onClick={() => setContentFilter("all")}
                className={clsx(
                  "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  contentFilter === "all"
                    ? "bg-white text-text-primary shadow-sm"
                    : "text-text-secondary hover:text-text-primary"
                )}
              >
                <span className="flex items-center gap-1.5">
                  <Filter className="h-4 w-4" />
                  All
                </span>
              </button>
              <button
                onClick={() => setContentFilter("personal")}
                className={clsx(
                  "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  contentFilter === "personal"
                    ? "bg-white text-text-primary shadow-sm"
                    : "text-text-secondary hover:text-text-primary"
                )}
              >
                <span className="flex items-center gap-1.5">
                  <User className="h-4 w-4" />
                  Personal
                </span>
              </button>
              <button
                onClick={() => setContentFilter("team")}
                className={clsx(
                  "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  contentFilter === "team"
                    ? "bg-white text-text-primary shadow-sm"
                    : "text-text-secondary hover:text-text-primary"
                )}
              >
                <span className="flex items-center gap-1.5">
                  <Users className="h-4 w-4" />
                  Team
                </span>
              </button>
            </div>
          )}

          <Link href="/outlines">
            <Button variant="outline">
              <FileText className="h-4 w-4 mr-2" />
              From Outline
            </Button>
          </Link>
          {showCreateButton ? (
            <Link href="/articles/new">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                New Article
              </Button>
            </Link>
          ) : isViewer ? (
            <Button disabled title="Viewers cannot create content">
              <Plus className="h-4 w-4 mr-2" />
              New Article
            </Button>
          ) : (
            <Button disabled title="Article limit reached">
              <Plus className="h-4 w-4 mr-2" />
              Limit Reached
            </Button>
          )}
        </div>
      </div>

      {/* Articles List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
        </div>
      ) : articles.length === 0 ? (
        <Card className="p-12 text-center">
          <Sparkles className="h-12 w-12 text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-medium text-text-primary mb-2">
            No articles yet
          </h3>
          <p className="text-text-secondary mb-6">
            {isViewer
              ? "Your team has not created any articles yet"
              : "Create an outline first, then generate an article from it"}
          </p>
          {!isViewer && (
            <Link href="/outlines">
              <Button>
                <FileText className="h-4 w-4 mr-2" />
                Create Outline
              </Button>
            </Link>
          )}
        </Card>
      ) : (
        <div className="space-y-4">
          {articles.map((article) => {
            const status = statusConfig[article.status];
            const StatusIcon = status.icon;
            const isTeamContent = !!article.team_id;
            const canModify = canEdit;

            return (
              <Card key={article.id} className="p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start gap-4">
                  {/* Status & SEO Score */}
                  <div className="flex flex-col items-center gap-2 w-16">
                    <span className={clsx("w-full text-center px-2 py-1 rounded-lg text-xs font-medium", status.color)}>
                      {status.label}
                    </span>
                    {article.seo_score !== undefined && (
                      <div className={clsx("text-center", getSeoScoreColor(article.seo_score))}>
                        <BarChart2 className="h-4 w-4 mx-auto" />
                        <span className="text-xs font-medium">{Math.round(article.seo_score)}</span>
                      </div>
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-2 mb-2">
                      <Link href={`/articles/${article.id}`} className="group flex-1">
                        <h3 className="font-medium text-text-primary group-hover:text-primary-600 line-clamp-1">
                          {article.title}
                        </h3>
                      </Link>
                      <ContentOwnershipBadge
                        teamId={article.team_id}
                        teamName={currentTeam?.name}
                        isPersonal={!isTeamContent}
                        variant="compact"
                      />
                    </div>

                    {article.meta_description && (
                      <p className="text-sm text-text-secondary mt-1 line-clamp-2">
                        {article.meta_description}
                      </p>
                    )}

                    <div className="flex items-center gap-4 mt-2 text-sm text-text-muted">
                      <span className="px-2 py-0.5 bg-surface-secondary rounded-md">
                        {article.keyword}
                      </span>
                      <span className="flex items-center gap-1">
                        <FileText className="h-3.5 w-3.5" />
                        {article.word_count} words
                      </span>
                      {article.read_time && (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3.5 w-3.5" />
                          {article.read_time} min read
                        </span>
                      )}
                      <span>{new Date(article.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="relative flex items-center gap-1">
                    {/* Show delete button directly for failed/stuck articles */}
                    {(article.status === "failed" || article.status === "generating") && (
                      <button
                        onClick={() => handleDelete(article.id)}
                        className="p-1.5 rounded-lg hover:bg-red-50 text-red-400 hover:text-red-600 transition-colors"
                        title="Delete article"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                    <button
                      onClick={() => setActiveMenu(activeMenu === article.id ? null : article.id)}
                      className="p-1.5 rounded-lg hover:bg-surface-secondary"
                      disabled={isViewer}
                    >
                      <MoreVertical className="h-4 w-4 text-text-muted" />
                    </button>

                    {activeMenu === article.id && (
                      <>
                        <div className="fixed inset-0 z-40" onClick={() => setActiveMenu(null)} />
                        <div className="absolute right-0 mt-1 w-40 bg-white rounded-lg border border-surface-tertiary shadow-lg z-50">
                          <Link
                            href={`/articles/${article.id}`}
                            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary"
                            onClick={() => setActiveMenu(null)}
                          >
                            <FileText className="h-4 w-4" />
                            {canModify ? "Edit" : "View"}
                          </Link>
                          {article.published_url && (
                            <a
                              href={article.published_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary"
                            >
                              <ExternalLink className="h-4 w-4" />
                              View Live
                            </a>
                          )}
                          <button
                            onClick={() => handleDelete(article.id)}
                            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                          >
                            <Trash2 className="h-4 w-4" />
                            Delete
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {/* Viewer Banner */}
                {isViewer && (
                  <div className="mt-3 pt-3 border-t border-surface-tertiary">
                    <p className="text-xs text-text-muted italic">
                      View-only mode: You cannot edit team content
                    </p>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
