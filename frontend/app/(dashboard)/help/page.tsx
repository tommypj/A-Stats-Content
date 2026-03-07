"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Fuse from "fuse.js";
import {
  Search,
  FileText,
  Mail,
  BookOpen,
  ExternalLink,
  Rocket,
  PenTool,
  Bot,
  BarChart3,
  Share2,
  Database,
  Image as ImageIcon,
  Users,
  Building2,
  CreditCard,
  Settings,
  ChevronRight,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { DOC_CATEGORIES, type SearchableDoc } from "@/lib/docs";

const ICON_MAP: Record<string, React.ElementType> = {
  Rocket,
  PenTool,
  Search,
  Bot,
  BarChart3,
  Share2,
  Database,
  Image: ImageIcon,
  Users,
  Building2,
  CreditCard,
  Settings,
};

// Build search index from manifest
const searchArticles: SearchableDoc[] = DOC_CATEGORIES.flatMap((cat) =>
  cat.articles.map((article) => ({
    title: article.title,
    description: article.description,
    category: article.category,
    categoryTitle: cat.title,
    slug: article.slug,
    href: `/help/${article.category}/${article.slug}`,
  }))
);

const fuse = new Fuse(searchArticles, {
  keys: [
    { name: "title", weight: 2 },
    { name: "description", weight: 1 },
    { name: "categoryTitle", weight: 0.5 },
  ],
  threshold: 0.4,
});

export default function HelpPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const results = query.trim().length >= 2
    ? fuse.search(query).slice(0, 8).map((r) => r.item)
    : [];

  return (
    <div className="space-y-8 max-w-4xl animate-in">
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          Help & Support
        </h1>
        <p className="mt-1 text-text-secondary">
          Find guides, tutorials, and answers to common questions.
        </p>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
        <input
          type="text"
          placeholder="Search help articles..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full pl-9 pr-4 py-2.5 text-sm bg-surface border border-cream-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-300 text-text-primary placeholder:text-text-muted"
        />
        {results.length > 0 && (
          <div className="absolute top-full mt-2 w-full bg-surface rounded-xl border border-cream-200 shadow-soft-lg overflow-hidden z-50">
            {results.map((article) => (
              <button
                key={`${article.category}/${article.slug}`}
                onClick={() => {
                  router.push(article.href);
                  setQuery("");
                }}
                className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-surface-secondary transition-colors"
              >
                <FileText className="h-4 w-4 text-primary-400 mt-0.5 shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">
                    {article.title}
                  </p>
                  <p className="text-xs text-text-muted truncate">
                    {article.categoryTitle}
                  </p>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Category grid */}
      <div>
        <h2 className="text-lg font-display font-semibold text-text-primary mb-4">
          Browse by Topic
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {DOC_CATEGORIES.map((cat) => {
            const Icon = ICON_MAP[cat.icon] || Rocket;
            return (
              <Link key={cat.slug} href={`/help/${cat.slug}`}>
                <Card className="p-5 hover:shadow-md transition-all group cursor-pointer h-full">
                  <div className="h-10 w-10 rounded-xl bg-primary-50 flex items-center justify-center mb-3">
                    <Icon className="h-5 w-5 text-primary-500" />
                  </div>
                  <h3 className="font-display font-semibold text-text-primary group-hover:text-primary-600 transition-colors">
                    {cat.title}
                  </h3>
                  <p className="text-sm text-text-secondary mt-1">
                    {cat.description}
                  </p>
                  <div className="flex items-center gap-1 mt-3 text-sm text-primary-500 font-medium">
                    <span>
                      {cat.articles.length} article{cat.articles.length !== 1 ? "s" : ""}
                    </span>
                    <ChevronRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Contact Support */}
      <Card className="p-6">
        <h2 className="text-lg font-display font-semibold text-text-primary mb-4">
          Need More Help?
        </h2>
        <div className="grid sm:grid-cols-2 gap-4">
          <a
            href="mailto:support@astats.app"
            className="flex items-center gap-3 p-4 rounded-xl bg-surface-secondary hover:bg-surface-tertiary transition-colors"
          >
            <Mail className="h-5 w-5 text-primary-500" />
            <div>
              <p className="font-medium text-text-primary">Email Support</p>
              <p className="text-sm text-text-secondary">support@astats.app</p>
            </div>
          </a>
          <Link
            href="/en/docs"
            className="flex items-center gap-3 p-4 rounded-xl bg-surface-secondary hover:bg-surface-tertiary transition-colors"
          >
            <BookOpen className="h-5 w-5 text-primary-500" />
            <div>
              <p className="font-medium text-text-primary flex items-center gap-1">
                Full Documentation <ExternalLink className="h-3.5 w-3.5" />
              </p>
              <p className="text-sm text-text-secondary">Browse the public docs</p>
            </div>
          </Link>
        </div>
      </Card>
    </div>
  );
}
