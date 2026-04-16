import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { branchTree } from "@/styles/motion";
import { TreeRootNode } from "./TreeRootNode";
import { TreeBranchLabel } from "./TreeBranchLabel";
import { TreeCareerNode } from "./TreeCareerNode";
import { TreeEndpointNode } from "./TreeEndpointNode";
import type { TreeNode } from "@/types/tree";
import type { TreeLayout, PositionedNode } from "@/data/treeLayout";

interface BranchTreeSVGProps {
  tree: TreeNode;
  layout: TreeLayout;
  emoji: string;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
}

// Generate deterministic stars
function generateStars(count: number, width: number, height: number) {
  const stars = [];
  for (let i = 0; i < count; i++) {
    // Pseudo-random using index
    const x = ((i * 137.508) % width);
    const y = ((i * 97.31 + 23) % height);
    const r = 0.5 + (i % 3) * 0.6;
    const delay = (i * 0.47) % 7;
    const dur = 3 + (i % 5);
    stars.push({ x, y, r, delay, dur });
  }
  return stars;
}

// Generate particles at branch junctions
function generateParticles(nodes: PositionedNode[]) {
  return nodes
    .filter((n) => n.level === 1 || n.level === 2)
    .map((n, i) => ({
      cx: n.x + 10 + (i % 3) * 12,
      cy: n.y + ((i % 2 === 0) ? -8 : 8),
      color: n.branchColor,
      delay: (i * 0.7) % 5,
    }));
}

export function BranchTreeSVG({ tree, layout, emoji, selectedNodeId, onSelectNode }: BranchTreeSVGProps) {
  const timeoutRefs = useRef<number[]>([]);

  // Illumination phase visibility
  const [phases, setPhases] = useState({
    rootGlow: false,
    rootNode: false,
    branchPaths: false,
    branchLabels: false,
    careerNodes: false,
    outgoingPaths: false,
    endpoints: false,
    particles: false,
  });

  const runIllumination = useCallback(() => {
    // Reset
    setPhases({
      rootGlow: false,
      rootNode: false,
      branchPaths: false,
      branchLabels: false,
      careerNodes: false,
      outgoingPaths: false,
      endpoints: false,
      particles: false,
    });

    const schedule = (ms: number, key: keyof typeof phases) => {
      const id = window.setTimeout(() => {
        setPhases((prev) => ({ ...prev, [key]: true }));
      }, ms);
      timeoutRefs.current.push(id);
    };

    schedule(branchTree.glowStart * 1000, "rootGlow");
    schedule(300, "rootNode");
    schedule(branchTree.linesStart * 1000 + 200, "branchPaths");
    schedule(branchTree.labelsStart * 1000 + 100, "branchLabels");
    schedule(branchTree.careerStart * 1000, "careerNodes");
    schedule(branchTree.careerStart * 1000, "outgoingPaths");
    schedule(branchTree.endpointsStart * 1000, "endpoints");
    schedule(branchTree.particlesStart * 1000, "particles");
  }, []);

  useEffect(() => {
    runIllumination();
    return () => {
      timeoutRefs.current.forEach(clearTimeout);
      timeoutRefs.current = [];
    };
  }, [runIllumination]);

  const rootNode = layout.nodes.find((n) => n.level === 0) ?? null;
  const careerNodes = layout.nodes.filter((n) => n.level === 1 || n.level === 2);
  const endpointNodes = layout.nodes.filter((n) => n.level === 3);
  const incomingPaths = layout.paths.filter((p) => p.group === "incoming");
  const outgoingPaths = layout.paths.filter((p) => p.group === "outgoing");
  const stars = useMemo(
    () => generateStars(40, layout.viewBoxWidth, layout.viewBoxHeight),
    [layout.viewBoxWidth, layout.viewBoxHeight],
  );
  const particles = useMemo(() => generateParticles(layout.nodes), [layout.nodes]);

  const hasSelection = selectedNodeId != null;

  function handleCanvasClick(e: React.MouseEvent<SVGSVGElement>) {
    if (e.target === e.currentTarget) {
      onSelectNode(null);
    }
  }

  function handleReplay() {
    timeoutRefs.current.forEach(clearTimeout);
    timeoutRefs.current = [];
    runIllumination();
  }

  return (
    <div className="relative w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${layout.viewBoxWidth} ${layout.viewBoxHeight}`}
        className="w-full min-w-[700px]"
        style={{ height: "auto", maxHeight: "70vh" }}
        role="img"
        aria-label={`Career branch tree showing ${layout.nodes.length} career paths from ${tree.title}`}
        data-testid="region-branch-tree"
        onClick={handleCanvasClick}
      >
        {/* Gradient defs */}
        <defs>
          {layout.gradientDefs.map((g) => (
            <linearGradient key={g.id} id={g.id} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={g.fromColor} />
              <stop offset="100%" stopColor={g.toColor} />
            </linearGradient>
          ))}
        </defs>

        {/* Stars background */}
        <g id="stars">
          {stars.map((s, i) => (
            <circle
              key={i}
              cx={s.x}
              cy={s.y}
              r={s.r}
              fill="#8A8595"
              opacity={0}
            >
              <animate
                attributeName="opacity"
                values="0;0.6;0"
                dur={`${s.dur}s`}
                begin={`${s.delay}s`}
                repeatCount="indefinite"
              />
            </circle>
          ))}
        </g>

        {/* Root glow */}
        <motion.g
          id="rootGlow"
          initial={{ opacity: 0 }}
          animate={{ opacity: phases.rootGlow ? 1 : 0 }}
          transition={{ duration: 0.8 }}
        >
          {rootNode && (
            <circle
              cx={rootNode.x}
              cy={rootNode.y}
              r={55}
              fill="#7DD4A3"
              opacity={0.08}
            />
          )}
        </motion.g>

        {/* Incoming branch paths (root → labels → career node LEFT edges) */}
        <motion.g
          id="branchPaths"
          initial={{ opacity: 0 }}
          animate={{ opacity: phases.branchPaths ? 1 : 0 }}
          transition={{ duration: 0.9 }}
        >
          {incomingPaths.map((p) => {
            const midX = (p.fromX + p.toX) / 2;
            return (
              <path
                key={p.id}
                d={`M ${p.fromX} ${p.fromY} C ${midX} ${p.fromY}, ${midX} ${p.toY}, ${p.toX} ${p.toY}`}
                fill="none"
                stroke={`url(#${p.gradientId})`}
                strokeWidth={p.strokeWidth}
                opacity={p.opacity}
              />
            );
          })}
        </motion.g>

        {/* Root node */}
        <motion.g
          initial={{ opacity: 0 }}
          animate={{ opacity: phases.rootNode ? 1 : 0 }}
          transition={{ duration: 0.6 }}
        >
          {rootNode && (
            <TreeRootNode
              node={rootNode}
              emoji={emoji}
              selected={selectedNodeId === rootNode.id}
              dimmed={hasSelection && selectedNodeId !== rootNode.id}
              onSelect={onSelectNode}
            />
          )}
        </motion.g>

        {/* Branch labels */}
        <motion.g
          id="branchLabels"
          initial={{ opacity: 0 }}
          animate={{ opacity: phases.branchLabels ? 1 : 0 }}
          transition={{ duration: 0.6 }}
        >
          {layout.branchLabels.map((bl) => (
            <TreeBranchLabel
              key={bl.id}
              id={bl.id}
              label={bl.label}
              x={bl.x}
              y={bl.y}
              color={bl.color}
              dimmed={hasSelection && selectedNodeId !== bl.id}
              onSelect={onSelectNode}
            />
          ))}
        </motion.g>

        {/* Career nodes (opaque fills — critical for paint order) */}
        <motion.g
          id="careerNodes"
          initial={{ opacity: 0 }}
          animate={{ opacity: phases.careerNodes ? 1 : 0 }}
          transition={{ duration: 0.7 }}
        >
          {careerNodes.map((node) => (
            <TreeCareerNode
              key={node.id}
              node={node}
              selected={selectedNodeId === node.id}
              dimmed={hasSelection && selectedNodeId !== node.id}
              onSelect={onSelectNode}
            />
          ))}
        </motion.g>

        {/* Outgoing paths (AFTER career nodes for correct paint order) */}
        <motion.g
          id="outgoingPaths"
          initial={{ opacity: 0 }}
          animate={{ opacity: phases.outgoingPaths ? 1 : 0 }}
          transition={{ duration: 0.7 }}
        >
          {outgoingPaths.map((p) => {
            const midX = (p.fromX + p.toX) / 2;
            return (
              <path
                key={p.id}
                d={`M ${p.fromX} ${p.fromY} C ${midX} ${p.fromY}, ${midX} ${p.toY}, ${p.toX} ${p.toY}`}
                fill="none"
                stroke={`url(#${p.gradientId})`}
                strokeWidth={p.strokeWidth}
                opacity={p.opacity}
              />
            );
          })}
        </motion.g>

        {/* Endpoint silhouettes */}
        <motion.g
          id="endpoints"
          initial={{ opacity: 0 }}
          animate={{ opacity: phases.endpoints ? 1 : 0 }}
          transition={{ duration: 0.9 }}
        >
          {endpointNodes.map((node) => (
            <TreeEndpointNode
              key={node.id}
              node={node}
              emoji={emoji}
              selected={selectedNodeId === node.id}
              dimmed={hasSelection && selectedNodeId !== node.id}
              onSelect={onSelectNode}
            />
          ))}
        </motion.g>

        {/* Particles */}
        <motion.g
          id="particles"
          initial={{ opacity: 0 }}
          animate={{ opacity: phases.particles ? 1 : 0 }}
          transition={{ duration: 1.2 }}
        >
          {particles.map((p, i) => (
            <circle key={i} cx={p.cx} cy={p.cy} r={1.2} fill={p.color} opacity={0.5}>
              <animateTransform
                attributeName="transform"
                type="translate"
                values={`0,0; ${15 + (i % 3) * 10},${(i % 2 === 0 ? -1 : 1) * 8}; 0,0`}
                dur={`${5 + (i % 4)}s`}
                begin={`${p.delay}s`}
                repeatCount="indefinite"
              />
            </circle>
          ))}
        </motion.g>
      </svg>

      {/* Replay button */}
      <button
        className="absolute bottom-4 left-4 font-body text-small text-text-muted px-3 py-1.5 rounded-full transition-all duration-normal hover:text-text-primary hover:bg-bp-surface"
        style={{ background: "rgba(35,37,69,0.8)" }}
        onClick={handleReplay}
        aria-label="Replay tree animation"
        data-testid="btn-replay-tree"
      >
        Replay
      </button>
    </div>
  );
}
