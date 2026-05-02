import { useEffect, useRef, useState } from "react";
import { BaseEdge, EdgeLabelRenderer, getBezierPath } from "@xyflow/react";
import type { EdgeProps } from "@xyflow/react";
import { motion, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";
import { useT } from "@/i18n/useT";
import {
  formatPayDelta,
  formatPayFull,
  type EdgeLabel,
  type EdgeLabelHoverContext,
} from "@/data/edgeLabel";

/**
 * T1.1 — Custom React Flow edge that renders the dominant delta as a
 * pill at the edge midpoint. Pill colors follow the spec's two-color
 * rule: improvement (thrive) vs neutral (muted). Hover expands to the
 * full delta detail.
 */
export interface EdgeWithLabelData extends Record<string, unknown> {
  label: EdgeLabel | null;
  hoverContext: EdgeLabelHoverContext;
  /** Original branch color for the underlying line. */
  stroke: string;
  /** Stroke width (pre-relatedness) for the line. */
  strokeWidth: number;
  /** Opacity (pre-relatedness) for the line. */
  opacity: number;
  /**
   * True when the edge connects to or from the currently-selected
   * node. Drives subtle shadow + scale emphasis on the pill.
   */
  selectedAdjacent?: boolean;
}

const HOVER_HOLD_MS = 200;
const HOVER_GRACE_MS = 100;

function HoverDetail({
  context,
  t,
}: {
  context: EdgeLabelHoverContext;
  t: (key: string) => string;
}): string {
  if (!context) return "";
  switch (context.kind) {
    case "education":
      return t("future.edge.hover.educationTo")
        .replace("{from}", context.fromKey ? t(context.fromKey) : context.fromText)
        .replace("{to}", t(context.toKey));
    case "experience":
      return t("future.edge.hover.experienceTo")
        .replace("{fromTier}", t(context.fromTierKey))
        .replace("{toTier}", t(context.toTierKey))
        .replace(
          "{years}",
          context.yearsDelta != null
            ? Math.round(Math.abs(context.yearsDelta)).toString()
            : "?",
        );
    case "pay":
      return t("future.edge.hover.payTo")
        .replace("{fromPay}", `$${Math.round(context.fromWage).toLocaleString()}`)
        .replace("{toPay}", `$${Math.round(context.toWage).toLocaleString()}`)
        .replace("{deltaPay}", formatPayFull(context.delta));
    case "relatedness_close":
    case "relatedness_stretch":
      return t("future.edge.hover.relatedRank")
        .replace("{label}", t(context.label))
        .replace("{rank}", context.rank.toString())
        .replace("{total}", context.total.toString());
  }
}

// Hover detail for pay needs to use the hover context's exact wage,
// but the default pill text already uses the rounded version. Keeping
// formatPayDelta exported just for tests + symmetry.
void formatPayDelta;

export function EdgeWithLabel(props: EdgeProps) {
  const {
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    data,
  } = props;
  const t = useT();
  const reducedMotion = useReducedMotion() ?? false;
  const [hovered, setHovered] = useState(false);
  // Refs (not state) so unmount cleanup can read the live value
  // without re-rendering. State setters survived the mount lifecycle
  // until the user navigated away — Finding #4 from §8 staff review.
  const hoverTimerRef = useRef<number | null>(null);
  const exitTimerRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (hoverTimerRef.current != null) {
        window.clearTimeout(hoverTimerRef.current);
      }
      if (exitTimerRef.current != null) {
        window.clearTimeout(exitTimerRef.current);
      }
    },
    [],
  );

  const d = (data ?? {}) as EdgeWithLabelData;
  const stroke = d.stroke ?? "var(--color-text-muted)";
  const strokeWidth = d.strokeWidth ?? 1.5;
  const opacity = d.opacity ?? 0.6;

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const handlePointerEnter = () => {
    if (exitTimerRef.current != null) {
      window.clearTimeout(exitTimerRef.current);
      exitTimerRef.current = null;
    }
    if (hovered) return;
    hoverTimerRef.current = window.setTimeout(
      () => setHovered(true),
      HOVER_HOLD_MS,
    );
  };

  const handlePointerLeave = () => {
    if (hoverTimerRef.current != null) {
      window.clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = null;
    }
    exitTimerRef.current = window.setTimeout(
      () => setHovered(false),
      HOVER_GRACE_MS,
    );
  };

  const renderLabel = d.label;

  return (
    <>
      <BaseEdge id={id} path={edgePath} style={{ stroke, strokeWidth, opacity }} />
      {renderLabel && (
        <EdgeLabelRenderer>
          {/* Outer wrapper owns the absolute positioning. Framer
              Motion's `layout` prop on the inner pill would otherwise
              overwrite our translate() with its own animated value
              and yank the pill back to (0,0) of the renderer. */}
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: "auto",
            }}
            onPointerEnter={handlePointerEnter}
            onPointerLeave={handlePointerLeave}
          >
            <motion.div
              layout="size"
              transition={reducedMotion ? { duration: 0 } : springs.snappy}
              data-testid={`edge-label-${id}`}
              data-edge-label-kind={renderLabel.kind}
              data-edge-label-positive={renderLabel.isPositive ? "true" : "false"}
              className={`tree-edge-pill ${
                renderLabel.isPositive
                  ? "tree-edge-pill--improvement"
                  : "tree-edge-pill--neutral"
              } ${d.selectedAdjacent ? "tree-edge-pill--adjacent" : ""}`}
            >
              {hovered
                ? HoverDetail({ context: d.hoverContext, t }) || renderLabel.text
                : renderLabel.text}
            </motion.div>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
