import { apiGet } from "@/api/client";

export interface HealthResponse {
  status: string;
  project: string;
  version: string;
  inference_backend: "ollama" | "openrouter" | string;
  inference_model: string;
}

export function fetchHealth(): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/health");
}
