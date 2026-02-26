"use client";

import { useState, useEffect, useCallback } from "react";
import {
  DollarSign,
  TrendingUp,
  Users,
  Target,
  Plus,
  Trash2,
  Upload,
  FileText,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import { toast } from "sonner";
import {
  api,
  parseApiError,
  RevenueOverview,
  ConversionGoal,
  RevenueByArticleItem,
  RevenueByKeywordItem,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const GOAL_TYPES = [
  { value: "page_visit", label: "Page Visit" },
  { value: "form_submit", label: "Form Submit" },
  { value: "purchase", label: "Purchase" },
  { value: "custom", label: "Custom" },
];

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);

const formatPercent = (value: number) => `${value.toFixed(2)}%`;

function TrendBadge({
  changePercent,
  trend,
}: {
  changePercent: number;
  trend: "up" | "down" | "stable";
}) {
  if (trend === "stable") {
    return <span className="text-xs text-text-muted">No change</span>;
  }
  const isUp = trend === "up";
  return (
    <span
      className={`flex items-center gap-0.5 text-xs font-medium ${
        isUp ? "text-green-600" : "text-red-500"
      }`}
    >
      {isUp ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
      {Math.abs(changePercent).toFixed(1)}%
    </span>
  );
}

export default function RevenueAttributionPage() {
  const today = new Date();
  const thirtyDaysAgo = new Date(today);
  thirtyDaysAgo.setDate(today.getDate() - 30);

  const [startDate, setStartDate] = useState(thirtyDaysAgo.toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState(today.toISOString().slice(0, 10));

  const [overview, setOverview] = useState<RevenueOverview | null>(null);
  const [goals, setGoals] = useState<ConversionGoal[]>([]);
  const [topArticles, setTopArticles] = useState<RevenueByArticleItem[]>([]);
  const [topKeywords, setTopKeywords] = useState<RevenueByKeywordItem[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [isCreatingGoal, setIsCreatingGoal] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [showGoalForm, setShowGoalForm] = useState(false);
  const [deletingGoalId, setDeletingGoalId] = useState<string | null>(null);

  const [newGoal, setNewGoal] = useState({
    name: "",
    goal_type: "page_visit",
    goal_config: "",
  });

  const [importData, setImportData] = useState({
    goal_id: "",
    csvText: "",
  });

  const loadOverview = useCallback(async () => {
    try {
      const data = await api.analytics.revenueOverview({
        start_date: startDate,
        end_date: endDate,
      });
      setOverview(data);
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  }, [startDate, endDate]);

  const loadGoals = useCallback(async () => {
    try {
      const data = await api.analytics.revenueGoals();
      setGoals(data.items);
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  }, []);

  const loadArticles = useCallback(async () => {
    try {
      const data = await api.analytics.revenueByArticle({
        start_date: startDate,
        end_date: endDate,
        page: 1,
        page_size: 10,
      });
      setTopArticles(data.items);
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  }, [startDate, endDate]);

  const loadKeywords = useCallback(async () => {
    try {
      const data = await api.analytics.revenueByKeyword({
        start_date: startDate,
        end_date: endDate,
        page: 1,
        page_size: 10,
      });
      setTopKeywords(data.items);
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  }, [startDate, endDate]);

  const loadAll = useCallback(async () => {
    setIsLoading(true);
    await Promise.all([loadOverview(), loadGoals(), loadArticles(), loadKeywords()]);
    setIsLoading(false);
  }, [loadOverview, loadGoals, loadArticles, loadKeywords]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleCreateGoal = async () => {
    if (!newGoal.name.trim()) {
      toast.error("Goal name is required");
      return;
    }
    try {
      setIsCreatingGoal(true);
      let parsedConfig: Record<string, unknown> | undefined;
      if (newGoal.goal_config.trim()) {
        try {
          parsedConfig = JSON.parse(newGoal.goal_config);
        } catch {
          toast.error("Goal config must be valid JSON");
          return;
        }
      }
      const created = await api.analytics.createRevenueGoal({
        name: newGoal.name,
        goal_type: newGoal.goal_type,
        ...(parsedConfig ? { goal_config: parsedConfig } : {}),
      });
      setGoals((prev) => [...prev, created]);
      setNewGoal({ name: "", goal_type: "page_visit", goal_config: "" });
      setShowGoalForm(false);
      toast.success("Conversion goal created");
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsCreatingGoal(false);
    }
  };

  const handleDeleteGoal = async (goalId: string) => {
    try {
      setDeletingGoalId(goalId);
      await api.analytics.deleteRevenueGoal(goalId);
      setGoals((prev) => prev.filter((g) => g.id !== goalId));
      toast.success("Goal deleted");
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setDeletingGoalId(null);
    }
  };

  const handleImport = async () => {
    if (!importData.goal_id) {
      toast.error("Please select a conversion goal");
      return;
    }
    if (!importData.csvText.trim()) {
      toast.error("Please paste CSV data");
      return;
    }

    const lines = importData.csvText.trim().split("\n");
    // Skip header row if it starts with non-numeric text
    const dataLines = lines.filter((line) => {
      const firstCell = line.split(",")[0].trim();
      return firstCell && !firstCell.toLowerCase().startsWith("page");
    });

    const conversions = dataLines.map((line) => {
      const parts = line.split(",").map((p) => p.trim());
      return {
        page_url: parts[0] || "",
        date: parts[1] || new Date().toISOString().slice(0, 10),
        visits: parseInt(parts[2] || "0", 10) || 0,
        conversions: parseInt(parts[3] || "0", 10) || 0,
        revenue: parseFloat(parts[4] || "0") || 0,
      };
    }).filter((c) => c.page_url);

    if (conversions.length === 0) {
      toast.error("No valid rows found in CSV data");
      return;
    }

    try {
      setIsImporting(true);
      const result = await api.analytics.importConversions({
        goal_id: importData.goal_id,
        conversions,
      });
      toast.success(result.message || `Imported ${result.imported_count} conversions`);
      setImportData({ goal_id: "", csvText: "" });
      await loadAll();
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsImporting(false);
    }
  };

  const handleGenerateReport = async () => {
    try {
      setIsGeneratingReport(true);
      const report = await api.analytics.generateRevenueReport("monthly");
      toast.success(
        `Report generated: ${formatCurrency(report.total_revenue)} revenue over ${report.total_conversions} conversions`
      );
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsGeneratingReport(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Revenue Attribution</h1>
          <p className="text-text-secondary mt-1">
            Track how your organic content drives conversions and revenue
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="text-sm border border-surface-tertiary rounded-lg px-3 py-1.5 bg-surface text-text-primary"
          />
          <span className="text-text-muted text-sm">to</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="text-sm border border-surface-tertiary rounded-lg px-3 py-1.5 bg-surface text-text-primary"
          />
          <Button onClick={loadAll} variant="outline" size="sm" disabled={isLoading}>
            Apply
          </Button>
          <Button
            onClick={handleGenerateReport}
            variant="primary"
            size="sm"
            disabled={isGeneratingReport}
          >
            <FileText className={`h-4 w-4 mr-1 ${isGeneratingReport ? "animate-pulse" : ""}`} />
            {isGeneratingReport ? "Generating..." : "Generate Report"}
          </Button>
        </div>
      </div>

      {/* Overview Cards */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-surface-tertiary animate-pulse rounded-2xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Revenue */}
          <Card>
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-text-secondary">Total Revenue</p>
                <div className="h-9 w-9 rounded-xl bg-green-50 flex items-center justify-center">
                  <DollarSign className="h-5 w-5 text-green-600" />
                </div>
              </div>
              <p className="text-2xl font-bold text-text-primary">
                {overview ? formatCurrency(overview.total_revenue) : "$0.00"}
              </p>
              {overview?.revenue_trend && (
                <div className="mt-1">
                  <TrendBadge
                    changePercent={overview.revenue_trend.change_percent}
                    trend={overview.revenue_trend.trend}
                  />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Total Conversions */}
          <Card>
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-text-secondary">Total Conversions</p>
                <div className="h-9 w-9 rounded-xl bg-blue-50 flex items-center justify-center">
                  <Target className="h-5 w-5 text-blue-600" />
                </div>
              </div>
              <p className="text-2xl font-bold text-text-primary">
                {overview ? overview.total_conversions.toLocaleString() : "0"}
              </p>
              {overview?.conversions_trend && (
                <div className="mt-1">
                  <TrendBadge
                    changePercent={overview.conversions_trend.change_percent}
                    trend={overview.conversions_trend.trend}
                  />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Organic Visits */}
          <Card>
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-text-secondary">Organic Visits</p>
                <div className="h-9 w-9 rounded-xl bg-purple-50 flex items-center justify-center">
                  <Users className="h-5 w-5 text-purple-600" />
                </div>
              </div>
              <p className="text-2xl font-bold text-text-primary">
                {overview ? overview.total_organic_visits.toLocaleString() : "0"}
              </p>
              {overview?.visits_trend && (
                <div className="mt-1">
                  <TrendBadge
                    changePercent={overview.visits_trend.change_percent}
                    trend={overview.visits_trend.trend}
                  />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Conversion Rate */}
          <Card>
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-text-secondary">Conversion Rate</p>
                <div className="h-9 w-9 rounded-xl bg-orange-50 flex items-center justify-center">
                  <TrendingUp className="h-5 w-5 text-orange-600" />
                </div>
              </div>
              <p className="text-2xl font-bold text-text-primary">
                {overview ? formatPercent(overview.conversion_rate) : "0.00%"}
              </p>
              <p className="text-xs text-text-muted mt-1">
                {overview ? overview.active_goals : 0} active goal
                {overview?.active_goals !== 1 ? "s" : ""}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Conversion Goals */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-primary-500" />
              Conversion Goals
            </CardTitle>
            <Button
              onClick={() => setShowGoalForm((v) => !v)}
              variant="outline"
              size="sm"
            >
              <Plus className="h-4 w-4 mr-1" />
              Add Goal
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Inline Add Form */}
          {showGoalForm && (
            <div className="mb-4 p-4 border border-surface-tertiary rounded-xl bg-surface-secondary space-y-3">
              <p className="text-sm font-medium text-text-primary">New Conversion Goal</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-text-secondary mb-1">Goal Name</label>
                  <input
                    type="text"
                    value={newGoal.name}
                    onChange={(e) => setNewGoal((p) => ({ ...p, name: e.target.value }))}
                    placeholder="e.g. Contact Form Submit"
                    className="w-full text-sm border border-surface-tertiary rounded-lg px-3 py-2 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-secondary mb-1">Goal Type</label>
                  <select
                    value={newGoal.goal_type}
                    onChange={(e) => setNewGoal((p) => ({ ...p, goal_type: e.target.value }))}
                    className="w-full text-sm border border-surface-tertiary rounded-lg px-3 py-2 bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    {GOAL_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs text-text-secondary mb-1">
                  Config (optional JSON, e.g. {"{"}"url": "/thank-you"{"}"})
                </label>
                <input
                  type="text"
                  value={newGoal.goal_config}
                  onChange={(e) => setNewGoal((p) => ({ ...p, goal_config: e.target.value }))}
                  placeholder='{"url": "/thank-you"}'
                  className="w-full text-sm border border-surface-tertiary rounded-lg px-3 py-2 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={handleCreateGoal}
                  variant="primary"
                  size="sm"
                  disabled={isCreatingGoal}
                >
                  {isCreatingGoal ? "Creating..." : "Create Goal"}
                </Button>
                <Button
                  onClick={() => {
                    setShowGoalForm(false);
                    setNewGoal({ name: "", goal_type: "page_visit", goal_config: "" });
                  }}
                  variant="ghost"
                  size="sm"
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {/* Goals List */}
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-12 bg-surface-tertiary animate-pulse rounded-xl" />
              ))}
            </div>
          ) : goals.length === 0 ? (
            <div className="text-center py-8">
              <Target className="h-10 w-10 text-text-muted mx-auto mb-2" />
              <p className="text-sm text-text-secondary">No conversion goals yet</p>
              <p className="text-xs text-text-muted mt-1">
                Add a goal to start tracking conversions
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {goals.map((goal) => (
                <div
                  key={goal.id}
                  className="flex items-center justify-between p-3 rounded-xl border border-surface-tertiary hover:bg-surface-secondary transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        goal.is_active
                          ? "bg-green-100 text-green-700"
                          : "bg-surface-tertiary text-text-muted"
                      }`}
                    >
                      {goal.is_active ? "Active" : "Inactive"}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-text-primary">{goal.name}</p>
                      <p className="text-xs text-text-muted capitalize">
                        {GOAL_TYPES.find((t) => t.value === goal.goal_type)?.label ?? goal.goal_type}
                        {goal.goal_config
                          ? ` — ${JSON.stringify(goal.goal_config)}`
                          : ""}
                      </p>
                    </div>
                  </div>
                  <Button
                    onClick={() => handleDeleteGoal(goal.id)}
                    variant="ghost"
                    size="sm"
                    disabled={deletingGoalId === goal.id}
                  >
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Top Articles by Revenue */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary-500" />
            Top Articles by Revenue
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-10 bg-surface-tertiary animate-pulse rounded-xl" />
              ))}
            </div>
          ) : topArticles.length === 0 ? (
            <p className="text-sm text-text-muted text-center py-6">
              No revenue data yet. Import conversion data to get started.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-surface-tertiary">
                    <th className="text-left py-2 px-3 text-xs font-semibold text-text-muted uppercase tracking-wide">
                      Article
                    </th>
                    <th className="text-left py-2 px-3 text-xs font-semibold text-text-muted uppercase tracking-wide">
                      Keyword
                    </th>
                    <th className="text-right py-2 px-3 text-xs font-semibold text-text-muted uppercase tracking-wide">
                      Visits
                    </th>
                    <th className="text-right py-2 px-3 text-xs font-semibold text-text-muted uppercase tracking-wide">
                      Conversions
                    </th>
                    <th className="text-right py-2 px-3 text-xs font-semibold text-text-muted uppercase tracking-wide">
                      Revenue
                    </th>
                    <th className="text-right py-2 px-3 text-xs font-semibold text-text-muted uppercase tracking-wide">
                      Conv. Rate
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-tertiary">
                  {topArticles.map((article) => (
                    <tr
                      key={article.article_id}
                      className="hover:bg-surface-secondary transition-colors"
                    >
                      <td className="py-2.5 px-3">
                        <p className="font-medium text-text-primary truncate max-w-[200px]">
                          {article.title}
                        </p>
                      </td>
                      <td className="py-2.5 px-3 text-text-secondary truncate max-w-[150px]">
                        {article.keyword}
                      </td>
                      <td className="py-2.5 px-3 text-right text-text-primary">
                        {article.visits.toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3 text-right text-text-primary">
                        {article.conversions.toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3 text-right font-medium text-green-600">
                        {formatCurrency(article.revenue)}
                      </td>
                      <td className="py-2.5 px-3 text-right text-text-secondary">
                        {formatPercent(article.conversion_rate)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Top Keywords by Revenue */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary-500" />
            Top Keywords by Revenue
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-10 bg-surface-tertiary animate-pulse rounded-xl" />
              ))}
            </div>
          ) : topKeywords.length === 0 ? (
            <p className="text-sm text-text-muted text-center py-6">
              No keyword revenue data yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-surface-tertiary">
                    <th className="text-left py-2 px-3 text-xs font-semibold text-text-muted uppercase tracking-wide">
                      Keyword
                    </th>
                    <th className="text-right py-2 px-3 text-xs font-semibold text-text-muted uppercase tracking-wide">
                      Visits
                    </th>
                    <th className="text-right py-2 px-3 text-xs font-semibold text-text-muted uppercase tracking-wide">
                      Conversions
                    </th>
                    <th className="text-right py-2 px-3 text-xs font-semibold text-text-muted uppercase tracking-wide">
                      Revenue
                    </th>
                    <th className="text-right py-2 px-3 text-xs font-semibold text-text-muted uppercase tracking-wide">
                      Conv. Rate
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-tertiary">
                  {topKeywords.map((kw, idx) => (
                    <tr
                      key={`${kw.keyword}-${idx}`}
                      className="hover:bg-surface-secondary transition-colors"
                    >
                      <td className="py-2.5 px-3 font-medium text-text-primary">
                        {kw.keyword}
                      </td>
                      <td className="py-2.5 px-3 text-right text-text-primary">
                        {kw.visits.toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3 text-right text-text-primary">
                        {kw.conversions.toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3 text-right font-medium text-green-600">
                        {formatCurrency(kw.revenue)}
                      </td>
                      <td className="py-2.5 px-3 text-right text-text-secondary">
                        {formatPercent(kw.conversion_rate)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Import Data */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5 text-primary-500" />
            Import Conversion Data
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-text-secondary">
            Paste CSV data with columns:{" "}
            <code className="text-xs bg-surface-tertiary px-1.5 py-0.5 rounded text-text-primary">
              page_url, date, visits, conversions, revenue
            </code>
          </p>

          <div>
            <label className="block text-xs text-text-secondary mb-1">Conversion Goal</label>
            <select
              value={importData.goal_id}
              onChange={(e) => setImportData((p) => ({ ...p, goal_id: e.target.value }))}
              className="w-full sm:w-64 text-sm border border-surface-tertiary rounded-lg px-3 py-2 bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Select a goal...</option>
              {goals.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-text-secondary mb-1">CSV Data</label>
            <textarea
              value={importData.csvText}
              onChange={(e) => setImportData((p) => ({ ...p, csvText: e.target.value }))}
              rows={6}
              placeholder={`/blog/my-post, 2025-01-01, 1200, 24, 480.00\n/blog/another-post, 2025-01-01, 850, 17, 340.00`}
              className="w-full text-sm border border-surface-tertiary rounded-lg px-3 py-2 bg-surface text-text-primary placeholder:text-text-muted font-mono resize-y focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <Button
            onClick={handleImport}
            variant="primary"
            size="sm"
            disabled={isImporting || !importData.goal_id || !importData.csvText.trim()}
          >
            <Upload className={`h-4 w-4 mr-1 ${isImporting ? "animate-pulse" : ""}`} />
            {isImporting ? "Importing..." : "Import Data"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
