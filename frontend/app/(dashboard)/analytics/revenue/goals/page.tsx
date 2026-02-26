"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, Plus, Pencil, Trash2, Check, X, Target } from "lucide-react";
import { toast } from "sonner";
import { api, parseApiError, ConversionGoal } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const GOAL_TYPES = [
  { value: "page_visit", label: "Page Visit" },
  { value: "form_submit", label: "Form Submit" },
  { value: "purchase", label: "Purchase" },
  { value: "custom", label: "Custom" },
];

const GOAL_TYPE_LABELS: Record<string, string> = {
  page_visit: "Page Visit",
  form_submit: "Form Submit",
  purchase: "Purchase",
  custom: "Custom",
};

const DEFAULT_CONFIGS: Record<string, string> = {
  page_visit: JSON.stringify({ url_pattern: "/thank-you" }, null, 2),
  form_submit: JSON.stringify({ form_id: "contact-form" }, null, 2),
  purchase: JSON.stringify({ min_value: 0 }, null, 2),
  custom: JSON.stringify({ event_name: "custom_event" }, null, 2),
};

interface FormData {
  name: string;
  goal_type: string;
  goal_config: string;
  is_active: boolean;
}

const EMPTY_FORM: FormData = {
  name: "",
  goal_type: "page_visit",
  goal_config: DEFAULT_CONFIGS["page_visit"],
  is_active: true,
};

function isValidJson(value: string): boolean {
  if (!value.trim()) return true;
  try {
    JSON.parse(value);
    return true;
  } catch {
    return false;
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function ConversionGoalsPage() {
  const [goals, setGoals] = useState<ConversionGoal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editingGoal, setEditingGoal] = useState<ConversionGoal | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<FormData>(EMPTY_FORM);
  const [isSaving, setIsSaving] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    loadGoals();
  }, []);

  async function loadGoals() {
    try {
      setIsLoading(true);
      const response = await api.analytics.revenueGoals();
      setGoals(response.items);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsLoading(false);
    }
  }

  function openAddForm() {
    setEditingGoal(null);
    setFormData(EMPTY_FORM);
    setConfigError(null);
    setShowForm(true);
  }

  function openEditForm(goal: ConversionGoal) {
    setEditingGoal(goal);
    setFormData({
      name: goal.name,
      goal_type: goal.goal_type,
      goal_config: goal.goal_config
        ? JSON.stringify(goal.goal_config, null, 2)
        : "",
      is_active: goal.is_active,
    });
    setConfigError(null);
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditingGoal(null);
    setFormData(EMPTY_FORM);
    setConfigError(null);
  }

  function handleGoalTypeChange(newType: string) {
    setFormData((prev) => ({
      ...prev,
      goal_type: newType,
      goal_config: editingGoal ? prev.goal_config : DEFAULT_CONFIGS[newType] ?? "{}",
    }));
    setConfigError(null);
  }

  function handleConfigChange(value: string) {
    setFormData((prev) => ({ ...prev, goal_config: value }));
    if (!isValidJson(value)) {
      setConfigError("Invalid JSON — please fix before saving.");
    } else {
      setConfigError(null);
    }
  }

  async function handleSave() {
    if (!formData.name.trim()) {
      toast.error("Goal name is required.");
      return;
    }
    if (formData.goal_config.trim() && !isValidJson(formData.goal_config)) {
      toast.error("Goal config contains invalid JSON.");
      return;
    }

    let parsedConfig: Record<string, unknown> | undefined;
    if (formData.goal_config.trim()) {
      parsedConfig = JSON.parse(formData.goal_config) as Record<string, unknown>;
    }

    setIsSaving(true);
    try {
      if (editingGoal) {
        const updated = await api.analytics.updateRevenueGoal(editingGoal.id, {
          name: formData.name.trim(),
          goal_type: formData.goal_type,
          goal_config: parsedConfig,
          is_active: formData.is_active,
        });
        setGoals((prev) =>
          prev.map((g) => (g.id === updated.id ? updated : g))
        );
        toast.success("Goal updated successfully.");
      } else {
        const created = await api.analytics.createRevenueGoal({
          name: formData.name.trim(),
          goal_type: formData.goal_type,
          goal_config: parsedConfig,
        });
        setGoals((prev) => [...prev, created]);
        toast.success("Goal created successfully.");
      }
      closeForm();
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete(goal: ConversionGoal) {
    if (!confirm(`Delete goal "${goal.name}"? This action cannot be undone.`)) {
      return;
    }
    setDeletingId(goal.id);
    try {
      await api.analytics.deleteRevenueGoal(goal.id);
      setGoals((prev) => prev.filter((g) => g.id !== goal.id));
      toast.success("Goal deleted.");
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setDeletingId(null);
    }
  }

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-10 bg-surface-tertiary animate-pulse rounded-xl w-48" />
        <div className="h-16 bg-surface-tertiary animate-pulse rounded-2xl" />
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-28 bg-surface-tertiary animate-pulse rounded-2xl"
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/analytics/revenue"
          className="inline-flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700 mb-4"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Revenue
        </Link>
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-text-primary">
              Conversion Goals
            </h1>
            <p className="mt-1 text-text-secondary">
              {goals.length} goal{goals.length !== 1 ? "s" : ""} configured
            </p>
          </div>
          {!showForm && (
            <Button
              variant="primary"
              onClick={openAddForm}
              leftIcon={<Plus className="h-4 w-4" />}
            >
              Add Goal
            </Button>
          )}
        </div>
      </div>

      {/* Inline Add/Edit Form */}
      {showForm && (
        <Card className="border-primary-200">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg text-text-primary">
              {editingGoal ? "Edit Goal" : "New Conversion Goal"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Name */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-text-primary">
                Goal Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, name: e.target.value }))
                }
                placeholder="e.g. Newsletter Sign-up"
                className="w-full px-3 py-2 border border-surface-tertiary rounded-xl text-sm text-text-primary bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 placeholder:text-text-muted"
              />
            </div>

            {/* Goal Type */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-text-primary">
                Goal Type
              </label>
              <select
                value={formData.goal_type}
                onChange={(e) => handleGoalTypeChange(e.target.value)}
                className="w-full px-3 py-2 border border-surface-tertiary rounded-xl text-sm text-text-primary bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {GOAL_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Goal Config */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-text-primary">
                Goal Config{" "}
                <span className="text-text-muted font-normal">(JSON)</span>
              </label>
              <textarea
                value={formData.goal_config}
                onChange={(e) => handleConfigChange(e.target.value)}
                rows={6}
                placeholder="{}"
                spellCheck={false}
                className={`w-full px-3 py-2 border rounded-xl text-sm text-text-primary bg-white font-mono focus:outline-none focus:ring-2 focus:ring-primary-500 resize-y ${
                  configError
                    ? "border-red-400 focus:ring-red-400"
                    : "border-surface-tertiary"
                }`}
              />
              {configError && (
                <p className="text-xs text-red-500">{configError}</p>
              )}
            </div>

            {/* Active Toggle */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                role="switch"
                aria-checked={formData.is_active}
                onClick={() =>
                  setFormData((prev) => ({
                    ...prev,
                    is_active: !prev.is_active,
                  }))
                }
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 ${
                  formData.is_active ? "bg-primary-500" : "bg-surface-tertiary"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                    formData.is_active ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
              <span className="text-sm text-text-primary">
                {formData.is_active ? "Active" : "Inactive"}
              </span>
            </div>

            {/* Form Actions */}
            <div className="flex items-center gap-3 pt-2">
              <Button
                variant="primary"
                onClick={handleSave}
                isLoading={isSaving}
                disabled={!!configError}
                leftIcon={<Check className="h-4 w-4" />}
              >
                {editingGoal ? "Save Changes" : "Create Goal"}
              </Button>
              <Button
                variant="ghost"
                onClick={closeForm}
                disabled={isSaving}
                leftIcon={<X className="h-4 w-4" />}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Goals List */}
      {goals.length === 0 && !showForm ? (
        <Card>
          <CardContent className="py-16 flex flex-col items-center gap-4">
            <div className="h-14 w-14 rounded-2xl bg-surface-tertiary flex items-center justify-center">
              <Target className="h-7 w-7 text-text-muted" />
            </div>
            <div className="text-center">
              <p className="font-medium text-text-primary">No conversion goals yet</p>
              <p className="mt-1 text-sm text-text-secondary">
                Add your first goal to start tracking conversions.
              </p>
            </div>
            <Button
              variant="primary"
              onClick={openAddForm}
              leftIcon={<Plus className="h-4 w-4" />}
            >
              Add Goal
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {goals.map((goal) => (
            <Card key={goal.id}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between gap-4">
                  {/* Left: Icon + Info */}
                  <div className="flex items-start gap-4 min-w-0">
                    <div className="mt-0.5 h-10 w-10 rounded-xl bg-surface-tertiary flex items-center justify-center shrink-0">
                      <Target className="h-5 w-5 text-text-muted" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-text-primary">
                          {goal.name}
                        </span>
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                            goal.is_active
                              ? "bg-green-100 text-green-700"
                              : "bg-surface-tertiary text-text-muted"
                          }`}
                        >
                          {goal.is_active ? "Active" : "Inactive"}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center gap-3 flex-wrap">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-lg bg-surface-tertiary text-xs text-text-secondary font-medium">
                          {GOAL_TYPE_LABELS[goal.goal_type] ?? goal.goal_type}
                        </span>
                        <span className="text-xs text-text-muted">
                          Created {formatDate(goal.created_at)}
                        </span>
                      </div>
                      {goal.goal_config &&
                        Object.keys(goal.goal_config).length > 0 && (
                          <pre className="mt-2 px-3 py-2 rounded-lg bg-surface-tertiary text-xs text-text-secondary font-mono overflow-x-auto max-w-lg">
                            {JSON.stringify(goal.goal_config, null, 2)}
                          </pre>
                        )}
                    </div>
                  </div>

                  {/* Right: Actions */}
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEditForm(goal)}
                      disabled={deletingId === goal.id}
                      leftIcon={<Pencil className="h-3.5 w-3.5" />}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(goal)}
                      isLoading={deletingId === goal.id}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      leftIcon={<Trash2 className="h-3.5 w-3.5" />}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
