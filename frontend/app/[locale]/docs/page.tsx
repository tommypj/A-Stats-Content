import Link from "next/link";
import { DOC_CATEGORIES, getSearchableArticles } from "@/lib/docs";
import DocsSearch from "@/components/docs/DocsSearch";
import {
  Rocket,
  PenTool,
  Search,
  Bot,
  BarChart3,
  Share2,
  Database,
  Image,
  Users,
  Building2,
  CreditCard,
  Settings,
} from "lucide-react";

const ICON_MAP: Record<string, React.ElementType> = {
  Rocket,
  PenTool,
  Search,
  Bot,
  BarChart3,
  Share2,
  Database,
  Image,
  Users,
  Building2,
  CreditCard,
  Settings,
};

export default function DocsHomePage() {
  const searchArticles = getSearchableArticles();

  return (
    <div className="space-y-10">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-bold text-text-primary">
          Documentation
        </h1>
        <p className="mt-2 text-text-secondary max-w-xl">
          Everything you need to know about using A-Stats to create content, track
          SEO performance, and grow your audience.
        </p>
        <div className="mt-6">
          <DocsSearch articles={searchArticles} linkPrefix="/docs" />
        </div>
      </div>

      {/* Category grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {DOC_CATEGORIES.map((cat) => {
          const Icon = ICON_MAP[cat.icon] || Rocket;
          return (
            <Link
              key={cat.slug}
              href={`/docs/${cat.slug}`}
              className="group p-5 rounded-xl border border-cream-200 hover:border-primary-200 hover:bg-primary-50/30 transition-all"
            >
              <div className="h-10 w-10 rounded-xl bg-primary-50 flex items-center justify-center mb-3">
                <Icon className="h-5 w-5 text-primary-500" />
              </div>
              <h2 className="font-display font-semibold text-text-primary group-hover:text-primary-600 transition-colors">
                {cat.title}
              </h2>
              <p className="text-sm text-text-secondary mt-1">{cat.description}</p>
              <p className="text-xs text-text-muted mt-2">
                {cat.articles.length} article{cat.articles.length !== 1 ? "s" : ""}
              </p>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
