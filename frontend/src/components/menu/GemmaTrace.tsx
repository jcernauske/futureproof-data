/**
 * <GemmaTrace> — live, animated rendering of Gemma's tool-call chain.
 *
 * Built per the §3 Visual Spec in `docs/specs/feature-gemma-trace.md`.
 * Pixel-perfect contract:
 *
 * - Rail container — recessed surface inside the parent chat bubble
 *   with a 3px `accent-insight` left stripe (the Gemma-voice signature).
 * - Header — `✦ Gemma is looking things up…` (streaming) /
 *   `✦ Gemma checked N sources.` (complete). Singular variants for n=1.
 * - Rows — pedagogical sentence + per-tool icon + status pill +
 *   duration. Click anywhere on a resolved row to expand the
 *   engineering view (raw tool name, args JSON, result preview JSON).
 * - States: streaming, complete, fallback (visually identical to
 *   complete; rows mount in resolved state with no entrance animation).
 *
 * Pure presentation — no API calls, no side-effects. The consumer
 * (`GemmaChat`) accumulates `GemmaTraceEvent[]` and passes them in.
 */

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { GemmaStar } from "@/components/ui/GemmaStar";
import { resolveTraceIcon } from "@/components/menu/icons";
import { resolveToolLabel } from "@/components/menu/toolLabels";
import type { GemmaTraceEvent, TraceMode } from "@/types/gemmaTrace";

interface GemmaTraceProps {
  events: GemmaTraceEvent[];
  mode: TraceMode;
}

interface Row {
  /** Backend's `dispatch_index` — unique row-correlation key. */
  turn: number;
  tool: string;
  args: Record<string, unknown>;
  // Populated on `turn_complete` arrival. While null the row is
  // in-progress (streaming state).
  resolved: {
    result_preview: string;
    duration_ms: number;
    error: string | null;
  } | null;
}

/**
 * Fold the event stream into the visible row list, correlated by
 * `turn` (= dispatch_index). A `turn_complete` swaps its matching
 * `turn_start` row from in-progress → resolved. If a `turn_complete`
 * arrives without a prior `turn_start`, mount a row directly in
 * resolved state (degenerate-stream defense).
 */
function rowsFromEvents(events: GemmaTraceEvent[]): Row[] {
  const rows: Row[] = [];
  const indexByTurn = new Map<number, number>();
  for (const ev of events) {
    if (ev.type === "turn_start") {
      if (indexByTurn.has(ev.turn)) continue; // ignore dup
      indexByTurn.set(ev.turn, rows.length);
      rows.push({
        turn: ev.turn,
        tool: ev.tool,
        args: ev.args,
        resolved: null,
      });
    } else if (ev.type === "turn_complete") {
      const idx = indexByTurn.get(ev.turn);
      const resolved = {
        result_preview: ev.result_preview,
        duration_ms: ev.duration_ms,
        error: ev.error,
      };
      if (idx === undefined) {
        // Degenerate: turn_complete with no prior turn_start. Mount
        // directly in resolved state.
        indexByTurn.set(ev.turn, rows.length);
        rows.push({
          turn: ev.turn,
          tool: ev.tool,
          args: ev.args,
          resolved,
        });
      } else {
        const existing = rows[idx]!;
        rows[idx] = {
          ...existing,
          // Prefer the tool/args from turn_complete in case turn_start
          // had a degenerate empty payload.
          tool: ev.tool || existing.tool,
          args: Object.keys(ev.args).length ? ev.args : existing.args,
          resolved,
        };
      }
    }
  }
  return rows;
}

function headerCopy(rows: Row[], mode: TraceMode): string {
  const total = rows.length;
  const anyUnresolved = rows.some((r) => r.resolved === null);
  const isStreaming = mode === "live" && anyUnresolved;
  if (isStreaming) {
    return total === 1
      ? "Looking something up…"
      : "Looking things up…";
  }
  // Complete or fallback — past tense.
  return total === 1
    ? "Checked one source."
    : `Checked ${total} sources.`;
}

export function GemmaTrace({ events, mode }: GemmaTraceProps) {
  const rows = useMemo(() => rowsFromEvents(events), [events]);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  // Empty rows → return null. Per §3 Scope, an answer with no tool
  // calls renders no trace section, no header, no skeleton.
  if (rows.length === 0) return null;

  const header = headerCopy(rows, mode);

  function toggleExpanded(turn: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(turn)) next.delete(turn);
      else next.add(turn);
      return next;
    });
  }

  return (
    <section
      data-testid="gemma-trace"
      role="region"
      aria-label="Reasoning steps for this answer"
      className="bg-bp-recessed border border-border-subtle rounded-lg overflow-hidden"
      style={{
        // 3px accent-insight left stripe — the Gemma-voice signature.
        // Rendered as a left border so it doesn't fight the rounded
        // corners of the rest of the rail.
        borderLeft: "3px solid var(--color-accent-insight)",
      }}
    >
      <div className="px-4 py-3">
        <header className="flex items-center gap-2 mb-3">
          <GemmaStar size={12} />
          {/* Header copy crossfade (F3) — 200ms opacity swap when the
              streaming-vs-complete copy changes. AnimatePresence
              keys off the header text so the swap fires on every
              meaningful change. */}
          <AnimatePresence mode="wait" initial={false}>
            <motion.span
              key={header}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              className="font-body text-small text-text-secondary"
            >
              {header}
            </motion.span>
          </AnimatePresence>
        </header>

        {/* Live region (F5) — dedicated role=status sibling of the
            <header>. Avoids the implicit banner role conflict on
            <header aria-live=...>. Visually hidden via sr-only; text
            announced when new rows resolve. The text matches the
            current header so screen-reader users get the same
            update cadence as sighted users. */}
        <span
          data-testid="gemma-trace-live"
          role="status"
          aria-live="polite"
          className="sr-only"
        >
          {header}
        </span>

        <ul
          data-testid="gemma-trace-rows"
          aria-label="Tools Gemma used"
          className="flex flex-col"
        >
          {rows.map((row, idx) => (
            <TraceRow
              key={row.turn}
              row={row}
              index={idx}
              total={rows.length}
              isFirst={idx === 0}
              expanded={expanded.has(row.turn)}
              onToggle={() => toggleExpanded(row.turn)}
              animate={mode === "live"}
            />
          ))}
        </ul>
      </div>
    </section>
  );
}

interface TraceRowProps {
  row: Row;
  index: number;
  total: number;
  isFirst: boolean;
  expanded: boolean;
  onToggle: () => void;
  animate: boolean;
}

function TraceRow({
  row,
  index,
  total,
  isFirst,
  expanded,
  onToggle,
  animate,
}: TraceRowProps) {
  const tool = resolveToolLabel(row.tool);
  const Icon = resolveTraceIcon(tool.icon);
  const inProgress = row.resolved === null;
  const error = row.resolved?.error ?? null;
  const isError = !inProgress && error !== null;

  const pedagogical = tool.hint(row.args);
  const status = inProgress
    ? "in progress"
    : isError
      ? "retry"
      : "done";
  const ariaLabel =
    `Step ${index + 1} of ${total}: ${pedagogical} ${status}` +
    (row.resolved ? `, ${row.resolved.duration_ms} ms` : "");

  // Row entrance animation — only in live mode (streaming state).
  // Complete + fallback mount instantly.
  const motionProps = animate
    ? {
        initial: { opacity: 0, y: 24 },
        animate: { opacity: 1, y: 0 },
        transition: springs.smooth,
      }
    : {};

  // Row background per state.
  const bgClass = inProgress
    ? "bg-state-loading"
    : expanded
      ? "bg-bp-mid"
      : "hover:bg-white/[0.04]";

  return (
    <motion.li
      data-testid={`gemma-trace-row-${row.turn}`}
      className={[
        "list-none",
        !isFirst && "border-t border-border-subtle",
      ]
        .filter(Boolean)
        .join(" ")}
      {...motionProps}
    >
      <button
        type="button"
        data-testid={`gemma-trace-expand-${row.turn}`}
        aria-label={ariaLabel}
        aria-expanded={expanded}
        aria-controls={`gemma-trace-detail-${row.turn}`}
        disabled={inProgress}
        onClick={onToggle}
        className={[
          "w-full flex items-center gap-3 px-2 py-2 rounded-sm",
          "text-left transition-colors duration-fast",
          // F1 — focus-visible (keyboard-only), 3px ring + 2px offset
          // per DESIGN.md §Focus States.
          "focus:outline-none focus-visible:ring-[3px] focus-visible:ring-focus-ring focus-visible:ring-offset-2",
          "disabled:cursor-default",
          "min-h-10",
          bgClass,
        ].join(" ")}
      >
        <span
          className={[
            "shrink-0 inline-flex items-center justify-center",
            inProgress
              ? "text-accent-insight animate-gemma-trace-pulse"
              : isError
                ? "text-text-muted"
                : "text-accent-info",
          ].join(" ")}
        >
          <Icon size={16} />
        </span>

        <span
          className={[
            "flex-1 min-w-0 truncate font-body text-body-sm",
            inProgress
              ? "text-text-secondary animate-gemma-trace-pulse"
              : "text-text-secondary",
          ].join(" ")}
          title={pedagogical}
        >
          {pedagogical}
        </span>

        {/* F2 — resolution-swap motion. Pill, duration, chevron all
            fade in together on `springs.snappy` when the row resolves
            (i.e. when row.resolved transitions from null → object).
            AnimatePresence keys the wrapper on the resolved-ness so
            the children mount once and animate on entrance. */}
        <AnimatePresence initial={false}>
          {row.resolved !== null && (
            <motion.span
              key="resolved"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={springs.snappy}
              className="contents"
            >
              <StatusPill error={isError} />
              <span
                data-testid={`gemma-trace-duration-${row.turn}`}
                className="shrink-0 font-data text-data-sm text-text-muted"
              >
                {row.resolved.duration_ms} ms
              </span>
              <span
                aria-hidden="true"
                className={[
                  "shrink-0 font-data text-micro text-text-muted",
                  "transition-transform duration-fast",
                  expanded ? "rotate-90" : "",
                ].join(" ")}
              >
                ▸
              </span>
            </motion.span>
          )}
        </AnimatePresence>
      </button>

      <AnimatePresence initial={false}>
        {expanded && row.resolved !== null && (
          <motion.div
            id={`gemma-trace-detail-${row.turn}`}
            data-testid={`gemma-trace-detail-${row.turn}`}
            role="region"
            aria-label={`Technical detail for step ${index + 1}`}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{
              // F4 — both axes use the named Brightpath spring per
              // §3 Motion Presets table (no custom durations).
              opacity: springs.smooth,
              height: springs.smooth,
            }}
            className="overflow-hidden"
          >
            <EngineeringDetail
              tool={row.tool}
              args={row.args}
              resultPreview={row.resolved.result_preview}
              durationMs={row.resolved.duration_ms}
              error={row.resolved.error}
              stepIndex={index}
              totalSteps={total}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.li>
  );
}

interface StatusPillProps {
  error: boolean;
}

function StatusPill({ error }: StatusPillProps) {
  return (
    <span
      className={[
        "shrink-0 inline-flex items-center gap-1",
        "px-2 py-[2px] rounded-full",
        "font-body text-micro font-semibold",
        error
          ? "bg-accent-alert/15 text-accent-alert"
          : "bg-accent-thrive/15 text-accent-thrive",
      ].join(" ")}
    >
      <span aria-hidden="true">{error ? "◇" : "◆"}</span>
      <span>{error ? "retry" : "done"}</span>
    </span>
  );
}

interface EngineeringDetailProps {
  tool: string;
  args: Record<string, unknown>;
  resultPreview: string;
  durationMs: number;
  error: string | null;
  stepIndex: number;
  totalSteps: number;
}

function EngineeringDetail({
  tool,
  args,
  resultPreview,
  durationMs,
  error,
  stepIndex,
  totalSteps,
}: EngineeringDetailProps) {
  const argsJson = useMemo(
    () => safeFormatJson(args),
    [args],
  );
  const resultJson = useMemo(
    () => safeFormatJson(resultPreview),
    [resultPreview],
  );

  return (
    <div
      className={[
        "mt-2 mb-2 mx-2 px-4 py-3",
        "bg-bp-mid border border-border-subtle rounded-md",
        "font-data overflow-x-auto",
      ].join(" ")}
    >
      <div className="font-data text-data-sm">
        <span className="text-text-muted">tool: </span>
        <span className="font-bold text-accent-info">{tool}</span>
      </div>

      <div className="mt-3">
        <div className="font-body text-stat-label font-semibold uppercase tracking-[1px] text-text-muted mb-1">
          args
        </div>
        <pre className="font-data text-data-sm leading-relaxed whitespace-pre m-0">
          <code>{argsJson}</code>
        </pre>
      </div>

      {error !== null ? (
        <div className="mt-3">
          <div className="font-body text-stat-label font-semibold uppercase tracking-[1px] text-accent-alert mb-1">
            error
          </div>
          <pre className="font-data text-data-sm leading-relaxed whitespace-pre m-0 text-accent-alert">
            <code>{error}</code>
          </pre>
        </div>
      ) : (
        <div className="mt-3">
          <div className="font-body text-stat-label font-semibold uppercase tracking-[1px] text-text-muted mb-1">
            result preview
          </div>
          <pre className="font-data text-data-sm leading-relaxed whitespace-pre m-0">
            <code>{resultJson}</code>
          </pre>
        </div>
      )}

      <div className="mt-3 font-data text-micro text-text-muted">
        {durationMs} ms · step {stepIndex + 1} of {totalSteps}
      </div>
    </div>
  );
}

/** Pretty-print a JSON-shaped value for the engineering view.
 *  Falls back to the raw string when the input isn't JSON-parseable. */
function safeFormatJson(value: unknown): string {
  if (typeof value === "string") {
    // Try to parse + reformat with 2-space indent. If parsing fails,
    // return the raw string (preserves the truncation marker the
    // backend may have appended).
    try {
      const parsed = JSON.parse(value);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return value;
    }
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
