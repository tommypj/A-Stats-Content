# Global Generation Tracker — Design

## Goal

Prevent generation failures when users navigate away from generation pages or when phones enter standby. Track all active generations globally, poll in the background, and notify via toast when complete.

## Architecture

Zustand store with localStorage persistence + a React provider component mounted at the dashboard layout level. Page components register generations with the store; the provider handles background polling and toast notifications.

## Store

```typescript
type GenerationType = "article" | "image" | "outline" | "bulk";
type GenerationStatus = "generating" | "completed" | "failed";

interface TrackedGeneration {
  id: string;
  type: GenerationType;
  status: GenerationStatus;
  title: string;
  startedAt: number;
  articleId?: string;
  imageId?: string;
}

interface GenerationTrackerState {
  generations: TrackedGeneration[];
  suppressedIds: Set<string>;
  track: (gen: TrackedGeneration) => void;
  update: (id: string, updates: Partial<TrackedGeneration>) => void;
  remove: (id: string) => void;
  clear: () => void;
  suppress: (id: string) => void;
  unsuppress: (id: string) => void;
}
```

## Polling Provider

`GenerationTrackerProvider` wraps the dashboard layout. Single `setInterval` (2s) iterates all active generations. For each:
- Skip if id is in `suppressedIds` (page is handling its own polling)
- Call appropriate status endpoint (GET /images/{id}, GET /articles/{id}, etc.)
- On completion/failure: update store, fire toast, remove from tracker

Bulk jobs: poll GET /bulk/jobs/{id} at 5s effective rate (skip every other tick).

## Timeouts

| Type | Max Duration |
|------|-------------|
| Article | 12 minutes |
| Image | 3 minutes |
| Outline | 3 minutes |
| Bulk | 30 minutes |

Stale generations (older than timeout) cleaned up on app load.

## Toast Behavior

| Type | Toast | Click Action |
|------|-------|-------------|
| Article | "Article ready: {title}" | Navigate to /articles/{id} |
| Image | "Image generated: {title}" | Navigate to /images |
| Outline | "Outline ready: {title}" | Dismiss only |
| Bulk | "Bulk job completed" | Dismiss only |

## Integration

Each page adds one call when starting generation:
```typescript
useGenerationTracker().track({ id, type, status: "generating", title });
```

Pages call `suppress(id)` on mount, `unsuppress(id)` on unmount to avoid double-polling.

## localStorage Persistence

Zustand `persist` middleware (same pattern as useAuthStore). On hydration, clean up any generations older than their type's timeout.

## Scope

- Option A: page components own their UI when user is on the page; global tracker only provides background polling + notifications when navigated away.
- Applies to all 4 flows: article, image, outline, bulk.
- Clickable toasts for articles and images only (they have detail pages).
