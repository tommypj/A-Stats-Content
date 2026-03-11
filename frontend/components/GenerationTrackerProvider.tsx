"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  useGenerationTracker,
  GENERATION_TIMEOUTS,
  type TrackedGeneration,
} from "@/stores/generation-tracker";
import { api } from "@/lib/api";

const POLL_INTERVAL = 2000;

async function checkStatus(
  gen: TrackedGeneration
): Promise<"generating" | "completed" | "failed"> {
  switch (gen.type) {
    case "image": {
      const img = await api.images.get(gen.id);
      if (img.status === "completed") return "completed";
      if (img.status === "failed") return "failed";
      return "generating";
    }
    case "article": {
      const art = await api.articles.get(gen.id);
      if (art.status === "completed" || art.status === "published")
        return "completed";
      if (art.status === "failed") return "failed";
      return "generating";
    }
    case "outline": {
      const out = await api.outlines.get(gen.id);
      if (out.status === "completed") return "completed";
      if (out.status === "failed") return "failed";
      return "generating";
    }
    case "bulk": {
      const job = await api.bulk.getJob(gen.id);
      if (job.status === "completed" || job.status === "partially_failed")
        return "completed";
      if (job.status === "failed" || job.status === "cancelled")
        return "failed";
      return "generating";
    }
    default:
      return "generating";
  }
}

function getTypeLabel(type: TrackedGeneration["type"]): string {
  if (type === "bulk") return "Bulk job";
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function GenerationTrackerPoller() {
  const router = useRouter();
  const { generations, suppressedIds, remove } = useGenerationTracker();
  const pollingRef = useRef(false);

  useEffect(() => {
    const interval = setInterval(async () => {
      if (pollingRef.current) return;
      pollingRef.current = true;

      try {
        const active = generations.filter(
          (g) => g.status === "generating" && !suppressedIds.includes(g.id)
        );

        for (const gen of active) {
          const timeout = GENERATION_TIMEOUTS[gen.type] ?? 180_000;
          if (Date.now() - gen.startedAt > timeout) {
            remove(gen.id);
            toast.error(`${getTypeLabel(gen.type)} timed out: ${gen.title}`);
            continue;
          }

          try {
            const status = await checkStatus(gen);

            if (status === "completed") {
              remove(gen.id);

              if (gen.type === "article") {
                toast.success(`Article ready: ${gen.title}`, {
                  action: {
                    label: "View",
                    onClick: () =>
                      router.push(`/articles/${gen.articleId ?? gen.id}`),
                  },
                  duration: 10000,
                });
              } else if (gen.type === "image") {
                toast.success(`Image generated: ${gen.title}`, {
                  action: {
                    label: "View",
                    onClick: () => router.push("/images"),
                  },
                  duration: 10000,
                });
              } else if (gen.type === "outline") {
                toast.success(`Outline ready: ${gen.title}`, {
                  duration: 6000,
                });
              } else if (gen.type === "bulk") {
                toast.success("Bulk job completed", { duration: 6000 });
              }
            } else if (status === "failed") {
              remove(gen.id);
              toast.error(
                `${getTypeLabel(gen.type)} failed: ${gen.title}`
              );
            }
          } catch {
            // Transient network error — skip, retry next cycle
          }
        }
      } finally {
        pollingRef.current = false;
      }
    }, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [generations, suppressedIds, remove, router]);

  return null;
}

export function GenerationTrackerProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <GenerationTrackerPoller />
      {children}
    </>
  );
}
