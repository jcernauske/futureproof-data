interface TreeBranchLabelProps {
  id: string;
  label: string;
  x: number;
  y: number;
  color: string;
  dimmed: boolean;
  onSelect: (id: string) => void;
}

export function TreeBranchLabel({ id, label, x, y, color, dimmed, onSelect }: TreeBranchLabelProps) {
  const pillWidth = Math.max(label.length * 8 + 24, 80);
  const pillHeight = 36;

  return (
    <g
      opacity={dimmed ? 0.4 : 1}
      style={{ transition: "opacity 300ms ease", cursor: "pointer" }}
      onClick={() => onSelect(id)}
      role="button"
      aria-label={`${label} pathway`}
      data-testid={`node-branch-${label.toLowerCase().replace(/\s+/g, "-")}`}
    >
      <rect
        x={x - pillWidth / 2}
        y={y - pillHeight / 2}
        width={pillWidth}
        height={pillHeight}
        rx={18}
        fill="#232545"
        stroke={color}
        strokeWidth={1.5}
      />
      <text
        x={x}
        y={y}
        textAnchor="middle"
        dominantBaseline="central"
        fontFamily="Nunito, sans-serif"
        fontWeight={700}
        fontSize={13}
        fill="#F5F0E8"
      >
        {label}
      </text>
    </g>
  );
}
