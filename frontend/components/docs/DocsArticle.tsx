import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { DocArticle } from "@/lib/docs";

interface DocsArticleProps {
  title: string;
  categoryTitle: string;
  categorySlug: string;
  content: string;
  prev: DocArticle | null;
  next: DocArticle | null;
  linkPrefix: string; // "/docs" for public, "/help" for in-app
}

export default function DocsArticle({
  title,
  categoryTitle,
  categorySlug,
  content,
  prev,
  next,
  linkPrefix,
}: DocsArticleProps) {
  return (
    <article className="max-w-3xl">
      {/* Category label */}
      <Link
        href={`${linkPrefix}/${categorySlug}`}
        className="text-sm font-medium text-primary-500 hover:text-primary-600 transition-colors"
      >
        {categoryTitle}
      </Link>

      <h1 className="text-3xl font-display font-bold text-text-primary mt-2 mb-8">
        {title}
      </h1>

      {/* Markdown content */}
      <div className="prose prose-sage max-w-none prose-headings:font-display prose-headings:text-text-primary prose-p:text-text-secondary prose-a:text-primary-500 hover:prose-a:text-primary-600 prose-strong:text-text-primary prose-code:text-primary-700 prose-code:bg-primary-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none prose-img:rounded-xl prose-li:text-text-secondary">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>

      {/* Prev / Next navigation */}
      <nav className="mt-12 pt-8 border-t border-cream-200 grid grid-cols-2 gap-4">
        {prev ? (
          <Link
            href={`${linkPrefix}/${prev.category}/${prev.slug}`}
            className="group flex flex-col p-4 rounded-xl border border-cream-200 hover:border-primary-200 hover:bg-primary-50/50 transition-colors"
          >
            <span className="text-xs text-text-muted flex items-center gap-1">
              <ChevronLeft className="h-3 w-3" /> Previous
            </span>
            <span className="text-sm font-medium text-text-primary group-hover:text-primary-600 mt-1">
              {prev.title}
            </span>
          </Link>
        ) : (
          <div />
        )}
        {next ? (
          <Link
            href={`${linkPrefix}/${next.category}/${next.slug}`}
            className="group flex flex-col items-end p-4 rounded-xl border border-cream-200 hover:border-primary-200 hover:bg-primary-50/50 transition-colors text-right"
          >
            <span className="text-xs text-text-muted flex items-center gap-1">
              Next <ChevronRight className="h-3 w-3" />
            </span>
            <span className="text-sm font-medium text-text-primary group-hover:text-primary-600 mt-1">
              {next.title}
            </span>
          </Link>
        ) : (
          <div />
        )}
      </nav>
    </article>
  );
}
