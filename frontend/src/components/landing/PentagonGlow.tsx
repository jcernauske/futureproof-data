import { motion } from "framer-motion";

const AXES = [
  { label: "Earnings", color: "var(--color-stat-ern)", labelClass: "top-[-4px] left-1/2 -translate-x-1/2" },
  { label: "ROI", color: "var(--color-stat-roi)", labelClass: "top-[32%] right-[-44px]" },
  { label: "Resilience", color: "var(--color-stat-res)", labelClass: "bottom-[6%] right-[-16px]" },
  { label: "Growth", color: "var(--color-stat-grw)", labelClass: "bottom-[6%] left-[-16px]" },
  { label: "Human", color: "var(--color-stat-hmn)", labelClass: "top-[32%] left-[-44px]" },
] as const;

export function PentagonGlow({ size = 260 }: { size?: number }) {
  return (
    <motion.div
      className="relative"
      style={{ width: size, height: size }}
      animate={{ y: [0, -8, 0] }}
      transition={{ duration: 6, ease: "easeInOut", repeat: Infinity }}
    >
      {AXES.map((axis, i) => (
        <span
          key={`label-${i}`}
          className={`absolute font-data text-stat-label tracking-widest stat-label-fade ${axis.labelClass}`}
          style={{ color: axis.color, animationDelay: `${0.5 + i * 0.1}s` }}
        >
          {axis.label}
        </span>
      ))}

      <svg
        viewBox="0 0 220 220"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
        className="w-full h-full"
        style={{ filter: "drop-shadow(0 0 40px rgba(125,212,163,0.12))" }}
      >
        <defs>
          <linearGradient id="pgrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--color-accent-thrive)" stopOpacity="0.12" />
            <stop offset="50%" stopColor="var(--color-accent-insight)" stopOpacity="0.08" />
            <stop offset="100%" stopColor="var(--color-accent-caution)" stopOpacity="0.12" />
          </linearGradient>
        </defs>

        {/* Grid rings */}
        <polygon points="110,22 188,86 158,172 62,172 32,86" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="0.5" />
        <polygon points="110,46 164,92 144,160 76,160 56,92" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="0.5" />
        <polygon points="110,70 140,98 130,148 90,148 80,98" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="0.5" />

        {/* Axis lines */}
        <line x1="110" y1="110" x2="110" y2="22" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5" />
        <line x1="110" y1="110" x2="188" y2="86" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5" />
        <line x1="110" y1="110" x2="158" y2="172" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5" />
        <line x1="110" y1="110" x2="62" y2="172" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5" />
        <line x1="110" y1="110" x2="32" y2="86" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5" />

        {/* Decorative data shape */}
        <polygon
          points="110,38 170,82 150,155 68,148 40,82"
          fill="url(#pgrad)"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth="1"
          opacity="0.7"
        />

        {/* Vertex dots */}
        {[
          { cx: 110, cy: 38, color: "var(--color-stat-ern)", delay: "0s" },
          { cx: 170, cy: 82, color: "var(--color-stat-roi)", delay: "0.8s" },
          { cx: 150, cy: 155, color: "var(--color-stat-res)", delay: "1.6s" },
          { cx: 68, cy: 148, color: "var(--color-stat-grw)", delay: "2.4s" },
          { cx: 40, cy: 82, color: "var(--color-stat-hmn)", delay: "3.2s" },
        ].map((v, i) => (
          <circle key={i} cx={v.cx} cy={v.cy} r="3.5" fill={v.color} opacity="0.7">
            <animate attributeName="opacity" values="0.5;0.9;0.5" dur="4s" begin={v.delay} repeatCount="indefinite" />
          </circle>
        ))}
      </svg>
    </motion.div>
  );
}
