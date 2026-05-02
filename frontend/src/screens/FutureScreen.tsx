import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import { getTree } from "@/api/tree";
import type { AskScope, BuildSummary } from "@/api/menu";
import { BranchTreeFlow, type PanTarget } from "@/components/tree/BranchTreeFlow";
import { TreeFallback } from "@/components/tree/TreeFallback";
import { BranchHighlightDriver } from "@/components/tree/BranchHighlightDriver";
import { FutureChatSheet } from "@/components/tree/FutureChatSheet";
import { SelectedNodeCard } from "@/components/tree/SelectedNodeCard";
import { EducationFilterRow } from "@/components/tree/EducationFilterRow";
import { StatFilterRow } from "@/components/tree/StatFilterRow";
import { TourChipRow } from "@/components/tree/TourChipRow";
import { BossFilterRow } from "@/components/tree/BossFilterRow";
import { ExperienceRangeSlider } from "@/components/tree/ExperienceRangeSlider";
import {
  CompanionRail,
  type CompanionMode,
  railWidth,
} from "@/components/tree/CompanionRail";
import {
  Breadcrumb,
  buildBreadcrumbSegments,
  findPathToNodeId,
} from "@/components/tree/Breadcrumb";
import {
  filterTreeByBoss,
  availableBossFilters,
  type BossFilter,
} from "@/data/bossFilter";
import {
  filterTreeByExperience,
  isFullRange as isFullExperienceRange,
  EXPERIENCE_RANGE_FULL,
  type ExperienceRange,
} from "@/data/experienceFilter";
import { computePathRarity } from "@/data/pathRarity";
import {
  filterTreeByEducation,
  availableEducationFilters,
  type EducationFilter,
} from "@/data/educationFilter";
import {
  filterTreeByStats,
  availableStatFilters,
  type StatFilter,
} from "@/data/statFilter";
import { GemmaChat } from "@/components/menu/GemmaChat";
import { PageContainer } from "@/components/ui/PageContainer";
import { useT } from "@/i18n/useT";
import type { TreeResponse, TreeNode } from "@/types/tree";

type ScreenState = "loading" | "tree" | "fallback" | "error";

interface FilterEmptyStateProps {
  careerTitle: string;
  filterLabel: string;
  onClear: () => void;
  t: (key: string) => string;
}

/**
 * Centered overlay rendered inside the tree pane when education
 * filters hide every L1 branch. The root stays visible underneath so
 * the student keeps spatial context — the overlay just explains why
 * the rest of the tree is empty and offers a one-tap reset.
 *
 * Pointer events: container is `pointer-events-none` so React Flow's
 * pan/zoom under the overlay still works on empty space; the inner
 * card re-enables pointer events for the clear button.
 */
function FilterEmptyState({
  careerTitle,
  filterLabel,
  onClear,
  t,
}: FilterEmptyStateProps) {
  const message = t("future.filter.empty.message")
    .replace("{career}", careerTitle)
    .replace("{filters}", filterLabel);
  return (
    <div
      className="absolute inset-0 flex items-end justify-center px-6 pb-10 pointer-events-none"
      data-testid="filter-empty-state"
    >
      <div className="pointer-events-auto bg-bp-deep/90 backdrop-blur-sm border border-border-subtle rounded-lg px-5 py-4 max-w-md text-center shadow-lg">
        <p className="font-body text-small text-text-secondary mb-2">
          {message}
        </p>
        <button
          type="button"
          data-testid="btn-clear-all-filters"
          onClick={onClear}
          className="font-body text-small font-semibold text-accent-info hover:underline cursor-pointer"
        >
          {t("future.filter.empty.clear")}
        </button>
      </div>
    </div>
  );
}

const NODE_DEBOUNCE_MS = 300;
const FLASH_TTL_MS = 700;
const TABLET_BREAKPOINT_PX = 768;

function buildSummaryFromBuild(
  build: ReturnType<typeof useBuildStore.getState>["build"],
): BuildSummary | null {
  if (!build) return null;
  const wins = build.gauntlet?.fights?.filter((f) => f.result === "win").length ?? 0;
  const losses = build.gauntlet?.fights?.filter((f) => f.result === "lose").length ?? 0;
  const draws = build.gauntlet?.fights?.filter((f) => f.result === "draw").length ?? 0;
  return {
    build_id: build.build_id,
    created_at: build.created_at,
    school_name: build.school_name,
    major_text: build.major_text,
    career_title: build.career.occupation_title,
    ern: build.career.stats.ern ?? null,
    roi: build.career.stats.roi ?? null,
    res: build.career.stats.res ?? null,
    grw: build.career.stats.grw ?? null,
    aura: build.career.stats.aura ?? null,
    wins,
    losses,
    draws,
    profile_name: build.profile_name ?? "",
    animal_emoji: build.animal_emoji ?? null,
  };
}

interface NodeRef {
  id: string;
  socCode: string;
  title: string;
  /** The full TreeNode the ref points at — needed for card rendering. */
  node: TreeNode;
}

function walkTreeNodes(tree: TreeNode): NodeRef[] {
  // Mirrors treeFlowLayout.ts ID scheme:
  //   root:     `root-${tree.soc_code}`
  //   L1:       `career-${branch.soc_code}-${branchIdx}`
  //   L2:       `endpoint-${ep.soc_code}-${branchIdx}-${epIdx}`
  // Branch-label intermediaries were removed — root connects directly
  // to the L1 career node.
  const out: NodeRef[] = [];
  out.push({
    id: `root-${tree.soc_code}`,
    socCode: tree.soc_code,
    title: tree.title,
    node: tree,
  });
  tree.children.forEach((branch, branchIdx) => {
    out.push({
      id: `career-${branch.soc_code}-${branchIdx}`,
      socCode: branch.soc_code,
      title: branch.title,
      node: branch,
    });
    branch.children.forEach((ep, epIdx) => {
      out.push({
        id: `endpoint-${ep.soc_code}-${branchIdx}-${epIdx}`,
        socCode: ep.soc_code,
        title: ep.title,
        node: ep,
      });
    });
  });
  return out;
}

function useIsTablet(): boolean {
  const [isTablet, setIsTablet] = useState(() =>
    typeof window === "undefined"
      ? true
      : window.matchMedia(`(min-width: ${TABLET_BREAKPOINT_PX}px)`).matches,
  );
  useEffect(() => {
    if (typeof window === "undefined") return;
    const mql = window.matchMedia(`(min-width: ${TABLET_BREAKPOINT_PX}px)`);
    const update = () => setIsTablet(mql.matches);
    update();
    mql.addEventListener("change", update);
    return () => mql.removeEventListener("change", update);
  }, []);
  return isTablet;
}

export function FutureScreen() {
  const navigate = useNavigate();
  const build = useBuildStore((s) => s.build);
  const animalEmoji = useProfileStore((s) => s.animalEmoji);
  const t = useT();
  const isTablet = useIsTablet();

  const [screenState, setScreenState] = useState<ScreenState>("loading");
  const [treeData, setTreeData] = useState<TreeResponse | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [debouncedSelectedNodeId, setDebouncedSelectedNodeId] = useState<
    string | null
  >(null);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [latestResponse, setLatestResponse] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [educationFilters, setEducationFilters] = useState<
    Set<EducationFilter>
  >(() => new Set());
  const [statFilters, setStatFilters] = useState<Set<StatFilter>>(
    () => new Set(),
  );
  const [bossFilters, setBossFilters] = useState<Set<BossFilter>>(
    () => new Set(),
  );
  // Companion rail mode (desktop only). Mobile uses the existing
  // FutureChatSheet; the rail is gated behind isTablet below.
  const [companionMode, setCompanionMode] = useState<CompanionMode>("peeked");
  const [companionUnread, setCompanionUnread] = useState(false);
  const lastSeenResponseRef = useRef<string | null>(null);
  const [refitToken, setRefitToken] = useState(0);
  const [viewportWidth, setViewportWidth] = useState(() =>
    typeof window === "undefined" ? 1280 : window.innerWidth,
  );
  useEffect(() => {
    if (typeof window === "undefined") return;
    const update = () => setViewportWidth(window.innerWidth);
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);
  const [experienceRange, setExperienceRange] = useState<ExperienceRange>(
    EXPERIENCE_RANGE_FULL,
  );
  // T1.4 breadcrumb snapshot: titles + SOC codes from the *last
  // successful* selection lineage. Persists across filter toggles so
  // a hidden segment renders as a ghost rather than vanishing.
  // Cleared on root-click or when the lineage changes.
  const [breadcrumbSnapshot, setBreadcrumbSnapshot] = useState<
    { socCode: string; title: string }[]
  >([]);
  // T1.2 — pan/zoom signal for the tour chip navigate-flash sequence.
  // Bumping the timestamp re-triggers the pan even on the same nodeId.
  const [panTarget, setPanTarget] = useState<PanTarget | null>(null);
  // Per-node path rarity for the in-flight tour. Populated only with
  // "stretch" / "longshot" entries — direct/adjacent get nothing so
  // the in-tree pill never appears on common paths. Cleared when the
  // tour ends or is cancelled.
  const [tourFlashRarity, setTourFlashRarity] = useState<
    Map<string, "stretch" | "longshot">
  >(() => new Map());
  const flashTimeoutsRef = useRef<Map<string, number>>(new Map());
  const tourTimeoutsRef = useRef<number[]>([]);

  const handleToggleEducationFilter = useCallback((filter: EducationFilter) => {
    setEducationFilters((prev) => {
      const next = new Set(prev);
      if (next.has(filter)) next.delete(filter);
      else next.add(filter);
      return next;
    });
  }, []);

  const handleToggleStatFilter = useCallback((filter: StatFilter) => {
    setStatFilters((prev) => {
      const next = new Set(prev);
      if (next.has(filter)) next.delete(filter);
      else next.add(filter);
      return next;
    });
  }, []);

  const handleToggleBossFilter = useCallback((filter: BossFilter) => {
    setBossFilters((prev) => {
      const next = new Set(prev);
      if (next.has(filter)) next.delete(filter);
      else next.add(filter);
      return next;
    });
  }, []);

  const handleClearAllFilters = useCallback(() => {
    setEducationFilters(new Set());
    setStatFilters(new Set());
    setBossFilters(new Set());
    setExperienceRange(EXPERIENCE_RANGE_FULL);
  }, []);

  // Nav guard
  useEffect(() => {
    if (!build) navigate("/my-build", { replace: true });
  }, [build, navigate]);

  // Fetch tree at depth=2 (root → L1 → L2). User asked for "connections
  // from connections" — depth=2 gets us there without the L3 sprawl.
  useEffect(() => {
    if (!build) return;
    let cancelled = false;
    setScreenState("loading");
    async function fetchTree() {
      try {
        const result = await getTree(build!.build_id, 2);
        if (cancelled) return;
        if (result.tree.children.length === 0) {
          setTreeData(result);
          setScreenState("fallback");
        } else {
          setTreeData(result);
          setScreenState("tree");
        }
      } catch (err) {
        if (cancelled) return;
        setError(t("future.error.tree"));
        if (import.meta.env.DEV) console.error("FutureScreen tree error:", err);
        setScreenState("error");
      }
    }
    fetchTree();
    return () => {
      cancelled = true;
    };
    // Depend on build_id (stable string), not the build object — a
    // store refactor that returned a new object identity for the same
    // logical build would otherwise refetch the tree on every change.
  }, [build?.build_id, retryCount]);

  // Compose education + stat filters into a single filtered tree.
  // Both filters preserve the root, so the stat filter's "compare to
  // root" reference is the same regardless of education filter
  // ordering. AND across categories: a branch must satisfy education
  // filters AND stat filters together.
  const filteredTree = useMemo(() => {
    if (!treeData) return null;
    let t = filterTreeByEducation(treeData.tree, educationFilters);
    t = filterTreeByBoss(t, bossFilters);
    t = filterTreeByExperience(t, experienceRange);
    t = filterTreeByStats(t, statFilters);
    return t;
  }, [treeData, educationFilters, statFilters, bossFilters, experienceRange]);

  // "Available" filter sets — computed from the *unfiltered* tree so
  // toggling a filter doesn't make sibling chips disappear. Chips not
  // in the available set render only if currently active (so the
  // student can always deactivate). Hides whole rows when nothing is
  // available — saves vertical real estate on small trees.
  const availableEdu = useMemo(
    () => (treeData ? availableEducationFilters(treeData.tree) : new Set<EducationFilter>()),
    [treeData],
  );
  const availableBoss = useMemo(
    () => (treeData ? availableBossFilters(treeData.tree) : new Set<BossFilter>()),
    [treeData],
  );
  const availableStat = useMemo(
    () => (treeData ? availableStatFilters(treeData.tree) : new Set<StatFilter>()),
    [treeData],
  );

  // Map node id → soc + title for selection lookups + highlight candidates.
  const nodeRefs = useMemo<NodeRef[]>(
    () => (filteredTree ? walkTreeNodes(filteredTree) : []),
    [filteredTree],
  );
  const nodeRefsById = useMemo(() => {
    const m = new Map<string, NodeRef>();
    for (const ref of nodeRefs) m.set(ref.id, ref);
    return m;
  }, [nodeRefs]);

  // If the active filter hides the currently-selected node, drop the
  // selection so the chat re-anchors at the root and the card swaps
  // back to the root summary.
  useEffect(() => {
    if (selectedNodeId && !nodeRefsById.has(selectedNodeId)) {
      setSelectedNodeId(null);
    }
  }, [selectedNodeId, nodeRefsById]);

  // T1.4 — user-initiated select/clear. The snapshot wipe ONLY fires
  // here (or in handleBreadcrumbClick on root) so the cascade
  // selectedNodeId-drop-on-filter-hide can NOT erase the breadcrumb.
  // That cascade is what drives the ghost-state UX: keep the snapshot,
  // hide the node — student sees "you'd be here if you cleared the
  // filter."
  const handleSelectNode = useCallback((id: string | null) => {
    setSelectedNodeId(id);
    if (id == null) {
      setBreadcrumbSnapshot([]);
    } else {
      setSheetOpen(true);
    }
  }, []);

  // Refresh the breadcrumb snapshot only when selection lands on a
  // visible node. NEVER wipes — the wipe paths live in
  // handleSelectNode(null) and handleBreadcrumbClick(root).
  useEffect(() => {
    if (!treeData) return;
    if (selectedNodeId == null) return;
    const path = findPathToNodeId(treeData.tree, selectedNodeId);
    if (path == null) return;
    setBreadcrumbSnapshot(
      path.map((n) => ({ socCode: n.soc_code, title: n.title })),
    );
  }, [selectedNodeId, treeData]);

  // Debounce selection so rapid taps don't queue several openers.
  useEffect(() => {
    const tid = window.setTimeout(() => {
      setDebouncedSelectedNodeId(selectedNodeId);
    }, NODE_DEBOUNCE_MS);
    return () => window.clearTimeout(tid);
  }, [selectedNodeId]);

  const handleRetry = useCallback(() => {
    setError(null);
    setRetryCount((c) => c + 1);
  }, []);

  const rootSocCode = filteredTree?.soc_code ?? null;
  const selectedRef = useMemo(() => {
    if (!debouncedSelectedNodeId) return null;
    return nodeRefsById.get(debouncedSelectedNodeId) ?? null;
  }, [debouncedSelectedNodeId, nodeRefsById]);
  const targetSocCode = selectedRef?.socCode ?? rootSocCode;

  const chatScope: AskScope | null = useMemo(() => {
    if (!build || !targetSocCode) return null;
    return {
      kind: "branch" as const,
      build_ids: [build.build_id] as [string],
      target_id: targetSocCode,
    };
  }, [build, targetSocCode]);

  const chipText = useMemo(() => {
    if (!chatScope) return undefined;
    if (selectedRef == null && filteredTree?.title) {
      return `branch · ${filteredTree.title}`;
    }
    return `branch · ${selectedRef?.title ?? "root"}`;
  }, [chatScope, selectedRef, filteredTree]);

  const skeletonHint = useMemo(() => {
    if (!chatScope) return undefined;
    if (selectedRef == null) return t("chat.opener.skeleton.reading");
    return t("chat.opener.skeleton.thinking").replace(
      "{branch}",
      selectedRef.title,
    );
  }, [chatScope, selectedRef, t]);

  const openerPrompt = useMemo(() => {
    if (!chatScope) return undefined;
    return selectedRef == null
      ? t("future.opener.root")
      : t("future.opener.branch");
  }, [chatScope, selectedRef, t]);

  // Highlight driver candidates: every tree node, keyed by its React
  // Flow id so the BranchTreeFlow can do an O(1) Set lookup.
  const highlightCandidates = useMemo(
    () =>
      nodeRefs.map((r) => ({
        id: r.id,
        title: r.title,
      })),
    [nodeRefs],
  );

  const handleHighlight = useCallback((nodeId: string) => {
    const prev = flashTimeoutsRef.current.get(nodeId);
    if (prev != null) window.clearTimeout(prev);
    setHighlightedNodeIds((curr) => {
      if (curr.has(nodeId)) return curr;
      const next = new Set(curr);
      next.add(nodeId);
      return next;
    });
    const tid = window.setTimeout(() => {
      setHighlightedNodeIds((curr) => {
        if (!curr.has(nodeId)) return curr;
        const next = new Set(curr);
        next.delete(nodeId);
        return next;
      });
      flashTimeoutsRef.current.delete(nodeId);
    }, FLASH_TTL_MS);
    flashTimeoutsRef.current.set(nodeId, tid);
  }, []);

  useEffect(() => {
    const timeouts = flashTimeoutsRef.current;
    return () => {
      timeouts.forEach((tid) => window.clearTimeout(tid));
      timeouts.clear();
    };
  }, []);

  // T1.2 — orchestrate the navigate-flash-navigate sequence for a
  // tour chip click. For each ranked node: pan + zoom in, wait for the
  // pan to settle, flash the node, wait for the flash to clear, advance
  // to the next. Re-clicking a chip cancels the in-flight tour and
  // restarts.
  const handlePlayTour = useCallback(
    (nodeIds: string[]) => {
      tourTimeoutsRef.current.forEach((tid) => window.clearTimeout(tid));
      tourTimeoutsRef.current = [];
      if (nodeIds.length === 0) return;

      const PAN_MS = 550;
      const FLASH_DELAY_MS = 220;
      const FLASH_HOLD_MS = 780;
      const STEP_MS = PAN_MS + FLASH_DELAY_MS + FLASH_HOLD_MS;
      const SETTLE_MS = 280;

      // Compute per-node rarity for any flashed node whose cumulative
      // path is unusual. Only "stretch" / "longshot" entries are kept;
      // direct / adjacent paths produce no in-tree signal.
      const rarityMap = new Map<string, "stretch" | "longshot">();
      if (treeData) {
        for (const id of nodeIds) {
          const path = findPathToNodeId(treeData.tree, id);
          if (!path) continue;
          const rarity = computePathRarity(path);
          if (rarity && (rarity.tier === "stretch" || rarity.tier === "longshot")) {
            rarityMap.set(id, rarity.tier);
          }
        }
      }
      setTourFlashRarity(rarityMap);

      nodeIds.forEach((nodeId, idx) => {
        const baseDelay = idx * STEP_MS;
        const panTid = window.setTimeout(() => {
          setPanTarget({
            nodeId,
            ts: Date.now(),
            zoom: 1.4,
            duration: PAN_MS,
          });
        }, baseDelay);
        const flashTid = window.setTimeout(
          () => handleHighlight(nodeId),
          baseDelay + PAN_MS + FLASH_DELAY_MS,
        );
        tourTimeoutsRef.current.push(panTid, flashTid);
      });

      // Tail of the tour: pan back to the top result (the headline
      // answer to "highest pay" / etc.), select it so the
      // SelectedNodeCard + path-rarity badge update, and open the
      // companion rail so the answer is actually visible. The
      // visionary's "no auto-open on click" rule doesn't apply here
      // — the tour is an explicit "show me X" gesture and the rail
      // open is the natural follow-through.
      const totalMs = nodeIds.length * STEP_MS + SETTLE_MS;
      const headline = nodeIds[0]!;
      const finishTid = window.setTimeout(() => {
        setPanTarget({
          nodeId: headline,
          ts: Date.now(),
          zoom: 1.4,
          duration: PAN_MS,
        });
        setSelectedNodeId(headline);
        setCompanionMode((prev) => (prev === "peeked" ? "open" : prev));
      }, totalMs);
      // Clear the flash-rarity map a beat after the last flash window
      // closes so the in-tree pills exit cleanly with the glow.
      const clearRarityTid = window.setTimeout(
        () => setTourFlashRarity(new Map()),
        totalMs + FLASH_HOLD_MS,
      );
      tourTimeoutsRef.current.push(finishTid, clearRarityTid);
    },
    [handleHighlight, treeData],
  );

  useEffect(() => {
    const timers = tourTimeoutsRef.current;
    return () => {
      timers.forEach((tid) => window.clearTimeout(tid));
      timers.length = 0;
    };
  }, []);

  const handleAssistantResponse = useCallback(
    (text: string) => {
      setLatestResponse(text);
      // Mark the rail as having unread content if the student isn't
      // currently looking at it — the peek strip pulses an info dot
      // until they open the rail.
      if (companionMode === "peeked" && text !== lastSeenResponseRef.current) {
        setCompanionUnread(true);
      }
    },
    [companionMode],
  );

  // When the rail is opened (or focused), mark whatever response is
  // currently latest as "seen" and clear the unread badge.
  useEffect(() => {
    if (companionMode !== "peeked") {
      lastSeenResponseRef.current = latestResponse;
      setCompanionUnread(false);
    }
  }, [companionMode, latestResponse]);

  // Whenever the rail finishes animating to a new width, bump the
  // refit token so React Flow's FitOnTreeChange re-runs with the
  // new tree pane bounds.
  const handleRailWidthSettle = useCallback(() => {
    setRefitToken((n) => n + 1);
  }, []);

  // T1.4 — clicking a breadcrumb segment re-selects (or clears for
  // root). Ghost segments still call the setter but the filter will
  // gate the result; the breadcrumb stays as the visual hint.
  const handleBreadcrumbClick = useCallback(
    (segment: { isRoot: boolean; nodeId: string | null }) => {
      if (segment.isRoot) {
        setSelectedNodeId(null);
        setBreadcrumbSnapshot([]);
        return;
      }
      if (segment.nodeId != null) {
        setSelectedNodeId(segment.nodeId);
      }
    },
    [],
  );

  if (!build) return null;

  const emoji = animalEmoji ?? "🐻";
  const buildSummary = buildSummaryFromBuild(build);
  const direction = isTablet ? "LR" : "TB";

  const renderEmbeddedChat = () =>
    chatScope ? (
      <GemmaChat
        open={true}
        build={buildSummary}
        scope={chatScope}
        chipText={chipText}
        variant="embedded"
        skeletonHint={skeletonHint}
        openerPrompt={openerPrompt}
        onAssistantResponse={handleAssistantResponse}
      />
    ) : null;

  // Card target — selectedRef.node when a tree node is picked, root
  // TreeNode when defaulting. Whether a card renders at all depends
  // only on `treeData` being loaded; see render section below.
  const cardNode = selectedRef?.node ?? filteredTree ?? null;
  const cardPicked = selectedNodeId !== null;

  // Mobile collapsed-sheet peek line. Per "(b)" decision: replace the
  // Gemma response preview with a compact at-a-glance node summary
  // (title · wage · education) so the student sees the SOC card's
  // headline without expanding the sheet. Falls back to the chat
  // chipText if the card isn't ready yet.
  const peekSummary = cardNode
    ? [
        cardNode.title,
        cardNode.median_wage != null
          ? `$${Math.round(cardNode.median_wage).toLocaleString()}/yr`
          : null,
        cardNode.education ?? null,
      ]
        .filter((s): s is string => !!s)
        .join(" · ")
    : null;

  // T1.4 breadcrumb segments — derived per render from snapshot +
  // current filtered tree so ghost state tracks the active filters.
  const breadcrumbSegments = useMemo(
    () =>
      filteredTree
        ? buildBreadcrumbSegments(
            breadcrumbSnapshot,
            filteredTree,
            selectedNodeId,
          )
        : [],
    [breadcrumbSnapshot, filteredTree, selectedNodeId],
  );

  // Cumulative skill-overlap rarity along the selection path. Computed
  // against the *unfiltered* tree (treeData.tree) so the badge tracks
  // the real path even when filters hide intermediate L1 nodes. Null
  // when nothing is selected, the path can't be resolved, or all hops
  // have null relatedness.
  const pathRarity = useMemo(() => {
    if (!treeData || !selectedNodeId) return null;
    const path = findPathToNodeId(treeData.tree, selectedNodeId);
    if (!path) return null;
    return computePathRarity(path);
  }, [treeData, selectedNodeId]);

  // Empty-state: filters are active but the filtered tree has no L1
  // branches. Honest framing — the data shows zero transitions matching
  // the active filter, not "we don't know."
  const anyFilterActive =
    educationFilters.size > 0 ||
    statFilters.size > 0 ||
    bossFilters.size > 0 ||
    !isFullExperienceRange(experienceRange);
  const filterEmpty =
    !!filteredTree && filteredTree.children.length === 0 && anyFilterActive;
  // Human-readable join of every active filter label across both
  // categories. Order mirrors the chip rows so the joined string
  // reads naturally ("Master's required and Higher earnings").
  const filterEmptyLabel = useMemo(() => {
    const labels: string[] = [];
    if (educationFilters.has("bachelors")) labels.push(t("future.filter.bachelors"));
    if (educationFilters.has("masters")) labels.push(t("future.filter.masters"));
    if (educationFilters.has("doctoral")) labels.push(t("future.filter.doctoral"));
    if (bossFilters.has("boss_ai")) labels.push(t("future.survives.ai"));
    if (bossFilters.has("boss_market")) labels.push(t("future.survives.market"));
    if (bossFilters.has("boss_burnout")) labels.push(t("future.survives.burnout"));
    if (statFilters.has("earnings")) labels.push(t("future.stat.earnings"));
    if (statFilters.has("ai_resilient")) labels.push(t("future.stat.aiResilient"));
    if (statFilters.has("growth")) labels.push(t("future.stat.growth"));
    if (labels.length === 0) return "";
    if (labels.length === 1) return labels[0]!;
    if (labels.length === 2) {
      return t("future.filter.empty.join.or")
        .replace("{a}", labels[0]!)
        .replace("{b}", labels[1]!);
    }
    const first = labels.slice(0, -1).join(", ");
    return t("future.filter.empty.join.or")
      .replace("{a}", first)
      .replace("{b}", labels[labels.length - 1]!);
  }, [educationFilters, statFilters, bossFilters, t]);

  return (
    <div className="min-h-screen pt-14">
      <AnimatePresence mode="wait">
        {screenState === "loading" && (
          <motion.div
            key="loading"
            className="flex flex-col items-center justify-center min-h-[60vh] px-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <motion.span
              className="text-hero-desktop block mb-6"
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            >
              {emoji}
            </motion.span>
            <h2 className="font-display font-semibold text-heading text-text-primary mb-2 text-center">
              {t("tree.mapping")}
            </h2>
            <p className="font-body text-body text-text-secondary text-center">
              {t("tree.tracing")}
            </p>
          </motion.div>
        )}

        {screenState === "tree" && treeData && (
          <motion.div
            key="tree"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            {/* Desktop layout — tree pane fills the viewport and the
                CompanionRail (selected card + chat) lives in a
                right-edge slide-over. Tree pane reflows via paddingRight
                so React Flow's container resize triggers a re-fit. */}
            <div
              className="hidden tablet:block transition-[padding] duration-200 ease-out"
              style={{
                paddingRight: railWidth(companionMode, viewportWidth),
              }}
            >
              <PageContainer variant="bleed" className="px-5 pb-2">
                {/* Top utility row — tour chips + breadcrumb sit
                    side-by-side; both wrap to their own line on narrow
                    viewports. */}
                <div className="mb-2 flex flex-row flex-wrap items-center gap-x-5 gap-y-2">
                  {filteredTree && (
                    <TourChipRow
                      tree={filteredTree}
                      onPlayTour={handlePlayTour}
                    />
                  )}
                  <Breadcrumb
                    segments={breadcrumbSegments}
                    onSegmentClick={handleBreadcrumbClick}
                  />
                </div>
                {/* Filter row — all four chip groups + slider on one
                    line when there's room; flex-wrap drops cleanly to
                    a second line on narrower viewports. Trimmed chip
                    labels (e.g. "Bachelor's" not "Bachelor's only")
                    keep this dense at 1280-1440 widths. */}
                <div className="mb-2 flex flex-row flex-wrap items-center gap-x-5 gap-y-2">
                  <EducationFilterRow
                    active={educationFilters}
                    onToggle={handleToggleEducationFilter}
                    available={availableEdu}
                  />
                  <BossFilterRow
                    active={bossFilters}
                    onToggle={handleToggleBossFilter}
                    available={availableBoss}
                  />
                  <StatFilterRow
                    active={statFilters}
                    onToggle={handleToggleStatFilter}
                    available={availableStat}
                  />
                  <ExperienceRangeSlider
                    range={experienceRange}
                    onChange={setExperienceRange}
                  />
                </div>
                {/* Tree fills the rest of the viewport. The chrome
                    above this is ~140px (utility row + filter row +
                    page padding); 56px is the global header. */}
                <div
                  className="relative w-full bg-bp-surface border border-border-subtle rounded-xl shadow-md overflow-hidden"
                  style={{
                    height: "calc(100vh - 56px - 140px)",
                    minHeight: 480,
                  }}
                >
                  {filteredTree && (
                    <BranchTreeFlow
                      tree={filteredTree}
                      emoji={emoji}
                      direction={direction}
                      selectedNodeId={selectedNodeId}
                      onSelectNode={handleSelectNode}
                      highlightedNodeIds={highlightedNodeIds}
                      panTarget={panTarget}
                      refitToken={refitToken}
                      flashRarityById={tourFlashRarity}
                    />
                  )}
                  {filterEmpty && (
                    <FilterEmptyState
                      careerTitle={filteredTree?.title ?? ""}
                      filterLabel={filterEmptyLabel}
                      onClear={handleClearAllFilters}
                      t={t}
                    />
                  )}
                </div>
              </PageContainer>
            </div>

            {/* Right-edge companion rail — desktop only. Houses the
                Save & Share + back link in its header, the
                SelectedNodeCard + Ask Gemma chat in its body. */}
            <div className="hidden tablet:block">
              <CompanionRail
                mode={companionMode}
                onModeChange={setCompanionMode}
                peekTitle={selectedRef?.title ?? filteredTree?.title ?? ""}
                hasUnread={companionUnread}
                onWidthSettle={handleRailWidthSettle}
                headerSlot={
                  <div className="flex flex-row items-center justify-between gap-3">
                    <button
                      type="button"
                      className="font-body text-small text-text-muted hover:text-text-primary transition-colors duration-normal"
                      onClick={() => navigate("/my-build")}
                    >
                      {t("tree.backBuild")}
                    </button>
                    <button
                      type="button"
                      className="font-body text-small font-bold text-text-inverse bg-accent-thrive px-4 py-2 rounded-lg transition-all duration-normal hover:brightness-110"
                      onClick={() => navigate("/save")}
                      aria-label={t("tree.saveShareAria")}
                      data-testid="btn-save-share"
                    >
                      {t("tree.saveShare")}
                    </button>
                  </div>
                }
              >
                {cardNode && (
                  <div className="mb-3">
                    <SelectedNodeCard
                      node={cardNode}
                      build={build}
                      picked={cardPicked}
                      root={filteredTree ?? undefined}
                      pathRarity={pathRarity}
                    />
                  </div>
                )}
                {renderEmbeddedChat()}
              </CompanionRail>
            </div>

            {/* Mobile: tree fills the viewport, chat lives in a bottom sheet. */}
            <div className="tablet:hidden">
              {filteredTree && (
                <div className="px-4 pt-2">
                  <TourChipRow
                    tree={filteredTree}
                    onPlayTour={handlePlayTour}
                  />
                </div>
              )}
              <div className="px-4">
                <Breadcrumb
                  segments={breadcrumbSegments}
                  onSegmentClick={handleBreadcrumbClick}
                  maxCharsPerSegment={16}
                />
              </div>
              <div className="px-4 pt-2 flex flex-row flex-wrap items-center gap-x-5 gap-y-3">
                <EducationFilterRow
                  active={educationFilters}
                  onToggle={handleToggleEducationFilter}
                  available={availableEdu}
                />
                <BossFilterRow
                  active={bossFilters}
                  onToggle={handleToggleBossFilter}
                  available={availableBoss}
                />
              </div>
              <div className="px-4 pt-2 pb-2 flex flex-row flex-wrap items-center gap-x-4 gap-y-2">
                <StatFilterRow
                  active={statFilters}
                  onToggle={handleToggleStatFilter}
                  available={availableStat}
                />
                <ExperienceRangeSlider
                  range={experienceRange}
                  onChange={setExperienceRange}
                />
              </div>
              <div
                className="relative w-full bg-bp-surface"
                style={{ height: "calc(100vh - 56px - 56px)" }}
              >
                {filteredTree && (
                  <BranchTreeFlow
                    tree={filteredTree}
                    emoji={emoji}
                    direction={direction}
                    selectedNodeId={selectedNodeId}
                    onSelectNode={handleSelectNode}
                    highlightedNodeIds={highlightedNodeIds}
                    panTarget={panTarget}
                  />
                )}
                {filterEmpty && (
                  <FilterEmptyState
                    careerTitle={filteredTree?.title ?? ""}
                    filterLabel={filterEmptyLabel}
                    onClear={handleClearAllFilters}
                    t={t}
                  />
                )}
              </div>
              <FutureChatSheet
                open={sheetOpen}
                onOpenChange={setSheetOpen}
                preview={peekSummary}
                chipText={chipText}
              >
                {cardNode && (
                  <div className="mb-3">
                    <SelectedNodeCard
                      node={cardNode}
                      build={build}
                      picked={cardPicked}
                      root={filteredTree ?? undefined}
                      pathRarity={pathRarity}
                    />
                  </div>
                )}
                {renderEmbeddedChat()}
              </FutureChatSheet>
            </div>

            <BranchHighlightDriver
              nodes={highlightCandidates}
              latestResponse={latestResponse}
              onHighlight={handleHighlight}
            />
          </motion.div>
        )}

        {screenState === "fallback" && treeData && (
          <motion.div
            key="fallback"
            className="px-5 pt-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <PageContainer variant="bleed" className="px-5">
              <div className="flex flex-col items-center gap-4 mt-6 mb-6">
                <TreeFallback careerTitle={build.career.occupation_title} />
              </div>
              <div className="flex flex-col gap-3">{renderEmbeddedChat()}</div>
              <div className="flex flex-col items-center gap-3 mt-6 mb-12">
                <button
                  className="font-body text-cta font-bold text-text-inverse bg-accent-thrive px-8 py-3 rounded-lg transition-all duration-normal hover:brightness-110"
                  onClick={() => navigate("/save")}
                  data-testid="btn-save-share"
                >
                  {t("tree.saveShare")}
                </button>
              </div>
            </PageContainer>
          </motion.div>
        )}

        {screenState === "error" && (
          <motion.div
            key="error"
            className="flex flex-col items-center justify-center min-h-[60vh] px-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <p className="font-body text-body-lg text-text-secondary mb-6 text-center">
              {t("tree.loadError")}
            </p>
            {error && (
              <p className="font-body text-small text-text-muted mb-4 text-center">
                {error}
              </p>
            )}
            <div className="flex gap-4">
              <button
                className="font-body text-cta text-text-secondary border border-border px-6 py-2.5 rounded-lg transition-all duration-normal hover:text-text-primary hover:bg-bp-surface"
                onClick={handleRetry}
              >
                {t("tree.tryAgain")}
              </button>
              <button
                className="font-body text-cta font-bold text-text-inverse bg-accent-thrive px-6 py-2.5 rounded-lg transition-all duration-normal hover:brightness-110"
                onClick={() => navigate("/save")}
              >
                {t("tree.continue")}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
