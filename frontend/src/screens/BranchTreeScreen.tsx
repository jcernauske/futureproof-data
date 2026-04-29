import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import { getTree } from "@/api/tree";
import type { AskScope, BuildSummary } from "@/api/menu";
import { BranchTreeFlow } from "@/components/tree/BranchTreeFlow";
import { TreeNodeDetailPanel } from "@/components/tree/TreeNodeDetailPanel";
import { TreeFallback } from "@/components/tree/TreeFallback";
import { BranchHighlightDriver } from "@/components/tree/BranchHighlightDriver";
import { GemmaChat } from "@/components/menu/GemmaChat";
import { AskGemmaChipRow } from "@/components/AskGemmaChipRow";
import { PageContainer } from "@/components/ui/PageContainer";
import { useT } from "@/i18n/useT";
import { computeLayout } from "@/data/treeLayout";
import { treeToFlow } from "@/data/treeFlowLayout";
import { chipResponseExpand, springs } from "@/styles/motion";
import type { TreeResponse } from "@/types/tree";
import type { PositionedNode } from "@/data/treeLayout";
import type { CareerPickChip } from "@/types/careerPick";

type ScreenState = "loading" | "tree" | "fallback" | "error";

const NODE_DEBOUNCE_MS = 300;
const FLASH_TTL_MS = 700;

const ELEVATION_HINT_ID = "branch-tree-chip-elevation-hint";

/**
 * Build the BuildSummary the embedded GemmaChat needs to render its
 * header chip / contextLine. The /branch-tree screen has the full
 * Build, but GemmaChat takes a BuildSummary; this is a lightweight
 * adapter so we don't have to thread two types through.
 */
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
    hmn: build.career.stats.hmn ?? null,
    wins,
    losses,
    draws,
    profile_name: build.profile_name ?? "",
    animal_emoji: build.animal_emoji ?? null,
  };
}

export function BranchTreeScreen() {
  const navigate = useNavigate();
  const build = useBuildStore((s) => s.build);
  const animalEmoji = useProfileStore((s) => s.animalEmoji);
  const t = useT();

  const [screenState, setScreenState] = useState<ScreenState>("loading");
  const [treeData, setTreeData] = useState<TreeResponse | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [debouncedSelectedNodeId, setDebouncedSelectedNodeId] =
    useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [latestResponse, setLatestResponse] = useState<string | null>(null);
  const [activeChipId, setActiveChipId] = useState<string | null>(null);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [mapDrawerOpen, setMapDrawerOpen] = useState(false);
  const flashTimeoutsRef = useRef<Map<string, number>>(new Map());

  // Navigation guard
  useEffect(() => {
    if (!build) {
      navigate("/reveal", { replace: true });
    }
  }, [build, navigate]);

  // Fetch tree data
  useEffect(() => {
    if (!build) return;

    let cancelled = false;
    const minDisplayMs = 1500;
    const startTime = Date.now();

    async function fetchTree() {
      try {
        const result = await getTree(build!.build_id);
        const elapsed = Date.now() - startTime;
        const remaining = Math.max(0, minDisplayMs - elapsed);

        await new Promise((resolve) => setTimeout(resolve, remaining));

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
        setError("Failed to load tree");
        if (import.meta.env.DEV) console.error("Tree fetch error:", err);
        setScreenState("error");
      }
    }

    fetchTree();
    return () => {
      cancelled = true;
    };
  }, [build, retryCount]);

  // Compute layout for detail panel node lookup
  const layout = useMemo(() => {
    if (!treeData) return null;
    return computeLayout(treeData.tree);
  }, [treeData]);

  // Node map from flow layout for detail panel lookups + the candidate
  // list for BranchHighlightDriver (every node's id+title).
  const flowResult = useMemo(() => {
    if (!treeData) return null;
    return treeToFlow(treeData.tree, animalEmoji ?? "🐻");
  }, [treeData, animalEmoji]);

  const flowNodeMap = flowResult?.nodeMap ?? null;

  // Build the (id, title) candidate list for BranchHighlightDriver.
  // Walks the tree response in parallel with treeFlowLayout's id schema
  // so we can map every TreeNode's data title back to a flow node.
  // Why this isn't just nodeMap: when an L1 branch has children,
  // treeFlowLayout collapses the L1's actual career title into a
  // generic ``branchLabel`` ("Specialize" / "Go Management" / etc.)
  // and emits career nodes for the L2 children. The L1's real title
  // never lands in ``nodeMap``, so Gemma quoting an L1 title would
  // silently fail to highlight anything. Here we map the L1 data
  // title onto the branchLabel node id so it still flashes.
  const highlightCandidates = useMemo(() => {
    if (!treeData) return [];
    const out: { id: string; title: string }[] = [];
    const root = treeData.tree;

    // Root: id matches treeFlowLayout's `root-${tree.soc_code}`.
    if (root.title) {
      out.push({ id: `root-${root.soc_code}`, title: root.title });
    }

    root.children.forEach((branch, branchIdx) => {
      const branchLabelId = `branch-${branchIdx}`;
      // Map the L1's real career title (e.g. "Administrative Services
      // Managers") onto the branchLabel node so Gemma quoting it
      // flashes the right node, even though the rendered label is
      // a generic category.
      if (branch.title) {
        out.push({ id: branchLabelId, title: branch.title });
      }

      const isDirectBranch = branch.children.length === 0;
      if (isDirectBranch) {
        // Direct branch — career node mirrors the L1.
        out.push({
          id: `career-${branch.soc_code}-${branchIdx}`,
          title: branch.title,
        });
        return;
      }

      // Non-direct: L2 career nodes + L3 endpoint nodes.
      branch.children.forEach((career) => {
        if (career.title) {
          out.push({
            id: `career-${career.soc_code}-${branchIdx}`,
            title: career.title,
          });
        }
        career.children.forEach((ep, epIdx) => {
          if (ep.title) {
            out.push({
              id: `endpoint-${ep.soc_code}-${branchIdx}-${epIdx}`,
              title: ep.title,
            });
          }
        });
      });
    });

    return out;
  }, [treeData]);

  const selectedNode: PositionedNode | null = useMemo(() => {
    if (!selectedNodeId) return null;
    if (flowNodeMap?.has(selectedNodeId)) return flowNodeMap.get(selectedNodeId)!;
    if (!layout) return null;
    return layout.nodes.find((n) => n.id === selectedNodeId) ?? null;
  }, [flowNodeMap, layout, selectedNodeId]);

  const rootNode: PositionedNode | null = useMemo(() => {
    if (!layout) return null;
    return layout.nodes.find((n) => n.level === 0) ?? null;
  }, [layout]);

  const handleSelectNode = useCallback((id: string | null) => {
    setSelectedNodeId(id);
    setActiveChipId(null);
  }, []);

  // 300ms debounce on selectedNodeId → debouncedSelectedNodeId so
  // rapid clicks don't queue 4 openers (genai-architect Finding 4).
  useEffect(() => {
    const tid = window.setTimeout(() => {
      setDebouncedSelectedNodeId(selectedNodeId);
    }, NODE_DEBOUNCE_MS);
    return () => window.clearTimeout(tid);
  }, [selectedNodeId]);

  const handleRetry = useCallback(() => {
    setError(null);
    setScreenState("loading");
    setRetryCount((c) => c + 1);
  }, []);

  // Compute the SOC code that anchors the chat. When no node selected,
  // anchor at the root career; when a node is selected, use its
  // soc_code (CareerBranch.to_soc on the backend — frontend has the
  // resolved soc_code via PositionedNode).
  const rootSocCode = treeData?.tree.soc_code ?? null;
  const selectedSocCode = useMemo(() => {
    if (!debouncedSelectedNodeId) return null;
    if (!flowNodeMap) return null;
    return flowNodeMap.get(debouncedSelectedNodeId)?.soc_code ?? null;
  }, [debouncedSelectedNodeId, flowNodeMap]);
  const targetSocCode = selectedSocCode ?? rootSocCode;

  // Memoize chatScope on primitive deps so identity stays stable
  // across parent re-renders — fp-architect condition #2.
  const chatScope: AskScope | null = useMemo(() => {
    if (!build || !targetSocCode) return null;
    return {
      kind: "branch" as const,
      build_ids: [build.build_id] as [string],
      target_id: targetSocCode,
    };
  }, [build, targetSocCode]);

  // Pre-compute scope chip text for the chat header. "branch · root"
  // when anchored at the root career; "branch · {to_title}" when on a
  // specific branch. Voice-contract clean (never "level up", never
  // "WIN/LOSE", just identifiers).
  const chipText = useMemo(() => {
    if (!chatScope) return undefined;
    if (selectedSocCode == null && rootSocCode != null) {
      return `branch · ${treeData?.tree.title ?? "root"}`;
    }
    const node = debouncedSelectedNodeId
      ? flowNodeMap?.get(debouncedSelectedNodeId)
      : null;
    return `branch · ${node?.title ?? "root"}`;
  }, [
    chatScope,
    selectedSocCode,
    rootSocCode,
    treeData,
    debouncedSelectedNodeId,
    flowNodeMap,
  ]);

  // Skeleton hint — parameterized by current scope (root vs branch).
  const skeletonHint = useMemo(() => {
    if (!chatScope) return undefined;
    if (selectedSocCode == null) {
      return t("chat.opener.skeleton.reading");
    }
    const node = debouncedSelectedNodeId
      ? flowNodeMap?.get(debouncedSelectedNodeId)
      : null;
    return t("chat.opener.skeleton.thinking").replace(
      "{branch}",
      node?.title ?? "this branch",
    );
  }, [chatScope, selectedSocCode, debouncedSelectedNodeId, flowNodeMap, t]);

  // Opener prompt — what the embedded chat sends as the user message
  // to trigger the auto-fired opener. Backend short-circuits on
  // history==[] for branch scope and uses the tools-disabled opener
  // path (genai-architect Finding 3).
  const openerPrompt = useMemo(() => {
    if (!chatScope) return undefined;
    return selectedSocCode == null
      ? "Give me a 3-sentence orientation on this career path and what branches I could take."
      : "Give me a 3-sentence orientation on this branch — what it is, the strongest tradeoff, and what to ask next.";
  }, [chatScope, selectedSocCode]);

  // Starter chip set — root-anchor vs per-branch.
  const starterChips = useMemo<CareerPickChip[]>(() => {
    if (!chatScope) return [];
    if (selectedSocCode == null) {
      return [
        { id: "root-safest", label: t("tree.starterRoot.safest"), elevated: false, terminal_title: null },
        { id: "root-bestPay", label: t("tree.starterRoot.bestPay"), elevated: false, terminal_title: null },
        { id: "root-management", label: t("tree.starterRoot.management"), elevated: false, terminal_title: null },
        { id: "root-aiChange", label: t("tree.starterRoot.aiChange"), elevated: false, terminal_title: null },
      ];
    }
    return [
      { id: "branch-risky", label: t("tree.starterBranch.risky"), elevated: false, terminal_title: null },
      { id: "branch-learn", label: t("tree.starterBranch.learn"), elevated: false, terminal_title: null },
      { id: "branch-timeline", label: t("tree.starterBranch.timeline"), elevated: false, terminal_title: null },
      { id: "branch-wrong", label: t("tree.starterBranch.wrong"), elevated: false, terminal_title: null },
    ];
  }, [chatScope, selectedSocCode, t]);

  // BranchHighlightDriver-driven flash. The driver schedules onHighlight
  // calls with stagger; we apply each one here and clear after the
  // 600ms animation window plus a small buffer.
  // Invariant (fp-architect condition #5): handleHighlight is
  // presentational only — it MUST NOT update selectedNodeId.
  // Each highlight gets its own 700ms TTL so multiple simultaneous
  // matches (one Gemma response naming N branches) all flash
  // concurrently instead of overwriting each other. The CSS keyframe
  // is 600ms; 700ms gives the animation room to finish before the
  // class is removed.
  const handleHighlight = useCallback((nodeId: string) => {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.debug("[BranchTreeScreen] handleHighlight", nodeId);
    }
    // Cancel any pending removal for this same nodeId so a re-fire
    // restarts the TTL cleanly.
    const prevTimeout = flashTimeoutsRef.current.get(nodeId);
    if (prevTimeout != null) window.clearTimeout(prevTimeout);

    setHighlightedNodeIds((prev) => {
      if (prev.has(nodeId)) return prev;
      const next = new Set(prev);
      next.add(nodeId);
      return next;
    });

    const tid = window.setTimeout(() => {
      setHighlightedNodeIds((prev) => {
        if (!prev.has(nodeId)) return prev;
        const next = new Set(prev);
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

  const handleAssistantResponse = useCallback((text: string) => {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.debug("[BranchTreeScreen] handleAssistantResponse", {
        len: text.length,
        preview: text.slice(0, 120),
      });
    }
    setLatestResponse(text);
  }, []);

  const handleChipClick = useCallback(
    (chip: CareerPickChip) => {
      setActiveChipId(chip.id);
      // The embedded GemmaChat doesn't expose an imperative submit, so
      // we surface chip-dispatch by writing into the input draft. The
      // student presses send (one-tap pattern). Future: expose an
      // imperative API on GemmaChat for chip-driven dispatches.
      const inputEl = document.querySelector<HTMLInputElement>(
        '[data-testid="input-chat"]',
      );
      if (inputEl) {
        const setter = Object.getOwnPropertyDescriptor(
          window.HTMLInputElement.prototype,
          "value",
        )?.set;
        setter?.call(inputEl, chip.label);
        inputEl.dispatchEvent(new Event("input", { bubbles: true }));
        inputEl.focus();
      }
    },
    [],
  );

  if (!build) return null;

  const emoji = animalEmoji ?? "🐻";
  const buildSummary = buildSummaryFromBuild(build);

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

  const renderChipRow = () =>
    starterChips.length > 0 ? (
      <AskGemmaChipRow
        chips={starterChips}
        activeChipId={activeChipId}
        onChipClick={handleChipClick}
        elevationHintId={ELEVATION_HINT_ID}
        ariaLabel="Starter questions about this career path"
        className="py-3 px-5 flex-wrap"
      />
    ) : null;

  const renderDetailDrawer = () => {
    if (!selectedNode) return null;
    const branchTitle = selectedNode.title || rootNode?.title || "this path";
    const drawerLabel = (
      detailDrawerOpen ? t("tree.hideData") : t("tree.seeData")
    ).replace("{branch}", branchTitle);
    return (
      <div className="flex flex-col">
        <button
          type="button"
          data-testid="btn-tree-detail-toggle"
          aria-label={drawerLabel}
          aria-expanded={detailDrawerOpen}
          onClick={() => setDetailDrawerOpen((s) => !s)}
          className="h-11 px-5 flex items-center justify-between bg-bp-surface border border-border-subtle rounded-md font-body text-small text-text-secondary hover:text-text-primary hover:bg-bp-raised transition-colors duration-normal cursor-pointer"
        >
          <span className="truncate">{drawerLabel}</span>
          <motion.span
            aria-hidden
            animate={{ rotate: detailDrawerOpen ? 180 : 0 }}
            transition={springs.snappy}
            className="shrink-0 ml-2"
          >
            ▾
          </motion.span>
        </button>
        <AnimatePresence initial={false}>
          {detailDrawerOpen && (
            <motion.div
              key="detail-drawer-body"
              initial={chipResponseExpand.initial}
              animate={chipResponseExpand.animate}
              exit={chipResponseExpand.exit}
              transition={chipResponseExpand.transition}
              className="overflow-hidden bg-bp-deep border-t border-border-subtle"
            >
              <div className="max-h-[40vh] overflow-y-auto px-5 py-4">
                <TreeNodeDetailPanel
                  variant="sidebar"
                  node={selectedNode}
                  rootNode={rootNode}
                  onClose={() => setDetailDrawerOpen(false)}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  };

  return (
    <div className="min-h-screen pt-14">
      {/* Visually-hidden ARIA hint for AskGemmaChipRow elevation */}
      <span id={ELEVATION_HINT_ID} className="sr-only">
        Selecting an elevated chip surfaces extra detail about that path.
      </span>

      <AnimatePresence mode="wait">
        {/* Loading state — unchanged */}
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

        {/* Tree-as-map + chat-as-guide layout */}
        {screenState === "tree" && treeData && (
          <motion.div
            key="tree"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            {/* Mobile "Show map" drawer — collapsed by default */}
            <div className="px-5 pt-3 pb-2 tablet:hidden">
              <button
                type="button"
                data-testid="btn-show-map"
                aria-label={mapDrawerOpen ? t("tree.hideMap") : t("tree.showMap")}
                aria-expanded={mapDrawerOpen}
                onClick={() => setMapDrawerOpen((s) => !s)}
                className="w-full h-11 flex items-center justify-between px-4 bg-bp-surface border border-border-subtle rounded-lg font-body text-small text-text-secondary hover:text-text-primary hover:bg-bp-raised transition-colors duration-normal cursor-pointer"
              >
                <span>{mapDrawerOpen ? t("tree.hideMap") : t("tree.showMap")}</span>
                <motion.span
                  aria-hidden
                  animate={{ rotate: mapDrawerOpen ? 180 : 0 }}
                  transition={springs.snappy}
                >
                  ▾
                </motion.span>
              </button>
              <AnimatePresence initial={false}>
                {mapDrawerOpen && (
                  <motion.div
                    key="mobile-map-drawer"
                    initial={chipResponseExpand.initial}
                    animate={chipResponseExpand.animate}
                    exit={chipResponseExpand.exit}
                    transition={chipResponseExpand.transition}
                    className="overflow-hidden mt-2"
                    style={{ "--branch-flow-node-scale": "0.85" } as React.CSSProperties}
                  >
                    <BranchTreeFlow
                      tree={treeData.tree}
                      emoji={emoji}
                      selectedNodeId={selectedNodeId}
                      onSelectNode={handleSelectNode}
                      highlightedNodeIds={highlightedNodeIds}
                      compact
                      heightClassName="h-[60vh]"
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <PageContainer variant="grid">
              {/* Tree column — desktop only (mobile uses the drawer above).
                  --branch-flow-node-scale activates the 0.85 shrink on
                  flow nodes via reactflow-dark.css's [data-compact]
                  rule (§3 Resolved Decision #7). */}
              <aside
                className="hidden tablet:block tablet:col-span-5"
                aria-label="Career path map"
                style={{ "--branch-flow-node-scale": "0.85" } as React.CSSProperties}
              >
                <BranchTreeFlow
                  tree={treeData.tree}
                  emoji={emoji}
                  selectedNodeId={selectedNodeId}
                  onSelectNode={handleSelectNode}
                  highlightedNodeIds={highlightedNodeIds}
                  compact
                  heightClassName="h-[70vh]"
                />
              </aside>

              {/* Chat column — primary surface across all breakpoints */}
              <section className="col-span-12 tablet:col-span-7 flex flex-col gap-3">
                {renderEmbeddedChat()}
                {renderChipRow()}
                {renderDetailDrawer()}
              </section>

              {/* CTA strip — full width */}
              <div className="col-span-12 flex flex-col items-center gap-3 mt-4 mb-12">
                <button
                  className="font-body text-cta font-bold text-text-inverse bg-accent-thrive px-8 py-3 rounded-lg transition-all duration-normal hover:brightness-110"
                  onClick={() => navigate("/save")}
                  aria-label="Save and share your build"
                  data-testid="btn-save-share"
                >
                  {t("tree.saveShare")}
                </button>
                <div className="flex gap-4">
                  <button
                    className="font-body text-small text-text-muted hover:text-text-primary transition-colors duration-normal"
                    onClick={() => navigate("/gauntlet")}
                  >
                    {t("tree.backGauntlet")}
                  </button>
                  <button
                    className="font-body text-small text-text-muted hover:text-text-primary transition-colors duration-normal"
                    onClick={() => navigate("/reveal")}
                  >
                    {t("tree.backBuild")}
                  </button>
                </div>
              </div>
            </PageContainer>

            {/* Presentational side-channel: parses Gemma's response and
                emits onHighlight per matched branch title. Renders
                nothing. */}
            <BranchHighlightDriver
              nodes={highlightCandidates}
              latestResponse={latestResponse}
              onHighlight={handleHighlight}
            />
          </motion.div>
        )}

        {/* Fallback state — single-node career, chat anchored at root */}
        {screenState === "fallback" && treeData && (
          <motion.div
            key="fallback"
            className="px-5 pt-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <PageContainer variant="grid">
              <aside
                className="hidden tablet:block tablet:col-span-5"
                aria-label="Career path map"
              >
                <div className="w-[200px] h-[200px] mb-4">
                  <svg viewBox="0 0 200 200" className="w-full h-full">
                    <circle
                      cx={100}
                      cy={80}
                      r={28}
                      fill="var(--color-bg-mid)"
                      stroke="var(--color-accent-thrive)"
                      strokeWidth={2.5}
                    />
                    <text x={100} y={82} textAnchor="middle" dominantBaseline="central" fontSize={22}>
                      {emoji}
                    </text>
                    <text
                      x={100}
                      y={124}
                      textAnchor="middle"
                      fontFamily="Fredoka, sans-serif"
                      fontWeight={600}
                      fontSize={12}
                      fill="var(--color-text-primary)"
                    >
                      {build.career.occupation_title}
                    </text>
                  </svg>
                </div>
                <TreeFallback careerTitle={build.career.occupation_title} />
              </aside>

              <section className="col-span-12 tablet:col-span-7 flex flex-col gap-3">
                {renderEmbeddedChat()}
                {renderChipRow()}
              </section>

              <div className="col-span-12 flex flex-col items-center gap-3 mt-4 mb-12">
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

        {/* Error state — unchanged */}
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
              <p className="font-body text-small text-text-muted mb-4 text-center">{error}</p>
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
