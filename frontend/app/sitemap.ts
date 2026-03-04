import { MetadataRoute } from "next";
import { DOC_CATEGORIES } from "@/lib/docs";

const baseUrl = "https://a-stats.app";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchBlogPosts(): Promise<Array<{ slug: string; updated_at?: string }>> {
  try {
    // Fetch up to 500 published posts for the sitemap
    const res = await fetch(`${API_URL}/api/v1/blog/posts?page=1&page_size=500`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.items || [];
  } catch {
    return [];
  }
}

async function fetchBlogCategories(): Promise<Array<{ slug: string }>> {
  try {
    const res = await fetch(`${API_URL}/api/v1/blog/categories`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [posts, categories] = await Promise.all([
    fetchBlogPosts(),
    fetchBlogCategories(),
  ]);

  const staticRoutes: MetadataRoute.Sitemap = [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${baseUrl}/register`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.9,
    },
    {
      url: `${baseUrl}/login`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.5,
    },
    {
      url: `${baseUrl}/legal/privacy`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.3,
    },
    {
      url: `${baseUrl}/legal/terms`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.3,
    },
    {
      url: `${baseUrl}/legal/cookies`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.2,
    },
    // Blog index
    {
      url: `${baseUrl}/en/blog`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.8,
    },
  ];

  const categoryRoutes: MetadataRoute.Sitemap = categories.map(cat => ({
    url: `${baseUrl}/en/blog/category/${cat.slug}`,
    lastModified: new Date(),
    changeFrequency: "weekly" as const,
    priority: 0.6,
  }));

  const postRoutes: MetadataRoute.Sitemap = posts.map(post => ({
    url: `${baseUrl}/en/blog/${post.slug}`,
    lastModified: post.updated_at ? new Date(post.updated_at) : new Date(),
    changeFrequency: "monthly" as const,
    priority: 0.7,
  }));

  // Documentation routes
  const docsIndexRoute: MetadataRoute.Sitemap = [
    {
      url: `${baseUrl}/en/docs`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.8,
    },
  ];

  const docsCategoryRoutes: MetadataRoute.Sitemap = DOC_CATEGORIES.map(cat => ({
    url: `${baseUrl}/en/docs/${cat.slug}`,
    lastModified: new Date(),
    changeFrequency: "weekly" as const,
    priority: 0.6,
  }));

  const docsArticleRoutes: MetadataRoute.Sitemap = DOC_CATEGORIES.flatMap(cat =>
    cat.articles.map(article => ({
      url: `${baseUrl}/en/docs/${cat.slug}/${article.slug}`,
      lastModified: new Date(),
      changeFrequency: "monthly" as const,
      priority: 0.7,
    }))
  );

  return [...staticRoutes, ...docsIndexRoute, ...docsCategoryRoutes, ...docsArticleRoutes, ...categoryRoutes, ...postRoutes];
}
