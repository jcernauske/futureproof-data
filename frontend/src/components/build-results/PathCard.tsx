import type { PentagonStats } from "@/types/build";
import { StatBarRow } from "./StatBarRow";

interface PathCardProps {
  programName: string;
  cipCode: string;
  careerName: string;
  socCode: string;
  stats: PentagonStats;
}

const STAT_KEYS = ["ern", "roi", "res", "grw", "hmn"] as const;

export function PathCard({ programName, cipCode, careerName, socCode, stats }: PathCardProps) {
  return (
    <div
      className="rounded-[20px] border border-border-subtle bg-bp-mid"
      style={{ padding: 24 }}
    >
      {/* Section label */}
      <div
        className="font-data font-bold uppercase text-accent-info"
        style={{ fontSize: 11, letterSpacing: 2, marginBottom: 16 }}
      >
        Your Path
      </div>

      {/* Program entry */}
      <div className="flex items-start gap-3 pb-4 border-b border-border-subtle">
        <span style={{ fontSize: 28, lineHeight: 1 }}>{"\u{1F393}"}</span>
        <div>
          <div className="font-display font-semibold text-text-primary" style={{ fontSize: 16 }}>
            {programName}
          </div>
          <div className="font-data text-text-muted" style={{ fontSize: 11, marginTop: 2 }}>
            CIP {cipCode}
          </div>
        </div>
      </div>

      {/* Career entry */}
      <div className="flex items-start gap-3 pt-4 pb-4 border-b border-border-subtle">
        <span style={{ fontSize: 28, lineHeight: 1 }}>{"\u{1F4BB}"}</span>
        <div>
          <div className="font-display font-semibold text-text-primary" style={{ fontSize: 16 }}>
            {careerName}
          </div>
          <div className="font-data text-text-muted" style={{ fontSize: 11, marginTop: 2 }}>
            SOC {socCode}
          </div>
        </div>
      </div>

      {/* Stat bars */}
      <div
        className="grid gap-x-4 gap-y-1.5 pt-4"
        style={{ gridTemplateColumns: "1fr 1fr" }}
      >
        {STAT_KEYS.map((key) => (
          <StatBarRow key={key} stat={key} value={stats[key]} />
        ))}
      </div>

      <style>{`
        @media (max-width: 480px) {
          .path-card-stats { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}
