import Link from "next/link";
import Image from "next/image";
import { Calendar, Clock } from "lucide-react";
import type { BlogPostCard } from "@/lib/api";

interface PostCardProps {
  post: BlogPostCard;
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function PostCard({ post }: PostCardProps) {
  return (
    <article className="bg-surface border border-surface-tertiary rounded-2xl overflow-hidden hover:shadow-lg transition-all duration-200 group flex flex-col">
      {/* Image */}
      <Link
        href={`/blog/${post.slug}`}
        className="block overflow-hidden aspect-[16/9] bg-surface-secondary flex-shrink-0"
      >
        {post.featured_image_url ? (
          <Image
            src={post.featured_image_url}
            alt={post.featured_image_alt || post.title}
            width={640}
            height={360}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center">
            <span className="text-primary-300 text-4xl font-bold">A</span>
          </div>
        )}
        {/* Category badge overlay */}
        {post.category && (
          <span className="absolute top-3 left-3 px-2.5 py-1 bg-primary-600 text-white text-xs font-semibold rounded-full">
            {post.category.name}
          </span>
        )}
      </Link>

      {/* Content */}
      <div className="p-5 flex flex-col flex-1">
        <Link href={`/blog/${post.slug}`} className="flex-1">
          <h2
            className="text-base font-bold text-text-primary leading-snug mb-3 group-hover:text-primary-600 transition-colors line-clamp-2"
            title={post.title}
          >
            {post.title}
          </h2>
        </Link>

        {(post.excerpt || post.meta_description) && (
          <p className="text-sm text-text-secondary leading-relaxed mb-4 line-clamp-2">
            {post.excerpt || post.meta_description}
          </p>
        )}

        {/* Footer meta */}
        <div className="flex items-center gap-3 text-xs text-text-muted mt-auto pt-3 border-t border-surface-tertiary">
          {/* Author avatar + name */}
          <div className="flex items-center gap-1.5">
            <div className="h-5 w-5 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
              <span className="text-primary-700 text-[9px] font-bold uppercase">
                {(post.author_name || "A")[0]}
              </span>
            </div>
            <span className="truncate max-w-[80px]">{post.author_name || "A-Stats"}</span>
          </div>

          <span className="text-surface-tertiary">·</span>

          {post.published_at && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {formatDate(post.published_at)}
            </span>
          )}

          <span className="text-surface-tertiary">·</span>

          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {post.reading_time_minutes}m
          </span>
        </div>
      </div>
    </article>
  );
}
