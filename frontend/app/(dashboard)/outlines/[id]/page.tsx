"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Loader2,
  RefreshCw,
  Sparkles,
  Save,
  Plus,
  Trash2,
  GripVertical,
  ChevronDown,
  ChevronUp,
  Download,
} from "lucide-react";
import { api, Outline, OutlineSection } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

export default function OutlineDetailPage() {
  const params = useParams();
  const router = useRouter();
  const outlineId = params.id as string;

  const [outline, setOutline] = useState<Outline | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [editedSections, setEditedSections] = useState<OutlineSection[]>([]);
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set([0]));
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showRegenerateConfirm, setShowRegenerateConfirm] = useState(false);

  useEffect(() => {
    loadOutline();
  }, [outlineId]);

  async function loadOutline() {
    try {
      setLoading(true);
      const data = await api.outlines.get(outlineId);
      setOutline(data);
      setEditedSections(data.sections || []);
    } catch (error) {
      toast.error("Failed to load outline. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!outline) return;

    setSaving(true);
    try {
      const updated = await api.outlines.update(outline.id, {
        sections: editedSections,
      });
      setOutline(updated);
    } catch (error) {
      toast.error("Failed to save changes.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRegenerate() {
    if (!outline) return;

    setRegenerating(true);
    try {
      const updated = await api.outlines.regenerate(outline.id);
      setOutline(updated);
      setEditedSections(updated.sections || []);
    } catch (error) {
      toast.error("Failed to regenerate outline. Please try again.");
    } finally {
      setRegenerating(false);
    }
  }

  function toggleSection(index: number) {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedSections(newExpanded);
  }

  function updateSection(index: number, updates: Partial<OutlineSection>) {
    setEditedSections(
      editedSections.map((section, i) =>
        i === index ? { ...section, ...updates } : section
      )
    );
  }

  function addSection() {
    setEditedSections([
      ...editedSections,
      {
        heading: "New Section",
        subheadings: [],
        notes: "",
        word_count_target: 200,
      },
    ]);
    setExpandedSections(new Set([...Array.from(expandedSections), editedSections.length]));
  }

  function removeSection(index: number) {
    setEditedSections(editedSections.filter((_, i) => i !== index));
  }

  function moveSection(index: number, direction: "up" | "down") {
    const newIndex = direction === "up" ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= editedSections.length) return;

    const newSections = [...editedSections];
    [newSections[index], newSections[newIndex]] = [newSections[newIndex], newSections[index]];
    setEditedSections(newSections);
  }

  async function handleExport(format: "markdown" | "html" | "csv") {
    if (!outline) return;
    setShowExportMenu(false);
    try {
      const response = await api.outlines.exportOne(outline.id, format);
      const ext = format === "markdown" ? "md" : format;
      const safeTitle = outline.title.replace(/[^\w\-]/g, "_").slice(0, 80);
      const filename = `${safeTitle}.${ext}`;
      const url = window.URL.createObjectURL(response.data as Blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success(`Outline exported as ${format.toUpperCase()}`);
    } catch {
      toast.error("Failed to export outline");
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!outline) {
    return (
      <div className="text-center py-12">
        <p className="text-text-secondary">Outline not found</p>
        <Link href="/outlines" className="text-primary-600 hover:underline mt-2 inline-block">
          Back to outlines
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <ConfirmDialog
        isOpen={showRegenerateConfirm}
        onClose={() => setShowRegenerateConfirm(false)}
        onConfirm={() => { setShowRegenerateConfirm(false); handleRegenerate(); }}
        title="Regenerate Outline"
        message="This will overwrite all current sections with a freshly generated outline. Any unsaved edits will be lost. Are you sure?"
        variant="warning"
        confirmLabel="Regenerate"
      />

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <Link
            href="/outlines"
            className="p-2 rounded-lg hover:bg-surface-secondary transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-text-secondary" />
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-text-primary">
              {outline.title}
            </h1>
            <div className="flex items-center gap-3 mt-2 text-sm text-text-secondary">
              <span className="px-2 py-0.5 bg-surface-secondary rounded-md">
                {outline.keyword}
              </span>
              <span>{outline.tone}</span>
              <span>{outline.word_count_target} words target</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Export dropdown */}
          <div className="relative">
            <Button
              variant="outline"
              onClick={() => setShowExportMenu((prev) => !prev)}
            >
              <Download className="h-4 w-4 mr-2" />
              Export
              <ChevronDown className="h-3 w-3 ml-1" />
            </Button>
            {showExportMenu && (
              <div className="absolute right-0 top-full mt-1 z-50 w-40 rounded-xl border border-surface-tertiary bg-surface shadow-lg py-1">
                <button
                  onClick={() => handleExport("markdown")}
                  className="w-full text-left px-4 py-2 text-sm text-text-primary hover:bg-surface-secondary transition-colors"
                >
                  Markdown (.md)
                </button>
                <button
                  onClick={() => handleExport("html")}
                  className="w-full text-left px-4 py-2 text-sm text-text-primary hover:bg-surface-secondary transition-colors"
                >
                  HTML (.html)
                </button>
                <button
                  onClick={() => handleExport("csv")}
                  className="w-full text-left px-4 py-2 text-sm text-text-primary hover:bg-surface-secondary transition-colors"
                >
                  CSV (.csv)
                </button>
              </div>
            )}
          </div>

          <Button
            variant="outline"
            onClick={() => setShowRegenerateConfirm(true)}
            disabled={regenerating}
          >
            {regenerating ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Regenerate
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            Save Changes
          </Button>
        </div>
      </div>

      {/* Sections Editor */}
      <div className="space-y-4">
        {editedSections.map((section, index) => (
          <Card key={section.heading || index} className="overflow-hidden">
            <div
              className="flex items-center gap-3 p-4 cursor-pointer hover:bg-surface-secondary/50"
              onClick={() => toggleSection(index)}
            >
              <GripVertical className="h-5 w-5 text-text-muted cursor-grab" />
              <div className="flex-1">
                <h3 className="font-medium text-text-primary">{section.heading}</h3>
                <p className="text-sm text-text-muted">
                  {section.subheadings?.length || 0} subheadings &middot; {section.word_count_target} words
                </p>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    moveSection(index, "up");
                  }}
                  disabled={index === 0}
                  className="p-1.5 rounded hover:bg-surface-secondary disabled:opacity-30"
                >
                  <ChevronUp className="h-4 w-4" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    moveSection(index, "down");
                  }}
                  disabled={index === editedSections.length - 1}
                  className="p-1.5 rounded hover:bg-surface-secondary disabled:opacity-30"
                >
                  <ChevronDown className="h-4 w-4" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeSection(index);
                  }}
                  className="p-1.5 rounded hover:bg-red-50 text-red-500"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>

            {expandedSections.has(index) && (
              <div className="p-4 border-t border-surface-tertiary space-y-4 bg-surface-secondary/30">
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1.5">
                    Section Heading (H2)
                  </label>
                  <input
                    type="text"
                    value={section.heading}
                    onChange={(e) => updateSection(index, { heading: e.target.value })}
                    className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1.5">
                    Subheadings (H3) - one per line
                  </label>
                  <textarea
                    value={section.subheadings?.join("\n") || ""}
                    onChange={(e) =>
                      updateSection(index, {
                        subheadings: e.target.value.split("\n").filter((s) => s.trim()),
                      })
                    }
                    rows={3}
                    className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all resize-none"
                    placeholder="Enter subheadings, one per line"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1.5">
                    Content Notes
                  </label>
                  <textarea
                    value={section.notes || ""}
                    onChange={(e) => updateSection(index, { notes: e.target.value })}
                    rows={2}
                    className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all resize-none"
                    placeholder="Notes about what to cover in this section"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1.5">
                    Target Word Count
                  </label>
                  <input
                    type="number"
                    value={section.word_count_target}
                    onChange={(e) =>
                      updateSection(index, { word_count_target: Number(e.target.value) })
                    }
                    min={50}
                    max={2000}
                    className="w-32 px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
                  />
                </div>
              </div>
            )}
          </Card>
        ))}

        <button
          onClick={addSection}
          className="w-full p-4 border-2 border-dashed border-surface-tertiary rounded-xl text-text-secondary hover:border-primary-400 hover:text-primary-600 transition-colors flex items-center justify-center gap-2"
        >
          <Plus className="h-5 w-5" />
          Add Section
        </button>
      </div>

      {/* Generate Article CTA */}
      {outline.status === "completed" && (
        <Card className="p-6 bg-gradient-to-r from-primary-50 to-healing-lavender/30 border-primary-200">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-text-primary mb-1">
                Ready to generate your article?
              </h3>
              <p className="text-sm text-text-secondary">
                Your outline has {editedSections.length} sections totaling ~
                {editedSections.reduce((sum, s) => sum + s.word_count_target, 0)} words
              </p>
            </div>
            <Link href={`/articles/new?outline=${outline.id}`}>
              <Button>
                <Sparkles className="h-4 w-4 mr-2" />
                Generate Article
              </Button>
            </Link>
          </div>
        </Card>
      )}
    </div>
  );
}
