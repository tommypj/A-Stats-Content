"use client";

import { useParams } from "next/navigation";
import { notFound } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { getArticle, getPrevNextArticles, type DocArticle } from "@/lib/docs";

export default function HelpArticlePage() {
  const params = useParams();
  const categorySlug = params.category as string;
  const articleSlug = params.slug as string;

  const article = getArticle(categorySlug, articleSlug);
  const { prev, next } = getPrevNextArticles(categorySlug, articleSlug);
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/docs-content/${categorySlug}/${articleSlug}.md`)
      .then((res) => {
        if (!res.ok) throw new Error("Not found");
        return res.text();
      })
      .then(setContent)
      .catch(() => setContent(null))
      .finally(() => setLoading(false));
  }, [categorySlug, articleSlug]);

  if (!article) notFound();

  if (loading) {
    return (
      <div className="max-w-3xl animate-in space-y-4">
        <div className="h-4 w-24 bg-cream-200 rounded animate-pulse" />
        <div className="h-8 w-64 bg-cream-200 rounded animate-pulse" />
        <div className="space-y-3 mt-8">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-4 bg-cream-100 rounded animate-pulse" style={{ width: `${70 + Math.random() * 30}%` }} />
          ))}
        </div>
      </div>
    );
  }

  if (!content) {
    return (
      <div className="max-w-3xl animate-in">
        <Link href={`/help/${categorySlug}`} className="text-sm text-primary-500 hover:text-primary-600">
          &larr; {article.categoryTitle}
        </Link>
        <h1 className="text-2xl font-display font-bold text-text-primary mt-2">{article.title}</h1>
        <p className="mt-4 text-text-secondary">This article is coming soon.</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl animate-in">
      <Link
        href={`/help/${categorySlug}`}
        className="text-sm font-medium text-primary-500 hover:text-primary-600 transition-colors"
      >
        {article.categoryTitle}
      </Link>

      <h1 className="text-2xl font-display font-bold text-text-primary mt-2 mb-8">
        {article.title}
      </h1>

      <div className="prose prose-sage max-w-none prose-headings:font-display prose-headings:text-text-primary prose-p:text-text-secondary prose-a:text-primary-500 hover:prose-a:text-primary-600 prose-strong:text-text-primary prose-code:text-primary-700 prose-code:bg-primary-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none prose-li:text-text-secondary">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>

      {/* Prev / Next */}
      <nav className="mt-12 pt-8 border-t border-cream-200 grid grid-cols-2 gap-4">
        {prev ? (
          <Link
            href={`/help/${prev.category}/${prev.slug}`}
            className="group flex flex-col p-4 rounded-xl border border-cream-200 hover:border-primary-200 hover:bg-primary-50/50 transition-colors"
          >
            <span className="text-xs text-text-muted flex items-center gap-1">
              <ChevronLeft className="h-3 w-3" /> Previous
            </span>
            <span className="text-sm font-medium text-text-primary group-hover:text-primary-600 mt-1">
              {prev.title}
            </span>
          </Link>
        ) : <div />}
        {next ? (
          <Link
            href={`/help/${next.category}/${next.slug}`}
            className="group flex flex-col items-end p-4 rounded-xl border border-cream-200 hover:border-primary-200 hover:bg-primary-50/50 transition-colors text-right"
          >
            <span className="text-xs text-text-muted flex items-center gap-1">
              Next <ChevronRight className="h-3 w-3" />
            </span>
            <span className="text-sm font-medium text-text-primary group-hover:text-primary-600 mt-1">
              {next.title}
            </span>
          </Link>
        ) : <div />}
      </nav>
    </div>
  );
}
