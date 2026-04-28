import { motion } from "framer-motion";
import { springs } from "@/styles/motion";
import type { PentagonStats } from "@/types/build";
import type { StatKey } from "@/data/statExplanations";

export interface PentagonOverlayShape {
  stats: PentagonStats;
  color: string;
  dimmed?: boolean;
}

interface PentagonChartProps {
  stats: PentagonStats;
  size?: number;
  animated?: boolean;
  delay?: number;
  highlightStat?: StatKey | null;
  dimOpacity?: number;
  overlays?: PentagonOverlayShape[];
}

const AXES: { key: StatKey; label: string; color: string }[] = [
  { key: "ern", label: "ERN", color: "var(--color-stat-ern)" },
  { key: "roi", label: "ROI", color: "var(--color-stat-roi)" },
  { key: "res", label: "RES", color: "var(--color-stat-res)" },
  { key: "grw", label: "GRW", color: "var(--color-stat-grw)" },
  { key: "hmn", label: "HMN", color: "var(--color-stat-hmn)" },
];

const CENTER = 110;
const RADIUS = 88;

function vertexPos(index: number, radius: number): [number, number] {
  const angle = (Math.PI * 2 * index) / 5 - Math.PI / 2;
  return [CENTER + radius * Math.cos(angle), CENTER + radius * Math.sin(angle)];
}

function gridPolygon(scale: number): string {
  return Array.from({ length: 5 })
    .map((_, i) => vertexPos(i, RADIUS * scale).join(","))
    .join(" ");
}

function dataPolygon(stats: PentagonStats): string {
  const keys: StatKey[] = ["ern", "roi", "res", "grw", "hmn"];
  return keys
    .map((key, i) => {
      const val = Math.max(0, Math.min(10, stats[key] ?? 0));
      return vertexPos(i, RADIUS * (val / 10)).join(",");
    })
    .join(" ");
}

export function PentagonChart({
  stats,
  size = 280,
  animated = true,
  delay = 0,
  highlightStat = null,
  dimOpacity = 1,
  overlays,
}: PentagonChartProps) {
  const isOverlayMode = overlays && overlays.length > 0;
  return (
    <motion.div
      id="svg-pentagon"
      role="img"
      aria-label="Five-stat radar chart showing your career stats"
      className="relative"
      style={{ width: size, height: size }}
      initial={animated ? { scale: 0, opacity: 0 } : undefined}
      animate={{ scale: 1, opacity: 1 }}
      transition={animated ? { ...springs.smooth, delay } : undefined}
    >
      <svg viewBox="0 0 220 220" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
        <defs>
          <linearGradient id="data-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--color-accent-thrive)" stopOpacity="0.2" />
            <stop offset="50%" stopColor="var(--color-accent-insight)" stopOpacity="0.15" />
            <stop offset="100%" stopColor="var(--color-accent-caution)" stopOpacity="0.2" />
          </linearGradient>
        </defs>

        {/* Grid rings — uniform 0.15 per DESIGN.md Pentagon spec */}
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

        {/* Axis lines */}
        {AXES.map((_, i) => {
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

        {isOverlayMode ? (
          <>
            {/* Render dimmed shapes first, highlighted last so it's on top */}
            {[...overlays.entries()]
              .sort(([, a], [, b]) => (a.dimmed ? 0 : 1) - (b.dimmed ? 0 : 1))
              .map(([idx, overlay]) => {
                const dimmed = overlay.dimmed ?? false;
                const shapeOpacity = dimmed ? 0.15 : 0.85;
                const drawDelay = delay + idx * 0.2;
                return (
                  <motion.g key={`overlay-${idx}`} data-testid={`overlay-shape-${idx}`}>
                    <motion.polygon
                      points={dataPolygon(overlay.stats)}
                      fill={overlay.color}
                      fillOpacity={dimmed ? 0.05 : 0.15}
                      stroke={overlay.color}
                      strokeOpacity={dimmed ? 0.2 : 0.6}
                      strokeWidth="1.5"
                      initial={animated ? { opacity: 0 } : undefined}
                      animate={{ opacity: shapeOpacity }}
                      transition={{ duration: 0.2, delay: animated ? drawDelay : 0 }}
                    />
                    {AXES.map((axis, i) => {
                      const val = Math.max(0, Math.min(10, overlay.stats[axis.key] ?? 0));
                      const [cx, cy] = vertexPos(i, RADIUS * (val / 10));
                      return (
                        <motion.g
                          key={`dot-${idx}-${i}`}
                          initial={animated ? { opacity: 0, scale: 0 } : undefined}
                          animate={{ opacity: dimmed ? 0.2 : 1, scale: 1 }}
                          transition={animated
                            ? { ...springs.bouncy, delay: drawDelay + 0.3 + i * 0.08 }
                            : { duration: 0.2 }}
                          style={{ transformOrigin: `${cx}px ${cy}px` }}
                        >
                          <circle cx={cx} cy={cy} r="10" fill={overlay.color} opacity="0.12" />
                          <circle cx={cx} cy={cy} r="5" fill={overlay.color} opacity="0.9" />
                        </motion.g>
                      );
                    })}
                  </motion.g>
                );
              })}
          </>
        ) : (
          <>
            <motion.polygon
              points={dataPolygon(stats)}
              fill="url(#data-grad)"
              stroke="var(--color-border-strong)"
              strokeWidth="1.5"
              initial={animated ? { opacity: 0 } : undefined}
              animate={{ opacity: 0.85 }}
              transition={animated ? { duration: 2, delay: delay + 0.3 } : undefined}
            />
            {AXES.map((axis, i) => {
              const val = Math.max(0, Math.min(10, stats[axis.key] ?? 0));
              const [cx, cy] = vertexPos(i, RADIUS * (val / 10));
              const isHighlighted = highlightStat === null || highlightStat === axis.key;
              const dotOpacity = isHighlighted ? 1 : dimOpacity;

              return (
                <motion.g
                  key={`dot-${i}`}
                  initial={animated ? { opacity: 0, scale: 0 } : undefined}
                  animate={{ opacity: dotOpacity, scale: 1 }}
                  transition={animated ? { ...springs.bouncy, delay: delay + 0.5 + i * 0.15 } : undefined}
                  style={{ transformOrigin: `${cx}px ${cy}px` }}
                >
                  <circle cx={cx} cy={cy} r="10" fill={axis.color} opacity="0.12" />
                  <circle cx={cx} cy={cy} r="5" fill={axis.color} opacity="0.9" />
                </motion.g>
              );
            })}
          </>
        )}
      </svg>

      {/* Stat labels */}
      {AXES.map((axis, i) => {
        const [x, y] = vertexPos(i, RADIUS + 18);
        const isHighlighted = highlightStat === null || highlightStat === axis.key;
        const pctX = (x / 220) * 100;
        const pctY = (y / 220) * 100;

        return (
          <motion.div
            key={`label-${i}`}
            className="absolute font-data text-micro tracking-[0.15em] uppercase text-center"
            style={{
              color: axis.color,
              left: `${pctX}%`,
              top: `${pctY}%`,
              transform: "translate(-50%, -50%)",
              opacity: isHighlighted ? 0.8 : dimOpacity * 0.4,
            }}
            initial={animated ? { opacity: 0 } : undefined}
            animate={{ opacity: isHighlighted ? 0.8 : dimOpacity * 0.4 }}
            transition={animated ? { duration: 1, delay: delay + 0.8 + i * 0.1 } : undefined}
          >
            {axis.label}
            {!isOverlayMode && (
              <div className="font-data text-data-sm font-bold mt-0.5" style={{ color: axis.color }}>
                {stats[axis.key] ?? "—"}
              </div>
            )}
          </motion.div>
        );
      })}
    </motion.div>
  );
}
