"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  RefreshCw,
  Pause,
  FileText,
  AlertTriangle,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";

import { api, parseApiError, BulkJobDetail, BulkJobItem } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const ITEM_STATUS: Record<string, { icon: typeof CheckCircle2; color: string }> = {
  pending: { icon: Clock, color: "text-gray-400" },
  processing: { icon: Loader2, color: "text-blue-500" },
  completed: { icon: CheckCircle2, color: "text-green-500" },
  failed: { icon: XCircle, color: "text-red-500" },
  cancelled: { icon: Pause, color: "text-gray-400" },
};

export default function BulkJobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [job, setJob] = useState<BulkJobDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadJob = useCallback(async () => {
    try {
      const data = await api.bulk.getJob(params.id as string);
      setJob(data);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    loadJob();
  }, [loadJob]);

  // Poll while processing
  useEffect(() => {
    if (!job || (job.status !== "processing" && job.status !== "pending")) return;
    const interval = setInterval(loadJob, 5000);
    return () => clearInterval(interval);
  }, [job?.status, loadJob]);

  const handleCancel = async () => {
    if (!job) return;
    try {
      await api.bulk.cancelJob(job.id);
      toast.success("Job cancelled");
      loadJob();
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  const handleRetry = async () => {
    if (!job) return;
    try {
      await api.bulk.retryFailed(job.id);
      toast.success("Retrying failed items");
      loadJob();
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!job) {
    return (
      <div className="text-center py-12">
        <p className="text-text-secondary">Job not found</p>
        <Link href="/bulk">
          <Button variant="outline" className="mt-4">Back to Bulk Content</Button>
        </Link>
      </div>
    );
  }

  const progress = job.total_items > 0
    ? Math.round(((job.completed_items + job.failed_items) / job.total_items) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/bulk">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-text-primary capitalize">
            {job.job_type.replace(/_/g, " ")}
          </h1>
          <p className="text-sm text-text-secondary">
            Created {new Date(job.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex gap-2">
          {(job.status === "processing" || job.status === "pending") && (
            <Button onClick={handleCancel} variant="outline" size="sm">
              <Pause className="h-4 w-4 mr-1" />
              Cancel
            </Button>
          )}
          {(job.status === "partially_failed" || job.status === "failed") && (
            <Button onClick={handleRetry} variant="primary" size="sm">
              <RefreshCw className="h-4 w-4 mr-1" />
              Retry Failed
            </Button>
          )}
        </div>
      </div>

      {/* Progress */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-xs text-text-secondary">Status</p>
            <p className={`text-sm font-bold mt-1 capitalize ${
              job.status === "completed" ? "text-green-600" :
              job.status === "processing" ? "text-blue-600" :
              job.status === "failed" ? "text-red-600" :
              "text-text-primary"
            }`}>
              {job.status.replace(/_/g, " ")}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-xs text-text-secondary">Total</p>
            <p className="text-lg font-bold text-text-primary mt-1">{job.total_items}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-xs text-text-secondary">Completed</p>
            <p className="text-lg font-bold text-green-600 mt-1">{job.completed_items}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-xs text-text-secondary">Failed</p>
            <p className="text-lg font-bold text-red-600 mt-1">{job.failed_items}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-xs text-text-secondary">Progress</p>
            <p className="text-lg font-bold text-text-primary mt-1">{progress}%</p>
          </CardContent>
        </Card>
      </div>

      {(job.status === "processing" || job.status === "pending") && (
        <div className="h-2 bg-surface-secondary rounded-full overflow-hidden">
          <div
            className="h-full bg-primary-500 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Items */}
      <Card>
        <CardHeader>
          <CardTitle>Items ({job.items.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {job.items.map((item) => {
              const cfg = ITEM_STATUS[item.status] || ITEM_STATUS.pending;
              const Icon = cfg.icon;
              return (
                <div
                  key={item.id}
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-secondary"
                >
                  <Icon className={`h-4 w-4 ${cfg.color} shrink-0 ${item.status === "processing" ? "animate-spin" : ""}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-text-primary truncate">
                      {item.keyword || item.title || "—"}
                    </p>
                    {item.error_message && (
                      <p className="text-xs text-red-500 truncate">{item.error_message}</p>
                    )}
                  </div>
                  {item.resource_id && item.resource_type === "outline" && (
                    <Link href={`/outlines/${item.resource_id}`}>
                      <Button variant="ghost" size="sm">
                        <ExternalLink className="h-3.5 w-3.5" />
                      </Button>
                    </Link>
                  )}
                  {item.resource_id && item.resource_type === "article" && (
                    <Link href={`/articles/${item.resource_id}`}>
                      <Button variant="ghost" size="sm">
                        <ExternalLink className="h-3.5 w-3.5" />
                      </Button>
                    </Link>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
