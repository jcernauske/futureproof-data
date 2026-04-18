import { useState } from "react";

/**
 * `<picture>` + WebP/PNG fallback with a first-class "capture-pending"
 * treatment that renders when both sources fail to load. Replaces the
 * earlier `bg-bp-surface` skeleton that shipped as part of the initial
 * landing pass — per the 2026-04-18 visual critique (§3 item 10) the
 * old skeleton read as a literal TODO rectangle.
 *
 * The fallback now renders a section-tone radial gradient + a 48px
 * pentagon-vertex dot pattern (echoing the product's signature visual),
 * which reads as "loading" rather than "broken."
 *
 * Accepts an optional `tone` so each section can key its fallback to
 * the right accent color (thrive for stats / alert for gauntlet /
 * insight for receipts and branches / info for ollama).
 */

type Tone = "thrive" | "alert" | "insight" | "info" | "caution" | "empathy";

interface ScreenshotWithFallbackProps {
  slug: string;
  alt: string;
  id?: string;
  className?: string;
  /** Section-tone accent used for the pending-capture gradient + dots. */
  tone?: Tone;
}

const TONE_RGBA: Record<Tone, string> = {
  thrive: "rgba(125, 212, 163, 0.18)",
  alert: "rgba(244, 169, 126, 0.18)",
  insight: "rgba(184, 169, 232, 0.18)",
  info: "rgba(123, 184, 224, 0.18)",
  caution: "rgba(233, 200, 116, 0.18)",
  empathy: "rgba(236, 164, 184, 0.18)",
};

// Five vertex positions on a 100×100 viewbox, mirroring PentagonGlow's topology.
const PENTAGON_DOTS: Array<{ cx: number; cy: number; delay: number }> = [
  { cx: 50, cy: 10, delay: 0.0 },
  { cx: 90, cy: 40, delay: 0.15 },
  { cx: 74, cy: 86, delay: 0.3 },
  { cx: 26, cy: 86, delay: 0.45 },
  { cx: 10, cy: 40, delay: 0.6 },
];

export function ScreenshotWithFallback({
  slug,
  alt,
  id,
  className,
  tone = "insight",
}: ScreenshotWithFallbackProps) {
  const [available, setAvailable] = useState(true);

  if (!available) {
    const tint = TONE_RGBA[tone];
    return (
      <div
        id={id}
        role="img"
        aria-label={alt}
        className={`${className ?? ""} relative overflow-hidden border border-border-subtle bg-bp-mid flex items-center justify-center`}
        style={{
          backgroundImage: `radial-gradient(ellipse at center, ${tint} 0%, transparent 70%)`,
        }}
      >
        <svg
          viewBox="0 0 100 100"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden
          className="w-[44%] h-[44%] opacity-60"
        >
          <polygon
            points={PENTAGON_DOTS.map((d) => `${d.cx},${d.cy}`).join(" ")}
            fill="none"
            stroke="currentColor"
            strokeWidth="0.6"
            className="text-border-subtle"
            strokeLinejoin="round"
          />
          {PENTAGON_DOTS.map((d, i) => (
            <circle
              key={i}
              cx={d.cx}
              cy={d.cy}
              r="2.2"
              fill="currentColor"
              className={`text-accent-${tone}`}
              style={{
                animation: `landing-pending-dot 2.4s ease-in-out ${d.delay}s infinite`,
              }}
            />
          ))}
        </svg>
      </div>
    );
  }

  return (
    <picture>
      <source
        type="image/webp"
        srcSet={`/assets/screenshots/landing/${slug}.webp`}
      />
      <img
        id={id}
        src={`/assets/screenshots/landing/${slug}.png`}
        alt={alt}
        loading="lazy"
        decoding="async"
        className={className}
        onError={() => setAvailable(false)}
      />
    </picture>
  );
}
