"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
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

  return (
    <div>
      {/* Category filter pills */}
      {categories.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-8">
          <button
            onClick={() => handleCategoryChange("")}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              !activeCategory
                ? "bg-primary-600 text-white"
                : "bg-surface border border-surface-tertiary text-text-secondary hover:border-primary-400"
            }`}
          >
            All
          </button>
          {categories.map(cat => (
            <button
              key={cat.id}
              onClick={() => handleCategoryChange(cat.slug)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                activeCategory === cat.slug
                  ? "bg-primary-600 text-white"
                  : "bg-surface border border-surface-tertiary text-text-secondary hover:border-primary-400"
              }`}
            >
              {cat.name}
              {cat.post_count > 0 && (
                <span className="ml-1.5 text-xs opacity-70">({cat.post_count})</span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Posts grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-surface border border-surface-tertiary rounded-2xl overflow-hidden animate-pulse">
              <div className="aspect-[16/9] bg-surface-secondary" />
              <div className="p-5 space-y-3">
                <div className="h-4 bg-surface-secondary rounded w-1/3" />
                <div className="h-6 bg-surface-secondary rounded w-full" />
                <div className="h-4 bg-surface-secondary rounded w-5/6" />
              </div>
            </div>
          ))}
        </div>
      ) : posts.length === 0 ? (
        <div className="py-20 text-center">
          <p className="text-text-secondary text-lg">No posts found.</p>
          {activeCategory && (
            <button
              onClick={() => handleCategoryChange("")}
              className="mt-4 text-primary-600 hover:text-primary-700 text-sm font-medium"
            >
              View all posts →
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {posts.map(post => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-12">
          <button
            onClick={() => loadPosts(page - 1, activeCategory)}
            disabled={page === 1 || loading}
            className="inline-flex items-center gap-2 px-4 py-2 border border-surface-tertiary rounded-lg text-sm disabled:opacity-40 hover:bg-surface-secondary transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </button>
          <span className="text-sm text-text-secondary">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => loadPosts(page + 1, activeCategory)}
            disabled={page === totalPages || loading}
            className="inline-flex items-center gap-2 px-4 py-2 border border-surface-tertiary rounded-lg text-sm disabled:opacity-40 hover:bg-surface-secondary transition-colors"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}
