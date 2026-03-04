"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Edit2, Trash2, Check, X } from "lucide-react";
import { api, parseApiError } from "@/lib/api";
import type { BlogCategory } from "@/lib/api";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_]+/g, "-")
    .replace(/-+/g, "-")
    .trim();
}

export default function AdminBlogCategoriesPage() {
  const [categories, setCategories] = useState<BlogCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [confirmDelete, setConfirmDelete] = useState<BlogCategory | null>(null);

  const loadCategories = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.admin.blog.categories.list();
      setCategories(data);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      setSaving(true);
      await api.admin.blog.categories.create({
        name: newName.trim(),
        description: newDesc.trim() || undefined,
      });
      toast.success("Category created");
      setNewName("");
      setNewDesc("");
      loadCategories();
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (cat: BlogCategory) => {
    setEditingId(cat.id);
    setEditName(cat.name);
    setEditDesc(cat.description || "");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName("");
    setEditDesc("");
  };

  const handleUpdate = async (id: string) => {
    if (!editName.trim()) return;
    try {
      setSaving(true);
      await api.admin.blog.categories.update(id, {
        name: editName.trim(),
        description: editDesc.trim() || undefined,
      });
      toast.success("Category updated");
      setEditingId(null);
      loadCategories();
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (cat: BlogCategory) => {
    if (cat.post_count > 0) {
      toast.error(`Cannot delete "${cat.name}" — it has ${cat.post_count} post(s). Reassign posts first.`);
      return;
    }
    setConfirmDelete(cat);
  };

  const confirmDeleteAction = async () => {
    if (!confirmDelete) return;
    try {
      await api.admin.blog.categories.delete(confirmDelete.id);
      toast.success("Category deleted");
      setConfirmDelete(null);
      loadCategories();
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary">Blog Categories</h1>
        <p className="text-sm text-text-secondary mt-1">Manage categories for blog posts</p>
      </div>

      {/* Create new */}
      <div className="bg-surface border border-surface-tertiary rounded-xl p-4 mb-6">
        <h2 className="text-sm font-semibold text-text-primary mb-3">New Category</h2>
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleCreate()}
            placeholder="Category name"
            className="flex-1 px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <input
            type="text"
            value={newDesc}
            onChange={e => setNewDesc(e.target.value)}
            placeholder="Description (optional)"
            className="flex-1 px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <button
            onClick={handleCreate}
            disabled={saving || !newName.trim()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
          >
            <Plus className="h-4 w-4" />
            Create
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-surface border border-surface-tertiary rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-text-secondary">Loading...</div>
        ) : categories.length === 0 ? (
          <div className="p-8 text-center text-text-secondary">No categories yet. Create one above.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-surface-secondary border-b border-surface-tertiary">
              <tr>
                <th className="p-3 text-left font-medium text-text-secondary">Name</th>
                <th className="p-3 text-left font-medium text-text-secondary hidden md:table-cell">Slug</th>
                <th className="p-3 text-left font-medium text-text-secondary hidden md:table-cell">Description</th>
                <th className="p-3 text-left font-medium text-text-secondary">Posts</th>
                <th className="p-3 text-left font-medium text-text-secondary">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-tertiary">
              {categories.map(cat => (
                <tr key={cat.id} className="hover:bg-surface-secondary/50">
                  <td className="p-3">
                    {editingId === cat.id ? (
                      <input
                        type="text"
                        value={editName}
                        onChange={e => setEditName(e.target.value)}
                        className="w-full px-2 py-1 border border-surface-tertiary rounded text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
                        autoFocus
                      />
                    ) : (
                      <span className="font-medium text-text-primary">{cat.name}</span>
                    )}
                  </td>
                  <td className="p-3 hidden md:table-cell text-text-muted font-mono text-xs">
                    {cat.slug}
                  </td>
                  <td className="p-3 hidden md:table-cell">
                    {editingId === cat.id ? (
                      <input
                        type="text"
                        value={editDesc}
                        onChange={e => setEditDesc(e.target.value)}
                        className="w-full px-2 py-1 border border-surface-tertiary rounded text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
                      />
                    ) : (
                      <span className="text-text-secondary">{cat.description || "—"}</span>
                    )}
                  </td>
                  <td className="p-3">
                    <span className="text-text-secondary">{cat.post_count}</span>
                  </td>
                  <td className="p-3">
                    <div className="flex items-center gap-1">
                      {editingId === cat.id ? (
                        <>
                          <button
                            onClick={() => handleUpdate(cat.id)}
                            disabled={saving}
                            className="p-1.5 rounded-lg hover:bg-green-50 text-green-600"
                            aria-label="Save"
                          >
                            <Check className="h-4 w-4" />
                          </button>
                          <button
                            onClick={cancelEdit}
                            className="p-1.5 rounded-lg hover:bg-surface-secondary text-text-secondary"
                            aria-label="Cancel"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={() => startEdit(cat)}
                            className="p-1.5 rounded-lg hover:bg-surface-secondary text-text-secondary hover:text-primary-600"
                            aria-label={`Edit ${cat.name}`}
                          >
                            <Edit2 className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(cat)}
                            className="p-1.5 rounded-lg hover:bg-red-50 text-text-secondary hover:text-red-600"
                            aria-label={`Delete ${cat.name}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <ConfirmDialog
        isOpen={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        onConfirm={confirmDeleteAction}
        title="Delete Category"
        message={`Delete category "${confirmDelete?.name}"? This cannot be undone.`}
        variant="danger"
        confirmLabel="Delete"
      />
    </div>
  );
}
