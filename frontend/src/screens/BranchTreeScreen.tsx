import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import { getTree } from "@/api/tree";
import { BranchTreeFlow } from "@/components/tree/BranchTreeFlow";
import { TreeNodeDetailPanel } from "@/components/tree/TreeNodeDetailPanel";
import { TreeFallback } from "@/components/tree/TreeFallback";
import { PageContainer } from "@/components/ui/PageContainer";
import { useT } from "@/i18n/useT";
import { computeLayout } from "@/data/treeLayout";
import { treeToFlow } from "@/data/treeFlowLayout";
import type { TreeResponse } from "@/types/tree";
import type { PositionedNode } from "@/data/treeLayout";

type ScreenState = "loading" | "tree" | "fallback" | "error";

export function BranchTreeScreen() {
  const navigate = useNavigate();
  const build = useBuildStore((s) => s.build);
  const animalEmoji = useProfileStore((s) => s.animalEmoji);
  const t = useT();

  const [screenState, setScreenState] = useState<ScreenState>("loading");
  const [treeData, setTreeData] = useState<TreeResponse | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

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

  // Node map from flow layout for detail panel lookups
  const flowNodeMap = useMemo(() => {
    if (!treeData) return null;
    return treeToFlow(treeData.tree, animalEmoji ?? "\uD83D\uDC3B").nodeMap;
  }, [treeData, animalEmoji]);

  const selectedNode: PositionedNode | null = useMemo(() => {
    if (!selectedNodeId) return null;
    // Try flow node map first, fall back to layout
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
  }, []);

  const handleRetry = useCallback(() => {
    setError(null);
    setScreenState("loading");
    setRetryCount((c) => c + 1);
  }, []);

  if (!build) return null;

  const emoji = animalEmoji ?? "\uD83D\uDC3B";

  return (
    <div className="min-h-screen pt-14">
      <AnimatePresence mode="wait">
        {/* Loading state */}
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
              className="text-[60px] block mb-6"
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

        {/* Tree visualization */}
        {screenState === "tree" && treeData && (
          <motion.div
            key="tree"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <PageContainer variant="grid">
              {/* Tree — full width on mobile/tablet, 8 cols on desktop */}
              <div className="col-span-12 desktop:col-span-8 relative">
                <BranchTreeFlow
                  tree={treeData.tree}
                  emoji={emoji}
                  selectedNodeId={selectedNodeId}
                  onSelectNode={handleSelectNode}
                />

                {/* Modal-style detail panel — only on mobile/tablet */}
                <div className="desktop:hidden">
                  <TreeNodeDetailPanel
                    variant="modal"
                    node={selectedNode}
                    rootNode={rootNode}
                    onClose={() => setSelectedNodeId(null)}
                  />
                </div>
              </div>

              {/* Sidebar detail panel — only on desktop */}
              <div className="hidden desktop:block desktop:col-span-4">
                <TreeNodeDetailPanel
                  variant="sidebar"
                  node={selectedNode}
                  rootNode={rootNode}
                  onClose={() => setSelectedNodeId(null)}
                />
              </div>

              {/* CTA area — full width */}
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
          </motion.div>
        )}

        {/* Fallback state */}
        {screenState === "fallback" && treeData && (
          <motion.div
            key="fallback"
            className="flex flex-col items-center justify-center min-h-[60vh] px-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            {/* Show root node only via SVG */}
            <div className="w-[200px] h-[200px] mb-4">
              <svg viewBox="0 0 200 200" className="w-full h-full">
                <circle cx={100} cy={80} r={28} fill="#232545" stroke="#7DD4A3" strokeWidth={2.5} />
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
                  fill="#F5F0E8"
                >
                  {build.career.occupation_title}
                </text>
              </svg>
            </div>
            <TreeFallback careerTitle={build.career.occupation_title} />
            <div className="flex flex-col items-center gap-3 mt-8">
              <button
                className="font-body text-cta font-bold text-text-inverse bg-accent-thrive px-8 py-3 rounded-lg transition-all duration-normal hover:brightness-110"
                onClick={() => navigate("/save")}
                data-testid="btn-save-share"
              >
                {t("tree.saveShare")}
              </button>
            </div>
          </motion.div>
        )}

        {/* Error state */}
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
