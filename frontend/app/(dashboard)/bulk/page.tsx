"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Layers,
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Plus,
  Trash2,
  ChevronRight,
  FileText,
  AlertTriangle,
  Pause,
} from "lucide-react";
import { toast } from "sonner";

import {
  api,
  parseApiError,
  BulkJob,
  BulkKeywordInput,
  ContentTemplate,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const STATUS_CONFIG: Record<string, { icon: typeof CheckCircle2; color: string; label: string }> = {
  pending: { icon: Clock, color: "text-gray-500", label: "Pending" },
  processing: { icon: Loader2, color: "text-blue-500", label: "Processing" },
  completed: { icon: CheckCircle2, color: "text-green-500", label: "Completed" },
  partially_failed: { icon: AlertTriangle, color: "text-yellow-500", label: "Partial" },
  failed: { icon: XCircle, color: "text-red-500", label: "Failed" },
  cancelled: { icon: Pause, color: "text-gray-400", label: "Cancelled" },
};

export default function BulkContentPage() {
  const [keywords, setKeywords] = useState("");
  const [templateId, setTemplateId] = useState<string>("");
  const [templates, setTemplates] = useState<ContentTemplate[]>([]);
  const [jobs, setJobs] = useState<BulkJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [pollingActive, setPollingActive] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [templatesRes, jobsRes] = await Promise.all([
        api.bulk.templates(),
        api.bulk.jobs({ page: 1, page_size: 20 }),
      ]);
      setTemplates(templatesRes.items);
      setJobs(jobsRes.items);

      // Check if any jobs are processing
      const hasActive = jobsRes.items.some((j) => j.status === "processing" || j.status === "pending");
      setPollingActive(hasActive);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Poll for active jobs
  useEffect(() => {
    if (!pollingActive) return;
    if (jobs.length === 0) return; // no jobs to poll
    const interval = setInterval(async () => {
      try {
        const jobsRes = await api.bulk.jobs({ page: 1, page_size: 20 });
        setJobs(jobsRes.items);
        const hasActive = jobsRes.items.some((j) => j.status === "processing" || j.status === "pending");
        if (!hasActive) setPollingActive(false);
      } catch {
        // Silent
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [pollingActive, jobs.length]);

  const parseKeywords = (): BulkKeywordInput[] => {
    const uniqueKeywords = [...new Set(
      keywords
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => line.length > 0)
    )];
    return uniqueKeywords.map((line) => ({ keyword: line }));
  };

  const handleCreate = async () => {
    const kws = parseKeywords();
    if (kws.length === 0) {
      toast.error("Enter at least one keyword");
      return;
    }
    if (kws.length > 50) {
      toast.error("Maximum 50 keywords per job");
      return;
    }

    try {
      setIsCreating(true);
      const job = await api.bulk.createOutlineJob({
        keywords: kws,
        template_id: templateId || undefined,
      });
      toast.success(`Bulk job started with ${job.total_items} keywords`);
      setKeywords("");
      setJobs((prev) => [job, ...prev]);
      setPollingActive(true);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsCreating(false);
    }
  };

  const handleCancel = async (jobId: string) => {
    try {
      await api.bulk.cancelJob(jobId);
      toast.success("Job cancelled");
      loadData();
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  const handleRetry = async (jobId: string) => {
    try {
      await api.bulk.retryFailed(jobId);
      toast.success("Retrying failed items");
      setPollingActive(true);
      loadData();
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  const keywordCount = parseKeywords().length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Bulk Content</h1>
          <p className="text-text-secondary mt-1">
            Generate outlines in bulk from a list of keywords
          </p>
        </div>
        <Link href="/bulk/templates">
          <Button variant="outline" size="sm">
            <Layers className="h-4 w-4 mr-1" />
            Templates
          </Button>
        </Link>
      </div>

      {/* Create Job */}
      <Card>
        <CardHeader>
          <CardTitle>Create Bulk Job</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1">
              Keywords (one per line)
            </label>
            <textarea
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder={"best project management tools\nhow to improve team productivity\nremote work best practices"}
              rows={6}
              className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-y"
            />
            <p className="text-xs text-text-muted mt-1">
              {keywordCount} keyword{keywordCount !== 1 ? "s" : ""} entered (max 50)
            </p>
          </div>

          {templates.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">
                Template (optional)
              </label>
              <select
                value={templateId}
                onChange={(e) => setTemplateId(e.target.value)}
                className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface text-text-primary"
              >
                <option value="">Default settings</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <Button
            onClick={handleCreate}
            variant="primary"
            disabled={isCreating || keywordCount === 0}
          >
            {isCreating ? (
              <Loader2 className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-1" />
            )}
            {isCreating ? "Starting..." : `Generate ${keywordCount} Outline${keywordCount !== 1 ? "s" : ""}`}
          </Button>
        </CardContent>
      </Card>

      {/* Jobs List */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-text-primary">Recent Jobs</h2>
          <Button onClick={loadData} variant="ghost" size="sm">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center min-h-[200px]">
            <div className="h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : jobs.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center">
              <Layers className="h-12 w-12 text-text-muted mx-auto mb-3" />
              <h3 className="text-lg font-semibold text-text-primary">No Jobs Yet</h3>
              <p className="text-text-secondary mt-1">
                Enter keywords above and click Generate to start your first bulk job.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => {
              const cfg = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending;
              const Icon = cfg.icon;
              const progress = job.total_items > 0
                ? Math.round(((job.completed_items + job.failed_items) / job.total_items) * 100)
                : 0;

              return (
                <Card key={job.id} className="hover:shadow-sm transition-shadow">
                  <CardContent className="p-4">
                    <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <Icon className={`h-5 w-5 ${cfg.color} shrink-0 ${job.status === "processing" ? "animate-spin" : ""}`} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-text-primary capitalize">
                              {job.job_type.replace(/_/g, " ")}
                            </span>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              job.status === "completed" ? "bg-green-100 text-green-700" :
                              job.status === "processing" ? "bg-blue-100 text-blue-700" :
                              job.status === "failed" ? "bg-red-100 text-red-700" :
                              job.status === "partially_failed" ? "bg-yellow-100 text-yellow-700" :
                              "bg-gray-100 text-gray-600"
                            }`}>
                              {cfg.label}
                            </span>
                          </div>
                          <p className="text-xs text-text-muted mt-0.5">
                            {job.completed_items}/{job.total_items} completed
                            {job.failed_items > 0 && ` · ${job.failed_items} failed`}
                            {" · "}
                            {new Date(job.created_at).toLocaleDateString()}
                          </p>
                          {(job.status === "processing" || job.status === "pending") && (
                            <div className="mt-2 h-1.5 bg-surface-secondary rounded-full overflow-hidden max-w-[200px]">
                              <div
                                className="h-full bg-primary-500 rounded-full transition-all duration-500"
                                style={{ width: `${progress}%` }}
                              />
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="flex gap-2 shrink-0">
                        {(job.status === "processing" || job.status === "pending") && (
                          <Button onClick={() => handleCancel(job.id)} variant="ghost" size="sm">
                            <Pause className="h-3.5 w-3.5 mr-1" />
                            Cancel
                          </Button>
                        )}
                        {(job.status === "partially_failed" || job.status === "failed") && (
                          <Button onClick={() => handleRetry(job.id)} variant="outline" size="sm">
                            <RefreshCw className="h-3.5 w-3.5 mr-1" />
                            Retry
                          </Button>
                        )}
                        <Link href={`/bulk/jobs/${job.id}`}>
                          <Button variant="ghost" size="sm">
                            Details
                            <ChevronRight className="h-3.5 w-3.5 ml-1" />
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
