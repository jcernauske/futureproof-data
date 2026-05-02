import { useCallback, useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { useT } from "@/i18n/useT";
import { rankNodesForTour, TOUR_LABEL_KEYS, type TourId } from "@/data/tourRanking";
import type { TreeNode } from "@/types/tree";

/**
 * T1.2 — Tour chip row above the tree. Each chip plays a guided
 * navigate-flash sequence on its top-3 ranked nodes: pan + zoom to a
 * node, flash it, advance to the next. The orchestration lives in the
 * host (`FutureScreen.handlePlayTour`) because it needs both the
 * highlight driver AND the React Flow viewport. No Gemma narration —
 * chat opener stays generic.
 *
 * Chips look distinct from the filter chip rails: insight-tinted with a
 * leading ✦ glyph so the student reads them as actions, not toggles.
 */

interface TourChipRowProps {
  /** Filtered tree the rankings consider. */
  tree: TreeNode;
  /** Receives the ranked node IDs (top-3) for the tour to play. */
  onPlayTour: (nodeIds: string[]) => void;
  /** True while the underlying tree is loading; chips render disabled. */
  loading?: boolean;
}

const TOUR_IDS: TourId[] = [
  "highest_ceiling",
  "ai_resilient",
  "fastest_to_mid",
  "biggest_pay_jump",
];

const ACTIVE_TTL_MS = 4500;

export function TourChipRow({ tree, onPlayTour, loading = false }: TourChipRowProps) {
  const t = useT();
  const reducedMotion = useReducedMotion() ?? false;

  const handleClick = useCallback(
    (id: TourId) => {
      const targets = rankNodesForTour(id, tree, 3);
      if (targets.length === 0) return;
      onPlayTour(targets);
    },
    [tree, onPlayTour],
  );

  return (
    <div
      className="flex flex-wrap items-center gap-2"
      data-testid="tour-chip-row"
      role="group"
      aria-label="Career tour shortcuts"
    >
      {TOUR_IDS.map((id) => {
        const labelKey = TOUR_LABEL_KEYS[id];
        const label = t(labelKey);
        const targets = rankNodesForTour(id, tree, 3);
        const isEmpty = !loading && targets.length === 0;
        const disabled = loading || isEmpty;
        return (
          <TourChip
            key={id}
            id={id}
            label={label}
            disabled={disabled}
            isEmpty={isEmpty}
            reducedMotion={reducedMotion}
            ariaLabel={t("future.tour.aria").replace("{label}", label)}
            emptyTooltip={t("future.tour.empty")}
            onClick={() => handleClick(id)}
          />
        );
      })}
    </div>
  );
}

interface TourChipProps {
  id: TourId;
  label: string;
  disabled: boolean;
  isEmpty: boolean;
  reducedMotion: boolean;
  ariaLabel: string;
  emptyTooltip: string;
  onClick: () => void;
}

function TourChip({
  id,
  label,
  disabled,
  isEmpty,
  reducedMotion,
  ariaLabel,
  emptyTooltip,
  onClick,
}: TourChipProps) {
  const [pulseTick, setPulseTick] = useState(0);
  const [active, setActive] = useState(false);
  const ttlTimeoutRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (ttlTimeoutRef.current != null) {
        window.clearTimeout(ttlTimeoutRef.current);
      }
    },
    [],
  );

  const handleClick = () => {
    if (disabled) return;
    onClick();
    setPulseTick((k) => k + 1);
    setActive(true);
    if (ttlTimeoutRef.current != null) {
      window.clearTimeout(ttlTimeoutRef.current);
    }
    ttlTimeoutRef.current = window.setTimeout(() => {
      setActive(false);
      ttlTimeoutRef.current = null;
    }, ACTIVE_TTL_MS);
  };

  const baseClass =
    "inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 font-body text-small font-bold border transition-colors duration-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]";
  const variantClass = isEmpty
    ? "bg-[rgba(184,169,232,0.08)] border-border-subtle text-text-muted cursor-not-allowed"
    : disabled
      ? "bg-state-disabled border-border-subtle text-text-muted cursor-not-allowed"
      : "bg-[rgba(184,169,232,0.08)] border-[rgba(184,169,232,0.22)] text-accent-insight hover:bg-[rgba(184,169,232,0.14)] hover:border-[rgba(184,169,232,0.36)] hover:text-text-primary hover:shadow-glow-insight cursor-pointer";

  const pulseAnim =
    active && !reducedMotion
      ? {
          boxShadow: [
            "0 0 0 rgba(184, 169, 232, 0)",
            "0 0 24px rgba(184, 169, 232, 0.45)",
            "0 0 12px rgba(184, 169, 232, 0.30)",
            "0 0 24px rgba(184, 169, 232, 0.45)",
            "0 0 0 rgba(184, 169, 232, 0)",
          ],
        }
      : undefined;

  return (
    <motion.button
      key={pulseTick}
      type="button"
      data-testid={`tour-chip-${id}`}
      data-empty={isEmpty ? "true" : "false"}
      data-active={active ? "true" : "false"}
      aria-label={ariaLabel}
      aria-disabled={disabled || undefined}
      title={isEmpty ? emptyTooltip : undefined}
      onClick={handleClick}
      animate={pulseAnim}
      transition={
        pulseAnim
          ? { duration: 1.4, times: [0, 0.15, 0.5, 0.85, 1], ease: "easeInOut" }
          : undefined
      }
      className={`${baseClass} ${variantClass}`}
    >
      <span aria-hidden="true" className="text-accent-insight">
        ✦
      </span>
      <span>{label}</span>
    </motion.button>
  );
}
