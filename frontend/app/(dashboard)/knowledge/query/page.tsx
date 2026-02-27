"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Sparkles, Clock, FileText, History, Loader2 } from "lucide-react";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";

import { api, parseApiError, QueryResponse } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { QueryInput } from "@/components/knowledge/query-input";
import { SourceSnippet } from "@/components/knowledge/source-snippet";

interface QueryHistoryItem {
  query: string;
  timestamp: string;
}

export default function QueryPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center p-12"><Loader2 className="h-8 w-8 animate-spin text-primary-500" /></div>}>
      <QueryPageContent />
    </Suspense>
  );
}

function QueryPageContent() {
  const searchParams = useSearchParams();
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [isQuerying, setIsQuerying] = useState(false);
  const [queryHistory, setQueryHistory] = useState<QueryHistoryItem[]>([]);

  useEffect(() => {
    // Load query from URL if present
    const urlQuery = searchParams.get("q");
    if (urlQuery) {
      setQuery(urlQuery);
      handleQuery(urlQuery);
    }

    // Load query history from localStorage
    try {
      const savedHistory = localStorage.getItem("knowledge_query_history");
      if (savedHistory) {
        setQueryHistory(JSON.parse(savedHistory));
      }
    } catch {
      // Ignore corrupt localStorage data
    }
  }, []);

  const saveToHistory = (query: string) => {
    const newHistory = [
      { query, timestamp: new Date().toISOString() },
      ...queryHistory.filter((item) => item.query !== query),
    ].slice(0, 50); // Keep only last 50 unique queries

    setQueryHistory(newHistory);
    try {
      localStorage.setItem("knowledge_query_history", JSON.stringify(newHistory));
    } catch {
      // Storage quota exceeded — trim to 10 entries and retry once
      const trimmed = newHistory.slice(0, 10);
      try {
        localStorage.setItem("knowledge_query_history", JSON.stringify(trimmed));
        setQueryHistory(trimmed);
      } catch {
        // Still failing — silently ignore, history just won't persist
      }
    }
  };

  async function handleQuery(queryText: string) {
    try {
      setIsQuerying(true);
      setQuery(queryText);
      const result = await api.knowledge.query(queryText);
      setResponse(result);
      saveToHistory(queryText);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to process query");
    } finally {
      setIsQuerying(false);
    }
  }

  const formatQueryTime = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-100 mb-4">
          <Sparkles className="h-8 w-8 text-primary-600" />
        </div>
        <h1 className="font-display text-3xl font-bold text-text-primary">
          AI Knowledge Query
        </h1>
        <p className="mt-2 text-text-secondary">
          Ask questions and get intelligent answers from your knowledge base
        </p>
      </div>

      {/* Query Input */}
      <Card>
        <CardContent className="p-6">
          <QueryInput
            onSubmit={handleQuery}
            isLoading={isQuerying}
            showExamples={!response}
          />
        </CardContent>
      </Card>

      {/* Query Response */}
      {isQuerying && (
        <Card>
          <CardContent className="p-6 space-y-4">
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
            <div className="pt-4 space-y-3">
              <Skeleton className="h-32" />
              <Skeleton className="h-32" />
            </div>
          </CardContent>
        </Card>
      )}

      {response && !isQuerying && (
        <div className="space-y-6">
          {/* AI Answer */}
          <Card className="border-l-4 border-l-primary-500">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary-500" />
                  AI Answer
                </CardTitle>
                <div className="flex items-center gap-2 text-sm text-text-muted">
                  <Clock className="h-4 w-4" />
                  {formatQueryTime(response.query_time_ms)}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown
                  skipHtml={true}
                  components={{
                    h1: ({ children }) => (
                      <h1 className="text-2xl font-bold text-text-primary mb-4">
                        {children}
                      </h1>
                    ),
                    h2: ({ children }) => (
                      <h2 className="text-xl font-semibold text-text-primary mb-3 mt-6">
                        {children}
                      </h2>
                    ),
                    h3: ({ children }) => (
                      <h3 className="text-lg font-semibold text-text-primary mb-2 mt-4">
                        {children}
                      </h3>
                    ),
                    p: ({ children }) => (
                      <p className="text-text-secondary mb-4 leading-relaxed">
                        {children}
                      </p>
                    ),
                    ul: ({ children }) => (
                      <ul className="list-disc list-inside mb-4 space-y-2 text-text-secondary">
                        {children}
                      </ul>
                    ),
                    ol: ({ children }) => (
                      <ol className="list-decimal list-inside mb-4 space-y-2 text-text-secondary">
                        {children}
                      </ol>
                    ),
                    code: ({ children }) => (
                      <code className="bg-surface-secondary px-1.5 py-0.5 rounded text-sm font-mono text-primary-600">
                        {children}
                      </code>
                    ),
                    pre: ({ children }) => (
                      <pre className="bg-surface-secondary p-4 rounded-xl overflow-x-auto mb-4">
                        {children}
                      </pre>
                    ),
                  }}
                >
                  {response.answer}
                </ReactMarkdown>
              </div>
            </CardContent>
          </Card>

          {/* Source Citations */}
          {response.sources.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Sources ({response.sources.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {response.sources.map((snippet, index) => (
                  <SourceSnippet key={snippet.source_id} snippet={snippet} index={index} />
                ))}
              </CardContent>
            </Card>
          )}

          {/* Ask Another Question */}
          <div className="text-center">
            <Button
              variant="outline"
              onClick={() => {
                setResponse(null);
                setQuery("");
              }}
            >
              Ask Another Question
            </Button>
          </div>
        </div>
      )}

      {/* Query History */}
      {!response && !isQuerying && queryHistory.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <History className="h-5 w-5" />
              Recent Queries
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {queryHistory.map((item) => (
                <button
                  key={item.timestamp}
                  onClick={() => handleQuery(item.query)}
                  className="w-full text-left p-3 rounded-lg hover:bg-surface-secondary transition-colors group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm text-text-primary group-hover:text-primary-500 flex-1">
                      {item.query}
                    </p>
                    <span className="text-xs text-text-muted flex-shrink-0">
                      {formatTimestamp(item.timestamp)}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
