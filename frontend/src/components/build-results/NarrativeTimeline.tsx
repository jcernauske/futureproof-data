import { useRef, useEffect } from "react";
import { GemmaThinking } from "@/components/ui/GemmaThinking";
import type { BossOutcome } from "@/types/build";

export interface NarrativeEntry {
  id: string;
  trigger: "initial" | "skill" | "wrapup";
  skillName?: string;
  narrative: string;
  result: BossOutcome;
  previousResult?: BossOutcome;
}

interface NarrativeTimelineProps {
  entries: NarrativeEntry[];
  bossColor: string;
  isLoading: boolean;
}

const RESULT_LABELS: Record<BossOutcome, string> = {
  win: "VICTORY",
  lose: "DEFEATED",
  draw: "STANDOFF",
  unknown: "UNKNOWN",
};

const RESULT_CSS: Record<BossOutcome, string> = {
  win: "var(--color-accent-thrive)",
  lose: "var(--color-accent-alert)",
  draw: "var(--color-accent-caution)",
  unknown: "var(--color-text-muted)",
};

export function NarrativeTimeline({
  entries,
  bossColor,
  isLoading,
}: NarrativeTimelineProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (entries.length > 1 || isLoading) {
      bottomRef.current?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
    }
  }, [entries.length, isLoading]);

  const skillEntries = entries.filter((e) => e.trigger === "skill");
  const hasSkillEntries = skillEntries.length > 0;

  return (
    <div className="relative mt-4" role="log" aria-label="Fight narrative timeline" aria-live="polite">
      {entries.map((entry) => {
        const isSkill = entry.trigger === "skill";
        const isWrapup = entry.trigger === "wrapup";
        const isInitial = entry.trigger === "initial";
        const resultChanged = entry.previousResult && entry.previousResult !== entry.result;

        // Initial and wrapup render as plain blocks (no timeline chrome)
        if (isInitial || isWrapup) {
          return (
            <div key={entry.id}>
              <div
                className="rounded-[14px] p-4"
                style={{
                  background: "rgba(27,29,48,0.6)",
                  borderLeft: isWrapup
                    ? "3px solid var(--color-accent-insight, #c49df5)"
                    : `3px solid ${bossColor}`,
                  boxShadow: isWrapup ? `0 0 24px ${bossColor}14` : undefined,
                  marginTop: isWrapup ? 12 : 0,
                }}
              >
                {isWrapup && (
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <span
                      className="inline-flex items-center gap-1.5 font-data font-bold uppercase"
                      style={{ fontSize: 11, letterSpacing: "1px", color: "var(--color-accent-insight, #c49df5)" }}
                    >
                      <span>&#10022;</span>
                      Gemma's Summary
                    </span>
                    {resultChanged && (
                      <span className="font-data" style={{ fontSize: 11 }}>
                        <span style={{ color: RESULT_CSS[entry.previousResult!] }}>
                          {RESULT_LABELS[entry.previousResult!]}
                        </span>
                        <span className="text-text-muted"> &rarr; </span>
                        <span style={{ color: RESULT_CSS[entry.result] }}>
                          {RESULT_LABELS[entry.result]}
                        </span>
                      </span>
                    )}
                  </div>
                )}
                <p
                  className="font-body text-text-primary"
                  style={{ fontSize: 15, lineHeight: 1.65 }}
                >
                  {entry.narrative}
                </p>
              </div>
            </div>
          );
        }

        // Skill entries render with timeline node + indent
        if (isSkill) {
          return (
            <div key={entry.id} className="relative" style={{ marginLeft: 8, marginTop: 8 }}>
              <div className="flex gap-3 items-center">
                {/* Node dot */}
                <div className="flex-shrink-0 flex items-center justify-center" style={{ width: 20 }}>
                  <div
                    className="rounded-full"
                    style={{
                      width: 8,
                      height: 8,
                      border: `2px solid ${bossColor}`,
                      backgroundColor: bossColor,
                    }}
                  />
                </div>

                {/* Card */}
                <div
                  className="flex-1 rounded-[14px] p-4 min-w-0"
                  style={{
                    background: "rgba(27,29,48,0.6)",
                    borderLeft: `3px solid ${bossColor}`,
                  }}
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    {entry.skillName && (
                      <span
                        className="inline-flex items-center gap-1 font-data font-bold rounded-full"
                        style={{
                          fontSize: 11,
                          padding: "3px 10px",
                          color: bossColor,
                          background: `${bossColor}1F`,
                          border: `1px solid ${bossColor}4D`,
                        }}
                      >
                        {resultChanged ? "↑" : "–"} {entry.skillName}
                      </span>
                    )}
                    {resultChanged && (
                      <span className="font-data" style={{ fontSize: 11 }}>
                        <span style={{ color: RESULT_CSS[entry.previousResult!] }}>
                          {RESULT_LABELS[entry.previousResult!]}
                        </span>
                        <span className="text-text-muted"> &rarr; </span>
                        <span style={{ color: RESULT_CSS[entry.result] }}>
                          {RESULT_LABELS[entry.result]}
                        </span>
                      </span>
                    )}
                  </div>
                  <p
                    className="font-body text-text-primary mt-2"
                    style={{ fontSize: 15, lineHeight: 1.65 }}
                  >
                    {entry.narrative}
                  </p>
                </div>
              </div>
            </div>
          );
        }

        return null;
      })}

      {/* Loading state */}
      {isLoading && (
        <div className="relative" style={{ marginLeft: hasSkillEntries ? 8 : 0, marginTop: 8 }}>
          <div className="flex gap-3 items-start">
            {hasSkillEntries && (
              <div className="flex-shrink-0 mt-4 flex items-center justify-center" style={{ width: 20 }}>
                <div
                  className="rounded-full"
                  style={{
                    width: 8,
                    height: 8,
                    backgroundColor: `${bossColor}66`,
                    animation: "timelinePulse 1.5s ease-in-out infinite",
                  }}
                />
              </div>
            )}
            <div
              className="flex-1 rounded-[14px] p-4"
              style={{
                background: "rgba(27,29,48,0.4)",
                borderLeft: `3px solid ${bossColor}44`,
              }}
            >
              <GemmaThinking message="Gemma is rethinking this one..." />
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />

      <style>{`
        @keyframes timelinePulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.7; }
        }
      `}</style>
    </div>
  );
}
