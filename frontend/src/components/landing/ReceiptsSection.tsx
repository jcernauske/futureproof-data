import { ReceiptPanelArt } from "./ReceiptPanelArt";

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
      className="relative px-6 tablet:px-10 py-16 tablet:py-20 desktop:py-32"
    >
      <div className="mx-auto max-w-[1280px] grid grid-cols-1 desktop:grid-cols-12 gap-10 desktop:gap-16 items-center">
        <div className="desktop:col-span-7 max-w-[62ch]">
          <p className="font-data text-micro tracking-[0.2em] uppercase text-accent-insight mb-4">
            Evidence
          </p>
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
          <div id="landing-receipts-screenshot" className="relative">
            <ReceiptPanelArt />
          </div>
        </div>
      </div>
    </section>
  );
}
