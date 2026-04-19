/**
 * Decorative receipt panel mock for the Receipts section's right column.
 * Renders a 9:16 portrait card that looks like an expanded stat receipt —
 * the "tap a number, see the provenance" moment — without pretending to
 * be a real screenshot.
 */
export function ReceiptPanelArt() {
  return (
    <div
      aria-hidden
      className="w-full aspect-[9/16] rounded-xl border border-border-subtle bg-bp-mid shadow-lg overflow-hidden relative"
    >
      {/* Top glow wash */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-1/3"
        style={{
          background:
            "radial-gradient(ellipse at top, rgba(184, 169, 232, 0.18) 0%, transparent 70%)",
        }}
      />

      <div className="relative h-full flex flex-col p-6 tablet:p-8">
        {/* Header — stat name + badge */}
        <div className="flex items-center justify-between mb-3">
          <p className="font-data text-micro tracking-[0.2em] uppercase text-accent-insight">
            Earnings
          </p>
          <span
            className="font-data text-micro tracking-widest uppercase px-2 py-0.5 rounded-full"
            style={{
              background:
                "color-mix(in srgb, var(--color-accent-insight) 15%, transparent)",
              color: "var(--color-accent-insight)",
              border:
                "1px solid color-mix(in srgb, var(--color-accent-insight) 30%, transparent)",
            }}
          >
            Receipt
          </span>
        </div>

        {/* Big value */}
        <div className="flex items-baseline gap-3 mb-2">
          <span
            className="font-display font-bold text-[72px] leading-none"
            style={{ color: "var(--color-stat-ern)" }}
          >
            78
          </span>
          <span className="font-data text-small text-text-muted">/10</span>
        </div>
        <p className="font-body text-small text-text-secondary mb-6">
          Earning Power
        </p>

        <div className="border-t border-border-subtle/50 mb-5" />

        {/* Provenance rows */}
        <div className="space-y-4 flex-1">
          <div>
            <p className="font-data text-micro tracking-[0.15em] uppercase text-text-muted mb-1">
              Source
            </p>
            <p className="font-body text-small text-text-primary leading-tight">
              BLS Occupational Outlook Handbook
            </p>
            <p className="font-data text-micro text-text-muted mt-0.5">
              SOC 13-2051 · 2024 ed.
            </p>
          </div>

          <div>
            <p className="font-data text-micro tracking-[0.15em] uppercase text-text-muted mb-1">
              Computation
            </p>
            <p className="font-body text-small text-text-primary leading-tight">
              Median wage, 25th pct tenure
            </p>
            <p className="font-data text-micro text-text-muted mt-0.5">
              $67,500 → tier 7/10
            </p>
          </div>

          <div>
            <p className="font-data text-micro tracking-[0.15em] uppercase text-text-muted mb-1">
              Cross-check
            </p>
            <p className="font-body text-small text-text-primary leading-tight">
              Scorecard mean @ 10yr
            </p>
            <p className="font-data text-micro text-text-muted mt-0.5">
              $71,200 · Δ +5.5%
            </p>
          </div>
        </div>

        {/* Tap cue */}
        <div className="mt-6 pt-4 border-t border-border-subtle/50 flex items-center justify-between">
          <span className="font-data text-micro text-text-muted">
            Open full receipt
          </span>
          <span
            className="font-data text-body"
            style={{ color: "var(--color-accent-insight)" }}
          >
            →
          </span>
        </div>
      </div>
    </div>
  );
}
