import { BOSS_META } from "./bossData";
import { useProfileStore } from "@/store/profileStore";
import { localizeProfileName } from "@/i18n/profileName";
import { useT } from "@/i18n/useT";

interface VSOverlayProps {
  playerEmoji: string;
  playerName: string;
  bossEmoji: string;
  bossShortName: string;
  bossId: string;
  isActive: boolean;
  isDone: boolean;
}

export function VSOverlay({ playerEmoji, playerName, bossEmoji, bossShortName, bossId, isActive, isDone }: VSOverlayProps) {
  const t = useT();
  const locale = useProfileStore((s) => s.locale);
  const displayName = localizeProfileName(playerName, locale);
  const boss = BOSS_META[bossId as keyof typeof BOSS_META];
  const bossColor = boss?.color ?? "var(--color-accent-insight)";
  // Prefer the i18n key from BOSS_META over the prop. The prop is now
  // already-localized (BossBand resolves it) but we keep the meta lookup
  // as a safety net for any caller that still passes raw English.
  const localizedBossName = boss ? t(boss.shortNameKey) : bossShortName;

  return (
    <div
      className="absolute inset-0 z-20 flex items-center justify-center rounded-[20px] overflow-hidden transition-opacity"
      style={{
        background: "var(--color-bg-void)",
        opacity: isActive && !isDone ? 1 : 0,
        pointerEvents: isActive && !isDone ? "auto" : "none",
        transitionDuration: isDone ? "120ms" : "200ms",
      }}
    >
      <div className="flex items-center gap-6">
        {/* Player portrait */}
        <div className="flex flex-col items-center gap-2">
          <div
            className="rounded-[20px] flex items-center justify-center"
            style={{
              width: 96,
              height: 96,
              background: "linear-gradient(135deg, rgba(123,184,224,0.30) 0%, rgba(123,184,224,0.12) 100%)",
              border: "1px solid var(--color-border-default)",
              animation: isActive ? "vsSlamLeft 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) 0.2s both" : undefined,
            }}
          >
            <span style={{ fontSize: 52 }}>{playerEmoji}</span>
          </div>
          <bdi className="font-body font-semibold text-text-secondary" style={{ fontSize: 13 }}>
            {displayName}
          </bdi>
        </div>

        {/* VS + collision */}
        <div className="flex flex-col items-center">
          <span
            className="font-display font-bold text-text-primary"
            style={{
              fontSize: 32,
              animation: isActive ? "vsTextPop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) 0.3s both" : undefined,
            }}
          >
            {t("build.vsOverlay.vs")}
          </span>
          <span
            style={{
              fontSize: 32,
              animation: isActive ? "collisionSlam 0.5s ease-out 0.38s both" : undefined,
            }}
          >
            💥
          </span>

          {/* Dust puffs */}
          {isActive && (
            <div className="absolute" style={{ top: "50%", left: "50%" }}>
              {[0, 1, 2, 3, 4].map((i) => (
                <span
                  key={i}
                  className="absolute block rounded-full bg-white/10"
                  style={{
                    width: 8,
                    height: 8,
                    animation: `dustPuff${i} 0.6s ease-out ${0.45 + i * 0.02}s both`,
                  }}
                />
              ))}
            </div>
          )}

          {/* Energy burst */}
          {isActive && (
            <div
              className="absolute rounded-full"
              style={{
                width: 120,
                height: 120,
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -50%)",
                background: `radial-gradient(circle, ${bossColor} 0%, transparent 70%)`,
                animation: "vsBurst 0.6s ease-out 0.5s both",
              }}
            />
          )}
        </div>

        {/* Boss portrait */}
        <div className="flex flex-col items-center gap-2">
          <div
            className="rounded-[20px] flex items-center justify-center"
            style={{
              width: 96,
              height: 96,
              background: boss?.gradient,
              border: `1px solid ${bossColor}`,
              animation: isActive ? "vsSlamRight 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) 0.23s both" : undefined,
            }}
          >
            <span style={{ fontSize: 52 }}>{bossEmoji}</span>
          </div>
          <bdi className="font-body font-semibold text-text-secondary" style={{ fontSize: 13 }}>
            {localizedBossName}
          </bdi>
        </div>
      </div>

      <style>{`
        @keyframes vsSlamLeft {
          from { transform: translateX(-40px) scale(0.6); opacity: 0; }
          to { transform: translateX(0) scale(1); opacity: 1; }
        }
        @keyframes vsSlamRight {
          from { transform: translateX(40px) scale(0.6); opacity: 0; }
          to { transform: translateX(0) scale(1); opacity: 1; }
        }
        @keyframes vsTextPop {
          from { transform: scale(0.8); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }
        @keyframes collisionSlam {
          0% { transform: scale(0); opacity: 1; }
          30% { transform: scale(1.3); opacity: 1; }
          60% { transform: scale(1.0); opacity: 0.8; }
          100% { transform: scale(0.6); opacity: 0; }
        }
        @keyframes dustPuff0 { from { transform: translate(0,0) scale(1); opacity: 0.5; } to { transform: translate(-50px, -40px) scale(2); opacity: 0; } }
        @keyframes dustPuff1 { from { transform: translate(0,0) scale(1); opacity: 0.5; } to { transform: translate(48px, -45px) scale(2.2); opacity: 0; } }
        @keyframes dustPuff2 { from { transform: translate(0,0) scale(1); opacity: 0.5; } to { transform: translate(-45px, 50px) scale(1.8); opacity: 0; } }
        @keyframes dustPuff3 { from { transform: translate(0,0) scale(1); opacity: 0.5; } to { transform: translate(55px, 35px) scale(2); opacity: 0; } }
        @keyframes dustPuff4 { from { transform: translate(0,0) scale(1); opacity: 0.5; } to { transform: translate(-15px, -55px) scale(1.6); opacity: 0; } }
        @keyframes vsBurst {
          0% { transform: translate(-50%, -50%) scale(0); opacity: 0.6; }
          100% { transform: translate(-50%, -50%) scale(2.5); opacity: 0; }
        }
        @media (max-width: 767px) {
          .vs-overlay-portraits { width: 72px !important; height: 72px !important; }
          .vs-overlay-portraits span { font-size: 40px !important; }
        }
      `}</style>
    </div>
  );
}
