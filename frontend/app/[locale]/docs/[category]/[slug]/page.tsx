import { notFound } from "next/navigation";
import {
  DOC_CATEGORIES,
  getArticle,
  getPrevNextArticles,
} from "@/lib/docs";
import { getDocContent } from "@/lib/docs-server";
import DocsArticle from "@/components/docs/DocsArticle";

export function generateStaticParams() {
  return DOC_CATEGORIES.flatMap((cat) =>
    cat.articles.map((article) => ({
      category: cat.slug,
      slug: article.slug,
    }))
  );
}

export function generateMetadata({
  params,
}: {
  params: { category: string; slug: string };
}) {
  const article = getArticle(params.category, params.slug);
  if (!article) return {};
  return {
    title: `${article.title} — A-Stats Docs`,
    description: article.description,
  };
}

export default function DocsArticlePage({
  params,
}: {
  params: { category: string; slug: string };
}) {
  const article = getArticle(params.category, params.slug);
  if (!article) notFound();

  const content = getDocContent(params.category, params.slug);
  if (!content) notFound();

  const { prev, next } = getPrevNextArticles(params.category, params.slug);

  return (
    <DocsArticle
      title={article.title}
      categoryTitle={article.categoryTitle}
      categorySlug={params.category}
      content={content}
      prev={prev}
      next={next}
      linkPrefix="/docs"
    />
  );
}
