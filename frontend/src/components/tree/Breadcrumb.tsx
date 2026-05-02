import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";
import { useT } from "@/i18n/useT";

/**
 * T1.4 — Selection breadcrumb above the tree. Renders only when the
 * student has a non-root selection. Each segment is clickable; if a
 * filter has hidden the segment's underlying node it renders in a
 * ghost state (50% opacity, strikethrough) but stays clickable —
 * clicking it is harmless because the filter still gates re-selection,
 * but the visible path tells the student "your selection is still
 * here, the filter is just hiding it."
 */

export interface BreadcrumbSegment {
  socCode: string;
  title: string;
  /** Tree node id (matches treeFlowLayout.ts ID scheme) for re-select. */
  nodeId: string | null;
  /** Hidden by an active filter — render in ghost state. */
  hidden: boolean;
  /** Currently selected — the deepest visible segment. */
  current: boolean;
  /** Marks the root segment so we can swap to root copy. */
  isRoot: boolean;
}

interface BreadcrumbProps {
  /** Ordered segments from root → deepest selection. Empty/single-segment hides. */
  segments: BreadcrumbSegment[];
  /** Click handler — passes the segment so caller decides what to do (re-select / clear). */
  onSegmentClick: (segment: BreadcrumbSegment) => void;
  /** Truncation cap. 24 desktop, 16 mobile. */
  maxCharsPerSegment?: number;
}

const SEPARATOR = "›";
const DEFAULT_MAX_CHARS = 24;

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}…`;
}

export function Breadcrumb({
  segments,
  onSegmentClick,
  maxCharsPerSegment = DEFAULT_MAX_CHARS,
}: BreadcrumbProps) {
  const t = useT();
  const reducedMotion = useReducedMotion() ?? false;

  // Hide breadcrumb in root-only mode — recovers vertical space until
  // the student actually starts wandering.
  if (segments.length <= 1) return null;

  return (
    <nav
      aria-label="Selection breadcrumb"
      data-testid="future-breadcrumb"
      className="flex flex-row items-center gap-1 mt-3 mb-3 h-6"
    >
      <AnimatePresence initial={false}>
        {segments.map((segment, idx) => {
          const display = segment.isRoot
            ? t("future.breadcrumb.root")
            : truncate(segment.title, maxCharsPerSegment);
          const truncated =
            !segment.isRoot && segment.title.length > maxCharsPerSegment;
          const ariaLabel = segment.hidden
            ? t("future.breadcrumb.aria.hidden")
            : segment.isRoot
              ? t("future.breadcrumb.aria.root")
              : t("future.breadcrumb.aria.select").replace("{title}", segment.title);

          const stateClass = segment.hidden
            ? "text-text-muted line-through opacity-50 hover:text-text-muted"
            : segment.current
              ? "bg-state-active text-accent-thrive"
              : "text-text-secondary hover:bg-white/[0.04] hover:text-text-primary";

          return (
            <motion.span
              key={`${segment.socCode}-${idx}`}
              className="flex items-center gap-1"
              initial={
                reducedMotion ? false : { opacity: 0, x: -8 }
              }
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8, transition: { duration: 0.15 } }}
              transition={reducedMotion ? { duration: 0 } : springs.snappy}
            >
              {idx > 0 && (
                <span
                  aria-hidden="true"
                  className="font-data text-text-muted opacity-50 select-none"
                >
                  {SEPARATOR}
                </span>
              )}
              <button
                type="button"
                data-testid={`breadcrumb-${idx}-${segment.socCode}`}
                data-hidden={segment.hidden ? "true" : "false"}
                data-current={segment.current ? "true" : "false"}
                title={
                  segment.hidden
                    ? t("future.breadcrumb.hiddenTooltip")
                    : truncated
                      ? segment.title
                      : undefined
                }
                aria-label={ariaLabel}
                onClick={() => onSegmentClick(segment)}
                className={`rounded-md px-2.5 py-1 font-body text-small font-semibold whitespace-nowrap transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] ${stateClass}`}
              >
                {display}
              </button>
            </motion.span>
          );
        })}
      </AnimatePresence>
    </nav>
  );
}

/**
 * Walk a tree to find the path from root → target node id (using the
 * same id scheme as treeFlowLayout.ts). Returns the path of TreeNodes
 * in order [root, ..., selected]. Returns null when the target isn't
 * reachable — the caller should drop the breadcrumb to root-only mode.
 */
import type { TreeNode } from "@/types/tree";

export function findPathToNodeId(
  tree: TreeNode,
  selectedNodeId: string,
): TreeNode[] | null {
  if (selectedNodeId === `root-${tree.soc_code}`) return [tree];
  for (let branchIdx = 0; branchIdx < tree.children.length; branchIdx++) {
    const branch = tree.children[branchIdx]!;
    const branchId = `career-${branch.soc_code}-${branchIdx}`;
    if (selectedNodeId === branchId) return [tree, branch];
    for (let epIdx = 0; epIdx < branch.children.length; epIdx++) {
      const ep = branch.children[epIdx]!;
      const epId = `endpoint-${ep.soc_code}-${branchIdx}-${epIdx}`;
      if (selectedNodeId === epId) return [tree, branch, ep];
    }
  }
  return null;
}

/**
 * Compute breadcrumb segments from a snapshot of the path (titles +
 * SOC codes from when the selection was last successful) plus the
 * current filtered tree (used to decide which segments are visible
 * vs. ghosted by the filter).
 */
export function buildBreadcrumbSegments(
  snapshot: { socCode: string; title: string }[],
  filteredTree: TreeNode,
  selectedNodeId: string | null,
): BreadcrumbSegment[] {
  if (snapshot.length === 0) return [];
  const visibleSocs = new Set<string>();
  visibleSocs.add(filteredTree.soc_code);
  filteredTree.children.forEach((b) => {
    visibleSocs.add(b.soc_code);
    b.children.forEach((ep) => visibleSocs.add(ep.soc_code));
  });

  return snapshot.map((entry, idx) => {
    const isRoot = idx === 0;
    const hidden = !isRoot && !visibleSocs.has(entry.socCode);

    // nodeId mirrors layout: root has stable id; non-root needs the
    // current branch index (recomputed below). For ghost segments we
    // can't know the branch index, so we punt with null.
    let nodeId: string | null = null;
    if (isRoot) {
      nodeId = `root-${filteredTree.soc_code}`;
    } else if (!hidden) {
      // Find the current branch/endpoint index in the filtered tree.
      const branchIdx = filteredTree.children.findIndex(
        (b) => b.soc_code === entry.socCode,
      );
      if (branchIdx !== -1) {
        nodeId = `career-${entry.socCode}-${branchIdx}`;
      } else {
        outer: for (let bi = 0; bi < filteredTree.children.length; bi++) {
          const branch = filteredTree.children[bi]!;
          const epIdx = branch.children.findIndex(
            (ep) => ep.soc_code === entry.socCode,
          );
          if (epIdx !== -1) {
            nodeId = `endpoint-${entry.socCode}-${bi}-${epIdx}`;
            break outer;
          }
        }
      }
    }

    return {
      socCode: entry.socCode,
      title: entry.title,
      nodeId,
      hidden,
      current: !hidden && nodeId != null && nodeId === selectedNodeId,
      isRoot,
    };
  });
}
