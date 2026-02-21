"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Plus,
  FileText,
  Clock,
  Loader2,
  RefreshCw,
  Trash2,
  MoreVertical,
  CheckCircle2,
  XCircle,
  Sparkles,
} from "lucide-react";
import { api, Outline } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { AIGenerationProgress } from "@/components/ui/ai-generation-progress";
import { clsx } from "clsx";

const statusConfig = {
  draft: { label: "Draft", color: "bg-gray-100 text-gray-700", icon: FileText },
  generating: { label: "Generating", color: "bg-yellow-100 text-yellow-700", icon: Loader2 },
  completed: { label: "Completed", color: "bg-green-100 text-green-700", icon: CheckCircle2 },
  failed: { label: "Failed", color: "bg-red-100 text-red-700", icon: XCircle },
};

export default function OutlinesPage() {
  const [outlines, setOutlines] = useState<Outline[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [activeMenu, setActiveMenu] = useState<string | null>(null);

  useEffect(() => {
    loadOutlines();
  }, []);

  async function loadOutlines() {
    try {
      setLoading(true);
      const response = await api.outlines.list({ page_size: 50 });
      setOutlines(response.items);
    } catch (error) {
      console.error("Failed to load outlines:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Are you sure you want to delete this outline?")) return;

    try {
      await api.outlines.delete(id);
      setOutlines(outlines.filter((o) => o.id !== id));
    } catch (error) {
      console.error("Failed to delete outline:", error);
    }
    setActiveMenu(null);
  }

  async function handleRegenerate(id: string) {
    try {
      const updated = await api.outlines.regenerate(id);
      setOutlines(outlines.map((o) => (o.id === id ? updated : o)));
    } catch (error) {
      console.error("Failed to regenerate outline:", error);
    }
    setActiveMenu(null);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-text-primary">
            Outlines
          </h1>
          <p className="text-text-secondary mt-1">
            Create and manage your article outlines
          </p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Outline
        </Button>
      </div>

      {/* Outlines Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
        </div>
      ) : outlines.length === 0 ? (
        <Card className="p-12 text-center">
          <FileText className="h-12 w-12 text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-medium text-text-primary mb-2">
            No outlines yet
          </h3>
          <p className="text-text-secondary mb-6">
            Create your first outline to start generating content
          </p>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Outline
          </Button>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {outlines.map((outline) => {
            const status = statusConfig[outline.status];
            const StatusIcon = status.icon;

            return (
              <Card key={outline.id} className="p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <span className={clsx("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium", status.color)}>
                    <StatusIcon className={clsx("h-3.5 w-3.5", outline.status === "generating" && "animate-spin")} />
                    {status.label}
                  </span>

                  <div className="relative">
                    <button
                      onClick={() => setActiveMenu(activeMenu === outline.id ? null : outline.id)}
                      className="p-1.5 rounded-lg hover:bg-surface-secondary"
                    >
                      <MoreVertical className="h-4 w-4 text-text-muted" />
                    </button>

                    {activeMenu === outline.id && (
                      <>
                        <div className="fixed inset-0 z-40" onClick={() => setActiveMenu(null)} />
                        <div className="absolute right-0 mt-1 w-40 bg-white rounded-lg border border-surface-tertiary shadow-lg z-50">
                          <button
                            onClick={() => handleRegenerate(outline.id)}
                            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary"
                          >
                            <RefreshCw className="h-4 w-4" />
                            Regenerate
                          </button>
                          <button
                            onClick={() => handleDelete(outline.id)}
                            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                          >
                            <Trash2 className="h-4 w-4" />
                            Delete
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                <Link href={`/outlines/${outline.id}`} className="block group">
                  <h3 className="font-medium text-text-primary group-hover:text-primary-600 line-clamp-2 mb-2">
                    {outline.title}
                  </h3>

                  <div className="flex items-center gap-2 text-sm text-text-muted mb-3">
                    <span className="px-2 py-0.5 bg-surface-secondary rounded-md">
                      {outline.keyword}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5" />
                      {outline.estimated_read_time || Math.ceil(outline.word_count_target / 200)} min
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-xs text-text-muted">
                    <span>{outline.sections?.length || 0} sections</span>
                    <span>{new Date(outline.created_at).toLocaleDateString()}</span>
                  </div>
                </Link>

                {outline.status === "completed" && (
                  <Link
                    href={`/articles/new?outline=${outline.id}`}
                    className="mt-4 flex items-center justify-center gap-2 w-full py-2 rounded-lg bg-primary-50 text-primary-600 text-sm font-medium hover:bg-primary-100 transition-colors"
                  >
                    <Sparkles className="h-4 w-4" />
                    Generate Article
                  </Link>
                )}
              </Card>
            );
          })}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreateOutlineModal
          onClose={() => setShowCreateModal(false)}
          onCreate={(outline) => {
            setOutlines([outline, ...outlines]);
            setShowCreateModal(false);
          }}
        />
      )}
    </div>
  );
}

function CreateOutlineModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (outline: Outline) => void;
}) {
  const [keyword, setKeyword] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [tone, setTone] = useState("professional");
  const [wordCount, setWordCount] = useState(1500);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!keyword.trim()) {
      setError("Keyword is required");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const outline = await api.outlines.create({
        keyword: keyword.trim(),
        target_audience: targetAudience.trim() || undefined,
        tone,
        word_count_target: wordCount,
        auto_generate: true,
      });
      onCreate(outline);
    } catch (err) {
      setError("Failed to create outline. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop: only dismissible when not generating */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={loading ? undefined : onClose}
      />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 p-6">
        <h2 className="text-xl font-display font-bold text-text-primary mb-4">
          Create New Outline
        </h2>

        {loading ? (
          /* Progress view shown while the API call is in flight */
          <div>
            <AIGenerationProgress
              type="outline"
              keyword={keyword}
              isGenerating={loading}
            />
            <div className="mt-4 flex justify-center">
              <button
                type="button"
                onClick={onClose}
                className="text-sm text-text-muted hover:text-text-secondary underline underline-offset-2 transition-colors"
              >
                Cancel and close
              </button>
            </div>
          </div>
        ) : (
          /* Normal form view */
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">
                Target Keyword *
              </label>
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="e.g., anxiety relief techniques"
                className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">
                Target Audience
              </label>
              <input
                type="text"
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
                placeholder="e.g., adults dealing with work stress"
                className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">
                  Tone
                </label>
                <select
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
                >
                  <option value="professional">Professional</option>
                  <option value="friendly">Friendly</option>
                  <option value="empathetic">Empathetic</option>
                  <option value="informative">Informative</option>
                  <option value="conversational">Conversational</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">
                  Word Count
                </label>
                <select
                  value={wordCount}
                  onChange={(e) => setWordCount(Number(e.target.value))}
                  className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
                >
                  <option value={800}>Short (~800 words)</option>
                  <option value={1500}>Medium (~1500 words)</option>
                  <option value={2500}>Long (~2500 words)</option>
                  <option value={4000}>Very Long (~4000 words)</option>
                </select>
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-600">{error}</p>
            )}

            <div className="flex gap-3 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button type="submit" className="flex-1">
                <Sparkles className="h-4 w-4 mr-2" />
                Generate Outline
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
