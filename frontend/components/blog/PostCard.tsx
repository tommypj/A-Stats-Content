import Link from "next/link";
import Image from "next/image";
import type { BlogPostCard } from "@/lib/api";

interface PostCardProps {
  post: BlogPostCard;
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function PostCard({ post }: PostCardProps) {
  return (
    <article className="bg-surface border border-surface-tertiary rounded-2xl overflow-hidden hover:shadow-md transition-shadow group">
      {post.featured_image_url && (
        <Link href={`/blog/${post.slug}`} className="block overflow-hidden aspect-[16/9] relative bg-surface-secondary">
          <Image
            src={post.featured_image_url}
            alt={post.featured_image_alt || post.title}
            fill
            className="object-cover group-hover:scale-105 transition-transform duration-300"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />
        </Link>
      )}

      <div className="p-5">
        {post.category && (
          <Link
            href={`/blog/category/${post.category.slug}`}
            className="inline-block mb-2 text-xs font-semibold uppercase tracking-wide text-primary-600 hover:text-primary-700"
          >
            {post.category.name}
          </Link>
        )}

        <Link href={`/blog/${post.slug}`}>
          <h2 className="text-lg font-bold text-text-primary leading-snug mb-2 group-hover:text-primary-600 transition-colors line-clamp-2" title={post.title}>
            {post.title}
          </h2>
        </Link>

        {post.excerpt && (
          <p className="text-sm text-text-secondary leading-relaxed mb-4 line-clamp-3">
            {post.excerpt}
          </p>
        )}

        <div className="flex items-center justify-between text-xs text-text-muted pt-2 border-t border-surface-tertiary">
          <span>{post.author_name || "A-Stats Team"}</span>
          <div className="flex items-center gap-3">
            {post.published_at && <span>{formatDate(post.published_at)}</span>}
            <span>{post.reading_time_minutes} min read</span>
          </div>
        </div>
      </div>
    </article>
  );
}
