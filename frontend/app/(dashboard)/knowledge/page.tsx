"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Database,
  FileText,
  MessageSquare,
  HardDrive,
  ArrowRight,
  Search,
  Upload,
} from "lucide-react";
import { toast } from "sonner";

import { api, parseApiError, KnowledgeStats, KnowledgeSource } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SourceCard } from "@/components/knowledge/source-card";
import { QueryInput } from "@/components/knowledge/query-input";
import { UploadModal } from "@/components/knowledge/upload-modal";

export default function KnowledgePage() {
  const router = useRouter();
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [recentSources, setRecentSources] = useState<KnowledgeSource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setIsLoading(true);
      const [statsData, sourcesResponse] = await Promise.all([
        api.knowledge.stats(),
        api.knowledge.sources({ page: 1, page_size: 5 }),
      ]);
      setStats(statsData);
      setRecentSources(sourcesResponse.items);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to load knowledge vault data");
    } finally {
      setIsLoading(false);
    }
  }

  const handleQuickQuery = (query: string) => {
    router.push(`/knowledge/query?q=${encodeURIComponent(query)}`);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("en-US").format(num);
  };

  const formatStorage = (mb: number) => {
    if (mb < 1) return `${(mb * 1024).toFixed(0)} KB`;
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(2)} GB`;
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-20" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-text-primary">
            Knowledge Vault
          </h1>
          <p className="mt-2 text-text-secondary">
            Your AI-powered knowledge base for intelligent content research
          </p>
        </div>
        <Button
          leftIcon={<Upload className="h-4 w-4" />}
          onClick={() => setIsUploadModalOpen(true)}
        >
          Upload Document
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Sources</CardTitle>
            <Database className="h-4 w-4 text-text-muted" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-text-primary">
              {stats ? formatNumber(stats.total_sources) : "0"}
            </div>
            <p className="text-xs text-text-muted mt-1">Documents in vault</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Knowledge Chunks</CardTitle>
            <FileText className="h-4 w-4 text-text-muted" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-text-primary">
              {stats ? formatNumber(stats.total_chunks) : "0"}
            </div>
            <p className="text-xs text-text-muted mt-1">Searchable segments</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Queries</CardTitle>
            <MessageSquare className="h-4 w-4 text-text-muted" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-text-primary">
              {stats ? formatNumber(stats.total_queries) : "0"}
            </div>
            <p className="text-xs text-text-muted mt-1">Questions answered</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Storage Used</CardTitle>
            <HardDrive className="h-4 w-4 text-text-muted" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-text-primary">
              {stats ? formatStorage(stats.storage_used_mb) : "0 MB"}
            </div>
            <p className="text-xs text-text-muted mt-1">Vector database size</p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Query */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Quick Query
          </CardTitle>
        </CardHeader>
        <CardContent>
          <QueryInput onSubmit={handleQuickQuery} showExamples />
        </CardContent>
      </Card>

      {/* Recent Sources & Quick Links */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Sources */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Recent Sources</CardTitle>
              <Link href="/knowledge/sources">
                <Button variant="ghost" size="sm">
                  View All
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent className="space-y-3">
              {recentSources.length === 0 ? (
                <div className="text-center py-8">
                  <FileText className="h-12 w-12 text-text-muted mx-auto mb-3" />
                  <p className="text-text-secondary">No sources uploaded yet</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-4"
                    onClick={() => setIsUploadModalOpen(true)}
                  >
                    Upload Your First Document
                  </Button>
                </div>
              ) : (
                recentSources.map((source) => (
                  <SourceCard
                    key={source.id}
                    source={source}
                    onClick={() => router.push(`/knowledge/sources/${source.id}`)}
                  />
                ))
              )}
            </CardContent>
          </Card>
        </div>

        {/* Quick Links */}
        <div className="space-y-4">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <Link href="/knowledge/query">
              <CardHeader>
                <CardTitle className="flex items-center justify-between text-base">
                  AI Query Interface
                  <ArrowRight className="h-5 w-5 text-text-muted" />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-text-secondary">
                  Ask questions and get AI-powered answers from your knowledge base
                </p>
              </CardContent>
            </Link>
          </Card>

          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <Link href="/knowledge/sources">
              <CardHeader>
                <CardTitle className="flex items-center justify-between text-base">
                  Manage Sources
                  <ArrowRight className="h-5 w-5 text-text-muted" />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-text-secondary">
                  View, search, and manage all your uploaded documents
                </p>
              </CardContent>
            </Link>
          </Card>

          <Card className="bg-primary-50 border-primary-200">
            <CardHeader>
              <CardTitle className="text-base text-primary-700">
                Knowledge Vault Tips
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-sm text-primary-600 space-y-2">
                <li>Upload PDFs, docs, and text files</li>
                <li>Tag sources for better organization</li>
                <li>Query across all sources at once</li>
                <li>Get AI-powered insights instantly</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSuccess={loadData}
      />
    </div>
  );
}
