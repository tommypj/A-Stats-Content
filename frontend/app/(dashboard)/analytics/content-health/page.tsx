"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  TrendingDown,
  ArrowDown,
  Eye,
  MousePointerClick,
  Target,
  RefreshCw,
  Sparkles,
  ChevronRight,
  Filter,
  Check,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";

import {
  api,
  parseApiError,
  ContentDecayAlert,
  ContentHealthSummary2,
  DecayAlertsParams,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GscConnectBanner } from "@/components/analytics/gsc-connect-banner";

const ALERT_TYPE_LABELS: Record<string, string> = {
  position_drop: "Position Drop",
  traffic_drop: "Traffic Drop",
  ctr_drop: "CTR Drop",
  impressions_drop: "Impressions Drop",
};

const ALERT_TYPE_ICONS: Record<string, typeof TrendingDown> = {
  position_drop: Target,
  traffic_drop: MousePointerClick,
  ctr_drop: TrendingDown,
  impressions_drop: Eye,
};

const METRIC_LABELS: Record<string, string> = {
  position: "Position",
  clicks: "Clicks",
  ctr: "CTR",
  impressions: "Impressions",
};

function formatMetricValue(metric: string, value: number): string {
  if (metric === "ctr") return `${(value * 100).toFixed(2)}%`;
  if (metric === "position") return value.toFixed(1);
  return Math.round(value).toLocaleString();
}

export default function ContentHealthPage() {
  const [isConnected, setIsConnected] = useState<boolean | null>(null);
  const [health, setHealth] = useState<ContentHealthSummary2 | null>(null);
  const [alerts, setAlerts] = useState<ContentDecayAlert[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isDetecting, setIsDetecting] = useState(false);
  const [isSuggesting, setIsSuggesting] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>("");
  const [filterSeverity, setFilterSeverity] = useState<string>("");
  const [showResolved, setShowResolved] = useState(false);

  const checkConnection = useCallback(async () => {
    try {
      const status = await api.analytics.status();
      setIsConnected(status.connected && !!status.site_url);
    } catch {
      setIsConnected(false);
    }
  }, []);

  const loadHealth = useCallback(async () => {
    try {
      const data = await api.analytics.contentHealth();
      setHealth(data);
    } catch (err) {
      // Non-critical, health might not be available
    }
  }, []);

  const loadAlerts = useCallback(async () => {
    try {
      setIsLoading(true);
      const params: DecayAlertsParams = {
        page,
        page_size: 20,
        sort_by: "created_at",
        sort_order: "desc",
      };
      if (filterType) params.alert_type = filterType;
      if (filterSeverity) params.severity = filterSeverity;
      if (!showResolved) params.is_resolved = false;

      const data = await api.analytics.decayAlerts(params);
      setAlerts(data.items);
      setTotal(data.total);
      setPages(data.pages);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsLoading(false);
    }
  }, [page, filterType, filterSeverity, showResolved]);

  useEffect(() => {
    checkConnection();
  }, [checkConnection]);

  useEffect(() => {
    if (isConnected) {
      loadHealth();
      loadAlerts();
    } else if (isConnected === false) {
      setIsLoading(false);
    }
  }, [isConnected, loadHealth, loadAlerts]);

  const handleDetect = async () => {
    try {
      setIsDetecting(true);
      const result = await api.analytics.detectDecay();
      toast.success(result.message);
      await loadHealth();
      await loadAlerts();
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsDetecting(false);
    }
  };

  const handleResolve = async (alertId: string) => {
    try {
      await api.analytics.resolveAlert(alertId);
      toast.success("Alert resolved");
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
      setTotal((prev) => prev - 1);
      if (health) {
        setHealth({
          ...health,
          total_active_alerts: health.total_active_alerts - 1,
        });
      }
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  const handleSuggest = async (alertId: string) => {
    try {
      setIsSuggesting(alertId);
      const result = await api.analytics.suggestRecovery(alertId);
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === alertId
            ? { ...a, suggested_actions: { suggestions: result.suggestions } }
            : a
        )
      );
      toast.success("Recovery suggestions generated");
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsSuggesting(null);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.analytics.markAllAlertsRead();
      setAlerts((prev) => prev.map((a) => ({ ...a, is_read: true })));
      toast.success("All alerts marked as read");
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  if (isConnected === null) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isConnected) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Content Health</h1>
          <p className="text-text-secondary mt-1">
            Monitor content performance and detect declining articles
          </p>
        </div>
        <GscConnectBanner onConnect={async () => {
          try {
            const { auth_url } = await api.analytics.getAuthUrl();
            window.open(auth_url, "_blank", "noopener,noreferrer");
          } catch (err) {
            toast.error(parseApiError(err).message);
          }
        }} />
      </div>
    );
  }

  const healthColor =
    health && health.health_score >= 80
      ? "text-green-600"
      : health && health.health_score >= 50
        ? "text-yellow-600"
        : "text-red-600";

  const healthBg =
    health && health.health_score >= 80
      ? "bg-green-50 border-green-200"
      : health && health.health_score >= 50
        ? "bg-yellow-50 border-yellow-200"
        : "bg-red-50 border-red-200";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Content Health</h1>
          <p className="text-text-secondary mt-1">
            Monitor declining content and take action to recover rankings
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={handleMarkAllRead}
            variant="outline"
            size="sm"
            disabled={alerts.every((a) => a.is_read)}
          >
            <Check className="h-4 w-4 mr-1" />
            Mark All Read
          </Button>
          <Button
            onClick={handleDetect}
            variant="primary"
            size="sm"
            disabled={isDetecting}
          >
            <RefreshCw className={`h-4 w-4 mr-1 ${isDetecting ? "animate-spin" : ""}`} />
            {isDetecting ? "Scanning..." : "Run Detection"}
          </Button>
        </div>
      </div>

      {/* Health Score + Stats */}
      {health && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <Card className={`${healthBg} border`}>
            <CardContent className="p-4 text-center">
              <p className="text-sm text-text-secondary">Health Score</p>
              <p className={`text-4xl font-bold mt-1 ${healthColor}`}>
                {health.health_score}
              </p>
              <p className="text-xs text-text-muted mt-1">out of 100</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-sm text-text-secondary">Published Articles</p>
              <p className="text-2xl font-bold text-text-primary mt-1">
                {health.total_published_articles}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-sm text-text-secondary">Declining</p>
              <p className="text-2xl font-bold text-red-600 mt-1">
                {health.declining_articles}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-sm text-text-secondary">Warnings</p>
              <p className="text-2xl font-bold text-yellow-600 mt-1">
                {health.active_warnings}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-sm text-text-secondary">Critical</p>
              <p className="text-2xl font-bold text-red-600 mt-1">
                {health.active_criticals}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-2 items-center">
        <Filter className="h-4 w-4 text-text-muted" />
        <select
          value={filterType}
          onChange={(e) => { setFilterType(e.target.value); setPage(1); }}
          className="text-sm border border-surface-tertiary rounded-lg px-3 py-1.5 bg-surface text-text-primary"
        >
          <option value="">All Types</option>
          <option value="position_drop">Position Drop</option>
          <option value="traffic_drop">Traffic Drop</option>
          <option value="ctr_drop">CTR Drop</option>
          <option value="impressions_drop">Impressions Drop</option>
        </select>
        <select
          value={filterSeverity}
          onChange={(e) => { setFilterSeverity(e.target.value); setPage(1); }}
          className="text-sm border border-surface-tertiary rounded-lg px-3 py-1.5 bg-surface text-text-primary"
        >
          <option value="">All Severities</option>
          <option value="warning">Warning</option>
          <option value="critical">Critical</option>
        </select>
        <label className="flex items-center gap-1.5 text-sm text-text-secondary cursor-pointer">
          <input
            type="checkbox"
            checked={showResolved}
            onChange={(e) => { setShowResolved(e.target.checked); setPage(1); }}
            className="rounded border-surface-tertiary"
          />
          Show Resolved
        </label>
      </div>

      {/* Alerts List */}
      {isLoading ? (
        <div className="flex items-center justify-center min-h-[200px]">
          <div className="h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : alerts.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-text-primary">All Clear!</h3>
            <p className="text-text-secondary mt-1">
              No content decay alerts detected. Your content is performing well.
            </p>
            <Button onClick={handleDetect} variant="outline" size="sm" className="mt-4">
              Run Detection
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => {
            const Icon = ALERT_TYPE_ICONS[alert.alert_type] || TrendingDown;
            const hasSuggestions = alert.suggested_actions?.suggestions?.length;

            return (
              <Card
                key={alert.id}
                className={`transition-colors ${!alert.is_read ? "border-l-4 border-l-primary-500" : ""} ${alert.is_resolved ? "opacity-60" : ""}`}
              >
                <CardContent className="p-4">
                  <div className="flex flex-col sm:flex-row sm:items-start gap-3">
                    {/* Icon + Severity */}
                    <div className="flex items-center gap-2 shrink-0">
                      {alert.severity === "critical" ? (
                        <AlertOctagon className="h-5 w-5 text-red-500" />
                      ) : (
                        <AlertTriangle className="h-5 w-5 text-yellow-500" />
                      )}
                      <Icon className="h-4 w-4 text-text-muted" />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className={`text-xs font-semibold uppercase px-2 py-0.5 rounded-full ${
                          alert.severity === "critical"
                            ? "bg-red-100 text-red-700"
                            : "bg-yellow-100 text-yellow-700"
                        }`}>
                          {alert.severity}
                        </span>
                        <span className="text-sm font-medium text-text-primary">
                          {ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type}
                        </span>
                        {alert.article_title && (
                          <Link
                            href={`/articles/${alert.article_id}`}
                            className="text-sm text-primary-600 hover:underline truncate max-w-[200px]"
                          >
                            {alert.article_title}
                          </Link>
                        )}
                      </div>

                      <p className="text-sm text-text-secondary">
                        <span className="font-medium">{alert.keyword || "Page"}</span>
                        {" — "}
                        {METRIC_LABELS[alert.metric_name] || alert.metric_name}:{" "}
                        <span className="text-text-primary font-medium">
                          {formatMetricValue(alert.metric_name, alert.metric_before)}
                        </span>
                        {" → "}
                        <span className="text-red-600 font-medium">
                          {formatMetricValue(alert.metric_name, alert.metric_after)}
                        </span>
                        {" "}
                        <span className="text-red-500">
                          ({alert.percentage_change > 0 ? "+" : ""}{alert.percentage_change.toFixed(1)}%)
                        </span>
                      </p>

                      <p className="text-xs text-text-muted mt-1">
                        {alert.period_days}-day comparison — {new Date(alert.created_at).toLocaleDateString()}
                      </p>

                      {/* Suggestions */}
                      {hasSuggestions ? (
                        <div className="mt-3 space-y-2">
                          <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
                            Recovery Suggestions
                          </p>
                          {alert.suggested_actions!.suggestions.map((s, i) => (
                            <div
                              key={i}
                              className="flex items-start gap-2 text-sm bg-surface-secondary rounded-lg p-2"
                            >
                              <ChevronRight className="h-4 w-4 text-primary-500 mt-0.5 shrink-0" />
                              <div>
                                <span className="font-medium text-text-primary">
                                  {s.action}
                                </span>
                                <span className="text-text-secondary ml-1">
                                  — {s.description}
                                </span>
                                <div className="flex gap-2 mt-0.5">
                                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                                    s.priority === "high" ? "bg-red-100 text-red-600" :
                                    s.priority === "medium" ? "bg-yellow-100 text-yellow-600" :
                                    "bg-green-100 text-green-600"
                                  }`}>
                                    {s.priority} priority
                                  </span>
                                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                                    s.estimated_impact === "high" ? "bg-blue-100 text-blue-600" :
                                    s.estimated_impact === "medium" ? "bg-gray-100 text-gray-600" :
                                    "bg-gray-50 text-gray-500"
                                  }`}>
                                    {s.estimated_impact} impact
                                  </span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>

                    {/* Actions */}
                    <div className="flex sm:flex-col gap-2 shrink-0">
                      {!hasSuggestions && !alert.is_resolved && (
                        <Button
                          onClick={() => handleSuggest(alert.id)}
                          variant="outline"
                          size="sm"
                          disabled={isSuggesting === alert.id}
                        >
                          <Sparkles className={`h-3.5 w-3.5 mr-1 ${isSuggesting === alert.id ? "animate-spin" : ""}`} />
                          {isSuggesting === alert.id ? "..." : "Suggest Fix"}
                        </Button>
                      )}
                      {alert.article_id && (
                        <Link href={`/articles/${alert.article_id}`}>
                          <Button variant="outline" size="sm" className="w-full">
                            <ExternalLink className="h-3.5 w-3.5 mr-1" />
                            Edit
                          </Button>
                        </Link>
                      )}
                      {!alert.is_resolved && (
                        <Button
                          onClick={() => handleResolve(alert.id)}
                          variant="ghost"
                          size="sm"
                        >
                          <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                          Resolve
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}

          {/* Pagination */}
          {pages > 1 && (
            <div className="flex items-center justify-between pt-4">
              <p className="text-sm text-text-secondary">
                Showing {(page - 1) * 20 + 1}-{Math.min(page * 20, total)} of {total} alerts
              </p>
              <div className="flex gap-2">
                <Button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  variant="outline"
                  size="sm"
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <Button
                  onClick={() => setPage((p) => Math.min(pages, p + 1))}
                  variant="outline"
                  size="sm"
                  disabled={page === pages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
