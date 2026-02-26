"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Plus,
  Trash2,
  Edit3,
  Layers,
  Save,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { api, parseApiError, ContentTemplate, TemplateConfig } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const DEFAULT_CONFIG: TemplateConfig = {
  tone: "professional",
  writing_style: "editorial",
  word_count_target: 1500,
  target_audience: "",
  custom_instructions: "",
  include_faq: true,
  include_conclusion: true,
  language: "en",
};

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<ContentTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [config, setConfig] = useState<TemplateConfig>(DEFAULT_CONFIG);
  const [isSaving, setIsSaving] = useState(false);

  const loadTemplates = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await api.bulk.templates();
      setTemplates(data.items);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const resetForm = () => {
    setShowForm(false);
    setEditingId(null);
    setName("");
    setDescription("");
    setConfig(DEFAULT_CONFIG);
  };

  const handleEdit = (t: ContentTemplate) => {
    setEditingId(t.id);
    setName(t.name);
    setDescription(t.description || "");
    setConfig({ ...DEFAULT_CONFIG, ...t.template_config });
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!name.trim()) {
      toast.error("Template name is required");
      return;
    }
    try {
      setIsSaving(true);
      if (editingId) {
        await api.bulk.updateTemplate(editingId, { name, description, template_config: config });
        toast.success("Template updated");
      } else {
        await api.bulk.createTemplate({ name, description, template_config: config });
        toast.success("Template created");
      }
      resetForm();
      loadTemplates();
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.bulk.deleteTemplate(id);
      toast.success("Template deleted");
      setTemplates((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/bulk">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-text-primary">Content Templates</h1>
          <p className="text-sm text-text-secondary">
            Reusable settings for bulk content generation
          </p>
        </div>
        {!showForm && (
          <Button onClick={() => setShowForm(true)} variant="primary" size="sm">
            <Plus className="h-4 w-4 mr-1" />
            New Template
          </Button>
        )}
      </div>

      {/* Create/Edit Form */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>{editingId ? "Edit Template" : "New Template"}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="E.g. Blog Post Standard"
                className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface text-text-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Description</label>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
                className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface text-text-primary"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1">Tone</label>
                <select value={config.tone} onChange={(e) => setConfig({ ...config, tone: e.target.value })} className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface text-text-primary">
                  <option value="professional">Professional</option>
                  <option value="friendly">Friendly</option>
                  <option value="conversational">Conversational</option>
                  <option value="informative">Informative</option>
                  <option value="empathetic">Empathetic</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1">Writing Style</label>
                <select value={config.writing_style} onChange={(e) => setConfig({ ...config, writing_style: e.target.value })} className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface text-text-primary">
                  <option value="editorial">Editorial</option>
                  <option value="narrative">Narrative</option>
                  <option value="listicle">Listicle</option>
                  <option value="balanced">Balanced</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1">Word Count Target</label>
                <input type="number" value={config.word_count_target} onChange={(e) => setConfig({ ...config, word_count_target: parseInt(e.target.value) || 1500 })} className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface text-text-primary" />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1">Language</label>
                <select value={config.language} onChange={(e) => setConfig({ ...config, language: e.target.value })} className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface text-text-primary">
                  <option value="en">English</option>
                  <option value="ro">Romanian</option>
                  <option value="es">Spanish</option>
                  <option value="de">German</option>
                  <option value="fr">French</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Target Audience</label>
              <input value={config.target_audience} onChange={(e) => setConfig({ ...config, target_audience: e.target.value })} placeholder="E.g. Small business owners" className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface text-text-primary" />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Custom Instructions</label>
              <textarea value={config.custom_instructions} onChange={(e) => setConfig({ ...config, custom_instructions: e.target.value })} placeholder="Any special instructions for AI generation..." rows={3} className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface text-text-primary resize-y" />
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={config.include_faq} onChange={(e) => setConfig({ ...config, include_faq: e.target.checked })} className="rounded" />
                Include FAQ section
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={config.include_conclusion} onChange={(e) => setConfig({ ...config, include_conclusion: e.target.checked })} className="rounded" />
                Include Conclusion
              </label>
            </div>
            <div className="flex gap-2">
              <Button onClick={handleSave} variant="primary" disabled={isSaving}>
                <Save className="h-4 w-4 mr-1" />
                {isSaving ? "Saving..." : "Save Template"}
              </Button>
              <Button onClick={resetForm} variant="ghost">
                <X className="h-4 w-4 mr-1" />
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Templates List */}
      {isLoading ? (
        <div className="flex items-center justify-center min-h-[200px]">
          <div className="h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : templates.length === 0 && !showForm ? (
        <Card>
          <CardContent className="p-8 text-center">
            <Layers className="h-12 w-12 text-text-muted mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-text-primary">No Templates</h3>
            <p className="text-text-secondary mt-1">Create a template to reuse generation settings across bulk jobs.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {templates.map((t) => (
            <Card key={t.id}>
              <CardContent className="p-4 flex items-center gap-3">
                <Layers className="h-5 w-5 text-primary-500 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary">{t.name}</p>
                  {t.description && <p className="text-xs text-text-muted truncate">{t.description}</p>}
                  <p className="text-xs text-text-muted mt-0.5">
                    {t.template_config.tone} · {t.template_config.writing_style} · {t.template_config.word_count_target} words
                  </p>
                </div>
                <Button onClick={() => handleEdit(t)} variant="ghost" size="sm">
                  <Edit3 className="h-3.5 w-3.5" />
                </Button>
                <Button onClick={() => handleDelete(t.id)} variant="ghost" size="sm" className="text-red-500 hover:text-red-600">
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
