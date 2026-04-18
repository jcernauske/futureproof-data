import { ScreenshotWithFallback } from "./ScreenshotWithFallback";

/**
 * Section D — Receipts Story
 * 7/5 split: typography left, receipt-panel screenshot right with insight glow.
 * See spec §3.7.
 *
 * Motion wrappers removed 2026-04-18 — see ProblemSection for context.
 */

interface Line {
  copy: string;
  className: string;
}

const RECEIPT_LINES: Line[] = [
  { copy: "700,000 cross-source rows.", className: "text-accent-thrive" },
  { copy: "280 data quality rules.", className: "text-accent-insight" },
  { copy: "Seven data contracts.", className: "text-accent-info" },
  {
    copy: "A chaos-monkey-hardened pipeline that catches its own mistakes before they reach you.",
    className: "text-text-primary",
  },
];

export function ReceiptsSection() {
  return (
    <section
      id="landing-section-receipts"
      className="relative border-t border-border-subtle px-6 tablet:px-10 py-16 tablet:py-20 desktop:py-32"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[120px]"
        style={{
          background:
            "radial-gradient(ellipse 60% 100% at 50% 0%, rgba(184, 169, 232, 0.18) 0%, transparent 65%)",
        }}
      />
      <div className="mx-auto max-w-[1280px] grid grid-cols-1 desktop:grid-cols-12 gap-10 desktop:gap-16 items-center">
        <div className="desktop:col-span-7 max-w-[62ch]">
          <h2 className="font-display font-bold text-heading tablet:text-title text-text-primary">
            Every number is tappable.
          </h2>

          <p className="mt-6 font-body text-body tablet:text-body-lg text-text-secondary leading-relaxed">
            Your stats aren't vibes. Tap any number and you get the raw inputs,
            the thresholds, the source datasets, and the exact computation that
            produced it.
          </p>

          <div className="mt-10 space-y-3">
            {RECEIPT_LINES.map((line) => (
              <p
                key={line.copy}
                className={`font-data font-bold text-data-lg leading-tight ${line.className}`}
              >
                {line.copy}
              </p>
            ))}
          </div>

          <p className="mt-8 font-body text-body text-text-muted italic">
            Your college brochure didn't do that.
          </p>
        </div>

        <div className="desktop:col-span-5 relative">
          <div
            className="absolute -inset-12 -z-10 blur-3xl pointer-events-none"
            style={{
              background:
                "radial-gradient(ellipse at center, rgba(184, 169, 232, 0.35) 0%, transparent 65%)",
            }}
            aria-hidden
          />
          <ScreenshotWithFallback
            id="landing-receipts-screenshot"
            slug="04-receipt-panel"
            alt="Expanded stat receipt panel showing raw inputs, thresholds, and source datasets."
            tone="insight"
            className="w-full aspect-[9/16] object-cover rounded-xl border border-border shadow-lg relative"
          />
        </div>
      </div>
    </section>
  );
}
