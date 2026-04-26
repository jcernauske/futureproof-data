import { motion } from "framer-motion";
import type { AppliedSkill } from "@/types/build";

interface SkillCardProps {
  skill: AppliedSkill;
  selected: boolean;
  onToggle: () => void;
}

const STAT_LABELS: Record<string, { label: string; signMultiplier?: number }> = {
  delta_ern: { label: "ERN" },
  delta_roi: { label: "ROI" },
  delta_res: { label: "RES" },
  delta_grw: { label: "GRW" },
  delta_hmn: { label: "HMN" },
  delta_burnout_raw: { label: "BRN", signMultiplier: -1 },
  delta_ceiling_raw: { label: "CEIL" },
};

function getStatDeltas(skill: AppliedSkill): Array<{ label: string; value: number }> {
  const deltas: Array<{ label: string; value: number }> = [];
  for (const [key, config] of Object.entries(STAT_LABELS)) {
    const raw = skill[key as keyof AppliedSkill] as number;
    const value = raw * (config.signMultiplier ?? 1);
    if (value !== 0) {
      deltas.push({ label: config.label, value });
    }
  }
  return deltas;
}

export function SkillCard({ skill, selected, onToggle }: SkillCardProps) {
  const deltas = getStatDeltas(skill);

  return (
    <motion.button
      id={`card-skill-${skill.id}`}
      role="checkbox"
      aria-checked={selected}
      aria-label={`${skill.title}: ${deltas.map((d) => `${d.label} ${d.value > 0 ? "+" : ""}${d.value}`).join(", ")}`}
      onClick={onToggle}
      className={`w-full flex items-center gap-4 p-4 rounded-lg border text-left cursor-pointer transition-all duration-normal ${
        selected
          ? "bg-bp-raised border-border-default shadow-glow-thrive/50"
          : "bg-bp-surface border-border-subtle hover:border-border-default"
      }`}
      whileTap={{ scale: 0.98 }}
    >
      <div className="flex-1 min-w-0">
        <div className="font-body font-bold text-body text-text-primary">
          {skill.title}
        </div>
        <div className="font-body text-small text-text-secondary mt-1">
          {skill.rationale}
        </div>
        <div className="flex flex-wrap gap-1.5 mt-2">
          {deltas.map((d) => (
            <span
              key={d.label}
              className={`inline-block px-2 py-0.5 rounded-full font-data text-data-sm ${
                d.value > 0
                  ? "bg-accent-thrive/15 text-accent-thrive"
                  : "bg-accent-alert/15 text-accent-alert"
              }`}
            >
              {d.label} {d.value > 0 ? "+" : ""}
              {d.value}
            </span>
          ))}
        </div>
      </div>
      <div
        className={`shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all duration-normal ${
          selected
            ? "bg-accent-thrive border-accent-thrive shadow-glow-thrive"
            : "bg-bp-deep border-border-subtle"
        }`}
      >
        {selected && (
          <svg
            width="12"
            height="12"
            viewBox="0 0 12 12"
            fill="none"
            className="text-text-inverse"
          >
            <path
              d="M2 6L5 9L10 3"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </div>
    </motion.button>
  );
}
