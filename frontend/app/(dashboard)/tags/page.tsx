"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, Loader2, Pencil, Trash2, Tag as TagIcon } from "lucide-react";
import { toast } from "sonner";
import { api, parseApiError, Tag, CreateTagInput } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Card, CardContent } from "@/components/ui/card";
import { useRequireAuth } from "@/lib/auth";
import { useProject } from "@/contexts/ProjectContext";
import { TierGate } from "@/components/ui/tier-gate";

const PRESET_COLORS = [
  "#6366f1", "#8b5cf6", "#ec4899", "#ef4444",
  "#f97316", "#eab308", "#22c55e", "#14b8a6",
  "#06b6d4", "#3b82f6", "#6b7280", "#1e293b",
];

export default function TagsPage() {
  const { isLoading: authLoading } = useRequireAuth();
  const { currentProject } = useProject();

  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Tag | null>(null);
  const [form, setForm] = useState<CreateTagInput>({ name: "", color: "#6366f1" });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.tags.list({
        page_size: 100,
        project_id: currentProject?.id,
      });
      setTags(res.items);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [currentProject?.id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const openCreate = () => {
    setEditing(null);
    setForm({ name: "", color: "#6366f1", project_id: currentProject?.id });
    setShowModal(true);
  };

  const openEdit = (t: Tag) => {
    setEditing(t);
    setForm({ name: t.name, color: t.color });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.name.trim()) {
      toast.error("Tag name is required");
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        await api.tags.update(editing.id, { name: form.name, color: form.color });
        toast.success("Tag updated");
      } else {
        await api.tags.create(form);
        toast.success("Tag created");
      }
      setShowModal(false);
      loadData();
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeleting(id);
    try {
      await api.tags.delete(id);
      toast.success("Tag deleted");
      loadData();
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setDeleting(null);
    }
  };

  if (authLoading) return null;

  return (
    <TierGate minimum="professional" feature="Content Tags">
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-text-primary">Tags</h1>
          <p className="mt-2 text-text-secondary">
            Organize your articles and outlines with tags
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4 mr-2" /> New Tag
        </Button>
      </div>

      {/* Loading */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-text-muted" />
        </div>
      ) : tags.length === 0 ? (
        <Card>
          <CardContent className="text-center py-16">
            <TagIcon className="h-12 w-12 mx-auto text-text-muted mb-4" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              No tags yet
            </h3>
            <p className="text-text-secondary mb-6 max-w-md mx-auto">
              Tags help you organize and filter your articles and outlines.
              Create color-coded tags like "SEO", "Product", or "How-to".
            </p>
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4 mr-2" /> Create your first tag
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-wrap gap-3">
          {tags.map((t) => (
            <div
              key={t.id}
              className="flex items-center gap-2 px-4 py-2 bg-surface-secondary border border-border rounded-xl group"
            >
              <span
                className="h-3 w-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: t.color }}
              />
              <span className="font-medium text-text-primary">{t.name}</span>
              <div className="flex items-center gap-0.5 ml-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => openEdit(t)}
                  className="p-1 text-text-muted hover:text-text-primary rounded"
                  aria-label="Edit tag"
                >
                  <Pencil className="h-3 w-3" />
                </button>
                <button
                  onClick={() => handleDelete(t.id)}
                  disabled={deleting === t.id}
                  className="p-1 text-text-muted hover:text-red-500 rounded"
                  aria-label="Delete tag"
                >
                  {deleting === t.id ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Trash2 className="h-3 w-3" />
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      <Dialog
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={editing ? "Edit Tag" : "New Tag"}
        size="sm"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              Name *
            </label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. SEO, Product, How-to"
              className="w-full px-3 py-2 bg-surface-secondary border border-border rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-brand-primary"
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Color
            </label>
            <div className="flex flex-wrap gap-2">
              {PRESET_COLORS.map((c) => (
                <button
                  key={c}
                  onClick={() => setForm((f) => ({ ...f, color: c }))}
                  className={`h-8 w-8 rounded-full border-2 transition-transform ${
                    form.color === c
                      ? "border-text-primary scale-110"
                      : "border-transparent hover:scale-105"
                  }`}
                  style={{ backgroundColor: c }}
                  aria-label={`Color ${c}`}
                />
              ))}
            </div>
          </div>

          {/* Preview */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              Preview
            </label>
            <div className="flex items-center gap-2 px-3 py-2 bg-surface-secondary rounded-lg w-fit">
              <span
                className="h-3 w-3 rounded-full"
                style={{ backgroundColor: form.color }}
              />
              <span className="font-medium text-text-primary">
                {form.name || "Tag name"}
              </span>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-border">
          <Button variant="outline" onClick={() => setShowModal(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            {editing ? "Save Changes" : "Create Tag"}
          </Button>
        </div>
      </Dialog>
    </div>
    </TierGate>
  );
}
