"use client";

import { FileText, FileType, File, AlertCircle, CheckCircle, Clock, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { KnowledgeSource } from "@/lib/api";
import { cn } from "@/lib/utils";

interface SourceCardProps {
  source: KnowledgeSource;
  onClick?: () => void;
}

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

export function SourceCard({ source, onClick }: SourceCardProps) {
  const IconComponent = FILE_TYPE_ICONS[source.file_type.toLowerCase()] || File;
  const statusStyle = STATUS_STYLES[source.status];
  const StatusIcon = statusStyle.icon;

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <Card
      className={cn(
        "transition-all duration-200",
        onClick && "cursor-pointer hover:shadow-lg hover:border-primary-500/50"
      )}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {/* File Icon */}
          <div className="flex-shrink-0 mt-1">
            <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
              <IconComponent className="h-5 w-5 text-primary-600" />
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Title & Status */}
            <div className="flex items-start justify-between gap-2 mb-1">
              <h3 className="font-semibold text-text-primary truncate">{source.title}</h3>
              <Badge variant={statusStyle.variant} className="flex-shrink-0">
                <StatusIcon
                  className={cn(
                    "h-3 w-3 mr-1",
                    source.status === "processing" && "animate-spin"
                  )}
                />
                {statusStyle.label}
              </Badge>
            </div>

            {/* Filename */}
            <p className="text-xs text-text-muted truncate mb-2">{source.filename}</p>

            {/* Tags */}
            {source.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-2">
                {source.tags.slice(0, 3).map((tag, index) => (
                  <span
                    key={index}
                    className="text-xs px-2 py-0.5 bg-surface-secondary rounded-full text-text-secondary"
                  >
                    {tag}
                  </span>
                ))}
                {source.tags.length > 3 && (
                  <span className="text-xs px-2 py-0.5 text-text-muted">
                    +{source.tags.length - 3}
                  </span>
                )}
              </div>
            )}

            {/* Meta Info */}
            <div className="flex items-center gap-4 text-xs text-text-muted">
              <span>{formatFileSize(source.file_size)}</span>
              {source.status === "completed" && (
                <>
                  <span>{source.chunk_count} chunks</span>
                  <span>{source.char_count.toLocaleString()} chars</span>
                </>
              )}
              <span>{formatDate(source.created_at)}</span>
            </div>

            {/* Error Message */}
            {source.status === "failed" && source.error_message && (
              <p className="mt-2 text-xs text-red-500 line-clamp-2">{source.error_message}</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
