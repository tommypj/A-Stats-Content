"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { SourceSnippet as SourceSnippetType } from "@/lib/api";
import { cn } from "@/lib/utils";

interface SourceSnippetProps {
  snippet: SourceSnippetType;
  index: number;
}

export function SourceSnippet({ snippet, index }: SourceSnippetProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const formatScore = (score: number) => {
    return `${(score * 100).toFixed(0)}% relevant`;
  };

  return (
    <Card className="border-l-4 border-l-primary-500">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {/* Source Number Badge */}
          <div className="flex-shrink-0">
            <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
              <span className="text-xs font-semibold text-primary-600">{index + 1}</span>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="flex items-center gap-2 min-w-0">
                <FileText className="h-4 w-4 text-text-muted flex-shrink-0" />
                <h4 className="font-medium text-text-primary truncate">
                  {snippet.source_title}
                </h4>
              </div>
              <span className="text-xs text-text-muted flex-shrink-0">
                {formatScore(snippet.relevance_score)}
              </span>
            </div>

            {/* Snippet Content */}
            <div className="relative">
              <p
                className={cn(
                  "text-sm text-text-secondary leading-relaxed",
                  !isExpanded && "line-clamp-3"
                )}
              >
                {snippet.content}
              </p>

              {/* Expand/Collapse Button */}
              {snippet.content.length > 200 && (
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="mt-2 flex items-center gap-1 text-xs text-primary-500 hover:text-primary-600 font-medium transition-colors"
                >
                  {isExpanded ? (
                    <>
                      Show less <ChevronUp className="h-3 w-3" />
                    </>
                  ) : (
                    <>
                      Show more <ChevronDown className="h-3 w-3" />
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
