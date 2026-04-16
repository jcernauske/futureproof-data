import { motion } from "framer-motion";
import type { PositionedNode } from "@/data/treeLayout";

interface TreeRootNodeProps {
  node: PositionedNode;
  emoji: string;
  selected: boolean;
  dimmed: boolean;
  onSelect: (id: string) => void;
}

export function TreeRootNode({ node, emoji, selected: _selected, dimmed, onSelect }: TreeRootNodeProps) {
  const salary = node.median_wage != null ? `$${node.median_wage.toLocaleString()}` : "";

  return (
    <g
      id="rootNode"
      opacity={dimmed ? 0.4 : 1}
      style={{ transition: "opacity 300ms ease" }}
    >
      {/* Outer glow */}
      <motion.circle
        cx={node.x}
        cy={node.y}
        r={55}
        fill="#7DD4A3"
        opacity={0}
        animate={{ opacity: [0.08, 0.22, 0.08] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
      />
      {/* Inner circle */}
      <circle
        cx={node.x}
        cy={node.y}
        r={28}
        fill="#232545"
        stroke="#7DD4A3"
        strokeWidth={2.5}
        style={{ cursor: "pointer" }}
        onClick={() => onSelect(node.id)}
        role="button"
        aria-label={`${node.title}: tap to view details`}
        data-testid="node-root"
      />
      {/* Emoji */}
      <text
        x={node.x}
        y={node.y + 2}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={22}
        style={{ pointerEvents: "none" }}
      >
        {emoji}
      </text>
      {/* Career title */}
      <text
        x={node.x}
        y={node.y + 44}
        textAnchor="middle"
        fontFamily="Fredoka, sans-serif"
        fontWeight={600}
        fontSize={12}
        fill="#F5F0E8"
      >
        {node.title}
      </text>
      {/* Salary */}
      {salary && (
        <text
          x={node.x}
          y={node.y + 58}
          textAnchor="middle"
          fontFamily="Space Mono, monospace"
          fontSize={10}
          fill="#8A8595"
        >
          {salary}
        </text>
      )}
    </g>
  );
}
