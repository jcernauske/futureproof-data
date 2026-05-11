import { create } from "zustand";
import { fetchHealth } from "@/api/health";

export type InferenceBackend = "ollama" | "openrouter" | "unknown";

interface InferenceState {
  backend: InferenceBackend;
  model: string | null;
  modelReachable: boolean;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

let refreshSeq = 0;

function normalizeBackend(value: string): InferenceBackend {
  if (value === "ollama" || value === "openrouter") return value;
  return "unknown";
}

export const useInferenceStore = create<InferenceState>((set) => ({
  backend: "unknown",
  model: null,
  modelReachable: true,
  loading: false,
  error: null,
  refresh: async () => {
    const myId = ++refreshSeq;
    set({ loading: true, error: null });
    try {
      const data = await fetchHealth();
      if (myId !== refreshSeq) return;
      set({
        backend: normalizeBackend(data.inference_backend),
        model: data.inference_model || null,
        modelReachable: data.model_reachable,
        loading: false,
        error: null,
      });
    } catch (e) {
      if (myId !== refreshSeq) return;
      set({
        loading: false,
        error: e instanceof Error ? e.message : "Failed to load inference backend",
      });
    }
  },
}));
