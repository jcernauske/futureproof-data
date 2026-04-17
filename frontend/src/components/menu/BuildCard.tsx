import { motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { MiniPentagon } from "@/components/menu/MiniPentagon";
import type { BuildSummary } from "@/api/menu";

interface BuildCardProps {
  build: BuildSummary;
  emoji: string;
  isMostRecent?: boolean;
  selectMode?: boolean;
  selected?: boolean;
  onTap: () => void;
}

function formatDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function BuildCard({
  build,
  emoji,
  isMostRecent = false,
  selectMode = false,
  selected = false,
  onTap,
}: BuildCardProps) {
  const labelColor = isMostRecent ? "text-accent-thrive" : "text-text-primary";
  const borderClass = selected
    ? "border-accent-thrive/40 shadow-glow-thrive"
    : "border-border-subtle";

  return (
    <motion.button
      type="button"
      data-testid={`card-build-${build.build_id}`}
      aria-label={`${build.school_name} — ${build.career_title}`}
      onClick={onTap}
      whileHover={{ x: 4 }}
      whileTap={{ scale: 0.98 }}
      transition={springs.snappy}
      className={`w-full flex items-center gap-4 px-5 py-4 rounded-lg border bg-bp-mid hover:bg-bp-surface transition-colors duration-normal text-left cursor-pointer ${borderClass}`}
    >
      {selectMode && (
        <span
          aria-hidden
          className={`shrink-0 w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all ${
            selected
              ? "border-accent-thrive bg-accent-thrive text-text-inverse"
              : "border-border-strong"
          }`}
        >
          {selected ? "✓" : ""}
        </span>
      )}

      <div
        aria-hidden
        className="shrink-0 w-11 h-11 rounded-full bg-bp-deep flex items-center justify-center text-2xl"
      >
        {emoji}
      </div>

      <div className="flex-1 min-w-0">
        <div className={`font-display font-semibold text-body ${labelColor} truncate`}>
          {build.school_name}
        </div>
        <div className="font-body text-small text-text-secondary truncate">
          {build.major_text} · {build.career_title}
        </div>
      </div>

      <div className="shrink-0 flex items-center gap-3">
        <MiniPentagon stats={build} />
        <div className="flex flex-col items-end gap-1">
          <div className="font-data text-micro text-text-muted">
            <span className="text-accent-thrive">{build.wins}</span>
            <span className="opacity-50">W·</span>
            <span className="text-accent-alert">{build.losses}</span>
            <span className="opacity-50">L·</span>
            <span className="text-accent-caution">{build.draws}</span>
            <span className="opacity-50">D</span>
          </div>
          <div className="font-data text-micro text-text-muted">
            {formatDate(build.created_at)}
          </div>
        </div>
      </div>
    </motion.button>
  );
}
