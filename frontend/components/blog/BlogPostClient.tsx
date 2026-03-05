"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import { Twitter, Linkedin, Facebook, Link2, Calendar, Clock, Mail, List } from "lucide-react";
import { toast } from "sonner";
import type { BlogPostCard, BlogPostDetail } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface BlogPostClientProps {
  post: BlogPostDetail;
  relatedPosts?: BlogPostCard[];
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function authorInitial(name: string | undefined): string {
  return (name || "A")[0].toUpperCase();
}

// ---------------------------------------------------------------------------
// Table of Contents helpers
// ---------------------------------------------------------------------------
interface TocHeading {
  id: string;
  text: string;
  level: 2 | 3;
}

function extractHeadings(html: string): TocHeading[] {
  const headings: TocHeading[] = [];
  const seen = new Map<string, number>();
  const regex = /<h([23])[^>]*>([\s\S]*?)<\/h[23]>/gi;
  let match;
  while ((match = regex.exec(html)) !== null) {
    const level = parseInt(match[1]) as 2 | 3;
    const text = match[2].replace(/<[^>]+>/g, "").trim();
    if (!text) continue;
    let id = text
      .toLowerCase()
      .replace(/[^\w\s-]/g, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-")
      .slice(0, 80);
    // deduplicate
    const count = seen.get(id) ?? 0;
    seen.set(id, count + 1);
    if (count > 0) id = `${id}-${count}`;
    headings.push({ id, text, level });
  }
  return headings;
}

function injectHeadingIds(html: string, headings: TocHeading[]): string {
  let idx = 0;
  return html.replace(/<h([23])([^>]*)>([\s\S]*?)<\/h[23]>/gi, (_, level, attrs, content) => {
    if (idx >= headings.length) return _;
    const { id } = headings[idx++];
    // Don't double-inject if id already present
    if (/\bid=/.test(attrs)) return _;
    return `<h${level}${attrs} id="${id}">${content}</h${level}>`;
  });
}

// ---------------------------------------------------------------------------
// Share button
// ---------------------------------------------------------------------------
function ShareButton({
  href,
  label,
  onClick,
  children,
}: {
  href?: string;
  label: string;
  onClick?: () => void;
  children: React.ReactNode;
}) {
  const cls =
    "h-10 w-10 rounded-full border border-surface-tertiary flex items-center justify-center text-text-secondary hover:border-primary-500 hover:text-primary-600 hover:bg-primary-50 transition-all duration-150";

  if (href) {
    return (
      <a href={href} target="_blank" rel="noreferrer" aria-label={label} className={cls}>
        {children}
      </a>
    );
  }
  return (
    <button onClick={onClick} aria-label={label} className={cls}>
      {children}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Related post item
// ---------------------------------------------------------------------------
function RelatedPostItem({ post }: { post: BlogPostCard }) {
  return (
    <Link href={`/blog/${post.slug}`} className="flex items-start gap-3 group">
      <div className="relative w-16 h-16 rounded-xl overflow-hidden flex-shrink-0 bg-surface-secondary">
        {post.featured_image_url ? (
          <Image
            src={post.featured_image_url}
            alt={post.featured_image_alt || post.title}
            fill
            className="object-cover group-hover:scale-105 transition-transform duration-200"
            sizes="64px"
          />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center">
            <span className="text-primary-300 font-bold text-lg">A</span>
          </div>
        )}
      </div>
      <div className="flex-1 min-w-0">
        {post.published_at && (
          <p className="flex items-center gap-1 text-[11px] text-text-muted mb-1">
            <Calendar className="h-3 w-3" />
            {formatDate(post.published_at)}
          </p>
        )}
        <p className="text-sm font-semibold text-text-primary group-hover:text-primary-600 transition-colors line-clamp-2 leading-snug">
          {post.title}
        </p>
      </div>
    </Link>
  );
}

// ---------------------------------------------------------------------------
// Tag pill
// ---------------------------------------------------------------------------
function TagPill({ name }: { name: string }) {
  return (
    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-surface-secondary text-text-secondary border border-surface-tertiary hover:border-primary-400 hover:text-primary-600 transition-colors cursor-default">
      {name}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Table of Contents component
// ---------------------------------------------------------------------------
function TableOfContents({ headings }: { headings: TocHeading[] }) {
  const [open, setOpen] = useState(false);

  if (headings.length < 2) return null;

  return (
    <>
      {/* Desktop — in sidebar (rendered there) */}
      {/* Mobile — collapsible above article */}
      <div className="lg:hidden mb-8 border border-surface-tertiary rounded-xl overflow-hidden">
        <button
          onClick={() => setOpen(v => !v)}
          className="w-full flex items-center justify-between px-4 py-3 bg-surface-secondary text-sm font-semibold text-text-primary"
        >
          <span className="flex items-center gap-2"><List className="h-4 w-4" /> Table of Contents</span>
          <span className="text-text-muted text-xs">{open ? "▲" : "▼"}</span>
        </button>
        {open && (
          <nav className="px-4 py-3 space-y-2">
            {headings.map((h) => (
              <a
                key={h.id}
                href={`#${h.id}`}
                onClick={() => setOpen(false)}
                className={`block text-sm text-text-secondary hover:text-primary-600 transition-colors leading-snug ${
                  h.level === 3 ? "pl-4 text-xs" : ""
                }`}
              >
                {h.text}
              </a>
            ))}
          </nav>
        )}
      </div>
    </>
  );
}

function TableOfContentsSidebar({ headings }: { headings: TocHeading[] }) {
  if (headings.length < 2) return null;
  return (
    <div className="bg-surface border border-surface-tertiary rounded-2xl p-5">
      <h3 className="text-sm font-bold text-text-primary mb-3 flex items-center gap-2">
        <List className="h-4 w-4" /> Table of Contents
      </h3>
      <nav className="space-y-2">
        {headings.map((h) => (
          <a
            key={h.id}
            href={`#${h.id}`}
            className={`block text-sm text-text-secondary hover:text-primary-600 transition-colors leading-snug ${
              h.level === 3 ? "pl-3 text-xs text-text-muted" : "font-medium"
            }`}
          >
            {h.text}
          </a>
        ))}
      </nav>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function BlogPostClient({ post, relatedPosts: initialRelated = [] }: BlogPostClientProps) {
  const [shareUrl, setShareUrl] = useState(`https://a-stats.app/en/blog/${post.slug}`);
  const [relatedPosts, setRelatedPosts] = useState<BlogPostCard[]>(initialRelated);

  useEffect(() => {
    setShareUrl(window.location.href);
  }, []);

  // Client-side fetch of related posts if none passed from server
  useEffect(() => {
    if (initialRelated.length > 0) return;
    if (!post.category?.slug) return;
    fetch(
      `${API_URL}/api/v1/blog/posts?category_slug=${encodeURIComponent(post.category.slug)}&page_size=4`
    )
      .then((r) => r.json())
      .then((data) => {
        const filtered = (data.items as BlogPostCard[])
          .filter((p) => p.slug !== post.slug)
          .slice(0, 3);
        setRelatedPosts(filtered);
      })
      .catch(() => {});
  }, [post.slug, post.category?.slug, initialRelated.length]);

  const copyLink = () => {
    navigator.clipboard.writeText(shareUrl).then(() => toast.success("Link copied!"));
  };

  // Extract headings and inject IDs into content
  const { processedHtml, headings } = useMemo(() => {
    if (!post.content_html) return { processedHtml: "", headings: [] };
    const extracted = extractHeadings(post.content_html);
    return {
      processedHtml: injectHeadingIds(post.content_html, extracted),
      headings: extracted,
    };
  }, [post.content_html]);

  return (
    <div className="flex gap-12">
      {/* ================================================================
          LEFT — Article (flex-1)
          ================================================================ */}
      <article className="flex-1 min-w-0">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 text-xs text-text-muted mb-6 flex-wrap">
          <Link href="/" className="hover:text-primary-600 transition-colors">Home</Link>
          <span>•</span>
          <Link href="/blog" className="hover:text-primary-600 transition-colors">Our Blogs</Link>
          {post.category && (
            <>
              <span>•</span>
              <Link
                href={`/blog/category/${post.category.slug}`}
                className="hover:text-primary-600 transition-colors"
              >
                {post.category.name}
              </Link>
            </>
          )}
        </nav>

        {/* Category badge */}
        {post.category && (
          <div className="mb-4">
            <Link
              href={`/blog/category/${post.category.slug}`}
              className="inline-flex items-center px-3 py-1 rounded-full bg-primary-50 text-primary-700 text-xs font-semibold border border-primary-100 hover:bg-primary-100 transition-colors"
            >
              {post.category.name}
            </Link>
          </div>
        )}

        {/* Title */}
        <h1 className="text-3xl md:text-4xl font-bold text-text-primary leading-tight mb-6">
          {post.title}
        </h1>

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-text-muted mb-8 pb-6 border-b border-surface-tertiary">
          {post.author_name && (
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center flex-shrink-0 shadow-sm">
                <span className="text-white text-xs font-bold">{authorInitial(post.author_name)}</span>
              </div>
              <span className="font-medium text-text-secondary">{post.author_name}</span>
            </div>
          )}
          {post.category && (
            <span className="hidden sm:inline px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-50 text-primary-700 border border-primary-100">
              {post.category.name}
            </span>
          )}
          <span className="flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" />
            {post.reading_time_minutes} min read
          </span>
          {post.published_at && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {formatDate(post.published_at)}
            </span>
          )}
          {post.updated_at && post.updated_at !== post.published_at && (
            <span className="flex items-center gap-1 text-text-muted/70 italic text-xs">
              Updated {formatDate(post.updated_at)}
            </span>
          )}
        </div>

        {/* Hero image — full width below meta */}
        {post.featured_image_url && (
          <div className="w-full mb-10">
            <div className="relative w-full overflow-hidden rounded-2xl bg-surface-secondary">
              <Image
                src={post.featured_image_url}
                alt={post.featured_image_alt || post.title}
                width={1200}
                height={630}
                className="w-full object-cover max-h-[480px]"
                priority
                sizes="(max-width: 768px) 100vw, (max-width: 1200px) 65vw, 760px"
              />
            </div>
          </div>
        )}

        {/* Mobile ToC */}
        <TableOfContents headings={headings} />

        {/* Article body */}
        {processedHtml && (
          <div
            className="prose prose-lg max-w-none
              prose-headings:font-bold prose-headings:text-text-primary
              prose-h2:text-2xl prose-h2:mt-10 prose-h2:mb-4
              prose-h3:text-xl prose-h3:mt-8 prose-h3:mb-3
              prose-p:text-text-secondary prose-p:leading-relaxed prose-p:mb-4
              prose-a:text-primary-600 prose-a:no-underline hover:prose-a:underline
              prose-strong:text-text-primary
              prose-li:text-text-secondary
              prose-blockquote:border-l-4 prose-blockquote:border-primary-500
              prose-blockquote:bg-primary-50 prose-blockquote:px-6 prose-blockquote:py-4
              prose-blockquote:rounded-r-xl prose-blockquote:not-italic
              prose-img:rounded-xl prose-img:shadow-md
              prose-code:bg-surface-secondary prose-code:text-primary-700 prose-code:px-1.5 prose-code:rounded prose-code:text-sm"
            dangerouslySetInnerHTML={{ __html: processedHtml }}
          />
        )}

        {/* Tags — mobile (below content) */}
        {post.tags.length > 0 && (
          <div className="lg:hidden mt-10 pt-6 border-t border-surface-tertiary">
            <p className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-3">Tags</p>
            <div className="flex flex-wrap gap-2">
              {post.tags.map((tag) => <TagPill key={tag.id} name={tag.name} />)}
            </div>
          </div>
        )}
      </article>

      {/* ================================================================
          RIGHT — Sticky Sidebar (~320px)
          ================================================================ */}
      <aside className="hidden lg:block w-80 flex-shrink-0">
        <div className="sticky top-8 space-y-6">

          {/* Table of Contents */}
          <TableOfContentsSidebar headings={headings} />

          {/* Share on Social Media */}
          <div className="bg-surface border border-surface-tertiary rounded-2xl p-5">
            <h3 className="text-sm font-bold text-text-primary mb-4">Share on Social Media</h3>
            <div className="flex items-center gap-3 flex-wrap">
              <ShareButton
                href={`https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(post.title)}`}
                label="Share on X / Twitter"
              >
                <Twitter className="h-4 w-4" />
              </ShareButton>
              <ShareButton
                href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`}
                label="Share on LinkedIn"
              >
                <Linkedin className="h-4 w-4" />
              </ShareButton>
              <ShareButton
                href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`}
                label="Share on Facebook"
              >
                <Facebook className="h-4 w-4" />
              </ShareButton>
              <ShareButton
                href={`mailto:?subject=${encodeURIComponent(post.title)}&body=${encodeURIComponent(shareUrl)}`}
                label="Share via email"
              >
                <Mail className="h-4 w-4" />
              </ShareButton>
              <ShareButton onClick={copyLink} label="Copy link">
                <Link2 className="h-4 w-4" />
              </ShareButton>
            </div>
          </div>

          {/* All Tags */}
          {post.tags.length > 0 && (
            <div className="bg-surface border border-surface-tertiary rounded-2xl p-5">
              <h3 className="text-sm font-bold text-text-primary mb-4">All Tags</h3>
              <div className="flex flex-wrap gap-2">
                {post.tags.map((tag) => <TagPill key={tag.id} name={tag.name} />)}
              </div>
            </div>
          )}

          {/* Related Blogs */}
          {relatedPosts.length > 0 && (
            <section aria-labelledby="related-posts-heading">
              <div className="bg-surface border border-surface-tertiary rounded-2xl p-5">
                <h3 id="related-posts-heading" className="text-sm font-bold text-text-primary mb-4">Related Blogs</h3>
                <div className="space-y-4">
                  {relatedPosts.map((related) => (
                    <RelatedPostItem key={related.id} post={related} />
                  ))}
                </div>
              </div>
            </section>
          )}

        </div>
      </aside>
    </div>
  );
}
