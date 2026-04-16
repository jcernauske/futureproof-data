import type { PositionedNode } from "@/data/treeLayout";

interface TreeCareerNodeProps {
  node: PositionedNode;
  selected: boolean;
  dimmed: boolean;
  onSelect: (id: string) => void;
}

export function TreeCareerNode({ node, selected, dimmed, onSelect }: TreeCareerNodeProps) {
  const rectWidth = 116;
  const rectHeight = 28;

  return (
    <g
      opacity={dimmed ? 0.4 : 1}
      style={{ transition: "opacity 300ms ease", cursor: "pointer" }}
      onClick={() => onSelect(node.id)}
      role="button"
      aria-label={`${node.title}: tap to view details`}
      data-testid={`node-career-${node.soc_code}`}
    >
      <rect
        x={node.x}
        y={node.y - rectHeight / 2}
        width={rectWidth}
        height={rectHeight}
        rx={14}
        fill="#232545"
        stroke={selected ? node.branchColor : "rgba(255,255,255,0.1)"}
        strokeWidth={selected ? 2 : 1}
      />
      <text
        x={node.x + rectWidth / 2}
        y={node.y}
        textAnchor="middle"
        dominantBaseline="central"
        fontFamily="Nunito, sans-serif"
        fontWeight={600}
        fontSize={11}
        fill="#C4BFB0"
      >
        {node.title.length > 16 ? node.title.slice(0, 15) + "\u2026" : node.title}
      </text>
    </g>
  );
}
