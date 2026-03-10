"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
import { TierGate } from "@/components/ui/tier-gate";

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
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Form state
  const [tone, setTone] = useState("");
  const [writingStyle, setWritingStyle] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [customInstructions, setCustomInstructions] = useState("");
  const [language, setLanguage] = useState("");

  // --- React Query hooks ---

  const { data: brandVoiceData, isLoading: loading, error: queryError } = useQuery({
    queryKey: ["projects", "brand-voice"],
    queryFn: () => api.projects.getBrandVoice(),
    staleTime: 30_000,
  });

  // Sync fetched data into form state
  const [formInitialized, setFormInitialized] = useState(false);
  useEffect(() => {
    if (brandVoiceData && !formInitialized) {
      setTone(brandVoiceData.tone || "");
      setWritingStyle(brandVoiceData.writing_style || "");
      setTargetAudience(brandVoiceData.target_audience || "");
      setCustomInstructions(brandVoiceData.custom_instructions || "");
      setLanguage(brandVoiceData.language || "");
      setFormInitialized(true);
    }
  }, [brandVoiceData, formInitialized]);

  const saveMutation = useMutation({
    mutationFn: (payload: BrandVoiceSettings) =>
      api.projects.updateBrandVoice(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", "brand-voice"] });
      setSaved(true);
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
      savedTimerRef.current = setTimeout(() => setSaved(false), 3000);
    },
  });

  const noProject =
    (queryError && parseApiError(queryError).message?.includes("No project selected")) ||
    (saveMutation.error && parseApiError(saveMutation.error).message?.includes("No project selected"));

  const error = (() => {
    if (noProject) return "";
    if (saveMutation.error) return parseApiError(saveMutation.error).message;
    if (queryError) return parseApiError(queryError).message;
    return "";
  })();

  const saving = saveMutation.isPending;

  const handleSave = () => {
    setSaved(false);

    const payload: BrandVoiceSettings = {};
    if (tone) payload.tone = tone;
    if (writingStyle) payload.writing_style = writingStyle;
    if (targetAudience.trim()) payload.target_audience = targetAudience.trim();
    if (customInstructions.trim()) payload.custom_instructions = customInstructions.trim();
    if (language) payload.language = language;

    saveMutation.mutate(payload);
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
    <TierGate minimum="starter" feature="Project Management">
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
          <label htmlFor="tone" className="block text-sm font-medium text-text-primary">
            Tone
          </label>
          <p className="text-xs text-text-secondary">
            The overall tone used when generating outlines and articles.
          </p>
          <select
            id="tone"
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
          <label htmlFor="writing-style" className="block text-sm font-medium text-text-primary">
            Writing Style
          </label>
          <p className="text-xs text-text-secondary">
            The structural approach and rhetorical style of generated content.
          </p>
          <select
            id="writing-style"
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
          <label htmlFor="target-audience" className="block text-sm font-medium text-text-primary">
            Target Audience
          </label>
          <p className="text-xs text-text-secondary">
            Describe who the content is written for (e.g., "marketing professionals", "first-time home buyers").
          </p>
          <Input
            id="target-audience"
            type="text"
            value={targetAudience}
            onChange={(e) => setTargetAudience(e.target.value)}
            placeholder="e.g., marketing professionals aged 25-45"
            className="w-full"
          />
        </div>

        {/* Language */}
        <div className="space-y-1.5">
          <label htmlFor="default-language" className="block text-sm font-medium text-text-primary">
            Default Language
          </label>
          <p className="text-xs text-text-secondary">
            When set, this overrides the per-article language selection.
          </p>
          <select
            id="default-language"
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
            <label htmlFor="brand-custom-instructions" className="block text-sm font-medium text-text-primary">
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
            id="brand-custom-instructions"
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
    </TierGate>
  );
}
