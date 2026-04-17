import type { CompareBuild, CompareBossRow } from "@/api/menu";

interface RiskHeadlineCardProps {
  boss: CompareBossRow;
  builds: CompareBuild[];
}

const BOSS_EMOJI: Record<string, string> = {
  AI: "🤖",
  Loans: "💸",
  Market: "📉",
  Burnout: "🔥",
  Ceiling: "🏛️",
};

const RESULT_PILL: Record<string, string> = {
  WIN: "bg-accent-thrive/15 text-accent-thrive",
  LOSE: "bg-accent-alert/15 text-accent-alert",
  DRAW: "bg-accent-caution/15 text-accent-caution",
};

function isDivergent(values: string[]): boolean {
  const meaningful = values.filter((v) => v !== "—");
  if (meaningful.length < 2) return false;
  return new Set(meaningful).size > 1;
}

export function RiskHeadlineCard({ boss, builds }: RiskHeadlineCardProps) {
  const divergent = isDivergent(boss.values);
  const borderClass = divergent
    ? "border-l-[3px] border-l-accent-caution"
    : "border-l-[3px] border-l-transparent";
  const titleColor = divergent ? "text-text-primary" : "text-text-secondary";

  return (
    <article
      data-testid={`card-risk-${boss.label.toLowerCase()}`}
      aria-label={`${boss.label}: ${divergent ? "builds disagree" : "builds agree"}`}
      className={`bg-bp-mid border border-border-subtle rounded-xl p-5 flex flex-col gap-3 ${borderClass}`}
    >
      <header className="flex items-center gap-3">
        <span aria-hidden className="text-xl">
          {BOSS_EMOJI[boss.label] ?? "•"}
        </span>
        <h3 className={`font-display font-semibold text-subheading ${titleColor}`}>
          {boss.label}
        </h3>
      </header>

      <div className="flex flex-col gap-2">
        {builds.map((build, idx) => {
          const result = boss.values[idx] ?? "—";
          const pill = RESULT_PILL[result] ?? "bg-bp-deep text-text-muted";
          return (
            <div
              key={build.build_id}
              className="flex items-center justify-between gap-3"
            >
              <span className="font-body text-small text-text-secondary truncate">
                {build.label}
              </span>
              <span
                className={`font-body text-micro font-bold px-3 py-1 rounded-full uppercase tracking-wider shrink-0 ${pill}`}
              >
                {result}
              </span>
            </div>
          );
        })}
      </div>

      {divergent && (
        <p className="font-body text-small italic text-accent-caution mt-1">
          Your builds disagree here.
        </p>
      )}
    </article>
  );
}
