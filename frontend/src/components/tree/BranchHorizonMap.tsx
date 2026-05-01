import { useEffect, useMemo, useState, type ReactElement } from "react";
import "@/styles/horizonMap.css";
import { useT } from "@/i18n/useT";
import {
  bucketBranches,
  eduRank,
  relatednessTier,
  SOC_ROLLUP_ORDER,
  type BucketedLane,
  type LaneId,
} from "@/data/horizonLayout";
import { BranchHorizonChip } from "./BranchHorizonChip";
import type { CareerBranch } from "@/types/build";

interface BranchHorizonMapProps {
  branches: CareerBranch[];
  buildEduLevel: string | null;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
  highlightedNodeIds?: ReadonlySet<string>;
}

const LANE_DATA: Record<LaneId, string> = {
  business: "business",
  technical: "technical",
  arts: "arts",
  education: "education",
  care: "care",
  service: "service",
  trades: "trades",
};

const TAXONOMY_ICON = (
  <svg
    className="horizon-lane-icon"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.4"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M4 7h16" />
    <path d="M4 12h16" />
    <path d="M4 17h16" />
    <path d="M8 4v16" />
  </svg>
);

/**
 * Anchor sub-line copy: "Bachelor's-anchored" / "Master's-anchored" / etc.
 * Falls back to "Bachelor's-anchored" when the build edu is null (D#3 fallback).
 */
function anchorTag(buildEduLevel: string | null): string {
  if (!buildEduLevel) return "Bachelor's-anchored";
  const rank = eduRank(buildEduLevel);
  if (rank == null) return "Bachelor's-anchored";
  if (rank <= 0) return "High-school-anchored";
  if (rank === 1) return "Sub-degree-anchored";
  if (rank === 2) return "Associate's-anchored";
  if (rank === 3) return "Bachelor's-anchored";
  if (rank === 4) return "Master's-anchored";
  return "Doctoral-anchored";
}

export function BranchHorizonMap({
  branches,
  buildEduLevel,
  selectedNodeId,
  onSelectNode,
  highlightedNodeIds,
}: BranchHorizonMapProps) {
  const t = useT();
  const [hideSupplemental, setHideSupplemental] = useState(false);
  const [expanded, setExpanded] = useState<Set<LaneId>>(() => new Set());

  const lanes = useMemo(
    () => bucketBranches(branches, buildEduLevel, hideSupplemental),
    [branches, buildEduLevel, hideSupplemental],
  );
  const visibleLaneIds = useMemo(() => {
    const ids = SOC_ROLLUP_ORDER.filter(
      (laneId) => lanes[laneId].totalBeforeCap > 0,
    );
    return ids.length > 0 ? ids : SOC_ROLLUP_ORDER.slice(0, 1);
  }, [lanes]);

  // When expanded, show all bucketed branches for that lane (recompute
  // without the cap so we don't truncate inside the expansion). Keyed on
  // a boolean so toggling between two lanes' expanded state doesn't
  // re-run the bucketer twice on the same input (faang-staff Finding 4).
  const anyExpanded = expanded.size > 0;
  const expandedLanes = useMemo(
    () =>
      anyExpanded
        ? bucketBranches(branches, buildEduLevel, hideSupplemental, {
            laneCap: Number.MAX_SAFE_INTEGER,
          })
        : null,
    [branches, buildEduLevel, hideSupplemental, anyExpanded],
  );

  const toggleExpand = (laneId: LaneId) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(laneId)) next.delete(laneId);
      else next.add(laneId);
      return next;
    });
  };

  // Drop the selection if the user toggles "Hide supplemental" on while a
  // Supplemental chip is selected — otherwise the chat stays anchored to a
  // now-invisible scope (faang-staff Finding 1).
  useEffect(() => {
    if (!hideSupplemental || !selectedNodeId) return;
    const selected = branches.find(
      (b) => `chip-${b.to_soc}` === selectedNodeId,
    );
    if (selected && relatednessTier(selected.relatedness) === "Supplemental") {
      onSelectNode(null);
    }
  }, [hideSupplemental, selectedNodeId, branches, onSelectNode]);

  const renderLane = (laneId: LaneId): ReactElement => {
    const lane = lanes[laneId];
    const isExpanded = expanded.has(laneId);
    const visibleLane: BucketedLane =
      isExpanded && expandedLanes ? expandedLanes[laneId] : lane;
    const visibleBranches = visibleLane.branches;
    const overflowCount = lane.totalBeforeCap - lane.branches.length;
    const hasSelection = visibleBranches.some(
      (b) => `chip-${b.to_soc}` === selectedNodeId,
    );

    return (
      <div
        key={laneId}
        className="horizon-lane"
        data-lane={LANE_DATA[laneId]}
        data-has-selection={hasSelection ? "true" : undefined}
      >
        <header
          className="horizon-lane-header"
          data-testid={`lane-header-${LANE_DATA[laneId]}`}
        >
          <div className="horizon-lane-header-left">
            <h4 className="horizon-lane-label">
              {TAXONOMY_ICON}
              {t(`tree.lane.${laneId}`)}
            </h4>
            <span className="horizon-lane-subtitle">
              {t(`tree.lane.${laneId}.subtitle`)}
            </span>
          </div>
          {visibleLane.totalBeforeCap > 0 && (
            <span className="horizon-lane-count">
              {isExpanded
                ? `${visibleBranches.length} shown`
                : `${visibleBranches.length} of ${visibleLane.totalBeforeCap} shown`}
            </span>
          )}
        </header>

        {visibleBranches.length === 0 ? (
          <div
            className="horizon-lane-empty"
            data-testid={`lane-empty-${LANE_DATA[laneId]}`}
            role="status"
          >
            <div className="horizon-lane-empty-icon" aria-hidden="true">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <path d="M12 8v4" />
                <path d="M12 16h.01" />
              </svg>
            </div>
            <div className="horizon-lane-empty-text">
              <div className="horizon-lane-empty-title">
                {t(`tree.lane.empty.${laneId}.title`)}
              </div>
              <div className="horizon-lane-empty-sub">
                {t(`tree.lane.empty.${laneId}.sub`)}
              </div>
            </div>
          </div>
        ) : (
          <div className="horizon-chip-row" data-expanded={isExpanded ? "true" : undefined}>
            {visibleBranches.map((branch) => {
              const id = `chip-${branch.to_soc}`;
              return (
                <BranchHorizonChip
                  key={id}
                  branch={branch}
                  selected={id === selectedNodeId}
                  flashing={highlightedNodeIds?.has(id) ?? false}
                  onClick={() => onSelectNode(id)}
                />
              );
            })}

            {!isExpanded && overflowCount > 0 && (
              <button
                type="button"
                className="horizon-chip-more"
                data-testid={`btn-lane-expand-${LANE_DATA[laneId]}`}
                aria-label={t("tree.expand.more")
                  .replace("{count}", String(overflowCount))
                  .replace("{lane}", t(`tree.lane.${laneId}.subtitle`))}
                onClick={() => toggleExpand(laneId)}
              >
                <span className="horizon-chip-more-count">
                  {t("tree.expand.more.count").replace("{count}", String(overflowCount))}
                </span>
                <span className="horizon-chip-more-hint">
                  {t(`tree.lane.${laneId}.morehint`)}
                </span>
              </button>
            )}

            {/* Only render Show Fewer when there's actual overflow to hide
             * (faang-staff Finding 2 — filter can shrink an expanded lane
             * below the cap, leaving a no-op collapse button). */}
            {isExpanded && lane.totalBeforeCap > lane.branches.length && (
              <button
                type="button"
                className="horizon-chip-collapse"
                data-testid={`btn-lane-collapse-${LANE_DATA[laneId]}`}
                aria-label={t("tree.expand.collapse")}
                onClick={() => toggleExpand(laneId)}
              >
                {t("tree.expand.collapse")}
              </button>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div
      className="horizon-col"
      data-testid="region-branch-horizon"
      role="region"
      aria-label={t("tree.horizon.regionLabel")}
    >
      <div className="horizon-header">
        <div className="horizon-header-row">
          <div>
            <div className="horizon-eyebrow">{t("tree.horizon.eyebrow")}</div>
            <h3 className="horizon-title">{t("tree.horizon.title")}</h3>
          </div>
          <button
            type="button"
            data-testid="toggle-hide-supplemental"
            role="switch"
            aria-checked={hideSupplemental}
            aria-label={t("tree.filter.hideSupplemental")}
            onClick={() => setHideSupplemental((s) => !s)}
            className="toggle-row"
          >
            <span className="toggle-label">{t("tree.filter.hideSupplemental")}</span>
            <span className="toggle-switch" data-on={hideSupplemental ? "true" : undefined} />
          </button>
        </div>
        <p className="horizon-anchor">
          <span className="horizon-anchor-tag">{anchorTag(buildEduLevel)}</span>
        </p>
      </div>

      <div className="horizon-lanes">
        {visibleLaneIds.map((laneId) => renderLane(laneId))}
      </div>
    </div>
  );
}
