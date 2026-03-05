"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Plus, Minus, ExternalLink, Loader2, Sparkles, Trash2, Image as ImageIcon } from "lucide-react";
import { api, parseApiError } from "@/lib/api";
import type { BlogCategory, BlogPostDetail, BlogTag } from "@/lib/api";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_]+/g, "-")
    .replace(/-+/g, "-")
    .trim();
}

interface FaqItem {
  question: string;
  answer: string;
}

function parseFaqItems(schemaFaq: Record<string, unknown> | undefined): FaqItem[] {
  if (!schemaFaq) return [];
  const entities = (schemaFaq.mainEntity as Array<Record<string, unknown>>) || [];
  return entities.map(e => ({
    question: (e.name as string) || "",
    answer: ((e.acceptedAnswer as Record<string, unknown>)?.text as string) || "",
  }));
}

export default function AdminEditBlogPostPage() {
  const params = useParams();
  const postId = params.id as string;
  const router = useRouter();
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [post, setPost] = useState<BlogPostDetail | null>(null);
  const [categories, setCategories] = useState<BlogCategory[]>([]);
  const [tags, setTags] = useState<BlogTag[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generatingImage, setGeneratingImage] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  // AI controls
  const [aiKeyword, setAiKeyword] = useState("");
  const [aiTone, setAiTone] = useState("professional");
  const [aiWordCount, setAiWordCount] = useState("1200");
  const [aiWritingStyle, setAiWritingStyle] = useState("balanced");
  const [aiVoice, setAiVoice] = useState("second_person");
  const [aiListUsage, setAiListUsage] = useState("balanced");
  const [aiCustomInstructions, setAiCustomInstructions] = useState("");
  const [aiLanguage, setAiLanguage] = useState("en");
  const [imagePrompt, setImagePrompt] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Form fields
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [contentHtml, setContentHtml] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [metaTitle, setMetaTitle] = useState("");
  const [metaDescription, setMetaDescription] = useState("");
  const [featuredImageUrl, setFeaturedImageUrl] = useState("");
  const [featuredImageAlt, setFeaturedImageAlt] = useState("");
  const [ogImageUrl, setOgImageUrl] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([]);
  const [faqItems, setFaqItems] = useState<FaqItem[]>([]);
  const [status, setStatus] = useState("draft");

  const loadPost = useCallback(async () => {
    try {
      setLoading(true);
      const [p, cats, tgs] = await Promise.all([
        api.admin.blog.posts.get(postId),
        api.admin.blog.categories.list(),
        api.admin.blog.tags.list(),
      ]);
      setPost(p);
      setCategories(cats);
      setTags(tgs);

      setTitle(p.title);
      setSlug(p.slug);
      setContentHtml(p.content_html || "");
      setExcerpt(p.excerpt || "");
      setMetaTitle(p.meta_title || "");
      setMetaDescription(p.meta_description || "");
      setFeaturedImageUrl(p.featured_image_url || "");
      setFeaturedImageAlt(p.featured_image_alt || "");
      setOgImageUrl(p.og_image_url || "");
      setCategoryId(p.category?.id || "");
      setSelectedTagIds(p.tags.map(t => t.id));
      setFaqItems(parseFaqItems(p.schema_faq));
      setStatus(p.status || "draft");
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [postId]);

  useEffect(() => {
    loadPost();
    return () => { if (pollRef.current) clearTimeout(pollRef.current); };
  }, [loadPost]);

  const toggleTag = (id: string) => {
    setSelectedTagIds(prev =>
      prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id]
    );
  };

  const addFaq = () => setFaqItems(prev => [...prev, { question: "", answer: "" }]);
  const removeFaq = (i: number) => setFaqItems(prev => prev.filter((_, idx) => idx !== i));
  const updateFaq = (i: number, field: "question" | "answer", value: string) => {
    setFaqItems(prev => prev.map((item, idx) => idx === i ? { ...item, [field]: value } : item));
  };

  const buildFaqSchema = () => {
    const valid = faqItems.filter(f => f.question.trim() && f.answer.trim());
    if (!valid.length) return undefined;
    return {
      "@type": "FAQPage",
      mainEntity: valid.map(f => ({
        "@type": "Question",
        name: f.question,
        acceptedAnswer: { "@type": "Answer", text: f.answer },
      })),
    };
  };

  const handleGenerate = async () => {
    if (!title.trim()) {
      toast.error("Enter a title first");
      return;
    }
    try {
      setGenerating(true);
      const result = await api.admin.blog.generateContent({
        title: title.trim(),
        keyword: aiKeyword || undefined,
        tone: aiTone,
        word_count: parseInt(aiWordCount) || 1200,
        writing_style: aiWritingStyle,
        voice: aiVoice,
        list_usage: aiListUsage,
        custom_instructions: aiCustomInstructions || undefined,
        language: aiLanguage,
      });
      setContentHtml(result.content_html);
      if (result.meta_description && !metaDescription) setMetaDescription(result.meta_description);
      if (result.image_prompt) setImagePrompt(result.image_prompt);
      toast.success("Content generated!");
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setGenerating(false);
    }
  };

  const pollImageStatus = (imageId: string) => {
    pollRef.current = setTimeout(async () => {
      try {
        const img = await api.images.get(imageId);
        if (img.status === "completed" && img.url) {
          setFeaturedImageUrl(img.url);
          setFeaturedImageAlt(imagePrompt.slice(0, 120));
          setGeneratingImage(false);
          toast.success("Image generated!");
        } else if (img.status === "failed") {
          setGeneratingImage(false);
          toast.error("Image generation failed");
        } else {
          pollImageStatus(imageId);
        }
      } catch {
        setGeneratingImage(false);
        toast.error("Image polling error");
      }
    }, 3000);
  };

  const handleGenerateImage = async () => {
    if (!imagePrompt.trim()) {
      toast.error("Generate content first to get an image prompt");
      return;
    }
    try {
      setGeneratingImage(true);
      const img = await api.images.generate({ prompt: imagePrompt });
      if (img.status === "completed" && img.url) {
        setFeaturedImageUrl(img.url);
        setFeaturedImageAlt(imagePrompt.slice(0, 120));
        setGeneratingImage(false);
        toast.success("Image generated!");
      } else {
        pollImageStatus(img.id);
      }
    } catch (err) {
      setGeneratingImage(false);
      toast.error(parseApiError(err).message);
    }
  };

  const handleSave = async () => {
    if (!title.trim()) {
      toast.error("Title is required");
      return;
    }
    try {
      setSaving(true);
      await api.admin.blog.posts.update(postId, {
        title: title.trim(),
        slug: slug.trim() || slugify(title.trim()),
        content_html: contentHtml || undefined,
        excerpt: excerpt || undefined,
        meta_title: metaTitle || undefined,
        meta_description: metaDescription || undefined,
        featured_image_url: featuredImageUrl || undefined,
        featured_image_alt: featuredImageAlt || undefined,
        og_image_url: ogImageUrl || undefined,
        category_id: categoryId || undefined,
        tag_ids: selectedTagIds,
        schema_faq: buildFaqSchema(),
      });
      toast.success("Post saved!");
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handlePublishToggle = async () => {
    try {
      setSaving(true);
      if (status === "published") {
        await api.admin.blog.posts.unpublish(postId);
        setStatus("draft");
        toast.success("Post unpublished");
      } else {
        await api.admin.blog.posts.publish(postId);
        setStatus("published");
        toast.success("Post published!");
      }
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      await api.admin.blog.posts.delete(postId);
      toast.success("Post deleted");
      router.push("/admin/blog");
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  if (loading) return <div className="p-8 text-center text-text-secondary">Loading...</div>;
  if (!post) return <div className="p-8 text-center text-text-secondary">Post not found.</div>;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Edit Post</h1>
          <p className="text-sm text-text-secondary mt-1">
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
              status === "published" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
            }`}>
              {status}
            </span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          {status === "published" && (
            <a
              href={`/en/blog/${slug}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 px-3 py-2 border border-surface-tertiary rounded-lg text-sm text-text-secondary hover:bg-surface-secondary"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Preview
            </a>
          )}
          <button
            onClick={handlePublishToggle}
            disabled={saving}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${
              status === "published"
                ? "bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100"
                : "bg-primary-600 text-white hover:bg-primary-700"
            }`}
          >
            {status === "published" ? "Unpublish" : "Publish"}
          </button>
          <button
            onClick={() => setConfirmDelete(true)}
            className="p-2 rounded-lg border border-red-200 text-red-600 hover:bg-red-50"
            aria-label="Delete post"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: main content */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-surface border border-surface-tertiary rounded-xl p-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Title *</label>
              <input
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Slug</label>
              <input
                type="text"
                value={slug}
                onChange={e => setSlug(e.target.value)}
                className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            {/* AI Generation */}
            <div className="border border-primary-200 bg-primary-50 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary-600" />
                  <span className="text-sm font-semibold text-primary-700">Generate with AI</span>
                </div>
                <button
                  onClick={() => setShowAdvanced(v => !v)}
                  className="text-xs text-primary-600 hover:text-primary-800 underline underline-offset-2"
                >
                  {showAdvanced ? "Hide advanced" : "Advanced options"}
                </button>
              </div>

              {/* Basic row */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-1">
                  <label className="block text-xs font-medium text-text-secondary mb-1">Target Keyword</label>
                  <input
                    type="text"
                    value={aiKeyword}
                    onChange={e => setAiKeyword(e.target.value)}
                    placeholder="e.g. SEO tips 2025"
                    className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1">Tone</label>
                  <select value={aiTone} onChange={e => setAiTone(e.target.value)} className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white">
                    <option value="professional">Professional</option>
                    <option value="conversational">Conversational</option>
                    <option value="educational">Educational</option>
                    <option value="persuasive">Persuasive</option>
                    <option value="friendly">Friendly</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1">Word Count</label>
                  <select value={aiWordCount} onChange={e => setAiWordCount(e.target.value)} className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white">
                    <option value="800">~800 words</option>
                    <option value="1200">~1200 words</option>
                    <option value="1800">~1800 words</option>
                    <option value="2500">~2500 words</option>
                  </select>
                </div>
              </div>

              {/* Advanced options */}
              {showAdvanced && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-primary-200">
                  <div>
                    <label className="block text-xs font-medium text-text-secondary mb-1">Writing Style</label>
                    <select value={aiWritingStyle} onChange={e => setAiWritingStyle(e.target.value)} className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white">
                      <option value="balanced">Balanced</option>
                      <option value="storytelling">Storytelling</option>
                      <option value="listicle">Listicle</option>
                      <option value="how_to">How-to</option>
                      <option value="academic">Academic</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-text-secondary mb-1">Voice</label>
                    <select value={aiVoice} onChange={e => setAiVoice(e.target.value)} className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white">
                      <option value="second_person">Second person (you/your)</option>
                      <option value="first_person">First person (I/we)</option>
                      <option value="third_person">Third person</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-text-secondary mb-1">List Usage</label>
                    <select value={aiListUsage} onChange={e => setAiListUsage(e.target.value)} className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white">
                      <option value="balanced">Balanced</option>
                      <option value="minimal">Minimal (prose-heavy)</option>
                      <option value="extensive">Extensive (list-heavy)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-text-secondary mb-1">Language</label>
                    <select value={aiLanguage} onChange={e => setAiLanguage(e.target.value)} className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white">
                      <option value="en">English</option>
                      <option value="es">Spanish</option>
                      <option value="fr">French</option>
                      <option value="de">German</option>
                      <option value="it">Italian</option>
                      <option value="pt">Portuguese</option>
                    </select>
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-xs font-medium text-text-secondary mb-1">Custom Instructions</label>
                    <textarea
                      value={aiCustomInstructions}
                      onChange={e => setAiCustomInstructions(e.target.value)}
                      placeholder="e.g. Include real examples, mention our product A-Stats..."
                      rows={2}
                      className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white"
                    />
                  </div>
                </div>
              )}

              <button
                onClick={handleGenerate}
                disabled={generating}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
              >
                {generating ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Generating...</>
                ) : (
                  <><Sparkles className="h-4 w-4" /> Generate Content</>
                )}
              </button>

              {/* Image generation */}
              {imagePrompt && (
                <div className="border-t border-primary-200 pt-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <ImageIcon className="h-4 w-4 text-primary-600" />
                    <span className="text-xs font-semibold text-primary-700">AI Image</span>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-text-secondary mb-1">Image Prompt</label>
                    <textarea
                      value={imagePrompt}
                      onChange={e => setImagePrompt(e.target.value)}
                      rows={2}
                      className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-xs font-mono focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white"
                    />
                  </div>
                  {featuredImageUrl && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={featuredImageUrl} alt="Generated" className="w-full max-h-40 object-cover rounded-lg" />
                  )}
                  <button
                    onClick={handleGenerateImage}
                    disabled={generatingImage}
                    className="inline-flex items-center gap-2 px-3 py-1.5 bg-white border border-primary-300 text-primary-700 rounded-lg text-xs font-medium hover:bg-primary-50 disabled:opacity-50"
                  >
                    {generatingImage ? (
                      <><Loader2 className="h-3 w-3 animate-spin" /> Generating image...</>
                    ) : (
                      <><ImageIcon className="h-3 w-3" /> {featuredImageUrl ? "Regenerate Image" : "Generate Image"}</>
                    )}
                  </button>
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Content (HTML)</label>
              <textarea
                value={contentHtml}
                onChange={e => setContentHtml(e.target.value)}
                rows={20}
                className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          {/* FAQ Schema */}
          <div className="bg-surface border border-surface-tertiary rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">FAQ Schema (optional)</h3>
              <button onClick={addFaq} className="inline-flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700">
                <Plus className="h-3 w-3" /> Add Q&A
              </button>
            </div>
            {faqItems.length === 0 && (
              <p className="text-xs text-text-muted">No FAQ items.</p>
            )}
            {faqItems.map((item, i) => (
              <div key={i} className="border border-surface-tertiary rounded-lg p-3 mb-3">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-medium text-text-secondary">Question {i + 1}</span>
                  <button onClick={() => removeFaq(i)} className="text-red-500 hover:text-red-700">
                    <Minus className="h-3 w-3" />
                  </button>
                </div>
                <input
                  type="text"
                  value={item.question}
                  onChange={e => updateFaq(i, "question", e.target.value)}
                  placeholder="Question"
                  className="w-full px-2 py-1.5 border border-surface-tertiary rounded text-sm mb-2 focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
                <textarea
                  value={item.answer}
                  onChange={e => updateFaq(i, "answer", e.target.value)}
                  placeholder="Answer"
                  rows={2}
                  className="w-full px-2 py-1.5 border border-surface-tertiary rounded text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
              </div>
            ))}
          </div>
        </div>

        {/* Right: sidebar */}
        <div className="space-y-4">
          {/* Category */}
          <div className="bg-surface border border-surface-tertiary rounded-xl p-4">
            <label className="block text-sm font-medium text-text-primary mb-2">Category</label>
            <select value={categoryId} onChange={e => setCategoryId(e.target.value)} className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500">
              <option value="">No category</option>
              {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>

          {/* Tags */}
          <div className="bg-surface border border-surface-tertiary rounded-xl p-4">
            <label className="block text-sm font-medium text-text-primary mb-2">Tags</label>
            {tags.length === 0 ? (
              <p className="text-xs text-text-muted">No tags yet.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {tags.map(t => (
                  <button
                    key={t.id}
                    onClick={() => toggleTag(t.id)}
                    className={`px-2 py-1 text-xs rounded-full border transition-colors ${
                      selectedTagIds.includes(t.id)
                        ? "bg-primary-600 text-white border-primary-600"
                        : "bg-surface text-text-secondary border-surface-tertiary hover:border-primary-400"
                    }`}
                  >
                    {t.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Excerpt */}
          <div className="bg-surface border border-surface-tertiary rounded-xl p-4">
            <label className="block text-sm font-medium text-text-primary mb-1">Excerpt</label>
            <textarea
              value={excerpt}
              onChange={e => setExcerpt(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* SEO */}
          <div className="bg-surface border border-surface-tertiary rounded-xl p-4 space-y-3">
            <h3 className="text-sm font-semibold text-text-primary">SEO</h3>
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Meta Title</label>
              <input
                type="text"
                value={metaTitle}
                onChange={e => setMetaTitle(e.target.value)}
                className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Meta Description</label>
              <textarea
                value={metaDescription}
                onChange={e => setMetaDescription(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          {/* Images */}
          <div className="bg-surface border border-surface-tertiary rounded-xl p-4 space-y-3">
            <h3 className="text-sm font-semibold text-text-primary">Images</h3>
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Featured Image URL</label>
              <input
                type="url"
                value={featuredImageUrl}
                onChange={e => setFeaturedImageUrl(e.target.value)}
                className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            {featuredImageUrl && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={featuredImageUrl} alt="Preview" className="w-full h-32 object-cover rounded-lg" />
            )}
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Alt Text</label>
              <input
                type="text"
                value={featuredImageAlt}
                onChange={e => setFeaturedImageAlt(e.target.value)}
                className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">OG Image URL</label>
              <input
                type="url"
                value={ogImageUrl}
                onChange={e => setOgImageUrl(e.target.value)}
                className="w-full px-3 py-2 border border-surface-tertiary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          {/* Save */}
          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>

      <ConfirmDialog
        isOpen={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        onConfirm={handleDelete}
        title="Delete Post"
        message={`Are you sure you want to delete "${title}"? This action cannot be undone.`}
        variant="danger"
        confirmLabel="Delete"
      />
    </div>
  );
}
