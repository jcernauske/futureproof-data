import { motion, AnimatePresence } from "framer-motion";
import { useMemo } from "react";
import { Button } from "@/components/ui/Button";
import { useT } from "@/i18n/useT";
import { localizeProfileName } from "@/i18n/profileName";
import { useProfileStore } from "@/store/profileStore";
import { springs } from "@/styles/motion";
import { EMOJI_BG } from "@/components/build-results/bossData";

interface BuildLoadingScreenProps {
  animalEmoji: string;
  profileName: string;
  schoolName: string;
  majorTitle: string;
  buildingStage: number;
  buildingTotal: number;
  error: string | null;
  onRetry: () => void;
  onGoBack: () => void;
}

const STAT_VERTICES = [
  { key: "ern",  label: "ERN",  hex: "#F2D477", cx: 110, cy: 22,  nameKey: "forge.stat.ern.name",  loadingKey: "forge.stat.ern.loading"  },
  { key: "roi",  label: "ROI",  hex: "#7DD4A3", cx: 209, cy: 93,  nameKey: "forge.stat.roi.name",  loadingKey: "forge.stat.roi.loading"  },
  { key: "res",  label: "RES",  hex: "#B8A9E8", cx: 171, cy: 198, nameKey: "forge.stat.res.name",  loadingKey: "forge.stat.res.loading"  },
  { key: "grw",  label: "GRW",  hex: "#7BB8E0", cx: 49,  cy: 198, nameKey: "forge.stat.grw.name",  loadingKey: "forge.stat.grw.loading"  },
  { key: "aura", label: "AURA", hex: "#E8B86B", cx: 11,  cy: 93,  nameKey: "forge.stat.aura.name", loadingKey: "forge.stat.aura.loading" },
] as const;

const PENTAGON_POINTS = STAT_VERTICES.map(v => `${v.cx},${v.cy}`).join(" ");

const PENTAGON_RADIUS = 95;

const EDGES = [
  { fromIdx: 4, toIdx: 0 },
  { fromIdx: 0, toIdx: 1 },
  { fromIdx: 1, toIdx: 2 },
  { fromIdx: 2, toIdx: 3 },
  { fromIdx: 3, toIdx: 4 },
] as const;

const EDGE_LENGTHS = EDGES.map(e => {
  const from = STAT_VERTICES[e.fromIdx]!;
  const to = STAT_VERTICES[e.toIdx]!;
  return Math.sqrt((to.cx - from.cx) ** 2 + (to.cy - from.cy) ** 2);
});

export function BuildLoadingScreen({
  animalEmoji,
  profileName,
  schoolName,
  majorTitle,
  buildingStage,
  buildingTotal,
  error,
  onRetry,
  onGoBack,
}: BuildLoadingScreenProps) {
  const t = useT();
  const locale = useProfileStore((s) => s.locale);
  const isIndeterminate = buildingTotal === 0;
  const pct = isIndeterminate ? 0 : Math.min(buildingStage / buildingTotal, 1);
  const emojiBg = EMOJI_BG[animalEmoji] ?? "var(--color-accent-info)";
  const displayName = localizeProfileName(profileName, locale);

  const activeEdgeIndex = pct > 0 ? Math.min(Math.floor(pct * 5), 4) : -1;
  const edgePct = activeEdgeIndex >= 0 ? Math.min((pct * 5) - activeEdgeIndex, 1) : 0;

  const litVertices = useMemo(() => {
    const lit = new Set<number>();
    for (let i = 0; i < EDGES.length; i++) {
      if (i < activeEdgeIndex || (i === activeEdgeIndex && edgePct >= 1)) {
        lit.add(EDGES[i]!.toIdx);
      }
    }
    return lit;
  }, [activeEdgeIndex, edgePct]);

  const activeStat = activeEdgeIndex >= 0 ? STAT_VERTICES[EDGES[activeEdgeIndex]!.toIdx] : null;

  return (
    <div className="min-h-screen pt-14 flex flex-col items-center justify-center" style={{ minHeight: "100dvh" }}>
      <div className="flex flex-col items-center py-8" style={{ maxWidth: 400 }}>
        {/* Avatar */}
        <motion.div
          className="rounded-full flex items-center justify-center border-2 border-border-default"
          style={{
            width: 120,
            height: 120,
            background: emojiBg,
            boxShadow: "0 0 30px 6px rgba(125,212,163,0.15), 0 0 60px 12px rgba(184,169,232,0.08)",
          }}
          initial={{ opacity: 0, scale: 0.7 }}
          animate={{ opacity: 1, scale: 1, y: [0, -6, 0] }}
          transition={{
            opacity: { duration: 0.6, ease: "easeOut" },
            scale: { ...springs.bouncy, duration: 0.8 },
            y: { duration: 4, ease: "easeInOut", repeat: Infinity, delay: 0.8 },
          }}
        >
          <span style={{ fontSize: 72, lineHeight: 1 }}>{animalEmoji}</span>
        </motion.div>

        {/* Identity inscription */}
        <motion.div
          className="text-center mt-3"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, ...springs.smooth }}
        >
          <p className="font-display font-semibold text-text-primary" style={{ fontSize: 24 }}>
            <bdi dir="auto">{displayName}</bdi>
          </p>
          <motion.p
            className="font-body text-text-secondary mt-1"
            style={{ fontSize: 16 }}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7, ...springs.smooth }}
          >
            {majorTitle} at {schoolName}
          </motion.p>
        </motion.div>

        {/* Ghost Pentagon + Progress Arc */}
        <motion.div
          className="relative mt-6"
          style={{ width: 280, height: 280 }}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1.0, ...springs.smooth }}
        >
          <svg
            viewBox="-54 -28 304 280"
            width={280}
            height={280}
            data-testid="build-loading-pentagon"
          >
            {/* Ghost pentagon wireframe */}
            <polygon
              points={PENTAGON_POINTS}
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth={1}
            />

            {/* Animated edge traces */}
            {EDGES.map((edge, i) => {
              if (i > activeEdgeIndex) return null;
              const from = STAT_VERTICES[edge.fromIdx]!;
              const to = STAT_VERTICES[edge.toIdx]!;
              const length = EDGE_LENGTHS[i]!;
              const isComplete = i < activeEdgeIndex || (i === activeEdgeIndex && edgePct >= 1);
              const offset = isComplete ? 0 : length * (1 - edgePct);
              return (
                <motion.line
                  key={`trace-${i}`}
                  x1={from.cx} y1={from.cy}
                  x2={to.cx} y2={to.cy}
                  stroke={to.hex}
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeDasharray={length}
                  animate={{ strokeDashoffset: offset, opacity: isComplete ? 0.45 : 0.8 }}
                  transition={{ type: "spring", stiffness: 80, damping: 15 }}
                />
              );
            })}

            {/* Vertex dots + glow */}
            {STAT_VERTICES.map((v, i) => {
              const isLit = litVertices.has(i);
              return (
                <g key={v.key}>
                  {isLit && (
                    <motion.circle
                      cx={v.cx} cy={v.cy}
                      fill={v.hex}
                      initial={{ r: 4, opacity: 0 }}
                      animate={{ r: [4, 18, 14], opacity: [0, 0.4, 0.15] }}
                      transition={{ duration: 0.8, ease: "easeOut" }}
                      style={{ filter: "blur(6px)" }}
                    />
                  )}
                  <motion.circle
                    cx={v.cx} cy={v.cy}
                    fill={isLit ? v.hex : "rgba(255,255,255,0.25)"}
                    initial={{ r: 4 }}
                    animate={isLit
                      ? { r: [4, 10, 6, 7], opacity: [0.25, 1, 0.9, 0.95] }
                      : { r: 4, opacity: 0.25 }
                    }
                    transition={isLit
                      ? { duration: 0.6, ease: [0.34, 1.56, 0.64, 1], times: [0, 0.4, 0.7, 1] }
                      : { duration: 0.3 }
                    }
                  />
                </g>
              );
            })}

            {/* Vertex labels */}
            {STAT_VERTICES.map((v, i) => {
              const isLit = litVertices.has(i);
              const labelOffset = 36;
              const angle = (-Math.PI / 2) + (2 * Math.PI * i / 5);
              const lx = 110 + (PENTAGON_RADIUS + labelOffset) * Math.cos(angle);
              const ly = 110 + (PENTAGON_RADIUS + labelOffset) * Math.sin(angle);
              return (
                <text
                  key={`label-${v.key}`}
                  x={lx} y={ly}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fill={isLit ? v.hex : "var(--color-text-muted)"}
                  opacity={isLit ? 0.85 : 0.4}
                  style={{
                    fontFamily: "'Space Mono', monospace",
                    fontSize: 13,
                    fontWeight: 600,
                    letterSpacing: 1,
                    transition: "fill 0.4s ease-out, opacity 0.4s ease-out",
                  }}
                >
                  {v.label}
                </text>
              );
            })}
          </svg>
        </motion.div>

        {/* Stat loading text */}
        <div className="relative mt-4" style={{ height: 56, width: "100%", maxWidth: 360 }}>
          <AnimatePresence mode="wait">
            {activeStat && !error && (
              <motion.div
                key={activeStat.key}
                className="absolute inset-0 flex flex-col items-center justify-center text-center"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ type: "spring", stiffness: 200, damping: 25 }}
              >
                <span
                  className="font-display font-semibold"
                  style={{ fontSize: 15, color: activeStat.hex, letterSpacing: 2, textTransform: "uppercase" as const }}
                >
                  {t(activeStat.nameKey)}
                </span>
                <motion.span
                  className="font-body text-text-secondary mt-1"
                  style={{ fontSize: 14, lineHeight: 1.4 }}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.15, type: "spring", stiffness: 200, damping: 25 }}
                >
                  {t(activeStat.loadingKey)}
                </motion.span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Error state */}
        {error && (
          <motion.div
            className="mt-8 bg-bp-mid rounded-xl p-8 border border-border-subtle max-w-md mx-auto text-center"
            style={{ borderLeftWidth: 3, borderLeftColor: "var(--color-accent-alert)" }}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={springs.smooth}
          >
            <div style={{ fontSize: 36 }}>&#x1F4AB;</div>
            <p className="font-body text-text-secondary mt-3" style={{ fontSize: 15, lineHeight: 1.5 }}>
              {t("build.error")}
            </p>
            <div className="flex gap-3 justify-center mt-5">
              <Button variant="primary" onClick={onRetry}>{t("build.tryAgain")}</Button>
              <Button variant="ghost" onClick={onGoBack}>{t("build.goBack")}</Button>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
