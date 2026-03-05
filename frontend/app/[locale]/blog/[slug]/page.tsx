import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import BlogPostClient from "@/components/blog/BlogPostClient";
import type { BlogPostCard, BlogPostDetail } from "@/lib/api";

export const revalidate = 300;

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchRelatedPosts(categorySlug: string | undefined, excludeSlug: string): Promise<BlogPostCard[]> {
  try {
    const params = new URLSearchParams({ page_size: "3" });
    if (categorySlug) params.set("category_slug", categorySlug);
    const res = await fetch(`${API_URL}/api/v1/blog/posts?${params}`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.items as BlogPostCard[]).filter((p) => p.slug !== excludeSlug);
  } catch {
    return [];
  }
}

async function fetchPost(slug: string): Promise<BlogPostDetail | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/blog/posts/${slug}`, {
      next: { revalidate: 300 },
    });
    if (res.status === 404) return null;
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string; locale: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = await fetchPost(slug);
  if (!post) {
    return { title: "Post Not Found — A-Stats Blog" };
  }

  const title = post.meta_title || post.title;
  const description = post.meta_description || post.excerpt || undefined;
  const imageUrl = post.og_image_url || post.featured_image_url;
  const canonical = `https://a-stats.app/en/blog/${post.slug}`;

  return {
    title: `${title} — A-Stats Blog`,
    description,
    openGraph: {
      title,
      description,
      url: canonical,
      type: "article",
      siteName: "A-Stats",
      publishedTime: post.published_at,
      modifiedTime: post.updated_at || post.published_at,
      authors: post.author_name ? [post.author_name] : undefined,
      images: imageUrl
        ? [{ url: imageUrl, width: 1200, height: 630, alt: post.featured_image_alt || title }]
        : [{ url: "https://a-stats.app/icon.png", width: 512, height: 512, alt: title }],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: imageUrl ? [imageUrl] : undefined,
    },
    alternates: {
      canonical,
    },
  };
}

function estimateWordCount(html: string | undefined): number | undefined {
  if (!html) return undefined;
  const text = html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  return text.split(" ").filter(Boolean).length;
}

function buildJsonLd(post: BlogPostDetail) {
  const baseUrl = "https://a-stats.app";
  const postUrl = `${baseUrl}/en/blog/${post.slug}`;

  // Build keywords from tags + category
  const keywords = [
    ...(post.tags?.map((t) => t.name) ?? []),
    ...(post.category ? [post.category.name] : []),
  ].join(", ") || undefined;

  const wordCount = estimateWordCount(post.content_html);

  const graph: Record<string, unknown>[] = [
    {
      "@type": "BlogPosting",
      "@id": postUrl,
      headline: post.title,
      description: post.meta_description || post.excerpt || undefined,
      datePublished: post.published_at,
      dateModified: post.updated_at || post.published_at,
      url: postUrl,
      inLanguage: "en",
      isAccessibleForFree: true,
      ...(keywords && { keywords }),
      ...(wordCount && { wordCount }),
      ...(post.category && { articleSection: post.category.name }),
      mainEntityOfPage: { "@type": "WebPage", "@id": postUrl },
      isPartOf: { "@id": `${baseUrl}/en/blog/#blog` },
      author: {
        "@type": "Person",
        name: post.author_name || "A-Stats Team",
      },
      publisher: { "@id": `${baseUrl}/#organization` },
      ...(post.featured_image_url && {
        image: {
          "@type": "ImageObject",
          url: post.featured_image_url,
          description: post.featured_image_alt || post.title,
        },
      }),
      // Speakable — helps AI engines identify the most citable parts of the page
      speakable: {
        "@type": "SpeakableSpecification",
        cssSelector: ["h1", "h2", ".article-description"],
      },
    },
    {
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Home", item: baseUrl },
        { "@type": "ListItem", position: 2, name: "Blog", item: `${baseUrl}/en/blog` },
        ...(post.category
          ? [{ "@type": "ListItem", position: 3, name: post.category.name, item: `${baseUrl}/en/blog/category/${post.category.slug}` },
             { "@type": "ListItem", position: 4, name: post.title, item: postUrl }]
          : [{ "@type": "ListItem", position: 3, name: post.title, item: postUrl }]),
      ],
    },
  ];

  // Conditional FAQPage
  if (post.schema_faq) {
    graph.push(post.schema_faq as Record<string, unknown>);
  }

  return { "@context": "https://schema.org", "@graph": graph };
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string; locale: string }>;
}) {
  const { slug } = await params;
  const post = await fetchPost(slug);

  if (!post) {
    notFound();
  }

  const [jsonLd, relatedPosts] = await Promise.all([
    Promise.resolve(buildJsonLd(post)),
    fetchRelatedPosts(post.category?.slug, slug),
  ]);

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <Suspense>
          <BlogPostClient post={post} relatedPosts={relatedPosts} />
        </Suspense>
      </div>
    </>
  );
}
