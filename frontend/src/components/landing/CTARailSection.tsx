/**
 * Section F — Live Demo / CTA Rail
 * Mirrors hero CTA DNA + earns its own visual reward: ghost pentagon echo,
 * stat-color dot rule, differentiated button label. Spec §3.9 + critique §3.17.
 *
 * Motion wrappers removed 2026-04-18 — see ProblemSection for context.
 */

const STAT_DOTS = [
  "text-stat-ern",
  "text-stat-roi",
  "text-stat-res",
  "text-stat-grw",
  "text-stat-hmn",
] as const;

function GhostPentagon() {
  return (
    <svg
      viewBox="0 0 220 220"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
      className="w-[320px] h-[320px] tablet:w-[400px] tablet:h-[400px] opacity-[0.22]"
    >
      <polygon
        points="110,22 188,86 158,172 62,172 32,86"
        fill="none"
        stroke="var(--color-text-muted)"
        strokeWidth="0.8"
        strokeLinejoin="round"
      />
      {[
        { cx: 110, cy: 22, color: "var(--color-stat-ern)" },
        { cx: 188, cy: 86, color: "var(--color-stat-roi)" },
        { cx: 158, cy: 172, color: "var(--color-stat-res)" },
        { cx: 62, cy: 172, color: "var(--color-stat-grw)" },
        { cx: 32, cy: 86, color: "var(--color-stat-hmn)" },
      ].map((v, i) => (
        <circle key={i} cx={v.cx} cy={v.cy} r="3" fill={v.color} />
      ))}
    </svg>
  );
}

export function CTARailSection() {
  return (
    <section
      id="landing-section-cta-rail"
      className="relative px-6 tablet:px-10 py-24 tablet:py-32 desktop:py-40 overflow-hidden"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute top-1/2 left-1/2 -translate-y-1/2 translate-x-[20%] tablet:translate-x-[25%] desktop:translate-x-[28%]"
      >
        <GhostPentagon />
      </div>

      <div className="relative mx-auto max-w-[640px] text-center">
        <div className="flex justify-center items-center gap-4 mb-6">
          {STAT_DOTS.map((cls, i) => (
            <span
              key={i}
              className={`${cls} w-[6px] h-[6px] rounded-full bg-current opacity-60`}
              aria-hidden
            />
          ))}
        </div>

        <h2 className="font-display font-bold text-heading tablet:text-title text-text-primary">
          Spec your first build.
        </h2>
        <p className="mt-6 font-body text-body tablet:text-body-lg text-text-secondary leading-normal">
          Takes about two minutes. No signup, no email. You'll get a
          three-word name and emoji — that's your identity.
        </p>
        <div className="mt-10 flex justify-center">
          <a
            id="landing-cta-rail"
            href="/app"
            aria-label="Start your first FutureProof build"
            className="inline-flex items-center justify-center gap-2 font-body font-bold text-cta bg-accent-thrive text-text-inverse rounded-lg h-14 px-8 transition-all duration-normal hover:brightness-95 hover:shadow-glow-thrive active:scale-[0.97]"
          >
            Start your build <span className="opacity-70">✦</span>
          </a>
        </div>
      </div>
    </section>
  );
}
