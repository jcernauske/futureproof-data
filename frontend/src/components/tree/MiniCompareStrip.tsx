import { motion, useReducedMotion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";
import { useT } from "@/i18n/useT";
import type { TreeNode } from "@/types/tree";
import { formatPayDelta } from "@/data/edgeLabel";

/**
 * T1.3 — Mini-compare delta strip rendered above the existing
 * SelectedNodeCard body when a non-root node is selected. Computes
 * `selected.<stat> − root.<stat>` for pay (median_wage), AI res, and
 * growth, and renders each as one row with a directional arrow.
 *
 * Per-row null-handling: if either side is null for a given stat the
 * row is hidden. If all three rows are hidden the strip suppresses
 * itself (header included) so the card never renders an empty
 * comparison shell.
 */

interface MiniCompareStripProps {
  selected: TreeNode;
  root: TreeNode;
  /** Below this viewport width the header swaps to its short form. */
  narrowBreakpointPx?: number;
}

type Direction = "up" | "down" | "flat";

interface DeltaRow {
  labelKey: string;
  display: string;
  direction: Direction;
}

const NARROW_BREAKPOINT = 480;

function direction(delta: number): Direction {
  if (delta > 0) return "up";
  if (delta < 0) return "down";
  return "flat";
}

function arrow(dir: Direction): string {
  switch (dir) {
    case "up":
      return "▲";
    case "down":
      return "▼";
    case "flat":
      return "▬";
  }
}

function formatStatDelta(delta: number): string {
  if (delta === 0) return "0";
  const sign = delta > 0 ? "+" : "−";
  return `${sign}${Math.abs(delta)}`;
}

function buildRows(selected: TreeNode, root: TreeNode): DeltaRow[] {
  const rows: DeltaRow[] = [];
  if (selected.median_wage != null && root.median_wage != null) {
    const delta = selected.median_wage - root.median_wage;
    rows.push({
      labelKey: "future.compare.row.pay",
      display: formatPayDelta(delta),
      direction: direction(delta),
    });
  }
  if (selected.res != null && root.res != null) {
    const delta = selected.res - root.res;
    rows.push({
      labelKey: "future.compare.row.aiRes",
      display: formatStatDelta(delta),
      direction: direction(delta),
    });
  }
  if (selected.grw != null && root.grw != null) {
    const delta = selected.grw - root.grw;
    rows.push({
      labelKey: "future.compare.row.growth",
      display: formatStatDelta(delta),
      direction: direction(delta),
    });
  }
  return rows;
}

function isNarrowViewport(narrowBreakpointPx: number): boolean {
  if (typeof window === "undefined") return false;
  return window.innerWidth < narrowBreakpointPx;
}

export function MiniCompareStrip({
  selected,
  root,
  narrowBreakpointPx = NARROW_BREAKPOINT,
}: MiniCompareStripProps) {
  const t = useT();
  const reducedMotion = useReducedMotion() ?? false;

  // Same SOC = no delta to surface. Caller should also gate, but the
  // strip is defensive — no "compared to itself" frame.
  if (selected.soc_code === root.soc_code) return null;

  const rows = buildRows(selected, root);
  if (rows.length === 0) return null;

  const narrow = isNarrowViewport(narrowBreakpointPx);
  const headerKey = narrow ? "future.compare.headerShort" : "future.compare.header";
  const headerText = t(headerKey)
    .replace("{career}", root.title.length > 28 ? `${root.title.slice(0, 27)}…` : root.title)
    .toUpperCase();

  return (
    <motion.section
      data-testid="selected-node-compare"
      aria-label={t("future.compare.aria")}
      initial={reducedMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={reducedMotion ? { duration: 0 } : { ...springs.smooth, delay: 0.08 }}
      className="rounded-lg border border-border-subtle bg-bp-deep px-3.5 py-3 mt-4 mb-5"
    >
      <header
        className="font-data text-[11px] font-bold tracking-[1.5px] text-accent-info mb-3"
        data-testid="compare-header"
      >
        {headerText}
      </header>
      <ul className="flex flex-col gap-2">
        {rows.map((row, i) => (
          <motion.li
            key={row.labelKey}
            initial={reducedMotion ? false : { opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            transition={
              reducedMotion
                ? { duration: 0 }
                : { ...springs.snappy, delay: i * stagger.fast }
            }
            className="flex flex-row items-center"
            data-testid={`compare-row-${row.labelKey.split(".").pop()}`}
            data-direction={row.direction}
          >
            <span
              className="font-body text-small font-semibold text-text-secondary"
              style={{ flex: "0 0 88px" }}
            >
              {t(row.labelKey)}
            </span>
            <span
              aria-hidden="true"
              className={`font-data text-[13px] text-center ${
                row.direction === "up" ? "text-accent-thrive" : "text-text-muted"
              }`}
              style={{ flex: "0 0 18px" }}
            >
              {arrow(row.direction)}
            </span>
            <span
              className={`font-data text-data-sm font-bold tabular-nums ${
                row.direction === "up" ? "text-accent-thrive" : "text-text-muted"
              }`}
              style={{ flex: 1 }}
            >
              {row.display}
            </span>
          </motion.li>
        ))}
      </ul>
    </motion.section>
  );
}
