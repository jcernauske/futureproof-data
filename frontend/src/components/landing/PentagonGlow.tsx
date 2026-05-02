import { motion } from "framer-motion";

const AXES = [
  { label: "Earnings", abbr: "ERN", color: "var(--color-stat-ern)", labelClass: "top-[-18px] left-1/2 -translate-x-1/2" },
  { label: "ROI", abbr: "ROI", color: "var(--color-stat-roi)", labelClass: "top-[28%] right-[-52px]" },
  { label: "Resilience", abbr: "RES", color: "var(--color-stat-res)", labelClass: "bottom-[2%] right-[-24px]" },
  { label: "Growth", abbr: "GRW", color: "var(--color-stat-grw)", labelClass: "bottom-[2%] left-[-24px]" },
  { label: "Brand Gravity", abbr: "AURA", color: "var(--color-stat-aura)", labelClass: "top-[28%] left-[-52px]" },
] as const;

// Vertex positions in SVG coordinates (220x220 viewBox)
const VERTICES = [
  { cx: 110, cy: 22 },  // ERN - top
  { cx: 188, cy: 86 },  // ROI - top right
  { cx: 158, cy: 172 }, // RES - bottom right
  { cx: 62, cy: 172 },  // GRW - bottom left
  { cx: 32, cy: 86 },   // AURA - top left
];

// Decorative data shape vertices (slightly inward, asymmetric for visual interest)
const SHAPE_POINTS = "110,38 170,82 150,155 68,148 40,82";

// Floating particles along axis lines
const PARTICLES = VERTICES.flatMap((_, axisIdx) => [
  { axis: axisIdx, t: 0.3, delay: axisIdx * 1.2, dur: 3.5 },
  { axis: axisIdx, t: 0.6, delay: axisIdx * 1.2 + 1.8, dur: 4.2 },
]).map((p) => ({
  cx: 110 + (VERTICES[p.axis]!.cx - 110) * p.t,
  cy: 110 + (VERTICES[p.axis]!.cy - 110) * p.t,
  color: [
    "var(--color-stat-ern)",
    "var(--color-stat-roi)",
    "var(--color-stat-res)",
    "var(--color-stat-grw)",
    "var(--color-stat-aura)",
  ][p.axis]!,
  delay: p.delay,
  dur: p.dur,
}));

export function PentagonGlow({ size = 280 }: { size?: number }) {
  return (
    <motion.div
      className="relative"
      style={{ width: size, height: size }}
      animate={{ y: [0, -10, 0] }}
      transition={{ duration: 7, ease: "easeInOut", repeat: Infinity }}
    >
      {/* Stat labels — prominent, staggered fade-in */}
      {AXES.map((axis, i) => (
        <motion.span
          key={`label-${i}`}
          className={`absolute font-data text-micro tracking-[0.15em] uppercase ${axis.labelClass}`}
          style={{ color: axis.color }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.7 }}
          transition={{ duration: 1.2, delay: 0.8 + i * 0.15, ease: "easeOut" }}
        >
          {axis.label}
        </motion.span>
      ))}

      {/* Core glow — breathes behind the pentagon */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(circle at 50% 50%, var(--color-state-active) 0%, transparent 55%)",
        }}
        animate={{ opacity: [0.4, 0.8, 0.4], scale: [0.95, 1.05, 0.95] }}
        transition={{ duration: 5, ease: "easeInOut", repeat: Infinity }}
      />

      <svg
        viewBox="0 0 220 220"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
        className="w-full h-full relative"
        style={{ filter: "drop-shadow(0 0 50px var(--color-state-active))" }}
      >
        <defs>
          <linearGradient id="pgrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--color-accent-thrive)" stopOpacity="0.15" />
            <stop offset="50%" stopColor="var(--color-accent-insight)" stopOpacity="0.10" />
            <stop offset="100%" stopColor="var(--color-accent-caution)" stopOpacity="0.15" />
          </linearGradient>
          <radialGradient id="core-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--color-accent-thrive)" stopOpacity="0.08" />
            <stop offset="100%" stopColor="var(--color-accent-thrive)" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Inner core glow */}
        <circle cx="110" cy="110" r="90" fill="url(#core-glow)">
          <animate attributeName="r" values="85;95;85" dur="6s" repeatCount="indefinite" />
        </circle>

        {/* Grid rings — breathing */}
        <polygon points="110,22 188,86 158,172 62,172 32,86" fill="none" stroke="var(--color-text-muted)" strokeWidth="0.5" opacity="0.15">
          <animate attributeName="opacity" values="0.1;0.2;0.1" dur="5s" repeatCount="indefinite" />
        </polygon>
        <polygon points="110,46 164,92 144,160 76,160 56,92" fill="none" stroke="var(--color-text-muted)" strokeWidth="0.5" opacity="0.1">
          <animate attributeName="opacity" values="0.08;0.15;0.08" dur="6s" begin="0.5s" repeatCount="indefinite" />
        </polygon>
        <polygon points="110,70 140,98 130,148 90,148 80,98" fill="none" stroke="var(--color-text-muted)" strokeWidth="0.5" opacity="0.08">
          <animate attributeName="opacity" values="0.05;0.12;0.05" dur="7s" begin="1s" repeatCount="indefinite" />
        </polygon>

        {/* Axis lines */}
        {VERTICES.map((v, i) => (
          <line key={`axis-${i}`} x1="110" y1="110" x2={v.cx} y2={v.cy} stroke="var(--color-text-muted)" strokeWidth="0.5" opacity="0.2">
            <animate attributeName="opacity" values="0.15;0.3;0.15" dur={`${4 + i * 0.5}s`} repeatCount="indefinite" />
          </line>
        ))}

        {/* Decorative data shape */}
        <polygon
          points={SHAPE_POINTS}
          fill="url(#pgrad)"
          stroke="rgba(255,255,255,0.12)"
          strokeWidth="1"
          opacity="0.7"
        >
          <animate attributeName="opacity" values="0.5;0.8;0.5" dur="6s" repeatCount="indefinite" />
        </polygon>

        {/* Floating particles along axis lines */}
        {PARTICLES.map((p, i) => (
          <circle key={`particle-${i}`} cx={p.cx} cy={p.cy} r="1.5" fill={p.color}>
            <animate attributeName="opacity" values="0;0.6;0" dur={`${p.dur}s`} begin={`${p.delay}s`} repeatCount="indefinite" />
            <animate attributeName="r" values="1;2.5;1" dur={`${p.dur}s`} begin={`${p.delay}s`} repeatCount="indefinite" />
          </circle>
        ))}

        {/* Vertex dots with glow halos */}
        {VERTICES.map((v, i) => {
          const colors = [
            "var(--color-stat-ern)",
            "var(--color-stat-roi)",
            "var(--color-stat-res)",
            "var(--color-stat-grw)",
            "var(--color-stat-aura)",
          ];
          const delay = `${i * 0.8}s`;
          return (
            <g key={`vertex-${i}`}>
              {/* Outer glow halo */}
              <circle cx={v.cx} cy={v.cy} r="14" fill={colors[i]} opacity="0.08">
                <animate attributeName="opacity" values="0.05;0.15;0.05" dur="4s" begin={delay} repeatCount="indefinite" />
                <animate attributeName="r" values="12;16;12" dur="4s" begin={delay} repeatCount="indefinite" />
              </circle>
              {/* Inner glow */}
              <circle cx={v.cx} cy={v.cy} r="10" fill={colors[i]} opacity="0.15">
                <animate attributeName="opacity" values="0.1;0.25;0.1" dur="4s" begin={delay} repeatCount="indefinite" />
              </circle>
              {/* Core dot */}
              <circle cx={v.cx} cy={v.cy} r="5" fill={colors[i]} opacity="0.8">
                <animate attributeName="opacity" values="0.6;1;0.6" dur="4s" begin={delay} repeatCount="indefinite" />
              </circle>
            </g>
          );
        })}
      </svg>
    </motion.div>
  );
}
