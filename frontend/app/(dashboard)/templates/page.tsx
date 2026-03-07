"use client";

import { useState, useEffect, useCallback } from "react";
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
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useRequireAuth } from "@/lib/auth";
import { useProject } from "@/contexts/ProjectContext";

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

  const [templates, setTemplates] = useState<ArticleTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<ArticleTemplate | null>(null);
  const [form, setForm] = useState<CreateTemplateInput>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.templates.list({
        page,
        page_size: pageSize,
        project_id: currentProject?.id,
      });
      setTemplates(res.items);
      setTotalPages(res.pages);
      setTotal(res.total);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [page, currentProject?.id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

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

  const handleDuplicate = async (t: ArticleTemplate) => {
    try {
      await api.templates.create({
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
      toast.success("Template duplicated");
      loadData();
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  const handleDelete = async (id: string) => {
    setDeleting(id);
    try {
      await api.templates.delete(id);
      toast.success("Template deleted");
      loadData();
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setDeleting(null);
    }
  };

  const handleSave = async () => {
    if (!form.name.trim()) {
      toast.error("Template name is required");
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        await api.templates.update(editing.id, form);
        toast.success("Template updated");
      } else {
        await api.templates.create(form);
        toast.success("Template created");
      }
      setShowModal(false);
      loadData();
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setSaving(false);
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-text-primary">
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
                    disabled={deleting === t.id}
                    aria-label="Delete template"
                    className="text-red-500 hover:text-red-600"
                  >
                    {deleting === t.id ? (
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
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-surface-primary border border-border rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-text-primary">
                {editing ? "Edit Template" : "New Template"}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="text-text-muted hover:text-text-primary"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">
                  Name *
                </label>
                <input
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
                <label className="block text-sm font-medium text-text-secondary mb-1">
                  Description
                </label>
                <input
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
                  <label className="block text-sm font-medium text-text-secondary mb-1">
                    Tone
                  </label>
                  <select
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
                  <label className="block text-sm font-medium text-text-secondary mb-1">
                    Word Count Target
                  </label>
                  <input
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
                <label className="block text-sm font-medium text-text-secondary mb-1">
                  Target Audience
                </label>
                <input
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
                  <label className="block text-sm font-medium text-text-secondary mb-1">
                    Writing Style
                  </label>
                  <input
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
                  <label className="block text-sm font-medium text-text-secondary mb-1">
                    Voice
                  </label>
                  <input
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
                <label className="block text-sm font-medium text-text-secondary mb-1">
                  Custom Instructions
                </label>
                <textarea
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
          </div>
        </div>
      )}
    </div>
  );
}
