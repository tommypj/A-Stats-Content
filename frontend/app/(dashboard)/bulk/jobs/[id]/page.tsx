"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
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
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { api, parseApiError, BulkJobDetail, BulkJobItem } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TierGate } from "@/components/ui/tier-gate";

const ITEM_STATUS: Record<string, { icon: typeof CheckCircle2; color: string }> = {
  pending: { icon: Clock, color: "text-text-muted" },
  processing: { icon: Loader2, color: "text-blue-500" },
  completed: { icon: CheckCircle2, color: "text-green-500" },
  failed: { icon: XCircle, color: "text-red-500" },
  cancelled: { icon: Pause, color: "text-text-muted" },
};

const ITEMS_PER_PAGE = 50;

export default function BulkJobDetailPage() {
  const params = useParams();
  const rawId = params.id;
  const jobId = Array.isArray(rawId) ? rawId[0] : (rawId ?? "");
  const queryClient = useQueryClient();
  // FE-CONTENT-18: Client-side pagination to avoid rendering large item lists
  const [itemsPage, setItemsPage] = useState(1);

  const { data: job, isLoading } = useQuery({
    queryKey: ["bulk", "job", jobId],
    queryFn: () => api.bulk.getJob(jobId),
    enabled: !!jobId,
    staleTime: 60_000,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "processing" || status === "pending") return 5000;
      return false;
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => api.bulk.cancelJob(jobId),
    onSuccess: () => {
      toast.success("Job cancelled");
      queryClient.invalidateQueries({ queryKey: ["bulk", "job", jobId] });
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const retryMutation = useMutation({
    mutationFn: () => api.bulk.retryFailed(jobId),
    onSuccess: () => {
      toast.success("Retrying failed items");
      queryClient.invalidateQueries({ queryKey: ["bulk", "job", jobId] });
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  if (!jobId) {
    return <div>Not found</div>;
  }

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
    <TierGate minimum="professional" feature="Bulk Content">
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
            <Button
              onClick={() => cancelMutation.mutate()}
              variant="outline"
              size="sm"
              disabled={cancelMutation.isPending}
            >
              {cancelMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <Pause className="h-4 w-4 mr-1" />
              )}
              Cancel
            </Button>
          )}
          {(job.status === "partially_failed" || job.status === "failed") && (
            <Button
              onClick={() => retryMutation.mutate()}
              variant="primary"
              size="sm"
              disabled={retryMutation.isPending}
            >
              {retryMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-1" />
              )}
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
            {job.items.slice(0, itemsPage * ITEMS_PER_PAGE).map((item) => {
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
          {job.items.length > itemsPage * ITEMS_PER_PAGE && (
            <div className="mt-4 text-center">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setItemsPage((p) => p + 1)}
              >
                Load more ({job.items.length - itemsPage * ITEMS_PER_PAGE} remaining)
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
    </TierGate>
  );
}
