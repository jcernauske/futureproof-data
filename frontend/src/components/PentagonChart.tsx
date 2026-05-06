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
  onHoverStat?: (key: StatKey | null) => void;
}

const AXES: { key: StatKey; label: string; color: string }[] = [
  { key: "ern", label: "ERN", color: "var(--color-stat-ern)" },
  { key: "roi", label: "ROI", color: "var(--color-stat-roi)" },
  { key: "res", label: "RES", color: "var(--color-stat-res)" },
  { key: "grw", label: "GRW", color: "var(--color-stat-grw)" },
  { key: "aura", label: "AURA", color: "var(--color-stat-aura)" },
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
  // Missing-data treatment (revised after user feedback 2026-05-02):
  // Null vertices collapse to radius 0 (center) so the polygon visibly
  // shrinks at missing axes. Earlier "anchor at outer perimeter"
  // treatment misread as "high score everywhere" because the polygon
  // fill dominated the visual weight, even with hollow ring + em-dash
  // label hints. Honest visual: missing data should not inflate the
  // shape. The em-dash label below the vertex carries the
  // "missing, not zero-scored" signal.
  const keys: StatKey[] = ["ern", "roi", "res", "grw", "aura"];
  return keys
    .map((key, i) => {
      const raw = stats[key];
      const val = raw === null || raw === undefined
        ? 0
        : Math.max(0, Math.min(10, raw));
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
  onHoverStat,
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
                      const rawVal = overlay.stats[axis.key];
                      // Missing values render at center (radius 0) with
                      // no dot — consistent with the single-shape branch.
                      if (rawVal === null || rawVal === undefined) {
                        return <motion.g key={`dot-${idx}-${i}`} />;
                      }
                      const val = Math.max(0, Math.min(10, rawVal));
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
              const rawVal = stats[axis.key];
              const isAbsent = rawVal === null || rawVal === undefined;
              // Missing vertices render at radius 0 (center) — no dot at
              // the outer perimeter to mislead the viewer. The em-dash
              // label below the axis carries the missing signal.
              if (isAbsent) {
                return (
                  <motion.g
                    key={`dot-${i}`}
                    data-stat={axis.key}
                    data-state="absent"
                  />
                );
              }
              const val = Math.max(0, Math.min(10, rawVal));
              const [cx, cy] = vertexPos(i, RADIUS * (val / 10));
              const isHighlighted = highlightStat === null || highlightStat === axis.key;
              const isActive = highlightStat === axis.key;
              const dotOpacity = isHighlighted ? 1 : dimOpacity;

              return (
                <motion.g
                  key={`dot-${i}`}
                  data-stat={axis.key}
                  initial={animated ? { opacity: 0, scale: 0 } : undefined}
                  animate={{
                    opacity: dotOpacity,
                    scale: isActive ? [1, 1.3, 1] : 1,
                  }}
                  transition={animated && !isActive
                    ? { ...springs.bouncy, delay: delay + 0.5 + i * 0.15 }
                    : isActive
                      ? { scale: { duration: 1.2, repeat: Infinity, ease: "easeInOut" } }
                      : undefined}
                  style={{ transformOrigin: `${cx}px ${cy}px` }}
                >
                  {isActive && (
                    <circle cx={cx} cy={cy} r="14" fill={axis.color} opacity="0.08">
                      <animate attributeName="r" values="10;18;10" dur="1.2s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="0.12;0.03;0.12" dur="1.2s" repeatCount="indefinite" />
                    </circle>
                  )}
                  <circle cx={cx} cy={cy} r="10" fill={axis.color} opacity="0.12" />
                  <circle cx={cx} cy={cy} r="5" fill={axis.color} opacity="0.9" />
                  {onHoverStat && (
                    <circle
                      cx={cx} cy={cy} r="16"
                      fill="transparent"
                      style={{ cursor: "pointer" }}
                      onMouseEnter={() => onHoverStat(axis.key)}
                      onMouseLeave={() => onHoverStat(null)}
                    />
                  )}
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
        const rawVal = stats[axis.key];
        const isAbsent = rawVal === null || rawVal === undefined;

        return (
          <motion.div
            key={`label-${i}`}
            data-stat-label={axis.key}
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
            {/* Missing-data label: "AURA —" with em-dash suffix per §3.
                The em-dash is read by screen readers as "AURA dash" —
                sufficient signal that there's no number here. */}
            {isAbsent ? `${axis.label} —` : axis.label}
            {!isOverlayMode && !isAbsent && (
              <div className="font-data text-data-sm font-bold mt-0.5" style={{ color: axis.color }}>
                {rawVal}
              </div>
            )}
          </motion.div>
        );
      })}
    </motion.div>
  );
}
