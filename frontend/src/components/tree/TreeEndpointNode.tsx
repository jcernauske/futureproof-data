import type { PositionedNode } from "@/data/treeLayout";

interface TreeEndpointNodeProps {
  node: PositionedNode;
  emoji: string;
  selected: boolean;
  dimmed: boolean;
  onSelect: (id: string) => void;
}

export function TreeEndpointNode({ node, emoji, selected, dimmed, onSelect }: TreeEndpointNodeProps) {
  const salary = node.median_wage != null ? `$${node.median_wage.toLocaleString()}` : "";

  return (
    <g
      opacity={dimmed ? 0.4 : 1}
      style={{ transition: "opacity 300ms ease", cursor: "pointer" }}
      onClick={() => onSelect(node.id)}
      role="button"
      aria-label={`${node.title}${salary ? ` (${salary})` : ""}: tap to view details`}
      data-testid={`node-endpoint-${node.soc_code}`}
    >
      <circle
        cx={node.x}
        cy={node.y}
        r={20}
        fill="#232545"
        stroke={selected ? node.branchColor : node.branchColor}
        strokeWidth={1.5}
        opacity={selected ? 1 : 0.6}
      />
      <text
        x={node.x}
        y={node.y + 2}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={16}
        opacity={0.6}
        style={{ pointerEvents: "none" }}
      >
        {emoji}
      </text>
      {/* Title */}
      <text
        x={node.x + 28}
        y={node.y - 4}
        fontFamily="Space Mono, monospace"
        fontSize={11}
        fill="#8A8595"
      >
        {node.title.length > 22 ? node.title.slice(0, 21) + "\u2026" : node.title}
      </text>
      {/* Salary */}
      {salary && (
        <text
          x={node.x + 28}
          y={node.y + 12}
          fontFamily="Space Mono, monospace"
          fontSize={9}
          fill={node.branchColor}
          opacity={0.7}
        >
          {salary}
        </text>
      )}
    </g>
  );
}
