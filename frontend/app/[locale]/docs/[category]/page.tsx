import Link from "next/link";
import { notFound } from "next/navigation";
import { DOC_CATEGORIES, getCategory } from "@/lib/docs";
import { ChevronRight } from "lucide-react";

export function generateStaticParams() {
  return DOC_CATEGORIES.map((cat) => ({ category: cat.slug }));
}

export function generateMetadata({ params }: { params: { category: string } }) {
  const cat = getCategory(params.category);
  if (!cat) return {};
  return {
    title: `${cat.title} — A-Stats Docs`,
    description: cat.description,
  };
}

export default function DocsCategoryPage({
  params,
}: {
  params: { category: string };
}) {
  const cat = getCategory(params.category);
  if (!cat) notFound();

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/docs"
          className="text-sm text-primary-500 hover:text-primary-600 transition-colors"
        >
          &larr; All categories
        </Link>
        <h1 className="text-3xl font-display font-bold text-text-primary mt-2">
          {cat.title}
        </h1>
        <p className="mt-1 text-text-secondary">{cat.description}</p>
      </div>

      <div className="space-y-2">
        {cat.articles.map((article) => (
          <Link
            key={article.slug}
            href={`/docs/${cat.slug}/${article.slug}`}
            className="group flex items-center justify-between p-4 rounded-xl border border-cream-200 hover:border-primary-200 hover:bg-primary-50/30 transition-all"
          >
            <div>
              <h2 className="font-medium text-text-primary group-hover:text-primary-600 transition-colors">
                {article.title}
              </h2>
              <p className="text-sm text-text-secondary mt-0.5">
                {article.description}
              </p>
            </div>
            <ChevronRight className="h-4 w-4 text-text-muted group-hover:text-primary-500 shrink-0 ml-4" />
          </Link>
        ))}
      </div>
    </div>
  );
}
