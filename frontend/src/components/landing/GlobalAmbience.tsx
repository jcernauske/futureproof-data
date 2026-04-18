import { useMemo } from "react";
import { useReducedMotion } from "framer-motion";

/**
 * Global atmospheric layer for the marketing Landing page. Renders a
 * fixed-position constellation of twinkling stars + a central breathing
 * ambient glow behind ALL sections (not just the hero) so the dark
 * background reads as a planetarium across the entire scroll, not just
 * the first viewport. Per landing-visual-critique-2026-04-18.md §3 item 23.
 *
 * Z-index behavior: `fixed inset-0 -z-10 pointer-events-none` — sits
 * behind all section content (sections are at the default z:auto > 0).
 * Body already carries the global radial-gradient stack (see index.css),
 * so this layer adds only the stars + breathing glow on top of that.
 *
 * Reduced-motion: `useReducedMotion()` suspends twinkle + breathe. Stars
 * render at their median opacity (0.25).
 */
const STAR_COUNT = 60;
const STAR_SEED = 424242;

/** Deterministic pseudo-random distribution — stable across re-renders. */
function mulberry32(seed: number) {
  let t = seed;
  return () => {
    t = (t + 0x6d2b79f5) | 0;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

interface Star {
  left: string;
  top: string;
  delay: string;
  duration: string;
}

function buildStarField(count: number): Star[] {
  const rng = mulberry32(STAR_SEED);
  const stars: Star[] = [];
  for (let i = 0; i < count; i += 1) {
    stars.push({
      left: `${(rng() * 100).toFixed(2)}%`,
      top: `${(rng() * 100).toFixed(2)}%`,
      delay: `${(rng() * 4).toFixed(2)}s`,
      duration: `${(3 + rng() * 3).toFixed(2)}s`,
    });
  }
  return stars;
}

export function GlobalAmbience() {
  const prefersReducedMotion = useReducedMotion();
  const stars = useMemo(() => buildStarField(STAR_COUNT), []);

  return (
    <div
      className="fixed inset-0 -z-10 pointer-events-none overflow-hidden"
      aria-hidden
    >
      {/* Breathing ambient glow — large central halo */}
      <div
        className={prefersReducedMotion ? "" : "ambient-glow"}
        style={
          prefersReducedMotion
            ? {
                position: "absolute",
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -60%)",
                width: 600,
                height: 600,
                background:
                  "radial-gradient(circle, rgba(125,212,163,0.06) 0%, rgba(184,169,232,0.04) 25%, rgba(123,184,224,0.03) 40%, transparent 65%)",
              }
            : undefined
        }
      />

      {/* Twinkle field — 60 stars distributed across the viewport */}
      {stars.map((star, i) => (
        <span
          key={i}
          className={prefersReducedMotion ? "" : "star"}
          style={{
            position: "absolute",
            left: star.left,
            top: star.top,
            width: 2,
            height: 2,
            background: "var(--color-text-primary)",
            borderRadius: "9999px",
            opacity: prefersReducedMotion ? 0.25 : undefined,
            animationDelay: prefersReducedMotion ? undefined : star.delay,
            animationDuration: prefersReducedMotion ? undefined : star.duration,
          }}
        />
      ))}

      {/* Thin noise film — inherits from body but sharpened here for the
          marketing surface's cinematic read. */}
      <div
        className="absolute inset-0 opacity-[0.025] mix-blend-overlay"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)' opacity='0.9'/></svg>\")",
          backgroundSize: "160px 160px",
        }}
      />
    </div>
  );
}
