import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import { getTree } from "@/api/tree";
import type { AskScope, BuildSummary } from "@/api/menu";
import { BranchHorizonMap } from "@/components/tree/BranchHorizonMap";
import { TreeFallback } from "@/components/tree/TreeFallback";
import { BranchHighlightDriver } from "@/components/tree/BranchHighlightDriver";
import { GemmaChat } from "@/components/menu/GemmaChat";
import { AskGemmaChipRow } from "@/components/AskGemmaChipRow";
import { PageContainer } from "@/components/ui/PageContainer";
import { useT } from "@/i18n/useT";
import { chipResponseExpand, springs } from "@/styles/motion";
import type { TreeResponse } from "@/types/tree";
import type { CareerBranch } from "@/types/build";
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

function treeResponseFromBuild(
  build: NonNullable<ReturnType<typeof useBuildStore.getState>["build"]>,
): TreeResponse {
  const career = build.career;
  return {
    tree: {
      soc_code: career.soc_code,
      title: career.occupation_title,
      level: 0,
      ern: career.stats.ern,
      roi: career.stats.roi,
      res: career.stats.res,
      grw: career.stats.grw,
      hmn: career.stats.hmn,
      median_wage: career.median_annual_wage,
      education: career.education_level_name,
      boss_ai: null,
      boss_loans: null,
      boss_market: null,
      boss_burnout: null,
      boss_ceiling: null,
      children: build.branches.map((branch) => ({
        soc_code: branch.to_soc,
        title: branch.to_title,
        level: 1,
        ern: null,
        roi: null,
        res: null,
        grw: null,
        hmn: null,
        median_wage: null,
        education: branch.related_education_level,
        boss_ai: null,
        boss_loans: null,
        boss_market: null,
        boss_burnout: null,
        boss_ceiling: null,
        children: [],
      })),
    },
    stats: {
      total_nodes: build.branches.length + 1,
      max_depth_reached: build.branches.length > 0 ? 1 : 0,
      mcp_calls: 0,
      dead_ends: 0,
      wall_clock_ms: 0,
    },
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
  const [mapDrawerOpen, setMapDrawerOpen] = useState(false);
  const flashTimeoutsRef = useRef<Map<string, number>>(new Map());

  // Navigation guard
  useEffect(() => {
    if (!build) {
      navigate("/my-build", { replace: true });
    }
  }, [build, navigate]);

  // Fetch tree data
  useEffect(() => {
    if (!build) return;

    if (build.branches.length > 0) {
      setTreeData(treeResponseFromBuild(build));
      setScreenState("tree");
      return;
    }

    let cancelled = false;
    async function fetchTree() {
      try {
        const result = await getTree(build!.build_id, 1);

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

  // Map keyed on `chip-${branch.to_soc}` for O(1) lookup of the
  // CareerBranch backing a selected chip. Replaces the dendrogram-era
  // `flowNodeMap` per Decision #14 of feature-tree-horizon-map.md.
  // Source is `build.branches` (D#16) — `treeData.tree.children` carries
  // the wrong shape (TreeNode, not CareerBranch).
  const chipBranchMap = useMemo(() => {
    const out = new Map<string, CareerBranch>();
    if (!build) return out;
    for (const branch of build.branches) {
      out.set(`chip-${branch.to_soc}`, branch);
    }
    return out;
  }, [build?.branches]);

  // Candidate list for BranchHighlightDriver. The horizon map is L1-only
  // (chip per CareerBranch), so the candidate set narrows from the old
  // root + L1-branchLabel + L2 + L3 schema to just `chip-${to_soc}`. See
  // Out-of-Scope: "L2/L3 title flashes" in the spec.
  const highlightCandidates = useMemo(() => {
    if (!build) return [];
    return build.branches.map((branch) => ({
      id: `chip-${branch.to_soc}`,
      title: branch.to_title,
    }));
  }, [build?.branches]);

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
    return chipBranchMap.get(debouncedSelectedNodeId)?.to_soc ?? null;
  }, [debouncedSelectedNodeId, chipBranchMap]);
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
    const branch = debouncedSelectedNodeId
      ? chipBranchMap.get(debouncedSelectedNodeId)
      : null;
    return `branch · ${branch?.to_title ?? "root"}`;
  }, [
    chatScope,
    selectedSocCode,
    rootSocCode,
    treeData,
    debouncedSelectedNodeId,
    chipBranchMap,
  ]);

  // Skeleton hint — parameterized by current scope (root vs branch).
  const skeletonHint = useMemo(() => {
    if (!chatScope) return undefined;
    if (selectedSocCode == null) {
      return t("chat.opener.skeleton.reading");
    }
    const branch = debouncedSelectedNodeId
      ? chipBranchMap.get(debouncedSelectedNodeId)
      : null;
    return t("chat.opener.skeleton.thinking").replace(
      "{branch}",
      branch?.to_title ?? "this branch",
    );
  }, [chatScope, selectedSocCode, debouncedSelectedNodeId, chipBranchMap, t]);

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

  return (
    <div className="min-h-screen pt-14">
      {/* Visually-hidden ARIA hint for AskGemmaChipRow elevation */}
      <span id={ELEVATION_HINT_ID} className="sr-only">
        {t("tree.elevationHint")}
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
                  >
                    <BranchHorizonMap
                      branches={build.branches}
                      buildEduLevel={build.career.education_level_name ?? null}
                      selectedNodeId={selectedNodeId}
                      onSelectNode={handleSelectNode}
                      highlightedNodeIds={highlightedNodeIds}
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <PageContainer variant="grid">
              {/* Tree column — desktop only (mobile uses the drawer above). */}
              <aside
                className="hidden tablet:block tablet:col-span-5"
                aria-label="Career path map"
              >
                <BranchHorizonMap
                  branches={build.branches}
                  buildEduLevel={build.career.education_level_name ?? null}
                  selectedNodeId={selectedNodeId}
                  onSelectNode={handleSelectNode}
                  highlightedNodeIds={highlightedNodeIds}
                />
              </aside>

              {/* Chat column — primary surface across all breakpoints */}
              <section className="col-span-12 tablet:col-span-7 flex flex-col gap-3">
                {renderEmbeddedChat()}
                {renderChipRow()}
              </section>

              {/* CTA strip — full width */}
              <div className="col-span-12 flex flex-col items-center gap-3 mt-4 mb-12">
                <button
                  className="font-body text-cta font-bold text-text-inverse bg-accent-thrive px-8 py-3 rounded-lg transition-all duration-normal hover:brightness-110"
                  onClick={() => navigate("/save")}
                  aria-label={t("tree.saveShareAria")}
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
                    onClick={() => navigate("/my-build")}
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
