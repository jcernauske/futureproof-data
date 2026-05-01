import { create } from "zustand";
import { listBuilds } from "@/api/menu";

interface BuildsCountState {
  count: number | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

// Concurrency token: every refresh() bumps it; only the most recent call is
// allowed to commit. Out-of-order responses (e.g., rapid delete after a slow
// initial fetch) can no longer stomp the fresher count.
let refreshSeq = 0;

export const useBuildsCountStore = create<BuildsCountState>((set) => ({
  count: null,
  loading: false,
  error: null,
  refresh: async () => {
    const myId = ++refreshSeq;
    set({ loading: true, error: null });
    try {
      const builds = await listBuilds();
      if (myId !== refreshSeq) return;
      set({ count: builds.length, loading: false, error: null });
    } catch (e) {
      if (myId !== refreshSeq) return;
      set({
        loading: false,
        error: e instanceof Error ? e.message : "Failed to load builds count",
      });
    }
  },
}));

export function useBuildsCount(): number | null {
  return useBuildsCountStore((s) => s.count);
}
