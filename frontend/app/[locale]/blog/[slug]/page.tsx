import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import BlogPostClient from "@/components/blog/BlogPostClient";
import type { BlogPostDetail } from "@/lib/api";

export const revalidate = 300;

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
      publishedTime: post.published_at,
      authors: post.author_name ? [post.author_name] : undefined,
      images: imageUrl
        ? [{ url: imageUrl, alt: post.featured_image_alt || title }]
        : undefined,
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

function buildJsonLd(post: BlogPostDetail) {
  const baseUrl = "https://a-stats.app";
  const postUrl = `${baseUrl}/en/blog/${post.slug}`;

  const graph: Record<string, unknown>[] = [
    {
      "@type": "BlogPosting",
      "@id": postUrl,
      headline: post.title,
      description: post.meta_description || post.excerpt || undefined,
      datePublished: post.published_at,
      dateModified: post.updated_at || post.published_at,
      url: postUrl,
      mainEntityOfPage: { "@type": "WebPage", "@id": postUrl },
      author: {
        "@type": "Person",
        name: post.author_name || "A-Stats Team",
      },
      publisher: {
        "@type": "Organization",
        name: "A-Stats",
        url: baseUrl,
        logo: {
          "@type": "ImageObject",
          url: `${baseUrl}/images/logo.png`,
        },
      },
      ...(post.featured_image_url && {
        image: {
          "@type": "ImageObject",
          url: post.featured_image_url,
          description: post.featured_image_alt || post.title,
        },
      }),
    },
    {
      "@type": "BreadcrumbList",
      itemListElement: [
        {
          "@type": "ListItem",
          position: 1,
          name: "Home",
          item: baseUrl,
        },
        {
          "@type": "ListItem",
          position: 2,
          name: "Blog",
          item: `${baseUrl}/en/blog`,
        },
        {
          "@type": "ListItem",
          position: 3,
          name: post.title,
          item: postUrl,
        },
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

  const jsonLd = buildJsonLd(post);

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <div className="min-h-screen bg-surface">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <Suspense>
            <BlogPostClient post={post} />
          </Suspense>
        </div>
      </div>
    </>
  );
}
