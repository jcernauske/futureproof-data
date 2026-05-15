import { useT } from "@/i18n/useT";

interface VictoryBarProps {
  rawWins: number;
  equippedWins: number;
  draws: number;
  losses: number;
  unknowns: number;
}

export function VictoryBar({ rawWins, equippedWins, draws, losses, unknowns }: VictoryBarProps) {
  const t = useT();
  const cells: { type: string; className: string; style: React.CSSProperties }[] = [];

  for (let i = 0; i < rawWins; i++) {
    cells.push({
      type: "raw",
      className: "raw",
      style: { background: "var(--color-accent-thrive)", boxShadow: "0 0 8px rgba(125,212,163,0.25)" },
    });
  }
  for (let i = 0; i < equippedWins; i++) {
    cells.push({
      type: "equipped",
      className: "equipped",
      style: { background: "var(--color-accent-insight)", boxShadow: "0 0 8px rgba(184,169,232,0.25)" },
    });
  }
  for (let i = 0; i < draws; i++) {
    cells.push({
      type: "draw",
      className: "draw-cell",
      style: { background: "var(--color-accent-caution)", opacity: 0.4 },
    });
  }
  for (let i = 0; i < losses; i++) {
    cells.push({
      type: "loss",
      className: "loss",
      style: { background: "var(--color-accent-alert)", opacity: 0.5 },
    });
  }
  for (let i = 0; i < unknowns; i++) {
    cells.push({
      type: "unknown",
      className: "unknown",
      style: { background: "var(--color-text-muted)", opacity: 0.25 },
    });
  }

  // Pad to 5 if needed
  while (cells.length < 5) {
    cells.push({
      type: "empty",
      className: "empty",
      style: { background: "var(--color-bg-deep)", border: "1px solid var(--color-border-default)" },
    });
  }

  const legendItems: { label: string; color: string; border?: string }[] = [];
  if (rawWins > 0) legendItems.push({ label: t("build.legend.decisive"), color: "var(--color-accent-thrive)" });
  if (equippedWins > 0) legendItems.push({ label: t("build.legend.skillAssisted"), color: "var(--color-accent-insight)" });
  if (draws > 0) legendItems.push({ label: t("build.legend.standoff"), color: "var(--color-accent-caution)" });
  if (losses > 0) legendItems.push({ label: t("build.legend.defeat"), color: "var(--color-accent-alert)" });
  if (unknowns > 0) legendItems.push({ label: t("build.legend.insufficientData"), color: "var(--color-text-muted)" });

  return (
    <div>
      {/* Victory bar cells */}
      <div className="flex gap-1.5 mx-auto" style={{ maxWidth: 320, marginTop: 20 }}>
        {cells.map((cell, i) => (
          <div
            key={i}
            className={`flex-1 rounded-full ${cell.className}`}
            style={{ height: 12, ...cell.style }}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="flex justify-center gap-4 flex-wrap" style={{ marginTop: 10 }}>
        {legendItems.map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <div
              className="rounded-full"
              style={{
                width: 8,
                height: 8,
                background: item.color,
                border: item.border ? `1px solid ${item.border}` : undefined,
              }}
            />
            <span className="font-data text-text-muted" style={{ fontSize: 11 }}>
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
