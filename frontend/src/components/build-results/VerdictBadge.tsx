import { VERDICT_TIERS } from "./bossData";
import { VictoryBar } from "./VictoryBar";
import { useT } from "@/i18n/useT";

interface VerdictBadgeProps {
  rawWins: number;
  equippedWins: number;
  losses: number;
  draws: number;
  unknowns: number;
}

function getVerdict(totalWins: number) {
  for (const tier of VERDICT_TIERS) {
    if (totalWins >= tier.min) return tier;
  }
  return VERDICT_TIERS[VERDICT_TIERS.length - 1]!;
}

function getNarrative(
  rawWins: number,
  equippedWins: number,
  draws: number,
  losses: number,
  unknowns: number,
  t: (key: string, vars?: Record<string, string | number>) => string,
): string {
  const total = rawWins + equippedWins;

  const standoffNote =
    draws > 0
      ? draws === 1
        ? t("build.noteStandoffOne")
        : t("build.noteStandoffMany", { count: draws })
      : "";
  const defeatNote =
    losses > 0
      ? losses === 1
        ? t("build.noteDefeatOne")
        : t("build.noteDefeatMany", { count: losses })
      : "";
  const unknownNote =
    unknowns > 0
      ? unknowns === 1
        ? t("build.noteUnknownOne")
        : t("build.noteUnknownMany", { count: unknowns })
      : "";

  if (total === 5 && equippedWins === 0) {
    return t("build.narrativeAllDecisive");
  }
  if (total === 5 && equippedWins > 0) {
    return t("build.narrativeAllWithSkills")
      .replace("{raw}", String(rawWins))
      .replace("{s}", rawWins !== 1 ? "s" : "")
      .replace("{equipped}", String(equippedWins))
      .replace("{victories}", equippedWins === 1 ? "victory" : "victories");
  }

  if (total > 0 && equippedWins === 0) {
    return t("build.narrativePartialRaw")
      .replace("{raw}", String(rawWins))
      .replace("{s}", rawWins !== 1 ? "s" : "")
      + standoffNote + defeatNote + unknownNote;
  }
  if (rawWins > 0 && equippedWins > 0) {
    return t("build.narrativePartialMixed")
      .replace("{raw}", String(rawWins))
      .replace("{s}", rawWins !== 1 ? "s" : "")
      .replace("{equipped}", String(equippedWins))
      .replace("{victories}", equippedWins === 1 ? "victory" : "victories")
      + standoffNote + defeatNote + unknownNote;
  }
  if (rawWins === 0 && equippedWins > 0) {
    return t("build.narrativeAllEquipped") + standoffNote + defeatNote + unknownNote;
  }
  return t("build.narrativeNone") + standoffNote + unknownNote;
}

export function VerdictBadge({ rawWins, equippedWins, losses, draws, unknowns }: VerdictBadgeProps) {
  const t = useT();
  const totalWins = rawWins + equippedWins;
  const verdict = getVerdict(totalWins);
  const narrative = getNarrative(rawWins, equippedWins, draws, losses, unknowns, t);

  return (
    <div
      className="rounded-[20px] bg-bp-mid text-center"
      style={{
        padding: "32px",
        border: `1px solid ${verdict.border}`,
        boxShadow: verdict.glow,
        animation: "verdictScaleIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both",
      }}
    >
      {/* Label */}
      <div
        className="font-data font-bold uppercase text-text-muted"
        style={{ fontSize: 11, letterSpacing: 2, marginBottom: 12 }}
      >
        {t("build.careerReadiness")}
      </div>

      {/* Verdict word */}
      <div
        className={`font-display font-bold ${verdict.accentClass}`}
        style={{ fontSize: 32 }}
      >
        {t(verdict.wordKey)}
      </div>
      <div className="font-body text-text-secondary" style={{ fontSize: 16, marginTop: 4 }}>
        {t(verdict.subtitleKey)}
      </div>

      {/* Victory bar */}
      <VictoryBar rawWins={rawWins} equippedWins={equippedWins} draws={draws} losses={losses} unknowns={unknowns} />

      {/* Tally */}
      <div className="font-data text-text-secondary" style={{ fontSize: 13, marginTop: 16 }}>
        <span className="text-accent-thrive">{totalWins}</span> {t("build.of")} {5 - unknowns} {t("build.victories")}
        {equippedWins > 0 && (
          <span>
            {" "}({rawWins} {t("build.decisive").replace("{s}", "")} + <span className="text-accent-insight">{equippedWins}</span> {t("build.skillAssisted")})
          </span>
        )}
        {draws > 0 && (
          <span>
            {" · "}<span className="text-accent-caution">{draws}</span> {t("build.standoffs").replace("{s}", draws !== 1 ? "s" : "")}
          </span>
        )}
        {losses > 0 && (
          <span>
            {" · "}<span className="text-accent-alert">{losses}</span> {t("build.defeats").replace("{s}", losses !== 1 ? "s" : "")}
          </span>
        )}
        {unknowns > 0 && (
          <span>
            {" · "}<span className="text-text-muted">{unknowns}</span> {t("build.insufficientData")}
          </span>
        )}
      </div>

      {/* Narrative */}
      <p
        className="font-body text-text-secondary mx-auto"
        style={{ fontSize: 15, lineHeight: 1.6, maxWidth: 520, marginTop: 16 }}
      >
        {narrative}
      </p>

      <style>{`
        @keyframes verdictScaleIn {
          from { transform: scale(0.85); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }
        @media (max-width: 767px) {
          .verdict-badge-card { padding: 24px !important; }
          .verdict-badge-card .verdict-word { font-size: 24px !important; }
        }
      `}</style>
    </div>
  );
}
