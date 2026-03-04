"use client";

import Link from "next/link";
import Image from "next/image";
import { Twitter, Linkedin, Link2 } from "lucide-react";
import { toast } from "sonner";
import type { BlogPostDetail } from "@/lib/api";

interface BlogPostClientProps {
  post: BlogPostDetail;
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function BlogPostClient({ post }: BlogPostClientProps) {
  const shareUrl = typeof window !== "undefined" ? window.location.href : `https://a-stats.app/en/blog/${post.slug}`;

  const copyLink = () => {
    navigator.clipboard.writeText(shareUrl).then(() => {
      toast.success("Link copied!");
    });
  };

  return (
    <article className="max-w-3xl mx-auto">
      {/* Breadcrumb */}
      <nav className="text-xs text-text-muted mb-6 flex items-center gap-1.5">
        <Link href="/" className="hover:text-text-secondary">Home</Link>
        <span>/</span>
        <Link href="/blog" className="hover:text-text-secondary">Blog</Link>
        {post.category && (
          <>
            <span>/</span>
            <Link href={`/blog/category/${post.category.slug}`} className="hover:text-text-secondary">
              {post.category.name}
            </Link>
          </>
        )}
        <span>/</span>
        <span className="text-text-secondary truncate max-w-[200px]">{post.title}</span>
      </nav>

      {/* Category + Tags */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        {post.category && (
          <Link
            href={`/blog/category/${post.category.slug}`}
            className="text-xs font-semibold uppercase tracking-wide text-primary-600 hover:text-primary-700"
          >
            {post.category.name}
          </Link>
        )}
        {post.tags.map(tag => (
          <span
            key={tag.id}
            className="px-2 py-0.5 text-xs bg-surface-secondary text-text-secondary rounded-full border border-surface-tertiary"
          >
            {tag.name}
          </span>
        ))}
      </div>

      {/* Title */}
      <h1 className="text-3xl md:text-4xl font-bold text-text-primary leading-tight mb-4">
        {post.title}
      </h1>

      {/* Meta */}
      <div className="flex flex-wrap items-center gap-4 text-sm text-text-muted mb-8 pb-6 border-b border-surface-tertiary">
        {post.author_name && (
          <span>By <strong className="text-text-secondary">{post.author_name}</strong></span>
        )}
        {post.published_at && <span>{formatDate(post.published_at)}</span>}
        <span>{post.reading_time_minutes} min read</span>
      </div>

      {/* Featured image */}
      {post.featured_image_url && (
        <div className="relative aspect-[16/9] rounded-2xl overflow-hidden mb-8 bg-surface-secondary">
          <Image
            src={post.featured_image_url}
            alt={post.featured_image_alt || post.title}
            fill
            className="object-cover"
            priority
            sizes="(max-width: 768px) 100vw, 768px"
          />
        </div>
      )}

      {/* Content */}
      {post.content_html && (
        <div
          className="prose prose-sm sm:prose max-w-none prose-headings:font-bold prose-a:text-primary-600 prose-a:no-underline hover:prose-a:underline"
          dangerouslySetInnerHTML={{ __html: post.content_html }}
        />
      )}

      {/* Social share */}
      <div className="mt-12 pt-8 border-t border-surface-tertiary">
        <p className="text-sm font-medium text-text-secondary mb-3">Share this post</p>
        <div className="flex items-center gap-3">
          <a
            href={`https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(post.title)}`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 px-3 py-2 border border-surface-tertiary rounded-lg text-sm text-text-secondary hover:bg-surface-secondary transition-colors"
          >
            <Twitter className="h-4 w-4" />
            X / Twitter
          </a>
          <a
            href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 px-3 py-2 border border-surface-tertiary rounded-lg text-sm text-text-secondary hover:bg-surface-secondary transition-colors"
          >
            <Linkedin className="h-4 w-4" />
            LinkedIn
          </a>
          <button
            onClick={copyLink}
            className="inline-flex items-center gap-2 px-3 py-2 border border-surface-tertiary rounded-lg text-sm text-text-secondary hover:bg-surface-secondary transition-colors"
          >
            <Link2 className="h-4 w-4" />
            Copy Link
          </button>
        </div>
      </div>
    </article>
  );
}
