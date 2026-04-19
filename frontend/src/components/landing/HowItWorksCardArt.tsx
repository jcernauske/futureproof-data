/**
 * Three thematic SVG visuals for the "How it works" cards. Replaces the
 * generic ScreenshotWithFallback pending state with content that says
 * something specific about each card's product moment.
 */

const CONTAINER =
  "w-full aspect-[16/10] rounded-lg border border-border-subtle shadow-md overflow-hidden relative";

/** STATS card — small pentagon with five color-coded vertex dots and rings. */
export function PentagonArt() {
  const vertices = [
    { cx: 80, cy: 16, color: "var(--color-stat-ern)" },
    { cx: 134, cy: 56, color: "var(--color-stat-roi)" },
    { cx: 113, cy: 116, color: "var(--color-stat-res)" },
    { cx: 47, cy: 116, color: "var(--color-stat-grw)" },
    { cx: 26, cy: 56, color: "var(--color-stat-hmn)" },
  ];
  const polygonPoints = vertices.map((v) => `${v.cx},${v.cy}`).join(" ");
  return (
    <div
      className={`${CONTAINER} bg-bp-deep`}
      style={{
        backgroundImage:
          "radial-gradient(ellipse at center, rgba(125, 212, 163, 0.10) 0%, transparent 65%)",
      }}
      aria-hidden
    >
      <svg
        viewBox="0 0 160 132"
        xmlns="http://www.w3.org/2000/svg"
        className="absolute inset-0 w-full h-full"
      >
        {/* Concentric rings */}
        <polygon
          points={polygonPoints}
          fill="none"
          stroke="var(--color-text-muted)"
          strokeWidth="0.6"
          opacity="0.25"
        />
        <polygon
          points="80,38 116,62 102,108 58,108 44,62"
          fill="none"
          stroke="var(--color-text-muted)"
          strokeWidth="0.6"
          opacity="0.18"
        />
        <polygon
          points="80,58 96,68 90,98 70,98 64,68"
          fill="none"
          stroke="var(--color-text-muted)"
          strokeWidth="0.6"
          opacity="0.12"
        />
        {/* Axes */}
        {vertices.map((v, i) => (
          <line
            key={`axis-${i}`}
            x1="80"
            y1="66"
            x2={v.cx}
            y2={v.cy}
            stroke="var(--color-text-muted)"
            strokeWidth="0.5"
            opacity="0.15"
          />
        ))}
        {/* Vertex dots with halos */}
        {vertices.map((v, i) => (
          <g key={`v-${i}`}>
            <circle cx={v.cx} cy={v.cy} r="9" fill={v.color} opacity="0.12" />
            <circle cx={v.cx} cy={v.cy} r="5" fill={v.color} opacity="0.85" />
          </g>
        ))}
      </svg>
    </div>
  );
}

/** GAUNTLET card — row of five boss icons, each with a unique color glow. */
export function BossRowArt() {
  const bosses = [
    { abbr: "AI", color: "var(--color-boss-ai)" },
    { abbr: "$", color: "var(--color-boss-loans)" },
    { abbr: "M", color: "var(--color-boss-market)" },
    { abbr: "B", color: "var(--color-boss-burnout)" },
    { abbr: "C", color: "var(--color-boss-ceiling)" },
  ];
  return (
    <div
      className={`${CONTAINER} bg-bp-deep flex items-center justify-center px-4`}
      style={{
        backgroundImage:
          "radial-gradient(ellipse at center, rgba(244, 169, 126, 0.10) 0%, transparent 65%)",
      }}
      aria-hidden
    >
      <div className="flex items-center gap-2 desktop:gap-3">
        {bosses.map((b, i) => (
          <div key={b.abbr} className="flex items-center gap-2 desktop:gap-3">
            <div className="relative flex items-center justify-center w-11 h-11 rounded-full">
              {/* halo */}
              <div
                className="absolute inset-0 rounded-full"
                style={{
                  background: b.color,
                  opacity: 0.14,
                  filter: "blur(4px)",
                }}
              />
              {/* core */}
              <div
                className="relative w-9 h-9 rounded-full flex items-center justify-center font-data text-micro font-bold"
                style={{
                  background: `color-mix(in srgb, ${b.color} 22%, transparent)`,
                  border: `1px solid ${b.color}`,
                  color: b.color,
                }}
              >
                {b.abbr}
              </div>
            </div>
            {i < bosses.length - 1 && (
              <span className="font-data text-micro text-text-muted opacity-50">
                ·
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/** BRANCHES card — small constellation: 1 root → 3 stems → 6 endpoints. */
export function BranchTreeArt() {
  const root = { cx: 80, cy: 110 };
  const stems = [
    { cx: 30, cy: 70 },
    { cx: 80, cy: 56 },
    { cx: 130, cy: 70 },
  ];
  const leaves = [
    { cx: 14, cy: 22, size: 4 },
    { cx: 46, cy: 16, size: 3.5 },
    { cx: 70, cy: 12, size: 4.5 },
    { cx: 92, cy: 12, size: 3.5 },
    { cx: 116, cy: 16, size: 4 },
    { cx: 146, cy: 22, size: 4.5 },
  ];
  const stemToLeaf: ReadonlyArray<readonly [number, number]> = [
    [0, 0],
    [0, 1],
    [1, 2],
    [1, 3],
    [2, 4],
    [2, 5],
  ];
  const insight = "var(--color-stat-res)";
  return (
    <div
      className={`${CONTAINER} bg-bp-deep`}
      style={{
        backgroundImage:
          "radial-gradient(ellipse at top, rgba(184, 169, 232, 0.12) 0%, transparent 70%)",
      }}
      aria-hidden
    >
      <svg
        viewBox="0 0 160 132"
        xmlns="http://www.w3.org/2000/svg"
        className="absolute inset-0 w-full h-full"
      >
        {/* root → stems */}
        {stems.map((s, i) => (
          <line
            key={`root-${i}`}
            x1={root.cx}
            y1={root.cy}
            x2={s.cx}
            y2={s.cy}
            stroke={insight}
            strokeWidth="0.8"
            opacity="0.35"
          />
        ))}
        {/* stems → leaves */}
        {stemToLeaf.map(([si, li], i) => (
          <line
            key={`branch-${i}`}
            x1={stems[si]!.cx}
            y1={stems[si]!.cy}
            x2={leaves[li]!.cx}
            y2={leaves[li]!.cy}
            stroke={insight}
            strokeWidth="0.7"
            opacity="0.45"
          />
        ))}
        {/* leaves */}
        {leaves.map((l, i) => (
          <g key={`leaf-${i}`}>
            <circle cx={l.cx} cy={l.cy} r={l.size + 4} fill={insight} opacity="0.10" />
            <circle cx={l.cx} cy={l.cy} r={l.size} fill={insight} opacity="0.85" />
          </g>
        ))}
        {/* stems */}
        {stems.map((s, i) => (
          <circle
            key={`stem-${i}`}
            cx={s.cx}
            cy={s.cy}
            r="3"
            fill={insight}
            opacity="0.55"
          />
        ))}
        {/* root */}
        <circle cx={root.cx} cy={root.cy} r="5" fill={insight} opacity="0.7" />
      </svg>
    </div>
  );
}
