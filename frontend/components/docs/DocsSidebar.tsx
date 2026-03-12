import { getCategoriesByTier } from "@/lib/docs";
import DocsSidebarLink from "./DocsSidebarLink";

export default function DocsSidebar() {
  const categories = getCategoriesByTier("features");
  return (
    <nav className="w-64 shrink-0 hidden lg:block">
      <div className="sticky top-24 space-y-6 max-h-[calc(100vh-8rem)] overflow-y-auto pr-4 pb-8">
        {categories.map((cat) => (
          <div key={cat.slug}>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
              {cat.title}
            </h3>
            <div className="space-y-0.5">
              {cat.articles.map((article) => (
                <DocsSidebarLink
                  key={article.slug}
                  href={`/docs/${cat.slug}/${article.slug}`}
                >
                  {article.title}
                </DocsSidebarLink>
              ))}
            </div>
          </div>
        ))}
      </div>
    </nav>
  );
}
