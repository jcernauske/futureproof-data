import { motion } from "framer-motion";
import { springs } from "@/styles/motion";
import type { CompareResult, CompareStatRow } from "@/api/menu";

interface PentagonOverlayProps {
  result: CompareResult;
  size?: number;
}

const BUILD_COLORS = [
  "var(--color-accent-thrive)",
  "var(--color-accent-info)",
  "var(--color-accent-empathy)",
];

const STAT_ORDER = ["ERN", "ROI", "RES", "GRW", "HMN"] as const;
const CENTER = 110;
const RADIUS = 88;

function vertexPos(i: number, radius: number): [number, number] {
  const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2;
  return [CENTER + radius * Math.cos(angle), CENTER + radius * Math.sin(angle)];
}

function gridPolygon(scale: number): string {
  return Array.from({ length: 5 })
    .map((_, i) => vertexPos(i, RADIUS * scale).join(","))
    .join(" ");
}

function statRowsByLabel(stats: CompareStatRow[]): Record<string, CompareStatRow> {
  const map: Record<string, CompareStatRow> = {};
  for (const row of stats) map[row.label] = row;
  return map;
}

function buildPolygon(stats: CompareStatRow[], buildIndex: number): string {
  const rows = statRowsByLabel(stats);
  return STAT_ORDER.map((label, i) => {
    const v = rows[label]?.values[buildIndex] ?? 0;
    const clamped = Math.max(0, Math.min(10, v));
    return vertexPos(i, RADIUS * (clamped / 10)).join(",");
  }).join(" ");
}

export function PentagonOverlay({ result, size = 280 }: PentagonOverlayProps) {
  return (
    <div className="flex flex-col items-center gap-4">
      <div
        role="img"
        aria-label={`Pentagon overlay comparing ${result.builds.length} builds`}
        data-testid="svg-pentagon-overlay"
        style={{ width: size, height: size }}
      >
        <svg viewBox="0 0 220 220" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
          {[1, 0.75, 0.5, 0.25].map((scale, i) => (
            <polygon
              key={`grid-${i}`}
              points={gridPolygon(scale)}
              fill="none"
              stroke="var(--color-text-muted)"
              strokeWidth="0.5"
              opacity={0.15}
            />
          ))}
          {STAT_ORDER.map((_, i) => {
            const [x, y] = vertexPos(i, RADIUS);
            return (
              <line
                key={`axis-${i}`}
                x1={CENTER}
                y1={CENTER}
                x2={x}
                y2={y}
                stroke="var(--color-text-muted)"
                strokeWidth="0.5"
                opacity="0.20"
              />
            );
          })}

          {result.builds.map((build, idx) => {
            const color = BUILD_COLORS[idx % BUILD_COLORS.length]!;
            const points = buildPolygon(result.stats, idx);
            const drawDelay = idx * 0.2;
            return (
              <motion.g
                key={`shape-${build.build_id}`}
                initial={{ opacity: 0, scale: 0.92 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ ...springs.smooth, delay: drawDelay }}
                style={{ transformOrigin: `${CENTER}px ${CENTER}px` }}
                data-testid={`overlay-shape-${idx}`}
              >
                <polygon
                  points={points}
                  fill={color}
                  fillOpacity="0.20"
                  stroke={color}
                  strokeOpacity="0.7"
                  strokeWidth="1.5"
                />
                {STAT_ORDER.map((label, i) => {
                  const v = statRowsByLabel(result.stats)[label]?.values[idx] ?? 0;
                  const clamped = Math.max(0, Math.min(10, v));
                  const [cx, cy] = vertexPos(i, RADIUS * (clamped / 10));
                  return (
                    <circle
                      key={`dot-${idx}-${i}`}
                      cx={cx}
                      cy={cy}
                      r="3"
                      fill={color}
                      opacity={0.9}
                    />
                  );
                })}
              </motion.g>
            );
          })}

          {STAT_ORDER.map((label, i) => {
            const [x, y] = vertexPos(i, RADIUS + 14);
            return (
              <text
                key={`label-${i}`}
                x={x}
                y={y}
                textAnchor="middle"
                dominantBaseline="middle"
                className="font-data"
                style={{
                  fontSize: 10,
                  fill: "var(--color-text-muted)",
                  letterSpacing: "0.15em",
                }}
              >
                {label}
              </text>
            );
          })}
        </svg>
      </div>

      <div
        className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2"
        data-testid="overlay-legend"
      >
        {result.builds.map((b, idx) => (
          <div key={b.build_id} className="flex items-center gap-2">
            <span
              className="w-3 h-3 rounded-full"
              style={{ background: BUILD_COLORS[idx % BUILD_COLORS.length] }}
            />
            <span className="font-body text-small text-text-secondary">{b.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
