import type { BuildSummary } from "@/api/menu";

interface MiniPentagonProps {
  stats: Pick<BuildSummary, "ern" | "roi" | "res" | "grw" | "aura">;
  size?: number;
}

const KEYS: (keyof MiniPentagonProps["stats"])[] = ["ern", "roi", "res", "grw", "aura"];

function vertex(i: number, radius: number, center: number): [number, number] {
  const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2;
  return [center + radius * Math.cos(angle), center + radius * Math.sin(angle)];
}

export function MiniPentagon({ stats, size = 40 }: MiniPentagonProps) {
  const center = size / 2;
  const maxRadius = size / 2 - 1;

  const gridPoints = Array.from({ length: 5 })
    .map((_, i) => vertex(i, maxRadius, center).join(","))
    .join(" ");

  // Missing-data treatment (revised after user feedback 2026-05-02):
  // Null vertices collapse to radius 0 (center). Earlier "anchor at
  // outer perimeter" treatment misread as "high score everywhere"
  // because the polygon fill dominated. Honest visual: the polygon
  // visibly shrinks at missing axes.
  const dataPoints = KEYS.map((key, i) => {
    const raw = stats[key];
    const v = raw === null || raw === undefined
      ? 0
      : Math.max(0, Math.min(10, raw));
    return vertex(i, maxRadius * (v / 10), center).join(",");
  }).join(" ");

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label="Mini pentagon stat shape"
    >
      <polygon
        points={gridPoints}
        fill="var(--color-bg-deep)"
        stroke="var(--color-text-muted)"
        strokeOpacity="0.15"
        strokeWidth="0.6"
      />
      <polygon
        points={dataPoints}
        fill="var(--color-accent-thrive)"
        fillOpacity="0.35"
        stroke="var(--color-accent-thrive)"
        strokeOpacity="0.7"
        strokeWidth="0.8"
      />
    </svg>
  );
}
