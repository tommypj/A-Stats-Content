"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Plus,
  Image as ImageIcon,
  Loader2,
  MoreVertical,
  Trash2,
  CheckCircle2,
  XCircle,
  Clock,
  Download,
  Copy,
  ExternalLink,
  Sparkles,
  Globe,
} from "lucide-react";
import { api, getImageUrl, parseApiError, GeneratedImage } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { clsx } from "clsx";

const statusConfig = {
  generating: { label: "Generating", color: "bg-yellow-100 text-yellow-700", icon: Loader2 },
  completed: { label: "Completed", color: "bg-green-100 text-green-700", icon: CheckCircle2 },
  failed: { label: "Failed", color: "bg-red-100 text-red-700", icon: XCircle },
};

export default function ImagesPage() {
  const [images, setImages] = useState<GeneratedImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<GeneratedImage | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [wpConnected, setWpConnected] = useState(false);
  const [wpUploading, setWpUploading] = useState<string | null>(null);
  const [wpUploaded, setWpUploaded] = useState<Set<string>>(new Set());
  const [wpError, setWpError] = useState("");

  useEffect(() => {
    loadImages();
    checkWpConnection();
  }, []);

  async function loadImages() {
    try {
      setLoading(true);
      const response = await api.images.list({ page_size: 50 });
      setImages(response.items);
    } catch (error) {
      console.error("Failed to load images:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Are you sure you want to delete this image?")) return;

    try {
      await api.images.delete(id);
      setImages(images.filter((img) => img.id !== id));
    } catch (error) {
      console.error("Failed to delete image:", error);
    }
    setActiveMenu(null);
  }

  async function handleCopyUrl(url: string, id: string) {
    try {
      await navigator.clipboard.writeText(url);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (error) {
      console.error("Failed to copy URL:", error);
    }
    setActiveMenu(null);
  }

  function handleDownload(url: string, id: string) {
    const link = document.createElement("a");
    link.href = url;
    link.download = `image-${id}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setActiveMenu(null);
  }

  async function checkWpConnection() {
    try {
      const status = await api.wordpress.status();
      setWpConnected(status.is_connected);
    } catch {
      setWpConnected(false);
    }
  }

  async function handleSendToWordPress(image: GeneratedImage) {
    setWpError("");
    setWpUploading(image.id);
    setActiveMenu(null);
    try {
      await api.wordpress.uploadMedia({
        image_id: image.id,
        alt_text: image.alt_text || undefined,
      });
      setWpUploaded((prev) => new Set(prev).add(image.id));
    } catch (err) {
      setWpError(parseApiError(err).message);
      setTimeout(() => setWpError(""), 5000);
    } finally {
      setWpUploading(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-bold text-text-primary">
            Images
          </h1>
          <p className="text-text-secondary mt-1">
            Manage your AI-generated images
          </p>
        </div>
        <Link href="/images/generate">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Generate Image
          </Button>
        </Link>
      </div>

      {/* Images Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
        </div>
      ) : images.length === 0 ? (
        <Card className="p-12 text-center">
          <ImageIcon className="h-12 w-12 text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-medium text-text-primary mb-2">
            No images yet
          </h3>
          <p className="text-text-secondary mb-6">
            Generate your first AI image to get started
          </p>
          <Link href="/images/generate">
            <Button>
              <Sparkles className="h-4 w-4 mr-2" />
              Generate Image
            </Button>
          </Link>
        </Card>
      ) : (
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {images.map((image) => {
            const status = statusConfig[image.status as keyof typeof statusConfig];
            const StatusIcon = status?.icon;

            return (
              <Card key={image.id} className="overflow-hidden hover:shadow-md transition-shadow">
                {/* Image Thumbnail */}
                <div className="relative aspect-square bg-surface-secondary">
                  {image.status === "completed" && image.url ? (
                    <button
                      onClick={() => setSelectedImage(image)}
                      className="w-full h-full group cursor-pointer"
                    >
                      <Image
                        src={getImageUrl(image.url)}
                        alt={image.alt_text || image.prompt}
                        fill
                        className="object-cover group-hover:opacity-90 transition-opacity"
                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
                      />
                    </button>
                  ) : image.status === "generating" ? (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center">
                        <Loader2 className="h-8 w-8 animate-spin text-primary-500 mx-auto mb-2" />
                        <p className="text-sm text-text-muted">Generating...</p>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <XCircle className="h-8 w-8 text-red-500" />
                    </div>
                  )}

                  {/* Status Badge */}
                  {status && (
                    <div className="absolute top-2 left-2">
                      <span className={clsx("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium", status.color)}>
                        <StatusIcon className={clsx("h-3.5 w-3.5", image.status === "generating" && "animate-spin")} />
                        {status.label}
                      </span>
                    </div>
                  )}

                  {/* Actions Menu */}
                  {image.status === "completed" && (
                    <div className="absolute top-2 right-2">
                      <button
                        onClick={() => setActiveMenu(activeMenu === image.id ? null : image.id)}
                        className="p-1.5 rounded-lg bg-white/90 hover:bg-white shadow-sm backdrop-blur-sm"
                      >
                        <MoreVertical className="h-4 w-4 text-text-muted" />
                      </button>

                      {activeMenu === image.id && (
                        <>
                          <div className="fixed inset-0 z-40" onClick={() => setActiveMenu(null)} />
                          <div className="absolute right-0 mt-1 w-48 bg-white rounded-lg border border-surface-tertiary shadow-lg z-50">
                            <button
                              onClick={() => handleCopyUrl(getImageUrl(image.url), image.id)}
                              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary"
                            >
                              <Copy className="h-4 w-4" />
                              {copiedId === image.id ? "Copied!" : "Copy URL"}
                            </button>
                            <button
                              onClick={() => handleDownload(getImageUrl(image.url), image.id)}
                              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary"
                            >
                              <Download className="h-4 w-4" />
                              Download
                            </button>
                            <a
                              href={getImageUrl(image.url)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary"
                            >
                              <ExternalLink className="h-4 w-4" />
                              Open in New Tab
                            </a>
                            {wpConnected && (
                              <button
                                onClick={() => handleSendToWordPress(image)}
                                disabled={wpUploading === image.id || wpUploaded.has(image.id)}
                                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary disabled:opacity-50"
                              >
                                {wpUploading === image.id ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : wpUploaded.has(image.id) ? (
                                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                                ) : (
                                  <Globe className="h-4 w-4" />
                                )}
                                {wpUploaded.has(image.id) ? "Sent to WordPress" : "Send to WordPress"}
                              </button>
                            )}
                            <button
                              onClick={() => handleDelete(image.id)}
                              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 border-t border-surface-tertiary"
                            >
                              <Trash2 className="h-4 w-4" />
                              Delete
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* Image Details */}
                <div className="p-3">
                  <p className="text-sm text-text-primary line-clamp-2 mb-2">
                    {image.prompt}
                  </p>

                  <div className="flex items-center justify-between text-xs text-text-muted">
                    <div className="flex items-center gap-2">
                      {image.style && (
                        <span className="px-2 py-0.5 bg-surface-secondary rounded-md">
                          {image.style}
                        </span>
                      )}
                      {image.width && image.height && (
                        <span>
                          {image.width}×{image.height}
                        </span>
                      )}
                    </div>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {new Date(image.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Full Size Image Modal */}
      {selectedImage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80" onClick={() => setSelectedImage(null)} />
          <div className="relative bg-white rounded-2xl shadow-xl max-w-5xl w-full max-h-[90vh] overflow-auto">
            <div className="sticky top-0 bg-white border-b border-surface-tertiary p-4 flex items-center justify-between z-10">
              <div>
                <h3 className="font-medium text-text-primary">Generated Image</h3>
                <p className="text-sm text-text-secondary mt-0.5">
                  {selectedImage.width}×{selectedImage.height} · {selectedImage.style}
                </p>
              </div>
              <button
                onClick={() => setSelectedImage(null)}
                className="p-2 rounded-lg hover:bg-surface-secondary"
              >
                <XCircle className="h-5 w-5 text-text-muted" />
              </button>
            </div>

            <div className="p-6">
              <div className="relative w-full" style={{ aspectRatio: `${selectedImage.width}/${selectedImage.height}` }}>
                <Image
                  src={getImageUrl(selectedImage.url)}
                  alt={selectedImage.alt_text || selectedImage.prompt}
                  fill
                  className="object-contain"
                  sizes="90vw"
                />
              </div>

              <div className="mt-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1">
                    Prompt
                  </label>
                  <p className="text-text-primary">
                    {selectedImage.prompt}
                  </p>
                </div>

                {selectedImage.alt_text && (
                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-1">
                      Alt Text
                    </label>
                    <p className="text-text-primary">
                      {selectedImage.alt_text}
                    </p>
                  </div>
                )}

                <div className="flex flex-wrap gap-3 pt-4">
                  <Button
                    variant="outline"
                    onClick={() => handleCopyUrl(getImageUrl(selectedImage.url), selectedImage.id)}
                    className="flex-1"
                  >
                    <Copy className="h-4 w-4 mr-2" />
                    {copiedId === selectedImage.id ? "Copied!" : "Copy URL"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => handleDownload(getImageUrl(selectedImage.url), selectedImage.id)}
                    className="flex-1"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download
                  </Button>
                  {wpConnected && (
                    <Button
                      variant="outline"
                      onClick={() => handleSendToWordPress(selectedImage)}
                      disabled={wpUploading === selectedImage.id || wpUploaded.has(selectedImage.id)}
                      className="flex-1"
                    >
                      {wpUploading === selectedImage.id ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      ) : wpUploaded.has(selectedImage.id) ? (
                        <CheckCircle2 className="h-4 w-4 text-green-600 mr-2" />
                      ) : (
                        <Globe className="h-4 w-4 mr-2" />
                      )}
                      {wpUploaded.has(selectedImage.id) ? "Sent!" : "Send to WordPress"}
                    </Button>
                  )}
                </div>
                {wpError && (
                  <p className="text-sm text-red-600 mt-2">{wpError}</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
