"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, parseApiError, EmailTemplateOverride } from "@/lib/api";
import { toast } from "sonner";
import { Mail, Send, Eye, Loader2, Pencil, ArrowLeft, Save, RotateCcw, Code, Monitor } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface EmailTemplate {
  email_key: string;
  phase: string;
  priority: number;
}

const PHASE_LABELS: Record<string, string> = {
  onboarding: "Onboarding",
  usage: "Conversion",
  conversion_tips: "Conversion",
  reengagement: "Retention",
  weekly_digest: "Ongoing",
  content_decay: "Ongoing",
  system: "System",
};

const PHASE_ORDER = ["Onboarding", "Conversion", "Retention", "Ongoing", "System"];

function groupByPhase(templates: EmailTemplate[]): Record<string, EmailTemplate[]> {
  const groups: Record<string, EmailTemplate[]> = {};
  for (const t of templates) {
    const label = PHASE_LABELS[t.phase] || t.phase;
    if (!groups[label]) groups[label] = [];
    groups[label].push(t);
  }
  // Sort within each group by priority
  for (const key of Object.keys(groups)) {
    groups[key].sort((a, b) => a.priority - b.priority);
  }
  return groups;
}

export default function AdminEmailsPage() {
  const queryClient = useQueryClient();

  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedKey, setSelectedKey] = useState<string>("");
  const [userName, setUserName] = useState("Test User");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [previewHtml, setPreviewHtml] = useState<string>("");
  const [previewSubject, setPreviewSubject] = useState<string>("");
  const [previewing, setPreviewing] = useState(false);
  const [sending, setSending] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const editIframeRef = useRef<HTMLIFrameElement>(null);

  // Edit mode state
  const [editMode, setEditMode] = useState(false);
  const [editSubject, setEditSubject] = useState("");
  const [editHtml, setEditHtml] = useState("");
  const [editTab, setEditTab] = useState<"editor" | "preview">("editor");

  // --- Overrides query ---
  const { data: overridesData } = useQuery({
    queryKey: ["admin", "email-overrides"],
    queryFn: () => api.admin.emails.getOverrides(),
    staleTime: 30_000,
  });

  const overridesMap = useMemo(() => {
    const map = new Map<string, EmailTemplateOverride>();
    if (overridesData?.overrides) {
      for (const o of overridesData.overrides) {
        map.set(o.email_key, o);
      }
    }
    return map;
  }, [overridesData]);

  // --- Save override mutation ---
  const saveOverrideMutation = useMutation({
    mutationFn: (params: { email_key: string; data: { subject?: string | null; html?: string | null } }) =>
      api.admin.emails.saveOverride(params.email_key, params.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "email-overrides"] });
      toast.success("Template override saved successfully.");
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  // --- Delete override mutation ---
  const deleteOverrideMutation = useMutation({
    mutationFn: (email_key: string) => api.admin.emails.deleteOverride(email_key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "email-overrides"] });
      toast.success("Template reset to default.");
      setEditMode(false);
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const loadTemplates = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.admin.emails.templates();
      setTemplates(data.templates);
      if (data.templates.length > 0 && !selectedKey) {
        setSelectedKey(data.templates[0].email_key);
      }
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [selectedKey]);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadPreview = useCallback(async () => {
    if (!selectedKey) return;
    try {
      setPreviewing(true);
      const data = await api.admin.emails.preview({
        email_key: selectedKey,
        user_name: userName || undefined,
      });
      setPreviewHtml(data.html);
      setPreviewSubject(data.subject);
    } catch (err) {
      toast.error(parseApiError(err).message);
      setPreviewHtml("");
      setPreviewSubject("");
    } finally {
      setPreviewing(false);
    }
  }, [selectedKey, userName]);

  useEffect(() => {
    if (selectedKey) {
      loadPreview();
      // Exit edit mode when switching templates
      setEditMode(false);
    }
  }, [selectedKey]);

  const handlePreview = () => {
    loadPreview();
  };

  const handleSendTest = async () => {
    if (!selectedKey) {
      toast.error("Please select a template first.");
      return;
    }
    if (!recipientEmail) {
      toast.error("Please enter a recipient email address.");
      return;
    }
    try {
      setSending(true);
      const result = await api.admin.emails.sendTest({
        email_key: selectedKey,
        recipient_email: recipientEmail,
        user_name: userName || undefined,
      });
      if (result.sent) {
        toast.success(result.message || "Test email sent successfully.");
      } else {
        toast.error(result.message || "Failed to send test email.");
      }
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setSending(false);
    }
  };

  const handleEnterEditMode = () => {
    const override = overridesMap.get(selectedKey);
    if (override) {
      setEditSubject(override.subject || previewSubject);
      setEditHtml(override.html || previewHtml);
    } else {
      setEditSubject(previewSubject);
      setEditHtml(previewHtml);
    }
    setEditTab("editor");
    setEditMode(true);
  };

  const handleSaveOverride = () => {
    if (!selectedKey) return;
    saveOverrideMutation.mutate({
      email_key: selectedKey,
      data: {
        subject: editSubject || null,
        html: editHtml || null,
      },
    });
  };

  const handleResetToDefault = () => {
    if (!selectedKey) return;
    if (!window.confirm("Reset this template to its default? This will remove your custom override.")) {
      return;
    }
    deleteOverrideMutation.mutate(selectedKey);
  };

  const grouped = groupByPhase(templates);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-text-muted" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary flex items-center gap-2">
          <Mail className="h-6 w-6" />
          Email Journey Templates
        </h1>
        <p className="mt-1 text-text-secondary">
          Preview, edit, and test email templates from all journey phases. Select a template to preview its rendered HTML and send test emails.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Template selector + controls */}
        <div className="space-y-4">
          {/* Template Selector */}
          <div className="bg-white rounded-xl border border-surface-tertiary shadow-sm p-4">
            <label
              htmlFor="template-select"
              className="block text-sm font-medium text-text-primary mb-2"
            >
              Select Template
            </label>
            <select
              id="template-select"
              value={selectedKey}
              onChange={(e) => setSelectedKey(e.target.value)}
              className="w-full border border-surface-tertiary rounded-lg px-3 py-2 text-sm text-text-primary bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              {PHASE_ORDER.map((phase) => {
                const group = grouped[phase];
                if (!group || group.length === 0) return null;
                return (
                  <optgroup key={phase} label={phase}>
                    {group.map((t) => (
                      <option key={t.email_key} value={t.email_key}>
                        {t.email_key.replace(/_/g, " ")}
                        {overridesMap.has(t.email_key) ? " \u2713" : ""}
                      </option>
                    ))}
                  </optgroup>
                );
              })}
              {/* Ungrouped templates */}
              {templates
                .filter((t) => !PHASE_ORDER.includes(PHASE_LABELS[t.phase] || t.phase))
                .map((t) => (
                  <option key={t.email_key} value={t.email_key}>
                    {t.email_key.replace(/_/g, " ")}
                    {overridesMap.has(t.email_key) ? " \u2713" : ""}
                  </option>
                ))}
            </select>
            <div className="mt-2 flex items-center justify-between">
              <p className="text-xs text-text-muted">
                {templates.length} template{templates.length !== 1 ? "s" : ""} available
              </p>
              {overridesMap.has(selectedKey) && (
                <span className="inline-flex items-center rounded-full bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-700">
                  Overridden
                </span>
              )}
            </div>
          </div>

          {/* User Name Input */}
          <div className="bg-white rounded-xl border border-surface-tertiary shadow-sm p-4">
            <label
              htmlFor="user-name"
              className="block text-sm font-medium text-text-primary mb-2"
            >
              User Name (for personalization)
            </label>
            <input
              id="user-name"
              type="text"
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
              placeholder="Test User"
              className="w-full border border-surface-tertiary rounded-lg px-3 py-2 text-sm text-text-primary bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
            <button
              onClick={handlePreview}
              disabled={previewing || !selectedKey}
              className="mt-3 w-full flex items-center justify-center gap-2 bg-primary-100 text-primary-700 rounded-lg px-4 py-2 text-sm font-medium hover:bg-primary-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {previewing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
              Refresh Preview
            </button>
          </div>

          {/* Send Test Form */}
          <div className="bg-white rounded-xl border border-surface-tertiary shadow-sm p-4">
            <h3 className="text-sm font-medium text-text-primary mb-3">
              Send Test Email
            </h3>
            <label
              htmlFor="recipient-email"
              className="block text-xs font-medium text-text-secondary mb-1"
            >
              Recipient Email
            </label>
            <input
              id="recipient-email"
              type="email"
              value={recipientEmail}
              onChange={(e) => setRecipientEmail(e.target.value)}
              placeholder="test@example.com"
              className="w-full border border-surface-tertiary rounded-lg px-3 py-2 text-sm text-text-primary bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
            <button
              onClick={handleSendTest}
              disabled={sending || !selectedKey || !recipientEmail}
              className="mt-3 w-full flex items-center justify-center gap-2 bg-[#da7756] text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-[#c4684a] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              Send Test
            </button>
          </div>
        </div>

        {/* Right: Preview / Edit panel */}
        <div className="lg:col-span-2 space-y-4">
          {/* Subject line */}
          {!editMode && previewSubject && (
            <div className="bg-white rounded-xl border border-surface-tertiary shadow-sm p-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-medium text-text-muted uppercase tracking-wider">
                    Subject
                  </span>
                  <p className="mt-1 text-sm font-medium text-text-primary">
                    {previewSubject}
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleEnterEditMode}
                  disabled={!previewHtml}
                >
                  <Pencil className="h-3.5 w-3.5 mr-1.5" />
                  Edit Template
                </Button>
              </div>
            </div>
          )}

          {/* Edit Mode */}
          {editMode && (
            <div className="space-y-4">
              {/* Edit header with back button */}
              <div className="flex items-center justify-between">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setEditMode(false)}
                >
                  <ArrowLeft className="h-3.5 w-3.5 mr-1.5" />
                  Back to Preview
                </Button>
                <div className="flex items-center gap-2">
                  {overridesMap.has(selectedKey) && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleResetToDefault}
                      disabled={deleteOverrideMutation.isPending}
                    >
                      {deleteOverrideMutation.isPending ? (
                        <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                      ) : (
                        <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                      )}
                      Reset to Default
                    </Button>
                  )}
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleSaveOverride}
                    disabled={saveOverrideMutation.isPending}
                  >
                    {saveOverrideMutation.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                    ) : (
                      <Save className="h-3.5 w-3.5 mr-1.5" />
                    )}
                    Save Override
                  </Button>
                </div>
              </div>

              {/* Subject input */}
              <div className="bg-white rounded-xl border border-surface-tertiary shadow-sm p-4">
                <label
                  htmlFor="edit-subject"
                  className="block text-xs font-medium text-text-muted uppercase tracking-wider mb-2"
                >
                  Subject Line
                </label>
                <input
                  id="edit-subject"
                  type="text"
                  value={editSubject}
                  onChange={(e) => setEditSubject(e.target.value)}
                  placeholder="Email subject line"
                  className="w-full border border-surface-tertiary rounded-lg px-3 py-2 text-sm text-text-primary bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              {/* Editor tabs */}
              <div className="bg-white rounded-xl border border-surface-tertiary shadow-sm overflow-hidden">
                <div className="px-4 py-3 border-b border-surface-tertiary flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setEditTab("editor")}
                      className={cn(
                        "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                        editTab === "editor"
                          ? "bg-primary-100 text-primary-700"
                          : "text-text-secondary hover:text-text-primary hover:bg-surface-secondary"
                      )}
                    >
                      <Code className="h-3.5 w-3.5" />
                      HTML Editor
                    </button>
                    <button
                      onClick={() => setEditTab("preview")}
                      className={cn(
                        "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                        editTab === "preview"
                          ? "bg-primary-100 text-primary-700"
                          : "text-text-secondary hover:text-text-primary hover:bg-surface-secondary"
                      )}
                    >
                      <Monitor className="h-3.5 w-3.5" />
                      Live Preview
                    </button>
                  </div>
                  <p className="text-xs text-text-muted">
                    Include <code className="bg-surface-secondary px-1 py-0.5 rounded text-xs">{"{unsubscribe_url}"}</code> for the unsubscribe link
                  </p>
                </div>

                {editTab === "editor" ? (
                  <div className="p-4">
                    <textarea
                      value={editHtml}
                      onChange={(e) => setEditHtml(e.target.value)}
                      className="w-full min-h-[500px] font-mono text-sm border border-surface-tertiary rounded-lg px-3 py-2 text-text-primary bg-surface-secondary focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-y"
                      placeholder="Paste or write your HTML email template here..."
                      spellCheck={false}
                    />
                  </div>
                ) : (
                  <div className="flex justify-center p-4 bg-surface-secondary">
                    <iframe
                      ref={editIframeRef}
                      srcDoc={editHtml}
                      title="Edit preview"
                      className="w-full max-w-[640px] min-h-[600px] bg-white border border-surface-tertiary rounded-lg"
                      sandbox="allow-same-origin"
                      style={{ border: "none" }}
                      onLoad={() => {
                        const iframe = editIframeRef.current;
                        if (iframe?.contentDocument?.body) {
                          const height = iframe.contentDocument.body.scrollHeight;
                          iframe.style.height = `${Math.max(600, height + 40)}px`;
                        }
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Default Preview (non-edit mode) */}
          {!editMode && (
            <div className="bg-white rounded-xl border border-surface-tertiary shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-surface-tertiary">
                <h3 className="text-sm font-medium text-text-primary">
                  Email Preview
                </h3>
              </div>
              {previewing ? (
                <div className="flex items-center justify-center py-20">
                  <Loader2 className="h-6 w-6 animate-spin text-text-muted" />
                </div>
              ) : previewHtml ? (
                <div className="flex justify-center p-4 bg-surface-secondary">
                  <iframe
                    ref={iframeRef}
                    srcDoc={previewHtml}
                    title="Email preview"
                    className="w-full max-w-[640px] min-h-[600px] bg-white border border-surface-tertiary rounded-lg"
                    sandbox="allow-same-origin"
                    style={{ border: "none" }}
                    onLoad={() => {
                      // Auto-resize iframe to content height
                      const iframe = iframeRef.current;
                      if (iframe?.contentDocument?.body) {
                        const height = iframe.contentDocument.body.scrollHeight;
                        iframe.style.height = `${Math.max(600, height + 40)}px`;
                      }
                    }}
                  />
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-20 text-text-muted">
                  <Mail className="h-10 w-10 mb-3 opacity-30" />
                  <p className="text-sm">
                    Select a template to preview its rendered HTML
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
