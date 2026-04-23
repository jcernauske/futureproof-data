import { VERDICT_TIERS } from "./bossData";
import { VictoryBar } from "./VictoryBar";

interface VerdictBadgeProps {
  rawWins: number;
  equippedWins: number;
  losses: number;
  draws: number;
}

function getVerdict(totalWins: number) {
  for (const tier of VERDICT_TIERS) {
    if (totalWins >= tier.min) return tier;
  }
  return VERDICT_TIERS[VERDICT_TIERS.length - 1]!;
}

function getNarrative(rawWins: number, equippedWins: number, draws: number, losses: number): string {
  const total = rawWins + equippedWins;
  if (total === 5 && equippedWins === 0) {
    return "You won every fight decisively. This path plays to your strengths.";
  }
  if (total === 5 && equippedWins > 0) {
    return `You won ${rawWins} fight${rawWins !== 1 ? "s" : ""} decisively, ${equippedWins} more ${equippedWins === 1 ? "victory" : "victories"} came from skills you chose to invest in — that’s not a shortcut, that’s a plan.`;
  }

  const standoffNote = draws > 0
    ? ` ${draws === 1 ? "One fight" : `${draws} fights`} ended in a standoff — close, but not a clear win.`
    : "";
  const defeatNote = losses > 0
    ? ` ${losses === 1 ? "One real challenge remains" : `${losses} real challenges remain`} — but now you can see ${losses === 1 ? "it" : "them"}.`
    : "";

  if (total > 0 && equippedWins === 0) {
    return `You won ${rawWins} fight${rawWins !== 1 ? "s" : ""} decisively.${standoffNote}${defeatNote}`;
  }
  if (rawWins > 0 && equippedWins > 0) {
    return `You won ${rawWins} fight${rawWins !== 1 ? "s" : ""} decisively, ${equippedWins} more ${equippedWins === 1 ? "victory" : "victories"} came from skills you chose to invest in.${standoffNote}${defeatNote}`;
  }
  if (rawWins === 0 && equippedWins > 0) {
    return `Every victory here came from skills you’d need to build. The path is absolutely doable — but it asks you to grow.${standoffNote}${defeatNote}`;
  }
  return `This path has real challenges — but now you can see them. That’s the first step to beating them.${standoffNote}`;
}

export function VerdictBadge({ rawWins, equippedWins, losses, draws }: VerdictBadgeProps) {
  const totalWins = rawWins + equippedWins;
  const verdict = getVerdict(totalWins);
  const narrative = getNarrative(rawWins, equippedWins, draws, losses);

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
        CAREER READINESS
      </div>

      {/* Verdict word */}
      <div
        className={`font-display font-bold ${verdict.accentClass}`}
        style={{ fontSize: 32 }}
      >
        {verdict.word}
      </div>
      <div className="font-body text-text-secondary" style={{ fontSize: 16, marginTop: 4 }}>
        {verdict.subtitle}
      </div>

      {/* Victory bar */}
      <VictoryBar rawWins={rawWins} equippedWins={equippedWins} draws={draws} losses={losses} />

      {/* Tally */}
      <div className="font-data text-text-secondary" style={{ fontSize: 13, marginTop: 16 }}>
        <span className="text-accent-thrive">{totalWins}</span> of 5 victories
        {equippedWins > 0 && (
          <span>
            {" "}({rawWins} decisive + <span className="text-accent-insight">{equippedWins}</span> skill-assisted)
          </span>
        )}
        {draws > 0 && (
          <span>
            {" · "}<span className="text-accent-caution">{draws}</span> standoff{draws !== 1 ? "s" : ""}
          </span>
        )}
        {losses > 0 && (
          <span>
            {" · "}<span className="text-accent-alert">{losses}</span> defeat{losses !== 1 ? "s" : ""}
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
