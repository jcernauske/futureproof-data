/**
 * ExplainStatReceiptCard — structured explainer-receipt for the
 * "Explain this to me" affordance on /my-build.
 *
 * Renders inside `GemmaChat` as the assistant's reply when the
 * receipt path fires. Visual design per
 * `docs/specs/feature-explain-stat-receipt.md` §3
 * (filled by @fp-design-visionary).
 *
 * Surfaces five states: default, missing school rank, missing
 * occupation wage, both missing, and the effort-line variant
 * (Decision 13 — when effort != "balanced", `payload.math_line`
 * carries a `\n`-separated second line).
 */
import { motion } from "framer-motion";
import { springs, staggerContainer, staggerItem } from "@/styles/motion";
import type { ExplainStatReceipt, StatComponent } from "@/types/chat";

interface ExplainStatReceiptCardProps {
  payload: ExplainStatReceipt;
}

/**
 * Short-form lookup for source pill display. Per §3 "Pill name
 * truncation": full source names get a kebab-case slug + a short
 * human-readable form for the pill content.
 */
const SOURCE_SHORT_FORMS: Array<{
  matcher: RegExp;
  shortForm: string;
  slug: string;
}> = [
  {
    matcher: /College Scorecard/i,
    shortForm: "College Scorecard",
    slug: "college-scorecard",
  },
  {
    matcher: /Occupational Outlook|Bureau of Labor Statistics/i,
    shortForm: "BLS Outlook",
    slug: "bls-ooh",
  },
];

function shortFormForSource(name: string): { shortForm: string; slug: string } {
  for (const entry of SOURCE_SHORT_FORMS) {
    if (entry.matcher.test(name)) {
      return { shortForm: entry.shortForm, slug: entry.slug };
    }
  }
  // Fallback: use the part before the first parenthesis or comma,
  // and slugify the original.
  const truncated = name.split(/[(,]/)[0]?.trim() ?? name;
  const slug = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return { shortForm: truncated, slug };
}

/**
 * Split the server-rendered `math_line` into the arithmetic line and
 * an optional effort-line footnote (per Decision 13). When effort is
 * "balanced" or the math collapses to the build's score, the effort
 * line is absent and `effortLine` is null.
 */
function splitMathLine(mathLine: string): {
  arithmetic: string;
  effortLine: string | null;
} {
  const lines = mathLine.split("\n");
  return {
    arithmetic: lines[0] ?? "",
    effortLine: lines.length > 1 ? lines.slice(1).join("\n") : null,
  };
}

/**
 * Tiny markdown-ish parser for the bold-segments used by
 * `_render_math_line`'s effort line (e.g. "Your **Focused** effort
 * setting lifts this to 9/10"). Renders bold runs as <strong>.
 * Gemma never writes into this string — the format is server-controlled
 * — so a focused parser is appropriate (no general markdown needed).
 */
function renderInlineBold(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-text-primary">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

/**
 * Stat-color CSS-variable lookup keyed on the stat code. v1.0 only
 * ships ERN.
 */
function statColorVar(statCode: ExplainStatReceipt["stat_code"]): string {
  return `var(--color-stat-${statCode.toLowerCase()})`;
}

/**
 * Convert an integer percentile to its ordinal form ("87th", "1st").
 * Used for the per-component percentile callout row.
 */
function ordinal(n: number): string {
  if (n % 100 >= 11 && n % 100 <= 13) return `${n}th`;
  switch (n % 10) {
    case 1:
      return `${n}st`;
    case 2:
      return `${n}nd`;
    case 3:
      return `${n}rd`;
    default:
      return `${n}th`;
  }
}

function ComponentRow({
  component,
  statCode,
}: {
  component: StatComponent;
  statCode: ExplainStatReceipt["stat_code"];
}) {
  const accent = statColorVar(statCode);
  const isMissing = component.missing_reason !== null;

  return (
    <motion.li
      variants={staggerItem}
      data-testid={`receipt-component-${statCode.toLowerCase()}-${component.weight_pct}`}
      aria-label={`${component.weight_pct} percent — ${component.label}`}
      className="flex items-start gap-3 list-none"
    >
      {/* Left-rail percentage chip — stays at full opacity even on
          missing-data rows so the visual rhythm of the bullet doesn't
          break (per design spec). */}
      <div
        className="flex-shrink-0 flex items-center justify-center font-data font-bold rounded-full"
        style={{
          width: 56,
          height: 28,
          fontSize: 13,
          color: accent,
          background: `color-mix(in oklab, ${accent} 12%, transparent)`,
        }}
      >
        {component.weight_pct}%
      </div>

      <div
        className={`flex-1 ${isMissing ? "text-text-muted" : "text-text-secondary"}`}
      >
        <h3 className="font-display font-semibold text-text-primary text-body-sm m-0">
          {component.label}
        </h3>
        <p
          className="font-body leading-relaxed mt-1"
          style={{ fontSize: 13 }}
        >
          {component.explainer}
        </p>

        {component.evidence_bullets && component.evidence_bullets.length > 0 && (
          <ul
            className="mt-2 space-y-1"
            data-testid={`receipt-evidence-${statCode.toLowerCase()}-${component.label.replace(/\s+/g, "-").toLowerCase()}`}
            aria-label={`Evidence for ${component.label}`}
          >
            {component.evidence_bullets.map((bullet, idx) => (
              <li
                key={`${bullet}-${idx}`}
                className="font-body text-text-secondary pl-3 relative"
                style={{ fontSize: 12, lineHeight: 1.45 }}
              >
                <span
                  aria-hidden
                  className="absolute left-0 text-text-muted"
                >
                  -
                </span>
                {bullet}
              </li>
            ))}
          </ul>
        )}

        {/* Percentile callout row — three states:
            1. value_pct populated → render ordinal percentile + optional anchor_dollars
            2. value_pct null AND missing_reason null → intentionally non-percentile
               (ROI DTE bucket, GRW employment change). Show anchor_dollars/anchor_text only.
            3. value_pct null AND missing_reason populated → missing data (open-ring glyph) */}
        {component.value_pct !== null ? (
          <p
            className="font-data text-text-muted mt-1"
            style={{ fontSize: 12 }}
          >
            {ordinal(component.value_pct)} percentile
            {component.anchor_dollars !== null && (
              <>
                {" · "}
                <span className="font-data">
                  median ${component.anchor_dollars.toLocaleString()}
                </span>
              </>
            )}
          </p>
        ) : component.missing_reason !== null ? (
          <p
            className="font-body text-text-muted mt-1"
            style={{ fontSize: 12 }}
            aria-label="data not available"
          >
            <span aria-hidden>◦ —</span>
          </p>
        ) : (
          /* Intentionally non-percentile component — show anchor only */
          (component.anchor_dollars !== null || component.anchor_text) && (
            <p
              className="font-data text-text-muted mt-1"
              style={{ fontSize: 12 }}
            >
              {component.anchor_dollars !== null && (
                <span className="font-data">
                  ${component.anchor_dollars.toLocaleString()}
                </span>
              )}
              {component.anchor_dollars !== null && component.anchor_text && (
                <span> · </span>
              )}
              {component.anchor_text && (
                <span className="font-body">{component.anchor_text}</span>
              )}
            </p>
          )
        )}

        {component.missing_reason !== null && (
          <p
            role="note"
            data-testid={`receipt-missing-${component.weight_pct}`}
            aria-label={`Note: ${component.missing_reason}`}
            className="font-body italic text-text-muted mt-1"
            style={{ fontSize: 12 }}
          >
            {component.missing_reason}
          </p>
        )}
      </div>
    </motion.li>
  );
}

export function ExplainStatReceiptCard({
  payload,
}: ExplainStatReceiptCardProps) {
  const accent = statColorVar(payload.stat_code);
  const { arithmetic, effortLine } = splitMathLine(payload.math_line);

  return (
    <motion.article
      data-testid="explain-stat-receipt"
      role="region"
      aria-label={`${payload.stat_name} explanation receipt`}
      initial={{ opacity: 0, y: 12, scale: 0.985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={springs.smooth}
      className="bg-bp-raised border border-border-default rounded-[14px]"
      style={{
        padding: 20,
        borderLeft: `3px solid ${accent}`,
        maxWidth: "100%",
        boxShadow: "0 8px 32px rgba(27,29,48,0.55)",
      }}
    >
      {/* Score callout — eyebrow + score on the same baseline-aligned row.
          When score is null, render an open ring + em-dash matching the
          pentagon vertex treatment (stat-display-surfaces.md §1b) instead
          of a fabricated number. */}
      <header className="flex justify-between items-baseline gap-3 flex-wrap">
        <div
          aria-hidden
          className="font-display text-text-muted uppercase"
          style={{
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: "1.5px",
          }}
        >
          {payload.stat_name}
        </div>
        {payload.score === null ? (
          <div
            data-testid="receipt-score"
            data-score-missing="true"
            aria-label={`${payload.stat_name} score not available for this combination yet`}
            className="font-data font-bold leading-none flex items-baseline gap-1"
            style={{ fontSize: 44, color: "var(--color-text-muted)" }}
          >
            <span aria-hidden>◦</span>
            <span aria-hidden>—</span>
            <span
              className="font-data text-text-muted"
              style={{ fontSize: 22, fontWeight: 400 }}
            >
              /{payload.score_max}
            </span>
          </div>
        ) : (
          <div
            data-testid="receipt-score"
            aria-label={`${payload.stat_name} score: ${payload.score} out of ${payload.score_max}`}
            className="font-data font-bold leading-none"
            style={{ fontSize: 44, color: accent }}
          >
            {payload.score}
            <span
              className="font-data text-text-muted"
              style={{ fontSize: 22, fontWeight: 400 }}
            >
              /{payload.score_max}
            </span>
          </div>
        )}
      </header>

      {/* The one-liner */}
      <p
        className="font-body text-text-secondary leading-relaxed mt-3"
        style={{ fontSize: 14 }}
      >
        {payload.one_liner}
      </p>

      {/* Score provenance byline — AURA-only; suppressed when null */}
      {payload.score_provenance && (
        <p
          data-testid="receipt-score-provenance"
          aria-label={`Score provenance: based on ${payload.score_provenance}`}
          className="font-body italic text-text-muted"
          style={{ fontSize: 13, lineHeight: 1.4, marginTop: 6 }}
        >
          based on {payload.score_provenance}
        </p>
      )}

      {/* How it works — components + math line */}
      <section aria-labelledby="receipt-howitworks-heading" className="mt-5">
        <h2
          id="receipt-howitworks-heading"
          className="font-display text-text-muted uppercase"
          style={{
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: "1.5px",
          }}
        >
          How it works
        </h2>
        <motion.ul
          data-testid="receipt-components"
          className="mt-3 space-y-4"
          variants={staggerContainer(0, 0.08)}
          initial="initial"
          animate="animate"
        >
          {payload.components.map((c, idx) => (
            <ComponentRow
              key={`${c.weight_pct}-${idx}`}
              component={c}
              statCode={payload.stat_code}
            />
          ))}
        </motion.ul>

        {/* Recessed math card (bg-bp-mid, sunk one tier below the
            receipt surface). Matches existing <code> treatment in
            ChatMessage so the eye reads "this is data, not prose." */}
        <div
          data-testid="receipt-math-line"
          role="math"
          aria-label={`Score formula: ${arithmetic}`}
          className="bg-bp-mid rounded-lg mt-4 text-center"
          style={{
            padding: "14px 18px",
            color: "var(--color-text-primary)",
          }}
        >
          <span
            className="font-data font-semibold"
            style={{ fontSize: 15 }}
          >
            {arithmetic}
          </span>
        </div>

        {/* Scoring scale — deterministic tier table rendered below
            the math line so students see where their ratio lands. */}
        {payload.scoring_scale && payload.scoring_scale.length > 0 && (
          <div
            data-testid="receipt-scoring-scale"
            className="bg-bp-mid rounded-lg mt-3 overflow-hidden"
            style={{ fontSize: 12 }}
          >
            <table className="w-full font-data" style={{ borderSpacing: 0 }}>
              <thead>
                <tr className="text-text-muted">
                  <th className="text-left px-3 py-1.5 font-semibold">
                    {payload.scoring_scale![0]?.range === payload.scoring_scale![0]?.score ? "Score" : "Input"}
                  </th>
                  <th className="text-left px-3 py-1.5 font-semibold">Rating</th>
                  {payload.scoring_scale![0]?.range !== payload.scoring_scale![0]?.score && (
                    <th className="text-right px-3 py-1.5 font-semibold">Score</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {(() => {
                  const hideScoreCol = payload.scoring_scale![0]?.range === payload.scoring_scale![0]?.score;
                  const activeIdx = payload.score === null ? -1 :
                    payload.scoring_scale!.reduce((best, tier, i) => {
                      const nums = tier.score.match(/\d+/g)?.map(Number) ?? [];
                      return payload.score! >= Math.min(...nums) &&
                        payload.score! <= Math.max(...nums) ? i : best;
                    }, -1);
                  return payload.scoring_scale!.map((tier, i) => {
                    const active = i === activeIdx;
                    return (
                      <tr
                        key={tier.label}
                        style={active ? {
                          background: `color-mix(in oklab, ${accent} 10%, transparent)`,
                        } : undefined}
                      >
                        <td className="px-3 py-1 text-text-secondary">
                          {tier.range}
                        </td>
                        <td
                          className={`px-3 py-1 ${active ? "text-text-primary font-semibold" : "text-text-muted"}`}
                        >
                          {tier.label}
                        </td>
                        {!hideScoreCol && (
                          <td
                            className={`px-3 py-1 text-right ${active ? "text-text-primary font-semibold" : "text-text-muted"}`}
                          >
                            {tier.score}
                          </td>
                        )}
                      </tr>
                    );
                  });
                })()}
              </tbody>
            </table>
          </div>
        )}

        {/* Effort line (Decision 13) — outside the math card, italic,
            small. A footnote on the math, not another arithmetic line. */}
        {effortLine !== null && (
          <p
            data-testid="receipt-effort-line"
            className="font-body italic text-text-muted text-center mt-2"
            style={{ fontSize: 12 }}
          >
            {renderInlineBold(effortLine)}
          </p>
        )}
      </section>

      {/* Sources */}
      <section aria-labelledby="receipt-sources-heading" className="mt-5">
        <h2
          id="receipt-sources-heading"
          className="font-display text-text-muted uppercase"
          style={{
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: "1.5px",
          }}
        >
          Sources
        </h2>
        <ul className="mt-2 flex flex-wrap gap-2">
          {payload.sources.map((s, idx) => {
            const { shortForm, slug } = shortFormForSource(s.name);
            return (
              <li key={`${slug}-${idx}`} className="list-none">
                <button
                  type="button"
                  data-testid={`receipt-source-${slug}`}
                  aria-label={`Source: ${s.name}`}
                  title={s.name}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border-subtle bg-bp-mid hover:bg-bp-raised hover:[border-color:var(--color-stat-ern)] focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-none transition-colors duration-fast"
                  style={{ fontSize: 12 }}
                >
                  <span className="font-body text-text-muted">{s.label}</span>
                  <span aria-hidden className="text-text-muted">·</span>
                  <span className="font-body text-text-primary">
                    {shortForm}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </section>

      {/* Why we mix both pieces */}
      <section aria-labelledby="receipt-why-heading" className="mt-5">
        <h2
          id="receipt-why-heading"
          className="font-display text-text-muted uppercase"
          style={{
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: "1.5px",
          }}
        >
          Why we mix both pieces
        </h2>
        <p
          className="font-body text-text-secondary leading-relaxed mt-2"
          style={{ fontSize: 14 }}
        >
          {payload.why_mix_paragraph}
        </p>
      </section>
    </motion.article>
  );
}
