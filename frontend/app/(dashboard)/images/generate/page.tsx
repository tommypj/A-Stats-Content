"use client";

import { Suspense, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
  Sparkles,
  Loader2,
  ArrowLeft,
  Copy,
  Download,
  Save,
  ImageIcon,
  CheckCircle2,
} from "lucide-react";
import { api, getImageUrl, GeneratedImage, Article } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { AIGenerationProgress } from "@/components/ui/ai-generation-progress";

const IMAGE_STYLES = [
  { value: "realistic", label: "Realistic" },
  { value: "photographic", label: "Photographic" },
  { value: "artistic", label: "Artistic" },
  { value: "minimalist", label: "Minimalist" },
  { value: "dramatic", label: "Dramatic" },
  { value: "vintage", label: "Vintage" },
  { value: "modern", label: "Modern" },
  { value: "abstract", label: "Abstract" },
  { value: "watercolor", label: "Watercolor" },
];

const IMAGE_SIZES = [
  { value: "1024x1024", label: "Square (1024×1024)", width: 1024, height: 1024 },
  { value: "1024x768", label: "Landscape (1024×768)", width: 1024, height: 768 },
  { value: "768x1024", label: "Portrait (768×1024)", width: 768, height: 1024 },
  { value: "1792x1024", label: "Wide (1792×1024)", width: 1792, height: 1024 },
  { value: "1024x1792", label: "Tall (1024×1792)", width: 1024, height: 1792 },
];

export default function GenerateImagePage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center p-12"><Loader2 className="h-8 w-8 animate-spin text-primary-500" /></div>}>
      <GenerateImageContent />
    </Suspense>
  );
}

function GenerateImageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const articleIdParam = searchParams.get("article");

  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("realistic");
  const [size, setSize] = useState("1024x1024");
  const [articleId, setArticleId] = useState<string>(articleIdParam || "");
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingArticles, setLoadingArticles] = useState(false);
  const [generatedImage, setGeneratedImage] = useState<GeneratedImage | null>(null);
  const [error, setError] = useState("");
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [promptSource, setPromptSource] = useState<"manual" | "article">("manual");

  useEffect(() => {
    loadArticles();
  }, []);

  // Auto-fill prompt when article selection changes
  useEffect(() => {
    if (!articleId) {
      if (promptSource === "article") {
        setPrompt("");
        setPromptSource("manual");
      }
      return;
    }
    const selected = articles.find((a) => a.id === articleId);
    if (selected?.image_prompt) {
      setPrompt(selected.image_prompt);
      setPromptSource("article");
    }
  }, [articleId, articles]);

  async function loadArticles() {
    try {
      setLoadingArticles(true);
      const response = await api.articles.list({ page_size: 100 });
      setArticles(response.items.filter(a => a.status === "completed" || a.status === "published"));
    } catch (err) {
      console.error("Failed to load articles:", err);
    } finally {
      setLoadingArticles(false);
    }
  }

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();

    if (!prompt.trim()) {
      setError("Please enter a prompt");
      return;
    }

    setLoading(true);
    setError("");
    setGeneratedImage(null);

    try {
      const selectedSize = IMAGE_SIZES.find(s => s.value === size);
      const image = await api.images.generate({
        prompt: prompt.trim(),
        style,
        width: selectedSize?.width,
        height: selectedSize?.height,
        article_id: articleId || undefined,
      });

      setGeneratedImage(image);

      // Poll for completion if status is generating
      if (image.status === "generating") {
        pollImageStatus(image.id);
      }
    } catch (err) {
      setError("Failed to generate image. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function pollImageStatus(imageId: string) {
    const maxAttempts = 30; // 30 attempts with 2s interval = 1 minute max
    let attempts = 0;

    const interval = setInterval(async () => {
      try {
        attempts++;
        const image = await api.images.get(imageId);

        if (image.status === "completed") {
          setGeneratedImage(image);
          clearInterval(interval);
        } else if (image.status === "failed" || attempts >= maxAttempts) {
          setError("Image generation failed or timed out");
          clearInterval(interval);
        }
      } catch (err) {
        console.error("Failed to poll image status:", err);
        clearInterval(interval);
      }
    }, 2000);
  }

  async function handleCopyUrl() {
    if (!generatedImage?.url) return;

    try {
      await navigator.clipboard.writeText(getImageUrl(generatedImage.url));
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    } catch (error) {
      console.error("Failed to copy URL:", error);
    }
  }

  function handleDownload() {
    if (!generatedImage?.url) return;

    const link = document.createElement("a");
    link.href = getImageUrl(generatedImage.url);
    link.download = `image-${generatedImage.id}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  function handleSaveAndReturn() {
    router.push("/images");
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/images">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-display font-bold text-text-primary">
            Generate Image
          </h1>
          <p className="text-text-secondary mt-1">
            Create AI-generated images for your content
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Generation Form */}
        <Card className="p-6">
          <form onSubmit={handleGenerate} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Image Prompt *
              </label>
              <textarea
                value={prompt}
                onChange={(e) => {
                  setPrompt(e.target.value);
                  setPromptSource("manual");
                }}
                placeholder="Describe the image you want to generate... (e.g., A serene meditation space with soft lighting and plants)"
                rows={4}
                className="w-full px-4 py-3 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all resize-none"
              />
              {promptSource === "article" ? (
                <p className="text-xs text-primary-600 mt-1.5">
                  Auto-generated from article — feel free to edit
                </p>
              ) : (
                <p className="text-xs text-text-muted mt-1.5">
                  Be specific and descriptive for best results
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Style
                </label>
                <select
                  value={style}
                  onChange={(e) => setStyle(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
                >
                  {IMAGE_STYLES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Size
                </label>
                <select
                  value={size}
                  onChange={(e) => setSize(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all"
                >
                  {IMAGE_SIZES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Link to Article (Optional)
              </label>
              <select
                value={articleId}
                onChange={(e) => setArticleId(e.target.value)}
                disabled={loadingArticles}
                className="w-full px-4 py-2.5 rounded-xl border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all disabled:opacity-50"
              >
                <option value="">None (standalone image)</option>
                {articles.map((article) => (
                  <option key={article.id} value={article.id}>
                    {article.title}
                  </option>
                ))}
              </select>
              {loadingArticles && (
                <p className="text-xs text-text-muted mt-1.5 flex items-center gap-1">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Loading articles...
                </p>
              )}
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generating Image...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Generate Image
                </>
              )}
            </Button>
          </form>

          {/* Tips */}
          <div className="mt-6 p-4 bg-primary-50 rounded-lg">
            <h4 className="text-sm font-medium text-primary-900 mb-2">
              Tips for better results:
            </h4>
            <ul className="text-xs text-primary-700 space-y-1">
              <li>• Be specific about colors, lighting, and composition</li>
              <li>• Mention the mood or atmosphere you want</li>
              <li>• Include details about style and artistic techniques</li>
              <li>• Avoid conflicting or contradictory descriptions</li>
            </ul>
          </div>
        </Card>

        {/* Preview */}
        <Card className="p-6">
          <h3 className="text-lg font-medium text-text-primary mb-4">
            Preview
          </h3>

          {loading || generatedImage?.status === "generating" ? (
            <AIGenerationProgress
              type="image"
              title={prompt.slice(0, 60)}
              isGenerating={loading || generatedImage?.status === "generating"}
            />
          ) : !generatedImage ? (
            <div className="aspect-square bg-surface-secondary rounded-xl flex items-center justify-center">
              <div className="text-center text-text-muted">
                <ImageIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">Your generated image will appear here</p>
              </div>
            </div>
          ) : generatedImage.status === "failed" ? (
            <div className="aspect-square bg-red-50 rounded-xl flex items-center justify-center border border-red-200">
              <div className="text-center text-red-600">
                <p className="text-sm font-medium">Generation failed</p>
                <p className="text-xs mt-1">Please try again with a different prompt</p>
              </div>
            </div>
          ) : (
            <>
              <div className="relative aspect-square bg-surface-secondary rounded-xl overflow-hidden mb-4">
                <Image
                  src={getImageUrl(generatedImage.url)}
                  alt={generatedImage.alt_text || generatedImage.prompt}
                  fill
                  className="object-contain"
                  sizes="(max-width: 1024px) 100vw, 50vw"
                />
              </div>

              {/* Success Message */}
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg mb-4 flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-green-900">
                    Image generated successfully!
                  </p>
                  <p className="text-xs text-green-700 mt-0.5">
                    {generatedImage.width}×{generatedImage.height} · {generatedImage.style}
                  </p>
                </div>
              </div>

              {/* Image Details */}
              <div className="space-y-3 mb-4">
                <div>
                  <label className="block text-xs font-medium text-text-muted mb-1">
                    Prompt
                  </label>
                  <p className="text-sm text-text-primary">
                    {generatedImage.prompt}
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-medium text-text-muted mb-1">
                    Image URL
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={getImageUrl(generatedImage.url)}
                      readOnly
                      className="flex-1 px-3 py-2 text-xs rounded-lg border border-surface-tertiary bg-surface-secondary"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleCopyUrl}
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                  {copiedUrl && (
                    <p className="text-xs text-green-600 mt-1">Copied to clipboard!</p>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  onClick={handleDownload}
                  className="flex-1"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download
                </Button>
                <Button
                  onClick={handleSaveAndReturn}
                  className="flex-1"
                >
                  <Save className="h-4 w-4 mr-2" />
                  Save to Gallery
                </Button>
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
