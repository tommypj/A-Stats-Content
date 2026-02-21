"use client";

import { Suspense, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Loader2,
  Sparkles,
} from "lucide-react";
import { api, Outline } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { AIGenerationProgress } from "@/components/ui/ai-generation-progress";

export default function NewArticlePage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center p-12"><Loader2 className="h-8 w-8 animate-spin text-primary-500" /></div>}>
      <NewArticleContent />
    </Suspense>
  );
}

function NewArticleContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const outlineId = searchParams.get("outline");

  const [outline, setOutline] = useState<Outline | null>(null);
  const [loading, setLoading] = useState(!!outlineId);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  // Manual creation fields
  const [title, setTitle] = useState("");
  const [keyword, setKeyword] = useState("");
  const [content, setContent] = useState("");
  const [metaDescription, setMetaDescription] = useState("");

  // Generation options
  const [tone, setTone] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [writingStyle, setWritingStyle] = useState("balanced");
  const [voice, setVoice] = useState("second_person");
  const [listUsage, setListUsage] = useState("balanced");
  const [customInstructions, setCustomInstructions] = useState("");

  useEffect(() => {
    if (outlineId) {
      loadOutline(outlineId);
    }
  }, [outlineId]);

  async function loadOutline(id: string) {
    try {
      setLoading(true);
      const data = await api.outlines.get(id);
      setOutline(data);
      setTone(data.tone);
      setTargetAudience(data.target_audience || "");
    } catch (error) {
      console.error("Failed to load outline:", error);
      setError("Failed to load outline");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerate() {
    if (!outline) return;

    setGenerating(true);
    setError("");

    try {
      const article = await api.articles.generate({
        outline_id: outline.id,
        tone: tone || undefined,
        target_audience: targetAudience || undefined,
        writing_style: writingStyle,
        voice: voice,
        list_usage: listUsage,
        custom_instructions: customInstructions || undefined,
      });

      router.push(`/articles/${article.id}`);
    } catch (err) {
      setError("Failed to generate article. Please try again.");
      console.error(err);
    } finally {
      setGenerating(false);
    }
  }

  async function handleCreate() {
    if (!title.trim() || !keyword.trim()) {
      setError("Title and keyword are required");
      return;
    }

    setGenerating(true);
    setError("");

    try {
      const article = await api.articles.create({
        title: title.trim(),
        keyword: keyword.trim(),
        content: content.trim() || undefined,
        meta_description: metaDescription.trim() || undefined,
      });

      router.push(`/articles/${article.id}`);
    } catch (err) {
      setError("Failed to create article. Please try again.");
      console.error(err);
    } finally {
      setGenerating(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href={outline ? `/outlines/${outline.id}` : "/articles"}
          className="p-2 rounded-lg hover:bg-surface-secondary transition-colors"
        >
          <ArrowLeft className="h-5 w-5 text-text-secondary" />
        </Link>
        <div>
          <h1 className="text-2xl font-display font-bold text-text-primary">
            {outline ? "Generate Article" : "New Article"}
          </h1>
          <p className="text-text-secondary mt-1">
            {outline
              ? "Generate an article from your outline"
              : "Create a new article manually"}
          </p>
        </div>
      </div>

      {outline ? (
        // Generate from Outline
        <Card className="p-6 space-y-6">
          {generating ? (
            <AIGenerationProgress
              type="article"
              title={outline.title}
              keyword={outline.keyword}
              isGenerating={generating}
            />
          ) : (
            <>
              <div className="p-4 bg-surface-secondary rounded-xl">
                <h3 className="font-medium text-text-primary mb-2">{outline.title}</h3>
                <div className="flex items-center gap-3 text-sm text-text-secondary">
                  <span className="px-2 py-0.5 bg-white rounded-md">{outline.keyword}</span>
                  <span>{outline.sections?.length || 0} sections</span>
                  <span>~{outline.word_count_target} words</span>
                </div>
              </div>

              {/* Writing Style Controls */}
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-text-primary mb-3">Writing Style</h4>
                  <div className="grid gap-3 md:grid-cols-3">
                    <div>
                      <label className="block text-xs font-medium text-text-secondary mb-1.5">
                        Style
                      </label>
                      <select
                        value={writingStyle}
                        onChange={(e) => setWritingStyle(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all text-sm"
                      >
                        <option value="balanced">Balanced (Recommended)</option>
                        <option value="editorial">Editorial</option>
                        <option value="narrative">Narrative / Storytelling</option>
                        <option value="listicle">Listicle</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-text-secondary mb-1.5">
                        Voice
                      </label>
                      <select
                        value={voice}
                        onChange={(e) => setVoice(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all text-sm"
                      >
                        <option value="second_person">You / Your (direct)</option>
                        <option value="first_person">I / We (personal)</option>
                        <option value="third_person">They / One (formal)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-text-secondary mb-1.5">
                        List Usage
                      </label>
                      <select
                        value={listUsage}
                        onChange={(e) => setListUsage(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all text-sm"
                      >
                        <option value="balanced">Balanced</option>
                        <option value="minimal">Minimal (mostly prose)</option>
                        <option value="heavy">Heavy (scannable)</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="block text-xs font-medium text-text-secondary mb-1.5">
                      Tone (optional override)
                    </label>
                    <select
                      value={tone}
                      onChange={(e) => setTone(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all text-sm"
                    >
                      <option value="">Use outline tone ({outline.tone})</option>
                      <option value="professional">Professional</option>
                      <option value="friendly">Friendly</option>
                      <option value="empathetic">Empathetic</option>
                      <option value="informative">Informative</option>
                      <option value="conversational">Conversational</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-text-secondary mb-1.5">
                      Target Audience (optional override)
                    </label>
                    <input
                      type="text"
                      value={targetAudience}
                      onChange={(e) => setTargetAudience(e.target.value)}
                      placeholder={outline.target_audience || "e.g., health-conscious adults"}
                      className="w-full px-3 py-2 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all text-sm"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1.5">
                    Custom Instructions (optional)
                  </label>
                  <textarea
                    value={customInstructions}
                    onChange={(e) => setCustomInstructions(e.target.value)}
                    placeholder="e.g., Include a personal anecdote in the introduction. Reference recent 2025 studies. Avoid medical disclaimers."
                    rows={2}
                    maxLength={1000}
                    className="w-full px-3 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all resize-none text-sm"
                  />
                  <p className="text-xs text-text-muted mt-1">
                    {customInstructions.length}/1000 characters
                  </p>
                </div>
              </div>

              {error && <p className="text-sm text-red-600">{error}</p>}

              <Button
                onClick={handleGenerate}
                disabled={generating}
                className="w-full"
                size="lg"
              >
                <Sparkles className="h-5 w-5 mr-2" />
                Generate Article
              </Button>
            </>
          )}
        </Card>
      ) : (
        // Manual Creation
        <Card className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1.5">
              Article Title *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter article title"
              className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1.5">
              Target Keyword *
            </label>
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="e.g., stress management techniques"
              className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1.5">
              Meta Description
            </label>
            <textarea
              value={metaDescription}
              onChange={(e) => setMetaDescription(e.target.value)}
              placeholder="SEO meta description (150-160 characters)"
              rows={2}
              maxLength={160}
              className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all resize-none"
            />
            <p className="text-xs text-text-muted mt-1">
              {metaDescription.length}/160 characters
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1.5">
              Content (optional)
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Write your article content in Markdown format..."
              rows={10}
              className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all resize-none font-mono text-sm"
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex gap-3 pt-4">
            <Link href="/articles" className="flex-1">
              <Button variant="outline" className="w-full">
                Cancel
              </Button>
            </Link>
            <Button
              onClick={handleCreate}
              disabled={generating}
              className="flex-1"
            >
              {generating ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : null}
              Create Article
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
