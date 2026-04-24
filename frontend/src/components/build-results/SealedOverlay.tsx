import type { BossId } from "@/types/build";
import { BOSS_META } from "./bossData";

interface SealedOverlayProps {
  bossId: BossId;
  isVisible: boolean;
  isTriggered: boolean;
  onReveal?: () => void;
}

/**
 * Sealed boss fight overlay — the "unopened booster pack" state.
 *
 * Design intent: contained menace. The boss is in there, pressing against
 * the seal. Desaturated color, slow breathing glow, wax-seal center motif.
 * The shimmer sweep on scroll-into-view says "something is here."
 * Tapping breaks the seal and triggers the VS overlay.
 */
export function SealedOverlay({ bossId, isVisible, isTriggered, onReveal }: SealedOverlayProps) {
  const boss = BOSS_META[bossId];

  return (
    <div
      className="absolute inset-0 z-10 flex flex-col items-center justify-center rounded-[20px] overflow-hidden cursor-pointer select-none"
      style={{
        background: `
          radial-gradient(ellipse 60% 50% at 50% 50%, ${boss.color}08 0%, transparent 70%),
          linear-gradient(180deg, var(--color-bg-mid) 0%, #191b2e 100%)
        `,
        opacity: isTriggered ? 0 : 1,
        pointerEvents: isTriggered ? "none" : "auto",
        transition: "opacity 0.35s ease-out",
      }}
      onClick={onReveal}
      role="button"
      tabIndex={isTriggered ? -1 : 0}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onReveal?.(); }}
      aria-label={`Reveal ${boss.shortName} fight`}
    >
      {/* Inner border glow — contained energy pressing against the edges */}
      <div
        className="absolute inset-0 rounded-[20px] pointer-events-none"
        style={{
          boxShadow: `inset 0 0 40px ${boss.color}0a, inset 0 0 80px ${boss.color}06`,
          border: `1px solid ${boss.color}15`,
          animation: "sealedBorderPulse 3s ease-in-out infinite",
        }}
      />

      {/* Surface texture — fine diagonal lines for materiality */}
      <div
        className="absolute inset-0 pointer-events-none rounded-[20px]"
        style={{
          opacity: 0.03,
          backgroundImage: `repeating-linear-gradient(
            135deg,
            transparent,
            transparent 4px,
            rgba(255,255,255,0.5) 4px,
            rgba(255,255,255,0.5) 5px
          )`,
        }}
      />

      {/* Ambient glow behind the seal — the boss's presence bleeding through */}
      <div
        className="absolute pointer-events-none"
        style={{
          width: 200,
          height: 200,
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -55%)",
          background: `radial-gradient(circle, ${boss.color}12 0%, ${boss.color}06 40%, transparent 70%)`,
          animation: "sealedGlowPulse 3s ease-in-out infinite",
          filter: "blur(20px)",
        }}
      />

      {/* Seal frame — hexagonal-feel rounded container */}
      <div
        className="relative flex items-center justify-center"
        style={{
          width: 80,
          height: 80,
          borderRadius: 20,
          background: `linear-gradient(145deg, ${boss.color}18 0%, ${boss.color}08 100%)`,
          border: `1.5px solid ${boss.color}25`,
          boxShadow: `
            0 0 24px ${boss.color}15,
            0 4px 16px rgba(0,0,0,0.3),
            inset 0 1px 0 ${boss.color}15
          `,
          animation: "sealedFrameBreathe 3s ease-in-out infinite",
        }}
      >
        {/* Emoji — desaturated, slightly dimmed, contained */}
        <span
          style={{
            fontSize: 40,
            filter: "saturate(0.25) brightness(0.75)",
            animation: "sealedEmojiBreathe 3s ease-in-out infinite",
          }}
        >
          {boss.emoji}
        </span>

        {/* Corner accents — subtle sealed-card framing */}
        <div className="absolute pointer-events-none" style={{
          inset: -1,
          borderRadius: 20,
        }}>
          {/* Top-left */}
          <div className="absolute" style={{ top: 6, left: 6, width: 12, height: 12, borderTop: `1.5px solid ${boss.color}30`, borderLeft: `1.5px solid ${boss.color}30`, borderRadius: "4px 0 0 0" }} />
          {/* Top-right */}
          <div className="absolute" style={{ top: 6, right: 6, width: 12, height: 12, borderTop: `1.5px solid ${boss.color}30`, borderRight: `1.5px solid ${boss.color}30`, borderRadius: "0 4px 0 0" }} />
          {/* Bottom-left */}
          <div className="absolute" style={{ bottom: 6, left: 6, width: 12, height: 12, borderBottom: `1.5px solid ${boss.color}30`, borderLeft: `1.5px solid ${boss.color}30`, borderRadius: "0 0 0 4px" }} />
          {/* Bottom-right */}
          <div className="absolute" style={{ bottom: 6, right: 6, width: 12, height: 12, borderBottom: `1.5px solid ${boss.color}30`, borderRight: `1.5px solid ${boss.color}30`, borderRadius: "0 0 4px 0" }} />
        </div>
      </div>

      {/* Boss name + subtitle */}
      <div className="text-center mt-4 relative z-[1]">
        <div
          className="font-display font-semibold"
          style={{
            fontSize: 18,
            color: "var(--color-text-secondary)",
            letterSpacing: 0.5,
          }}
        >
          {boss.shortName}
        </div>
        <div
          className="font-body text-text-muted mt-0.5"
          style={{ fontSize: 13 }}
        >
          {boss.subtitle}
        </div>
      </div>

      {/* "Scroll to reveal" CTA with animated chevron */}
      <div
        className="flex flex-col items-center mt-5 relative z-[1]"
        style={{ animation: "sealedCtaPulse 2.5s ease-in-out infinite" }}
      >
        <div
          className="font-data font-bold uppercase"
          style={{
            fontSize: 10,
            letterSpacing: 2.5,
            color: "var(--color-text-muted)",
            opacity: 0.7,
          }}
        >
          TAP TO REVEAL
        </div>
        {/* Chevron pair — staggered bounce */}
        <div className="flex flex-col items-center -mt-0.5" style={{ gap: 0 }}>
          <svg
            width="16" height="8" viewBox="0 0 16 8"
            style={{ opacity: 0.3, animation: "sealedChevron 2s ease-in-out infinite" }}
          >
            <path d="M1 1L8 6L15 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" fill="none"
              style={{ color: "var(--color-text-muted)" }}
            />
          </svg>
          <svg
            width="16" height="8" viewBox="0 0 16 8"
            style={{ opacity: 0.2, animation: "sealedChevron 2s ease-in-out infinite 0.15s", marginTop: -3 }}
          >
            <path d="M1 1L8 6L15 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" fill="none"
              style={{ color: "var(--color-text-muted)" }}
            />
          </svg>
        </div>
      </div>

      {/* Shimmer sweep — holographic card catch-light on scroll into view */}
      {isVisible && !isTriggered && (
        <div
          className="absolute inset-0 pointer-events-none rounded-[20px]"
          style={{
            background: `linear-gradient(
              105deg,
              transparent 0%,
              transparent 35%,
              ${boss.color}08 42%,
              rgba(255,255,255,0.06) 48%,
              rgba(255,255,255,0.09) 50%,
              rgba(255,255,255,0.06) 52%,
              ${boss.color}08 58%,
              transparent 65%,
              transparent 100%
            )`,
            backgroundSize: "300% 100%",
            animation: "sealedShimmerSweep 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94) 0.15s both",
          }}
        />
      )}

      <style>{`
        @keyframes sealedBorderPulse {
          0%, 100% { opacity: 0.7; }
          50% { opacity: 1; }
        }

        @keyframes sealedGlowPulse {
          0%, 100% { opacity: 0.6; transform: translate(-50%, -55%) scale(0.95); }
          50% { opacity: 1; transform: translate(-50%, -55%) scale(1.05); }
        }

        @keyframes sealedFrameBreathe {
          0%, 100% {
            transform: scale(1);
            box-shadow:
              0 0 24px var(--sealed-boss-color-15, rgba(255,255,255,0.08)),
              0 4px 16px rgba(0,0,0,0.3),
              inset 0 1px 0 var(--sealed-boss-color-15, rgba(255,255,255,0.06));
          }
          50% {
            transform: scale(1.02);
            box-shadow:
              0 0 32px var(--sealed-boss-color-20, rgba(255,255,255,0.12)),
              0 4px 20px rgba(0,0,0,0.35),
              inset 0 1px 0 var(--sealed-boss-color-20, rgba(255,255,255,0.08));
          }
        }

        @keyframes sealedEmojiBreathe {
          0%, 100% { filter: saturate(0.25) brightness(0.70); }
          50% { filter: saturate(0.35) brightness(0.80); }
        }

        @keyframes sealedCtaPulse {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 1; }
        }

        @keyframes sealedChevron {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(2px); }
        }

        @keyframes sealedShimmerSweep {
          0% { background-position: 100% 0; }
          100% { background-position: -50% 0; }
        }
      `}</style>
    </div>
  );
}
