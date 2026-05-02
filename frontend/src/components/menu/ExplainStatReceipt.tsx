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
 * Stat-color CSS-variable lookup keyed on the stat code. Falls back to
 * the ERN gold for safety; v1.0 only ships ERN.
 */
function statColorVar(statCode: ExplainStatReceipt["stat_code"]): string {
  return `var(--color-stat-${statCode.toLowerCase()})`;
}

function ComponentRow({
  component,
  statCode,
}: {
  component: StatComponent;
  statCode: ExplainStatReceipt["stat_code"];
}) {
  const accent = statColorVar(statCode);
  const isMissing =
    component.value_pct === null ||
    component.anchor_dollars === null ||
    component.missing_reason !== null;

  return (
    <li
      data-testid={`receipt-component-${statCode.toLowerCase()}-${component.weight_pct}`}
      aria-label={`${component.weight_pct} percent — ${component.label}`}
      className="flex items-start gap-3"
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
        <div className="font-display font-semibold text-text-primary text-body-sm">
          {component.label}
        </div>
        <p
          className="font-body leading-relaxed mt-1"
          style={{ fontSize: 13 }}
        >
          {component.explainer}
        </p>
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
    </li>
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
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
      className="bg-bp-raised border border-border-subtle rounded-xl"
      style={{
        padding: 20,
        borderLeft: `3px solid ${accent}`,
        maxWidth: "100%",
      }}
    >
      {/* Score callout — stat-color font-data headline */}
      <header className="flex items-baseline gap-3 flex-wrap">
        <h3
          className="font-display font-bold text-text-primary"
          style={{ fontSize: 18 }}
        >
          {payload.stat_name}
        </h3>
        <div
          className="font-data font-bold leading-none"
          aria-label={`Score: ${payload.score} out of ${payload.score_max}`}
          style={{ fontSize: 32, color: accent }}
        >
          {payload.score}
          <span
            className="font-data font-normal opacity-50"
            style={{ fontSize: 18 }}
          >
            /{payload.score_max}
          </span>
        </div>
      </header>

      {/* The one-liner */}
      <p
        className="font-body text-text-secondary leading-relaxed mt-3"
        style={{ fontSize: 14 }}
      >
        {payload.one_liner}
      </p>

      {/* How it works — components + math line */}
      <section className="mt-5">
        <div
          className="font-display font-semibold text-text-primary"
          style={{ fontSize: 13, letterSpacing: "0.3px" }}
        >
          How it works
        </div>
        <motion.ul
          className="mt-3 space-y-4"
          variants={staggerContainer(0, 0.08)}
          initial="initial"
          animate="animate"
        >
          {payload.components.map((c) => (
            <motion.div key={c.weight_pct} variants={staggerItem}>
              <ComponentRow
                component={c}
                statCode={payload.stat_code}
              />
            </motion.div>
          ))}
        </motion.ul>

        {/* Recessed math card (bg-bp-mid, sunk one tier below the
            receipt surface). Matches existing <code> treatment in
            ChatMessage so the eye reads "this is data, not prose." */}
        <div
          data-testid="receipt-math-line"
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

      {/* Where the data comes from */}
      <section className="mt-5">
        <div
          className="font-display font-semibold text-text-primary"
          style={{ fontSize: 13, letterSpacing: "0.3px" }}
        >
          Where the data comes from
        </div>
        <ul className="mt-2 flex flex-wrap gap-2">
          {payload.sources.map((s, i) => (
            <li key={i}>
              <button
                type="button"
                data-testid={`receipt-source-${i}`}
                aria-label={`Source: ${s.name}`}
                title={s.name}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border-subtle bg-bp-deep font-body text-text-secondary hover:text-text-primary hover:border-border-default transition-colors"
                style={{ fontSize: 12 }}
              >
                {s.label}
              </button>
            </li>
          ))}
        </ul>
      </section>

      {/* Why we mix both pieces */}
      <section className="mt-5">
        <div
          className="font-display font-semibold text-text-primary"
          style={{ fontSize: 13, letterSpacing: "0.3px" }}
        >
          Why we mix both pieces
        </div>
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
