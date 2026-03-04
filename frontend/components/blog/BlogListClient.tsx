"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { ChevronLeft, ChevronRight, Calendar, Clock, ArrowRight } from "lucide-react";
import PostCard from "./PostCard";
import type { BlogPostCard, BlogCategory } from "@/lib/api";

interface BlogListClientProps {
  initialPosts: BlogPostCard[];
  initialTotal: number;
  initialPage: number;
  categories: BlogCategory[];
  categorySlug?: string;
  totalPages: number;
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function FeaturedPostCard({ post }: { post: BlogPostCard }) {
  return (
    <article className="group bg-surface border border-surface-tertiary rounded-2xl overflow-hidden hover:shadow-xl transition-all duration-300 mb-10">
      <div className="grid grid-cols-1 md:grid-cols-[3fr_2fr] min-h-[360px]">
        {/* Image */}
        <Link
          href={`/blog/${post.slug}`}
          className="relative overflow-hidden block min-h-[240px] md:min-h-full bg-surface-secondary"
        >
          {post.featured_image_url ? (
            <Image
              src={post.featured_image_url}
              alt={post.featured_image_alt || post.title}
              fill
              className="object-cover group-hover:scale-105 transition-transform duration-500"
              sizes="(max-width: 768px) 100vw, 60vw"
              priority
            />
          ) : (
            <div className="absolute inset-0 bg-gradient-to-br from-primary-100 to-primary-200 flex items-center justify-center">
              <span className="text-primary-400 text-7xl font-bold">A</span>
            </div>
          )}
          {/* Featured label */}
          <span className="absolute top-4 left-4 px-3 py-1 bg-primary-600 text-white text-xs font-bold rounded-full tracking-wide uppercase">
            Featured
          </span>
          {post.category && (
            <span className="absolute top-4 left-[110px] px-3 py-1 bg-white/90 text-primary-700 text-xs font-semibold rounded-full">
              {post.category.name}
            </span>
          )}
        </Link>

        {/* Content */}
        <div className="flex flex-col justify-between p-8">
          <div>
            <Link href={`/blog/${post.slug}`}>
              <h2 className="text-2xl font-bold text-text-primary leading-tight mb-4 group-hover:text-primary-600 transition-colors line-clamp-3">
                {post.title}
              </h2>
            </Link>
            {post.excerpt && (
              <p className="text-sm text-text-secondary leading-relaxed line-clamp-3 mb-6">
                {post.excerpt}
              </p>
            )}
          </div>

          {/* Meta + CTA */}
          <div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-text-muted mb-5">
              <div className="flex items-center gap-1.5">
                <div className="h-6 w-6 rounded-full bg-primary-100 flex items-center justify-center">
                  <span className="text-primary-700 text-[10px] font-bold uppercase">
                    {(post.author_name || "A")[0]}
                  </span>
                </div>
                <span className="font-medium text-text-secondary">{post.author_name || "A-Stats Team"}</span>
              </div>
              {post.published_at && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  {formatDate(post.published_at)}
                </span>
              )}
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {post.reading_time_minutes} min read
              </span>
            </div>

            <Link
              href={`/blog/${post.slug}`}
              className="inline-flex items-center gap-2 text-sm font-semibold text-primary-600 hover:text-primary-700 group/link"
            >
              Read article
              <ArrowRight className="h-4 w-4 group-hover/link:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>
      </div>
    </article>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-surface border border-surface-tertiary rounded-2xl overflow-hidden animate-pulse">
      <div className="aspect-[16/9] bg-surface-secondary" />
      <div className="p-5 space-y-3">
        <div className="h-3 bg-surface-secondary rounded-full w-1/4" />
        <div className="h-5 bg-surface-secondary rounded w-full" />
        <div className="h-5 bg-surface-secondary rounded w-4/5" />
        <div className="h-3 bg-surface-secondary rounded-full w-1/2 mt-4" />
      </div>
    </div>
  );
}

export default function BlogListClient({
  initialPosts,
  initialTotal,
  initialPage,
  categories,
  categorySlug,
  totalPages: initialTotalPages,
}: BlogListClientProps) {
  const router = useRouter();

  const [posts, setPosts] = useState<BlogPostCard[]>(initialPosts);
  const [total, setTotal] = useState(initialTotal);
  const [page, setPage] = useState(initialPage);
  const [totalPages, setTotalPages] = useState(initialTotalPages);
  const [loading, setLoading] = useState(false);
  const [activeCategory, setActiveCategory] = useState(categorySlug || "");

  const loadPosts = useCallback(async (p: number, cat: string) => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.set("page", String(p));
      params.set("page_size", "12");
      if (cat) params.set("category_slug", cat);

      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/blog/posts?${params.toString()}`);
      if (!res.ok) return;
      const data = await res.json();
      setPosts(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
      setPage(p);
    } catch {
      // silently fail — show existing posts
    } finally {
      setLoading(false);
    }
  }, []);

  const handleCategoryChange = (slug: string) => {
    setActiveCategory(slug);
    loadPosts(1, slug);
    if (slug) {
      router.push(`/blog/category/${slug}`);
    } else {
      router.push("/blog");
    }
  };

  const [featured, ...rest] = posts;

  return (
    <div>
      {/* Category filter pills */}
      {categories.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-10">
          <button
            onClick={() => handleCategoryChange("")}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-150 ${
              !activeCategory
                ? "bg-primary-600 text-white shadow-sm"
                : "bg-surface border border-surface-tertiary text-text-secondary hover:border-primary-400 hover:text-primary-600"
            }`}
          >
            All Posts
          </button>
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => handleCategoryChange(cat.slug)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-150 ${
                activeCategory === cat.slug
                  ? "bg-primary-600 text-white shadow-sm"
                  : "bg-surface border border-surface-tertiary text-text-secondary hover:border-primary-400 hover:text-primary-600"
              }`}
            >
              {cat.name}
              {cat.post_count > 0 && (
                <span className="ml-1.5 opacity-60">({cat.post_count})</span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Posts */}
      {loading ? (
        <div>
          {/* Featured skeleton */}
          <div className="bg-surface border border-surface-tertiary rounded-2xl overflow-hidden mb-10 animate-pulse">
            <div className="grid grid-cols-1 md:grid-cols-[3fr_2fr] min-h-[360px]">
              <div className="bg-surface-secondary min-h-[240px]" />
              <div className="p-8 space-y-4">
                <div className="h-6 bg-surface-secondary rounded w-5/6" />
                <div className="h-6 bg-surface-secondary rounded w-4/6" />
                <div className="h-4 bg-surface-secondary rounded w-full mt-2" />
                <div className="h-4 bg-surface-secondary rounded w-3/4" />
              </div>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        </div>
      ) : posts.length === 0 ? (
        <div className="py-24 text-center">
          <p className="text-text-secondary text-lg mb-2">No posts found</p>
          {activeCategory && (
            <button
              onClick={() => handleCategoryChange("")}
              className="mt-3 text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              ← View all posts
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Featured first post */}
          {featured && page === 1 && <FeaturedPostCard post={featured} />}

          {/* Grid of remaining posts */}
          {rest.length > 0 && (
            <>
              {page === 1 && rest.length > 0 && (
                <h2 className="text-base font-semibold text-text-secondary uppercase tracking-wider mb-6">
                  Latest Posts
                </h2>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {(page === 1 ? rest : posts).map((post) => (
                  <PostCard key={post.id} post={post} />
                ))}
              </div>
            </>
          )}

          {/* Total count */}
          <p className="text-xs text-text-muted text-center mt-8">
            Showing {posts.length} of {total} posts
          </p>
        </>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-12">
          <button
            onClick={() => loadPosts(page - 1, activeCategory)}
            disabled={page === 1 || loading}
            className="inline-flex items-center gap-2 px-4 py-2 border border-surface-tertiary rounded-xl text-sm font-medium disabled:opacity-40 hover:bg-surface-secondary transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </button>
          <span className="text-sm text-text-secondary tabular-nums">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => loadPosts(page + 1, activeCategory)}
            disabled={page === totalPages || loading}
            className="inline-flex items-center gap-2 px-4 py-2 border border-surface-tertiary rounded-xl text-sm font-medium disabled:opacity-40 hover:bg-surface-secondary transition-colors"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}
