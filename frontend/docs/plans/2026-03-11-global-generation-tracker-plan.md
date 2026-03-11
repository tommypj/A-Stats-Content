# Global Generation Tracker Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Track all active generations (article, image, outline, bulk) globally so polling continues when users navigate away or phones enter standby, with toast notifications on completion.

**Architecture:** Zustand store with localStorage persistence holds tracked generations. A React provider component at the dashboard layout level runs a single polling loop. Page components register generations and suppress polling when they handle their own UI. On completion/failure, toasts fire with optional click-to-navigate.

**Tech Stack:** Zustand, zustand/middleware (persist), React, sonner (toast), Next.js router

---

### Task 1: Create the Zustand generation tracker store

**Files:**
- Create: `frontend/stores/generation-tracker.ts`

**Step 1: Create the store**

```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type GenerationType = "article" | "image" | "outline" | "bulk";
export type GenerationStatus = "generating" | "completed" | "failed";

export interface TrackedGeneration {
  id: string;
  type: GenerationType;
  status: GenerationStatus;
  title: string;
  startedAt: number;
  articleId?: string;
  imageId?: string;
}

// Max polling duration per type (ms)
export const GENERATION_TIMEOUTS: Record<GenerationType, number> = {
  article: 12 * 60 * 1000,  // 12 minutes
  image: 3 * 60 * 1000,     // 3 minutes
  outline: 3 * 60 * 1000,   // 3 minutes
  bulk: 30 * 60 * 1000,     // 30 minutes
};

interface GenerationTrackerState {
  generations: TrackedGeneration[];
  suppressedIds: string[];

  track: (gen: TrackedGeneration) => void;
  update: (id: string, updates: Partial<TrackedGeneration>) => void;
  remove: (id: string) => void;
  clear: () => void;
  suppress: (id: string) => void;
  unsuppress: (id: string) => void;
}

export const useGenerationTracker = create<GenerationTrackerState>()(
  persist(
    (set) => ({
      generations: [],
      suppressedIds: [],

      track: (gen) =>
        set((state) => {
          // Don't add duplicates
          if (state.generations.some((g) => g.id === gen.id)) return state;
          return { generations: [...state.generations, gen] };
        }),

      update: (id, updates) =>
        set((state) => ({
          generations: state.generations.map((g) =>
            g.id === id ? { ...g, ...updates } : g
          ),
        })),

      remove: (id) =>
        set((state) => ({
          generations: state.generations.filter((g) => g.id !== id),
          suppressedIds: state.suppressedIds.filter((sid) => sid !== id),
        })),

      clear: () => set({ generations: [], suppressedIds: [] }),

      suppress: (id) =>
        set((state) => ({
          suppressedIds: state.suppressedIds.includes(id)
            ? state.suppressedIds
            : [...state.suppressedIds, id],
        })),

      unsuppress: (id) =>
        set((state) => ({
          suppressedIds: state.suppressedIds.filter((sid) => sid !== id),
        })),
    }),
    {
      name: "generation-tracker",
      partialize: (state) => ({
        generations: state.generations,
        // Don't persist suppressedIds — they're only valid while a page is mounted
      }),
      onRehydrateStorage: () => (state) => {
        if (!state) return;
        // Clean up stale generations on app load
        const now = Date.now();
        const fresh = state.generations.filter((g) => {
          const timeout = GENERATION_TIMEOUTS[g.type] ?? 180_000;
          return now - g.startedAt < timeout;
        });
        if (fresh.length !== state.generations.length) {
          state.generations = fresh;
        }
      },
    }
  )
);
```

**Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/stores/generation-tracker.ts
git commit -m "feat: add Zustand generation tracker store with localStorage persistence"
```

---

### Task 2: Create the GenerationTrackerProvider component

**Files:**
- Create: `frontend/components/GenerationTrackerProvider.tsx`

**Step 1: Create the provider**

This component mounts at the dashboard layout level. It runs a single 2s polling loop over all active, non-suppressed generations. On completion/failure, it fires toast notifications and removes the generation from the store.

```typescript
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

const POLL_INTERVAL = 2000; // 2 seconds

async function checkStatus(gen: TrackedGeneration): Promise<"generating" | "completed" | "failed"> {
  switch (gen.type) {
    case "image": {
      const img = await api.images.get(gen.id);
      if (img.status === "completed") return "completed";
      if (img.status === "failed") return "failed";
      return "generating";
    }
    case "article": {
      const art = await api.articles.get(gen.id);
      if (art.status === "completed" || art.status === "published") return "completed";
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
      if (job.status === "completed" || job.status === "partially_failed") return "completed";
      if (job.status === "failed" || job.status === "cancelled") return "failed";
      return "generating";
    }
    default:
      return "generating";
  }
}

function GenerationTrackerPoller() {
  const router = useRouter();
  const { generations, suppressedIds, update, remove } = useGenerationTracker();
  const pollingRef = useRef(false);

  useEffect(() => {
    const interval = setInterval(async () => {
      // Prevent overlapping poll cycles
      if (pollingRef.current) return;
      pollingRef.current = true;

      try {
        const active = generations.filter(
          (g) => g.status === "generating" && !suppressedIds.includes(g.id)
        );

        for (const gen of active) {
          // Check timeout
          const timeout = GENERATION_TIMEOUTS[gen.type] ?? 180_000;
          if (Date.now() - gen.startedAt > timeout) {
            toast.error(`${gen.type === "bulk" ? "Bulk job" : gen.type.charAt(0).toUpperCase() + gen.type.slice(1)} timed out: ${gen.title}`);
            remove(gen.id);
            continue;
          }

          try {
            const status = await checkStatus(gen);

            if (status === "completed") {
              remove(gen.id);

              const label = gen.type === "bulk"
                ? "Bulk job completed"
                : `${gen.type.charAt(0).toUpperCase() + gen.type.slice(1)} ready: ${gen.title}`;

              if (gen.type === "article" && gen.articleId) {
                toast.success(label, {
                  action: {
                    label: "View",
                    onClick: () => router.push(`/articles/${gen.articleId}`),
                  },
                  duration: 10000,
                });
              } else if (gen.type === "image") {
                toast.success(label, {
                  action: {
                    label: "View",
                    onClick: () => router.push("/images"),
                  },
                  duration: 10000,
                });
              } else {
                toast.success(label, { duration: 6000 });
              }
            } else if (status === "failed") {
              remove(gen.id);
              toast.error(`${gen.type.charAt(0).toUpperCase() + gen.type.slice(1)} failed: ${gen.title}`);
            }
          } catch {
            // Transient network error — skip this generation, retry next cycle
          }
        }
      } finally {
        pollingRef.current = false;
      }
    }, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [generations, suppressedIds, update, remove, router]);

  return null;
}

export function GenerationTrackerProvider({ children }: { children: React.ReactNode }) {
  return (
    <>
      <GenerationTrackerPoller />
      {children}
    </>
  );
}
```

**Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/components/GenerationTrackerProvider.tsx
git commit -m "feat: add GenerationTrackerProvider with background polling and toast notifications"
```

---

### Task 3: Mount the provider in the dashboard layout

**Files:**
- Modify: `frontend/app/(dashboard)/layout.tsx:925-934`

**Step 1: Add import and wrap content**

At the top of the file, add:
```typescript
import { GenerationTrackerProvider } from "@/components/GenerationTrackerProvider";
```

In the return block (around line 925-934), wrap `ProjectProvider` with `GenerationTrackerProvider`:

Change:
```tsx
  return (
    <PostHogProvider>
      <Suspense fallback={null}>
        <PostHogPageview />
      </Suspense>
      <ProjectProvider>
        <DashboardContent>{children}</DashboardContent>
      </ProjectProvider>
    </PostHogProvider>
  );
```

To:
```tsx
  return (
    <PostHogProvider>
      <Suspense fallback={null}>
        <PostHogPageview />
      </Suspense>
      <GenerationTrackerProvider>
        <ProjectProvider>
          <DashboardContent>{children}</DashboardContent>
        </ProjectProvider>
      </GenerationTrackerProvider>
    </PostHogProvider>
  );
```

**Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/app/\(dashboard\)/layout.tsx
git commit -m "feat: mount GenerationTrackerProvider in dashboard layout"
```

---

### Task 4: Integrate tracker into image generation page

**Files:**
- Modify: `frontend/app/(dashboard)/images/generate/page.tsx`

**Step 1: Add imports and hooks**

Add near the top imports:
```typescript
import { useGenerationTracker } from "@/stores/generation-tracker";
```

Inside `GenerateImageContent`, add after existing hooks:
```typescript
const { track, suppress, unsuppress } = useGenerationTracker();
```

**Step 2: Track standalone image generation**

In `handleGenerate`, inside the per-call `onSuccess` callback (around line 188), after `setGeneratedImage(image)` and before `pollImageStatus(image.id)`, add:
```typescript
track({ id: image.id, type: "image", status: "generating", title: prompt.trim().slice(0, 60), startedAt: Date.now() });
suppress(image.id);
```

**Step 3: Track prompt card image generation**

In `handleGenerateForPrompt`, inside the per-call `onSuccess` callback (around line 217), after `setPromptCardImages(...)` and before `pollPromptCardImage(...)`, add:
```typescript
track({ id: image.id, type: "image", status: "generating", title: articlePrompts[index]?.slice(0, 60) || "Image", startedAt: Date.now() });
suppress(image.id);
```

**Step 4: Remove from tracker on local polling completion**

In `pollImageStatus`, where status === "completed" (around the `setGeneratedImage(image)` line), add after the `clearInterval`:
```typescript
remove(image.id);
```
Import `remove` from the tracker hook: update the destructuring to include `remove`.

Do the same in `pollPromptCardImage` where status === "completed".

Also in both pollers' failure/timeout branches, add `remove(imageId)`.

**Step 5: Unsuppress on unmount**

In the existing cleanup `useEffect` (the one that sets `isMountedRef.current = false`), do NOT add unsuppress here — the `remove()` calls in the pollers already clean up. But if the user navigates away mid-generation (before polling completes), the global tracker needs to take over. So instead of `suppress`/`unsuppress`, we should only suppress while the local poller is actively running. The simplest approach: call `unsuppress(id)` in the unmount cleanup for any active generation.

Add a ref to track the current actively-polling image IDs:
```typescript
const activePollingIds = useRef<string[]>([]);
```

When calling `suppress(image.id)`, also push to `activePollingIds.current`.
In the unmount cleanup, call:
```typescript
activePollingIds.current.forEach((id) => unsuppress(id));
```

When a poller completes (success or failure), remove the id from `activePollingIds.current` and call `remove(id)`.

**Step 6: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds

**Step 7: Commit**

```bash
git add frontend/app/\(dashboard\)/images/generate/page.tsx
git commit -m "feat: integrate generation tracker into image generation page"
```

---

### Task 5: Integrate tracker into image gallery regeneration

**Files:**
- Modify: `frontend/app/(dashboard)/images/page.tsx`

**Step 1: Add imports and hooks**

```typescript
import { useGenerationTracker } from "@/stores/generation-tracker";
```

Inside the component, add:
```typescript
const { track, suppress, unsuppress, remove } = useGenerationTracker();
```

**Step 2: Track regeneration**

In `handleRegenerate` (around line 346), after `const image = await api.images.generate(...)`, add:
```typescript
track({ id: image.id, type: "image", status: "generating", title: regenPrompt.trim().slice(0, 60), startedAt: Date.now() });
suppress(image.id);
```

**Step 3: Remove on polling completion**

In the regeneration polling interval (around line 357-380), where `updated.status === "completed"`, add `remove(image.id)`.
Same for failure/timeout branches.

**Step 4: Unsuppress on unmount**

Same pattern as Task 4 — track active polling IDs, unsuppress on unmount.

**Step 5: Verify build and commit**

```bash
git add frontend/app/\(dashboard\)/images/page.tsx
git commit -m "feat: integrate generation tracker into image gallery regeneration"
```

---

### Task 6: Integrate tracker into article generation page

**Files:**
- Modify: `frontend/app/(dashboard)/articles/new/page.tsx`

**Step 1: Add imports and hooks**

```typescript
import { useGenerationTracker } from "@/stores/generation-tracker";
```

Inside the component, add:
```typescript
const { track, suppress, unsuppress, remove } = useGenerationTracker();
```

**Step 2: Track article generation**

In the `generateMutation.mutationFn` (around line 84), right after `const article = await api.articles.generate(...)`, add:
```typescript
track({ id: article.id, type: "article", status: "generating", title: outline?.title?.slice(0, 60) || outline?.keyword || "Article", startedAt: Date.now(), articleId: article.id });
suppress(article.id);
```

**Step 3: Remove on polling completion**

In the while loop (around line 113), when `updated.status === "completed" || "published"`, add before `return article.id`:
```typescript
remove(article.id);
```

Also add `remove(article.id)` in the failure case (line 117) before throwing.

And after the MAX_POLLS timeout (line 128-129), add `unsuppress(article.id)` (don't remove — let global tracker take over since it might still be running on the backend).

**Step 4: Unsuppress on unmount**

The existing `mountedRef` controls the while loop. When the component unmounts, `mountedRef.current = false` breaks the loop. At that point, the generation is still tracked globally. Add to the unmount cleanup:
```typescript
// Let global tracker take over for any in-progress generations
generations.filter(g => g.type === "article").forEach(g => unsuppress(g.id));
```

Or simpler: just call `unsuppress(article.id)` in the `onSettled` callback (line 143) only if the article status is still generating.

**Step 5: Verify build and commit**

```bash
git add frontend/app/\(dashboard\)/articles/new/page.tsx
git commit -m "feat: integrate generation tracker into article generation"
```

---

### Task 7: Integrate tracker into outline creation

**Files:**
- Modify: `frontend/app/(dashboard)/outlines/page.tsx`

**Step 1: Add imports and hooks**

```typescript
import { useGenerationTracker } from "@/stores/generation-tracker";
```

Inside the `CreateOutlineModal` component, add:
```typescript
const { track } = useGenerationTracker();
```

**Step 2: Track outline creation**

In the `createMutation` `onSuccess` callback (around line 570-572), the outline is created with `auto_generate: true`. The mutation returns the created outline. Modify:

```typescript
onSuccess: (outline) => {
  if (outline.status === "generating") {
    track({ id: outline.id, type: "outline", status: "generating", title: outline.keyword?.slice(0, 60) || "Outline", startedAt: Date.now() });
  }
  onCreate();
},
```

Note: Outline generation relies on React Query background refetching for status updates. The global tracker will independently poll `GET /outlines/{id}` and fire a toast when done. No suppress/unsuppress needed since the outline page doesn't do explicit polling.

**Step 3: Verify build and commit**

```bash
git add frontend/app/\(dashboard\)/outlines/page.tsx
git commit -m "feat: integrate generation tracker into outline creation"
```

---

### Task 8: Integrate tracker into bulk job creation

**Files:**
- Modify: `frontend/app/(dashboard)/bulk/page.tsx`

**Step 1: Add imports and hooks**

```typescript
import { useGenerationTracker } from "@/stores/generation-tracker";
```

Inside the component, add:
```typescript
const { track, suppress, unsuppress, remove } = useGenerationTracker();
```

**Step 2: Track bulk job creation**

In `handleCreate` (around line 116), after `const job = await api.bulk.createOutlineJob(...)`, add:
```typescript
track({ id: job.id, type: "bulk", status: "generating", title: `${job.total_items} keywords`, startedAt: Date.now() });
suppress(job.id);
```

**Step 3: Remove on local polling completion**

The bulk page has its own polling loop (controlled by `pollingActive`). In the polling `useEffect`, when a job reaches a terminal state (`completed`, `partially_failed`, `failed`, `cancelled`), call `remove(job.id)`.

**Step 4: Unsuppress on unmount**

In the cleanup of the polling `useEffect`, unsuppress all tracked bulk generation IDs so the global tracker takes over.

**Step 5: Verify build and commit**

```bash
git add frontend/app/\(dashboard\)/bulk/page.tsx
git commit -m "feat: integrate generation tracker into bulk job creation"
```

---

### Task 9: Final build verification and integration test

**Step 1: Full build**

Run: `cd frontend && npx next build 2>&1 | tail -10`
Expected: Build succeeds with no errors

**Step 2: Manual testing checklist**

- [ ] Start image generation → navigate away → see toast when done
- [ ] Start article generation → navigate away → see toast with "View" button → click navigates to article
- [ ] Start outline generation → navigate away → see toast when done
- [ ] Start bulk job → navigate away → see toast when done
- [ ] Stay on generation page → generation completes normally (no double toast)
- [ ] Close phone screen during generation → wake up → generation completes with toast
- [ ] Refresh page during generation → localStorage restores tracking → toast fires on completion

**Step 3: Commit**

```bash
git commit -m "feat: global generation tracker - complete integration"
```
