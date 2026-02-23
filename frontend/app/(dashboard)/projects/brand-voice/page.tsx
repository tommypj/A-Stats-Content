"use client";

import { useEffect, useState } from "react";
import { api, BrandVoiceSettings, parseApiError } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  MessageSquare,
  Save,
  Loader2,
  CheckCircle,
  AlertCircle,
  Info,
} from "lucide-react";

const TONE_OPTIONS = [
  { value: "", label: "Not set" },
  { value: "professional", label: "Professional" },
  { value: "casual", label: "Casual" },
  { value: "authoritative", label: "Authoritative" },
  { value: "friendly", label: "Friendly" },
  { value: "academic", label: "Academic" },
  { value: "conversational", label: "Conversational" },
];

const WRITING_STYLE_OPTIONS = [
  { value: "", label: "Not set" },
  { value: "informative", label: "Informative" },
  { value: "persuasive", label: "Persuasive" },
  { value: "narrative", label: "Narrative" },
  { value: "technical", label: "Technical" },
  { value: "conversational", label: "Conversational" },
];

const LANGUAGE_OPTIONS = [
  { value: "", label: "Not set (use article default)" },
  { value: "en", label: "English" },
  { value: "es", label: "Spanish" },
  { value: "de", label: "German" },
  { value: "fr", label: "French" },
  { value: "it", label: "Italian" },
  { value: "pt", label: "Portuguese" },
  { value: "nl", label: "Dutch" },
  { value: "pl", label: "Polish" },
  { value: "sv", label: "Swedish" },
  { value: "da", label: "Danish" },
  { value: "no", label: "Norwegian" },
  { value: "fi", label: "Finnish" },
  { value: "ro", label: "Romanian" },
  { value: "cs", label: "Czech" },
  { value: "hu", label: "Hungarian" },
  { value: "tr", label: "Turkish" },
  { value: "ru", label: "Russian" },
  { value: "zh", label: "Chinese (Simplified)" },
  { value: "ja", label: "Japanese" },
  { value: "ko", label: "Korean" },
  { value: "ar", label: "Arabic" },
];

const MAX_CUSTOM_INSTRUCTIONS = 500;

export default function BrandVoicePage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [noProject, setNoProject] = useState(false);

  // Form state
  const [tone, setTone] = useState("");
  const [writingStyle, setWritingStyle] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [customInstructions, setCustomInstructions] = useState("");
  const [language, setLanguage] = useState("");

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError("");
      setNoProject(false);
      const data = await api.projects.getBrandVoice();
      setTone(data.tone || "");
      setWritingStyle(data.writing_style || "");
      setTargetAudience(data.target_audience || "");
      setCustomInstructions(data.custom_instructions || "");
      setLanguage(data.language || "");
    } catch (err) {
      const parsed = parseApiError(err);
      // 400 means no project is selected
      if (parsed.message?.includes("No project selected")) {
        setNoProject(true);
      } else {
        setError(parsed.message || "Failed to load brand voice settings.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setSaved(false);
      setError("");

      const payload: BrandVoiceSettings = {};
      if (tone) payload.tone = tone;
      if (writingStyle) payload.writing_style = writingStyle;
      if (targetAudience.trim()) payload.target_audience = targetAudience.trim();
      if (customInstructions.trim()) payload.custom_instructions = customInstructions.trim();
      if (language) payload.language = language;

      await api.projects.updateBrandVoice(payload);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      const parsed = parseApiError(err);
      if (parsed.message?.includes("No project selected")) {
        setNoProject(true);
      } else {
        setError(parsed.message || "Failed to save brand voice settings.");
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="h-8 w-48 bg-surface-secondary rounded animate-pulse" />
        <div className="h-64 bg-surface-secondary rounded-xl animate-pulse" />
      </div>
    );
  }

  if (noProject) {
    return (
      <div className="max-w-2xl mx-auto">
        <Card className="p-8 text-center space-y-3">
          <Info className="h-10 w-10 text-primary-400 mx-auto" />
          <h2 className="text-lg font-semibold text-text-primary">No Project Selected</h2>
          <p className="text-sm text-text-secondary">
            Brand Voice settings are saved at the project level. Please switch to a project
            using the project switcher in the sidebar before configuring your brand voice.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-primary-100 flex items-center justify-center">
          <MessageSquare className="h-5 w-5 text-primary-700" />
        </div>
        <div>
          <h1 className="text-2xl font-display font-bold text-text-primary">Brand Voice</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            Set default tone and style for AI-generated content in this project.
          </p>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Success alert */}
      {saved && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm">
          <CheckCircle className="h-4 w-4 shrink-0" />
          Brand voice settings saved successfully.
        </div>
      )}

      {/* Settings card */}
      <Card className="p-6 space-y-6">
        {/* Tone */}
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-text-primary">
            Tone
          </label>
          <p className="text-xs text-text-secondary">
            The overall tone used when generating outlines and articles.
          </p>
          <select
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg border border-surface-tertiary bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            {TONE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Writing style */}
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-text-primary">
            Writing Style
          </label>
          <p className="text-xs text-text-secondary">
            The structural approach and rhetorical style of generated content.
          </p>
          <select
            value={writingStyle}
            onChange={(e) => setWritingStyle(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg border border-surface-tertiary bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            {WRITING_STYLE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Target audience */}
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-text-primary">
            Target Audience
          </label>
          <p className="text-xs text-text-secondary">
            Describe who the content is written for (e.g., "marketing professionals", "first-time home buyers").
          </p>
          <Input
            type="text"
            value={targetAudience}
            onChange={(e) => setTargetAudience(e.target.value)}
            placeholder="e.g., marketing professionals aged 25-45"
            className="w-full"
          />
        </div>

        {/* Language */}
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-text-primary">
            Default Language
          </label>
          <p className="text-xs text-text-secondary">
            When set, this overrides the per-article language selection.
          </p>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg border border-surface-tertiary bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            {LANGUAGE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Custom instructions */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-text-primary">
              Custom Instructions
            </label>
            <span
              className={`text-xs ${
                customInstructions.length > MAX_CUSTOM_INSTRUCTIONS
                  ? "text-red-500"
                  : "text-text-secondary"
              }`}
            >
              {customInstructions.length} / {MAX_CUSTOM_INSTRUCTIONS}
            </span>
          </div>
          <p className="text-xs text-text-secondary">
            Any additional instructions to pass to the AI when generating content for this project.
          </p>
          <textarea
            value={customInstructions}
            onChange={(e) => setCustomInstructions(e.target.value)}
            placeholder="e.g., Always cite at least two statistics. Avoid jargon. Use the Oxford comma."
            rows={4}
            maxLength={MAX_CUSTOM_INSTRUCTIONS}
            className="w-full px-3 py-2 text-sm rounded-lg border border-surface-tertiary bg-surface text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
          />
        </div>

        {/* Save button */}
        <div className="flex justify-end pt-2">
          <Button
            onClick={handleSave}
            disabled={saving || customInstructions.length > MAX_CUSTOM_INSTRUCTIONS}
            className="flex items-center gap-2"
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : saved ? (
              <CheckCircle className="h-4 w-4" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {saving ? "Saving..." : saved ? "Saved" : "Save Brand Voice"}
          </Button>
        </div>
      </Card>

      {/* Info note */}
      <div className="flex items-start gap-2 px-4 py-3 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-sm">
        <Info className="h-4 w-4 shrink-0 mt-0.5" />
        <span>
          These settings are used as defaults when creating outlines and articles. You can still
          override them on a per-item basis when creating content.
        </span>
      </div>
    </div>
  );
}
