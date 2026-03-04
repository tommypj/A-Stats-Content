import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import BlogListClient from "@/components/blog/BlogListClient";
import type { BlogCategory, BlogPostCard } from "@/lib/api";

export const revalidate = 120;

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchCategory(slug: string): Promise<BlogCategory | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/blog/categories`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    const cats: BlogCategory[] = await res.json();
    return cats.find(c => c.slug === slug) || null;
  } catch {
    return null;
  }
}

async function fetchPostsByCategory(slug: string): Promise<{
  items: BlogPostCard[];
  total: number;
  total_pages: number;
}> {
  try {
    const res = await fetch(
      `${API_URL}/api/v1/blog/posts?page=1&page_size=12&category_slug=${encodeURIComponent(slug)}`,
      { next: { revalidate: 120 } }
    );
    if (!res.ok) return { items: [], total: 0, total_pages: 1 };
    return res.json();
  } catch {
    return { items: [], total: 0, total_pages: 1 };
  }
}

async function fetchAllCategories(): Promise<BlogCategory[]> {
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

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const category = await fetchCategory(slug);
  if (!category) return { title: "Category Not Found — A-Stats Blog" };

  return {
    title: `${category.name} — A-Stats Blog`,
    description:
      category.description ||
      `Browse all ${category.name} articles on the A-Stats blog.`,
    openGraph: {
      title: `${category.name} — A-Stats Blog`,
      url: `https://a-stats.app/en/blog/category/${slug}`,
    },
  };
}

export default async function BlogCategoryPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  const [category, postsData, allCategories] = await Promise.all([
    fetchCategory(slug),
    fetchPostsByCategory(slug),
    fetchAllCategories(),
  ]);

  if (!category) {
    notFound();
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Header */}
        <div className="text-center mb-12">
          <p className="text-sm font-semibold uppercase tracking-wide text-primary-600 mb-2">Category</p>
          <h1 className="text-4xl md:text-5xl font-bold text-text-primary mb-4">
            {category.name}
          </h1>
          {category.description && (
            <p className="text-lg text-text-secondary max-w-2xl mx-auto">
              {category.description}
            </p>
          )}
          <p className="text-sm text-text-muted mt-2">{category.post_count} posts</p>
        </div>

        <Suspense fallback={<div className="py-12 text-center text-text-secondary">Loading posts...</div>}>
          <BlogListClient
            initialPosts={postsData.items}
            initialTotal={postsData.total}
            initialPage={1}
            categories={allCategories}
            categorySlug={slug}
            totalPages={postsData.total_pages}
          />
        </Suspense>
    </div>
  );
}
