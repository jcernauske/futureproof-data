import { useEffect } from "react";
import { useInferenceStore } from "@/store/inferenceStore";
import { useT } from "@/i18n/useT";

interface InferenceBadgeProps {
  className?: string;
}

// Pulls the parameter size out of a model identifier so the badge can
// distinguish Gemma 4B-on-Ollama from Gemma 26B-on-OpenRouter at a glance.
// MoE slugs like ``google/gemma-4-26b-a4b-it`` carry both total (26b) and
// active (a4b) sizes — we pick the largest match because users care about
// total parameters, not active.
export function extractParameterSize(model: string | null | undefined): string | null {
  if (!model) return null;
  const matches = [...model.matchAll(/(\d+)b/gi)];
  if (matches.length === 0) return null;
  const sizes = matches
    .map((m) => parseInt(m[1] ?? "", 10))
    .filter((n) => Number.isFinite(n) && n > 0);
  if (sizes.length === 0) return null;
  return `${Math.max(...sizes)}B`;
}

export function InferenceBadge({ className = "" }: InferenceBadgeProps) {
  const t = useT();
  const backend = useInferenceStore((s) => s.backend);
  const model = useInferenceStore((s) => s.model);
  const loading = useInferenceStore((s) => s.loading);
  const error = useInferenceStore((s) => s.error);
  const refresh = useInferenceStore((s) => s.refresh);

  useEffect(() => {
    if (backend === "unknown" && !loading && !error) {
      refresh();
    }
  }, [backend, loading, error, refresh]);

  if (backend === "unknown") return null;

  const isOllama = backend === "ollama";
  const label = isOllama
    ? t("header.inferenceLocalLabel")
    : t("header.inferenceCloudLabel");
  const size = extractParameterSize(model);
  const dotClass = isOllama ? "bg-accent-thrive" : "bg-accent-insight";
  const ringClass = isOllama
    ? "ring-1 ring-accent-thrive/30"
    : "ring-1 ring-accent-insight/30";
  const titleTemplate = isOllama
    ? t("header.inferenceLocalTitle")
    : t("header.inferenceCloudTitle");
  const title = titleTemplate.replace("{model}", model ?? "—");

  return (
    <span
      data-testid="inference-badge"
      data-backend={backend}
      data-model-size={size ?? ""}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-bp-surface/40 ${ringClass} font-body text-micro text-text-secondary leading-none ${className}`}
      title={title}
      aria-label={title}
    >
      <span
        aria-hidden="true"
        className={`block w-1.5 h-1.5 rounded-full ${dotClass}`}
      />
      <span>{label}</span>
      {size && (
        <>
          <span aria-hidden="true" className="text-text-muted">·</span>
          <span className="text-text-primary font-data">{size}</span>
        </>
      )}
    </span>
  );
}
