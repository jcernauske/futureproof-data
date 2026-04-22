import type { BossId } from "@/types/build";
import { BOSS_META } from "./bossData";

interface SealedOverlayProps {
  bossId: BossId;
  isVisible: boolean;
  isTriggered: boolean;
}

export function SealedOverlay({ bossId, isVisible, isTriggered }: SealedOverlayProps) {
  const boss = BOSS_META[bossId];

  return (
    <div
      className="absolute inset-0 z-10 flex items-center justify-center gap-6 rounded-[20px] overflow-hidden transition-opacity duration-200"
      style={{
        background: "var(--color-bg-mid)",
        opacity: isTriggered ? 0 : 1,
        pointerEvents: isTriggered ? "none" : "auto",
      }}
    >
      {/* Boss portrait */}
      <div
        className="rounded-[14px] flex items-center justify-center"
        style={{
          width: 64,
          height: 64,
          background: boss.gradient,
          border: `1px solid ${boss.color}40`,
          filter: "saturate(0.3) brightness(0.7)",
          animation: "sealedPulse 2s ease-in-out infinite",
        }}
      >
        <span style={{ fontSize: 36 }}>{boss.emoji}</span>
      </div>

      <div className="text-center">
        <div className="font-display font-semibold text-text-secondary" style={{ fontSize: 16 }}>
          {boss.shortName}
        </div>
        <div className="font-body text-text-muted" style={{ fontSize: 13, marginTop: 2 }}>
          {boss.subtitle}
        </div>
        <div
          className="font-data font-bold uppercase text-text-muted"
          style={{ fontSize: 11, letterSpacing: 1.5, marginTop: 8, opacity: 0.6 }}
        >
          AWAITING
        </div>
      </div>

      {/* Shimmer sweep */}
      {isVisible && !isTriggered && (
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ animation: "sealedShimmer 0.6s ease-out both" }}
        />
      )}

      <style>{`
        @keyframes sealedPulse {
          0%, 100% { opacity: 0.7; }
          50% { opacity: 0.85; }
        }
        @keyframes sealedShimmer {
          from { background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.05) 45%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.05) 55%, transparent 100%); background-size: 200% 100%; background-position: -100% 0; }
          to { background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.05) 45%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.05) 55%, transparent 100%); background-size: 200% 100%; background-position: 200% 0; }
        }
      `}</style>
    </div>
  );
}
