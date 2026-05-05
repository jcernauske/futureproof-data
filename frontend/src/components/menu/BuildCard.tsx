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
  onDelete?: (buildId: string) => void;
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
  onDelete,
}: BuildCardProps) {
  const labelColor = isMostRecent ? "text-accent-thrive" : "text-text-primary";
  const borderClass = selected
    ? "border-accent-thrive/40 shadow-glow-thrive"
    : "border-border-subtle";

  return (
    <motion.div
      role="button"
      tabIndex={0}
      data-testid={`card-build-${build.build_id}`}
      aria-label={`${build.school_name} — ${build.career_title}`}
      onClick={onTap}
      onKeyDown={(e) => {
        if (e.target !== e.currentTarget) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onTap();
        }
      }}
      whileHover={{ x: 4 }}
      whileTap={{ scale: 0.98 }}
      transition={springs.snappy}
      className={`group relative w-full flex items-center gap-4 pl-14 pr-5 py-4 rounded-lg border bg-bp-mid hover:bg-bp-surface transition-colors duration-normal text-left cursor-pointer ${borderClass}`}
    >
      {/* Keep selection out of the flex row so compare mode can fade it in
          without reflowing every card. */}
      <motion.span
        aria-hidden
        className="absolute left-5 top-1/2 -translate-y-1/2 flex items-center"
        initial={false}
        animate={{
          scale: selectMode ? 1 : 0.72,
          x: selectMode ? 0 : -4,
          opacity: selectMode ? 1 : 0,
        }}
        transition={springs.snappy}
      >
        <span
          className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-colors ${
            selected
              ? "border-accent-thrive bg-accent-thrive text-text-inverse"
              : "border-border-strong"
          }`}
        >
          {selected ? "✓" : ""}
        </span>
      </motion.span>

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

      {/* Delete slot stays the same width; only the inner affordance fades.
          That avoids a right-side layout shift when compare mode toggles. */}
      {onDelete && (
        <span className="shrink-0 w-7 ml-1 overflow-hidden flex items-center">
          <button
            type="button"
            data-testid={`btn-delete-${build.build_id}`}
            aria-label={`Delete build for ${build.school_name}`}
            onClick={(e) => {
              e.stopPropagation();
              onDelete(build.build_id);
            }}
            tabIndex={selectMode ? -1 : 0}
            aria-hidden={selectMode}
            className={`w-7 h-7 rounded-md flex items-center justify-center text-text-muted hover:!opacity-100 hover:bg-accent-alert/20 hover:text-accent-alert transition-all duration-normal ${
              selectMode ? "opacity-0 pointer-events-none" : "opacity-0 group-hover:opacity-100"
            }`}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M5.25 1.75h3.5M1.75 3.5h10.5m-1.167 0-.411 6.17c-.062.926-.092 1.389-.306 1.74a1.75 1.75 0 0 1-.762.685c-.37.155-.835.155-1.764.155H6.16c-.93 0-1.394 0-1.764-.155a1.75 1.75 0 0 1-.762-.686c-.214-.35-.244-.813-.306-1.74L2.917 3.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </span>
      )}
    </motion.div>
  );
}
