"use client";

import { useState } from "react";
import {
  Plus,
  Loader2,
  Pencil,
  Trash2,
  Copy,
  FileText,
  X,
} from "lucide-react";
import { toast } from "sonner";
import {
  api,
  parseApiError,
  ArticleTemplate,
  CreateTemplateInput,
} from "@/lib/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useRequireAuth } from "@/lib/auth";
import { useProject } from "@/contexts/ProjectContext";
import { TierGate } from "@/components/ui/tier-gate";

const TONE_OPTIONS = [
  "professional",
  "casual",
  "academic",
  "conversational",
  "persuasive",
  "informative",
];

const EMPTY_FORM: CreateTemplateInput = {
  name: "",
  description: "",
  target_audience: "",
  tone: "professional",
  word_count_target: 1500,
  writing_style: "",
  voice: "",
  custom_instructions: "",
  sections: [],
};

export default function TemplatesPage() {
  const { isLoading: authLoading } = useRequireAuth();
  const { currentProject } = useProject();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<ArticleTemplate | null>(null);
  const [form, setForm] = useState<CreateTemplateInput>(EMPTY_FORM);

  // --- React Query hooks ---

  const { data: templatesData, isLoading: loading } = useQuery({
    queryKey: ["templates", "list", { page, page_size: pageSize, project_id: currentProject?.id }],
    queryFn: () =>
      api.templates.list({
        page,
        page_size: pageSize,
        project_id: currentProject?.id,
      }),
    staleTime: 30_000,
  });

  const templates = templatesData?.items ?? [];
  const totalPages = templatesData?.pages ?? 0;
  const total = templatesData?.total ?? 0;

  const createMutation = useMutation({
    mutationFn: (data: CreateTemplateInput) => api.templates.create(data),
    onSuccess: () => {
      toast.success("Template created");
      setShowModal(false);
      queryClient.invalidateQueries({ queryKey: ["templates"] });
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: CreateTemplateInput }) =>
      api.templates.update(id, data),
    onSuccess: () => {
      toast.success("Template updated");
      setShowModal(false);
      queryClient.invalidateQueries({ queryKey: ["templates"] });
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.templates.delete(id),
    onSuccess: () => {
      toast.success("Template deleted");
      queryClient.invalidateQueries({ queryKey: ["templates"] });
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const duplicateMutation = useMutation({
    mutationFn: (data: CreateTemplateInput) => api.templates.create(data),
    onSuccess: () => {
      toast.success("Template duplicated");
      queryClient.invalidateQueries({ queryKey: ["templates"] });
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const saving = createMutation.isPending || updateMutation.isPending;

  const openCreate = () => {
    setEditing(null);
    setForm({ ...EMPTY_FORM, project_id: currentProject?.id });
    setShowModal(true);
  };

  const openEdit = (t: ArticleTemplate) => {
    setEditing(t);
    setForm({
      name: t.name,
      description: t.description || "",
      project_id: t.project_id,
      target_audience: t.target_audience || "",
      tone: t.tone || "professional",
      word_count_target: t.word_count_target,
      writing_style: t.writing_style || "",
      voice: t.voice || "",
      custom_instructions: t.custom_instructions || "",
      sections: t.sections || [],
    });
    setShowModal(true);
  };

  const handleDuplicate = (t: ArticleTemplate) => {
    duplicateMutation.mutate({
      name: `${t.name} (copy)`,
      description: t.description,
      project_id: t.project_id,
      target_audience: t.target_audience,
      tone: t.tone,
      word_count_target: t.word_count_target,
      writing_style: t.writing_style,
      voice: t.voice,
      custom_instructions: t.custom_instructions,
      sections: t.sections,
    });
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id);
  };

  const handleSave = () => {
    if (!form.name.trim()) {
      toast.error("Template name is required");
      return;
    }
    if (editing) {
      updateMutation.mutate({ id: editing.id, data: form });
    } else {
      createMutation.mutate(form);
    }
  };

  // Section helpers
  const addSection = () => {
    setForm((f) => ({
      ...f,
      sections: [...(f.sections || []), { heading: "" }],
    }));
  };

  const updateSection = (idx: number, heading: string) => {
    setForm((f) => ({
      ...f,
      sections: (f.sections || []).map((s, i) =>
        i === idx ? { ...s, heading } : s
      ),
    }));
  };

  const removeSection = (idx: number) => {
    setForm((f) => ({
      ...f,
      sections: (f.sections || []).filter((_, i) => i !== idx),
    }));
  };

  if (authLoading) return null;

  return (
    <TierGate minimum="professional" feature="Article Templates">
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-text-primary">
            Templates
          </h1>
          <p className="mt-2 text-text-secondary">
            Save and reuse article configurations
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4 mr-2" /> New Template
        </Button>
      </div>

      {/* Loading */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-24 bg-surface-tertiary animate-pulse rounded-2xl"
            />
          ))}
        </div>
      ) : templates.length === 0 ? (
        /* Empty state */
        <Card>
          <CardContent className="text-center py-16">
            <FileText className="h-12 w-12 mx-auto text-text-muted mb-4" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              No templates yet
            </h3>
            <p className="text-text-secondary mb-6 max-w-md mx-auto">
              Templates let you save your preferred article settings — tone,
              audience, word count, sections — and reuse them when creating new
              outlines.
            </p>
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4 mr-2" /> Create your first template
            </Button>
          </CardContent>
        </Card>
      ) : (
        /* Template grid */
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((t) => (
            <Card key={t.id} className="group relative">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg leading-tight line-clamp-1" title={t.name}>
                  {t.name}
                </CardTitle>
                {t.description && (
                  <p className="text-sm text-text-secondary line-clamp-2">
                    {t.description}
                  </p>
                )}
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex flex-wrap gap-2 text-xs text-text-muted mb-4">
                  {t.tone && (
                    <span className="px-2 py-0.5 bg-surface-tertiary rounded-full capitalize">
                      {t.tone}
                    </span>
                  )}
                  <span className="px-2 py-0.5 bg-surface-tertiary rounded-full">
                    {t.word_count_target.toLocaleString()} words
                  </span>
                  {t.sections && t.sections.length > 0 && (
                    <span className="px-2 py-0.5 bg-surface-tertiary rounded-full">
                      {t.sections.length} sections
                    </span>
                  )}
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => openEdit(t)}
                    aria-label="Edit template"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDuplicate(t)}
                    aria-label="Duplicate template"
                  >
                    <Copy className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(t.id)}
                    disabled={deleteMutation.isPending && deleteMutation.variables === t.id}
                    aria-label="Delete template"
                    className="text-red-500 hover:text-red-600"
                  >
                    {deleteMutation.isPending && deleteMutation.variables === t.id ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="h-3.5 w-3.5" />
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-text-secondary">
            Showing {(page - 1) * pageSize + 1}-
            {Math.min(page * pageSize, total)} of {total}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Create/Edit Modal */}
      <Dialog
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={editing ? "Edit Template" : "New Template"}
        size="lg"
      >
        <div className="space-y-4">
          {/* Name */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-text-secondary mb-1">
              Name *
            </label>
            <input
              id="name"
              type="text"
              value={form.name}
              onChange={(e) =>
                setForm((f) => ({ ...f, name: e.target.value }))
              }
              placeholder="e.g. Long-form SEO guide"
              className="w-full px-3 py-2 bg-surface-secondary border border-border rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-brand-primary"
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-text-secondary mb-1">
              Description
            </label>
            <input
              id="description"
              type="text"
              value={form.description || ""}
              onChange={(e) =>
                setForm((f) => ({ ...f, description: e.target.value }))
              }
              placeholder="Brief description of when to use this template"
              className="w-full px-3 py-2 bg-surface-secondary border border-border rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-brand-primary"
            />
          </div>

          {/* Two-column row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="tone" className="block text-sm font-medium text-text-secondary mb-1">
                Tone
              </label>
              <select
                id="tone"
                value={form.tone || "professional"}
                onChange={(e) =>
                  setForm((f) => ({ ...f, tone: e.target.value }))
                }
                className="w-full px-3 py-2 bg-surface-secondary border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-brand-primary"
              >
                {TONE_OPTIONS.map((t) => (
                  <option key={t} value={t}>
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="word-count-target" className="block text-sm font-medium text-text-secondary mb-1">
                Word Count Target
              </label>
              <input
                id="word-count-target"
                type="number"
                min={100}
                max={20000}
                value={form.word_count_target || 1500}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    word_count_target: parseInt(e.target.value) || 1500,
                  }))
                }
                className="w-full px-3 py-2 bg-surface-secondary border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-brand-primary"
              />
            </div>
          </div>

          {/* Target Audience */}
          <div>
            <label htmlFor="target-audience" className="block text-sm font-medium text-text-secondary mb-1">
              Target Audience
            </label>
            <input
              id="target-audience"
              type="text"
              value={form.target_audience || ""}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  target_audience: e.target.value,
                }))
              }
              placeholder="e.g. Marketing managers at B2B SaaS companies"
              className="w-full px-3 py-2 bg-surface-secondary border border-border rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-brand-primary"
            />
          </div>

          {/* Writing style & Voice */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="writing-style" className="block text-sm font-medium text-text-secondary mb-1">
                Writing Style
              </label>
              <input
                id="writing-style"
                type="text"
                value={form.writing_style || ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    writing_style: e.target.value,
                  }))
                }
                placeholder="e.g. Data-driven, concise"
                className="w-full px-3 py-2 bg-surface-secondary border border-border rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-brand-primary"
              />
            </div>
            <div>
              <label htmlFor="voice" className="block text-sm font-medium text-text-secondary mb-1">
                Voice
              </label>
              <input
                id="voice"
                type="text"
                value={form.voice || ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, voice: e.target.value }))
                }
                placeholder="e.g. Authoritative, friendly"
                className="w-full px-3 py-2 bg-surface-secondary border border-border rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-brand-primary"
              />
            </div>
          </div>

          {/* Custom Instructions */}
          <div>
            <label htmlFor="custom-instructions" className="block text-sm font-medium text-text-secondary mb-1">
              Custom Instructions
            </label>
            <textarea
              id="custom-instructions"
              rows={3}
              value={form.custom_instructions || ""}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  custom_instructions: e.target.value,
                }))
              }
              placeholder="Any special instructions for article generation..."
              className="w-full px-3 py-2 bg-surface-secondary border border-border rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-brand-primary resize-none"
            />
          </div>

          {/* Sections */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-text-secondary">
                Sections
              </label>
              <Button variant="ghost" size="sm" onClick={addSection}>
                <Plus className="h-3.5 w-3.5 mr-1" /> Add Section
              </Button>
            </div>
            {(form.sections || []).length === 0 ? (
              <p className="text-sm text-text-muted">
                No sections defined. Sections will be auto-generated.
              </p>
            ) : (
              <div className="space-y-2">
                {(form.sections || []).map((s, i) => (
                  <div key={i} className="flex gap-2">
                    <input
                      type="text"
                      value={s.heading}
                      onChange={(e) => updateSection(i, e.target.value)}
                      placeholder={`Section ${i + 1} heading`}
                      className="flex-1 px-3 py-2 bg-surface-secondary border border-border rounded-lg text-text-primary placeholder:text-text-muted text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary"
                    />
                    <button
                      onClick={() => removeSection(i)}
                      className="text-text-muted hover:text-red-500"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-border">
          <Button variant="outline" onClick={() => setShowModal(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            {editing ? "Save Changes" : "Create Template"}
          </Button>
        </div>
      </Dialog>
    </div>
    </TierGate>
  );
}
