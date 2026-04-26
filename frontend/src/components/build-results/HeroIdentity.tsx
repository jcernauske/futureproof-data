import { EMOJI_BG } from "./bossData";
import { useT } from "@/i18n/useT";

interface HeroIdentityProps {
  profileName: string;
  animalEmoji: string;
  schoolName: string;
  programName: string;
}

export function HeroIdentity({ profileName, animalEmoji, schoolName, programName }: HeroIdentityProps) {
  const t = useT();
  const emojiBg = EMOJI_BG[animalEmoji] ?? "var(--color-accent-info)";

  return (
    <div
      className="hero-identity-wrap relative z-[2] flex items-center gap-6 max-w-[1280px] mx-auto px-8"
      style={{ marginTop: "-48px", animation: "simpleFade 0.3s ease-out 0.3s both" }}
    >
      {/* Avatar */}
      <div
        className="hero-avatar flex-shrink-0 rounded-full flex items-center justify-center border-2 border-border-default"
        style={{
          width: 120,
          height: 120,
          background: emojiBg,
          boxShadow: "0 0 30px 6px rgba(125,212,163,0.15), 0 0 60px 12px rgba(184,169,232,0.08)",
          animation: "emojiBounce 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) 0.5s both",
        }}
      >
        <span className="hero-emoji" style={{ fontSize: 80, lineHeight: 1, animation: "emojiBounce 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) 0.5s both" }}>
          {animalEmoji}
        </span>
      </div>

      {/* Text */}
      <div>
        <div
          className="hero-name font-display font-bold text-text-primary"
          style={{ fontSize: 40, animation: "fadeInUp 0.4s ease-out 0.65s both" }}
        >
          {profileName}
        </div>
        <div
          className="hero-subtitle font-body text-text-secondary"
          style={{ fontSize: 18, fontWeight: 600, animation: "simpleFade 0.3s ease-out 0.75s both" }}
        >
          {t("build.studying").replace("{program}", programName).replace("{school}", schoolName)}
        </div>
      </div>

      <style>{`
        @keyframes simpleFade {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes emojiBounce {
          from { transform: scale(0.8); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @media (max-width: 767px) {
          .hero-identity-wrap { margin-top: -32px !important; gap: 16px !important; padding: 0 16px !important; }
          .hero-identity-wrap .hero-avatar { width: 80px !important; height: 80px !important; }
          .hero-identity-wrap .hero-emoji { font-size: 40px !important; }
          .hero-identity-wrap .hero-name { font-size: 28px !important; }
          .hero-identity-wrap .hero-subtitle { font-size: 16px !important; }
        }
      `}</style>
    </div>
  );
}
