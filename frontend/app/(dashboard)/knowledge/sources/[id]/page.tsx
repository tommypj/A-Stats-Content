"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  FileText,
  FileType,
  File,
  Calendar,
  HardDrive,
  Hash,
  AlertCircle,
  CheckCircle,
  Clock,
  Loader2,
  Trash2,
  RefreshCw,
  Tag,
} from "lucide-react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { api, parseApiError } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog } from "@/components/ui/dialog";
import { TierGate } from "@/components/ui/tier-gate";

const FILE_TYPE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  pdf: FileType,
  txt: FileText,
  md: FileText,
  docx: File,
  html: FileText,
};

const STATUS_STYLES = {
  pending: { variant: "warning" as const, icon: Clock, label: "Pending" },
  processing: { variant: "default" as const, icon: Loader2, label: "Processing" },
  completed: { variant: "success" as const, icon: CheckCircle, label: "Completed" },
  failed: { variant: "danger" as const, icon: AlertCircle, label: "Failed" },
};

export default function SourceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const sourceId = params.id as string;

  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const sourceQueryKey = ["knowledge", "sources", sourceId];

  const { data: source, isLoading } = useQuery({
    queryKey: sourceQueryKey,
    queryFn: () => api.knowledge.getSource(sourceId),
    staleTime: 60_000,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "processing" || status === "pending" ? 3000 : false;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.knowledge.deleteSource(sourceId),
    onSuccess: () => {
      toast.success("Source deleted successfully");
      queryClient.invalidateQueries({ queryKey: ["knowledge", "sources"] });
      router.push("/knowledge/sources");
    },
    onError: (error) => {
      toast.error(parseApiError(error).message);
      setShowDeleteDialog(false);
    },
  });

  const reprocessMutation = useMutation({
    mutationFn: () => api.knowledge.reprocess(sourceId),
    onSuccess: () => {
      toast.success("Source reprocessing started");
      queryClient.invalidateQueries({ queryKey: sourceQueryKey });
    },
    onError: (error) => {
      toast.error(parseApiError(error).message);
    },
  });

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-16" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Skeleton className="h-64" />
          </div>
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  if (!source) return null;

  const IconComponent = FILE_TYPE_ICONS[source.file_type.toLowerCase()] || File;
  const statusStyle = STATUS_STYLES[source.status];
  const StatusIcon = statusStyle.icon;

  return (
    <TierGate minimum="professional" feature="Knowledge Vault">
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/knowledge/sources")}
          className="mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Sources
        </Button>

        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-xl bg-primary-100 flex items-center justify-center flex-shrink-0">
              <IconComponent className="h-8 w-8 text-primary-600" />
            </div>
            <div>
              <h1 className="font-display text-3xl font-bold text-text-primary">
                {source.title}
              </h1>
              <p className="mt-1 text-text-muted">{source.filename}</p>
            </div>
          </div>

          <Badge variant={statusStyle.variant} className="flex-shrink-0">
            <StatusIcon
              className={`h-4 w-4 mr-1 ${
                source.status === "processing" ? "animate-spin" : ""
              }`}
            />
            {statusStyle.label}
          </Badge>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          {source.description && (
            <Card>
              <CardHeader>
                <CardTitle>Description</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-text-secondary leading-relaxed">
                  {source.description}
                </p>
              </CardContent>
            </Card>
          )}

          {/* Processing Details */}
          {source.status === "completed" && (
            <Card>
              <CardHeader>
                <CardTitle>Processing Details</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="flex items-center gap-2 text-text-muted mb-1">
                      <Hash className="h-4 w-4" />
                      <span className="text-sm">Total Chunks</span>
                    </div>
                    <p className="text-2xl font-bold text-text-primary">
                      {source.chunk_count.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <div className="flex items-center gap-2 text-text-muted mb-1">
                      <FileText className="h-4 w-4" />
                      <span className="text-sm">Total Characters</span>
                    </div>
                    <p className="text-2xl font-bold text-text-primary">
                      {source.char_count.toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200">
                  <p className="text-sm text-green-700">
                    This document has been successfully processed and indexed. It's now
                    searchable in your knowledge base.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Error Details */}
          {source.status === "failed" && source.error_message && (
            <Card className="border-red-500">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-red-600">
                  <AlertCircle className="h-5 w-5" />
                  Processing Failed
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-red-600 mb-4">{source.error_message}</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => reprocessMutation.mutate()}
                  isLoading={reprocessMutation.isPending}
                  leftIcon={<RefreshCw className="h-4 w-4" />}
                >
                  Retry Processing
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Tags */}
          {source.tags.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Tag className="h-5 w-5" />
                  Tags
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {source.tags.map((tag) => (
                    <Badge key={tag} variant="secondary">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column - Metadata & Actions */}
        <div className="space-y-6">
          {/* Metadata */}
          <Card>
            <CardHeader>
              <CardTitle>Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex items-center gap-2 text-text-muted mb-1">
                  <FileType className="h-4 w-4" />
                  <span className="text-xs font-medium">File Type</span>
                </div>
                <p className="text-sm text-text-primary uppercase">
                  {source.file_type}
                </p>
              </div>

              <div>
                <div className="flex items-center gap-2 text-text-muted mb-1">
                  <HardDrive className="h-4 w-4" />
                  <span className="text-xs font-medium">File Size</span>
                </div>
                <p className="text-sm text-text-primary">
                  {formatFileSize(source.file_size)}
                </p>
              </div>

              <div>
                <div className="flex items-center gap-2 text-text-muted mb-1">
                  <Calendar className="h-4 w-4" />
                  <span className="text-xs font-medium">Uploaded</span>
                </div>
                <p className="text-sm text-text-primary">
                  {formatDate(source.created_at)}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {source.status === "failed" && (
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => reprocessMutation.mutate()}
                  isLoading={reprocessMutation.isPending}
                  leftIcon={<RefreshCw className="h-4 w-4" />}
                >
                  Reprocess Source
                </Button>
              )}

              <Button
                variant="destructive"
                className="w-full"
                onClick={() => setShowDeleteDialog(true)}
                leftIcon={<Trash2 className="h-4 w-4" />}
              >
                Delete Source
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog
        isOpen={showDeleteDialog}
        onClose={() => setShowDeleteDialog(false)}
        title="Delete Source"
        description="Are you sure you want to delete this source? This action cannot be undone."
        size="sm"
      >
        <div className="space-y-4">
          <div className="p-4 bg-red-50 rounded-lg border border-red-200">
            <p className="text-sm text-red-700">
              <strong>{source.title}</strong> and all its associated data will be
              permanently deleted from your knowledge base.
            </p>
          </div>

          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
              disabled={deleteMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteMutation.mutate()}
              isLoading={deleteMutation.isPending}
            >
              Delete Permanently
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
    </TierGate>
  );
}
