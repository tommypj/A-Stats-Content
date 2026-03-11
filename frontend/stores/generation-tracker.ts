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

export const GENERATION_TIMEOUTS: Record<GenerationType, number> = {
  article: 12 * 60 * 1000,
  image: 3 * 60 * 1000,
  outline: 3 * 60 * 1000,
  bulk: 30 * 60 * 1000,
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
      }),
      onRehydrateStorage: () => (state) => {
        if (!state) return;
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
