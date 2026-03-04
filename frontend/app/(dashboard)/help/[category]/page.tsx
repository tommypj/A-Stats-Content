"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { notFound } from "next/navigation";
import { getCategory } from "@/lib/docs";
import { Card } from "@/components/ui/card";
import { ChevronRight } from "lucide-react";

export default function HelpCategoryPage() {
  const params = useParams();
  const cat = getCategory(params.category as string);
  if (!cat) notFound();

  return (
    <div className="space-y-6 max-w-4xl animate-in">
      <div>
        <Link
          href="/help"
          className="text-sm text-primary-500 hover:text-primary-600 transition-colors"
        >
          &larr; All topics
        </Link>
        <h1 className="text-2xl font-display font-bold text-text-primary mt-2">
          {cat.title}
        </h1>
        <p className="mt-1 text-text-secondary">{cat.description}</p>
      </div>

      <div className="space-y-2">
        {cat.articles.map((article) => (
          <Link
            key={article.slug}
            href={`/help/${cat.slug}/${article.slug}`}
          >
            <Card className="p-4 hover:shadow-md transition-all group cursor-pointer flex items-center justify-between">
              <div>
                <h2 className="font-medium text-text-primary group-hover:text-primary-600 transition-colors">
                  {article.title}
                </h2>
                <p className="text-sm text-text-secondary mt-0.5">
                  {article.description}
                </p>
              </div>
              <ChevronRight className="h-4 w-4 text-text-muted group-hover:text-primary-500 shrink-0 ml-4" />
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
