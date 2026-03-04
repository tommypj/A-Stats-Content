import type { Metadata } from "next";
import { Suspense } from "react";
import BlogListClient from "@/components/blog/BlogListClient";
import type { BlogCategory, BlogPostCard } from "@/lib/api";

export const revalidate = 60;

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchPosts(page = 1): Promise<{
  items: BlogPostCard[];
  total: number;
  total_pages: number;
}> {
  try {
    const res = await fetch(`${API_URL}/api/v1/blog/posts?page=${page}&page_size=12`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return { items: [], total: 0, total_pages: 1 };
    return res.json();
  } catch {
    return { items: [], total: 0, total_pages: 1 };
  }
}

async function fetchCategories(): Promise<BlogCategory[]> {
  try {
    const res = await fetch(`${API_URL}/api/v1/blog/categories`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: "Blog — A-Stats | SEO & AEO Content Insights",
    description:
      "Expert guides on SEO, AEO, AI content, and content marketing. Learn how to rank on Google and get cited by AI answer engines.",
    openGraph: {
      title: "A-Stats Blog",
      description: "Expert guides on SEO, AEO, AI content, and content marketing.",
      url: "https://a-stats.app/en/blog",
      type: "website",
    },
    alternates: {
      types: {
        "application/rss+xml": `${API_URL}/api/v1/blog/feed.xml`,
      },
    },
  };
}

export default async function BlogPage() {
  const [postsData, categories] = await Promise.all([fetchPosts(), fetchCategories()]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-text-primary mb-4">
            A-Stats Blog
          </h1>
          <p className="text-lg text-text-secondary max-w-2xl mx-auto">
            Expert insights on SEO, AEO, AI content generation, and content marketing strategy.
          </p>
        </div>

        <Suspense fallback={<div className="py-12 text-center text-text-secondary">Loading posts...</div>}>
          <BlogListClient
            initialPosts={postsData.items}
            initialTotal={postsData.total}
            initialPage={1}
            categories={categories}
            totalPages={postsData.total_pages}
          />
        </Suspense>
    </div>
  );
}
