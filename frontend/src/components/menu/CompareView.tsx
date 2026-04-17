import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";
import { compareBuilds, sendChat, type CompareResult } from "@/api/menu";
import { PentagonOverlay } from "@/components/menu/PentagonOverlay";
import { RiskHeadlineCard } from "@/components/menu/RiskHeadlineCard";
import { Button } from "@/components/ui/Button";

interface CompareViewProps {
  buildIds: string[];
  onBack: () => void;
}

type Phase = "loading" | "ready" | "error";

export function CompareView({ buildIds, onBack }: CompareViewProps) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);

  useEffect(() => {
    if (buildIds.length === 0) {
      setError("No builds selected to compare.");
      setPhase("error");
      return;
    }
    let cancelled = false;
    setPhase("loading");
    (async () => {
      try {
        const r = await compareBuilds(buildIds);
        if (cancelled) return;
        setResult(r);
        setPhase("ready");

        try {
          const labels = r.builds.map((b) => b.label).join(" vs ");
          const prompt = `Compare these builds and explain the tradeoffs without declaring a winner: ${labels}`;
          const narrative = await sendChat(buildIds[0]!, prompt, []);
          if (!cancelled) setSummary(narrative);
        } catch {
          if (!cancelled) setSummary(null);
        }
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Failed to compare builds");
        setPhase("error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [buildIds]);

  if (phase === "loading") {
    return (
      <div
        data-testid="region-compare"
        className="flex flex-col items-center justify-center gap-4 py-16"
      >
        <motion.div
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
          className="w-16 h-16 rounded-full"
          style={{
            background:
              "radial-gradient(circle, var(--color-state-loading) 0%, transparent 70%)",
          }}
        />
        <p className="font-body text-body text-text-secondary">
          Comparing your builds…
        </p>
      </div>
    );
  }

  if (phase === "error" || !result) {
    return (
      <div className="flex flex-col items-center gap-4 py-12 text-center">
        <p className="font-display text-heading text-accent-alert">
          Couldn't load the comparison.
        </p>
        <p className="font-body text-body text-text-secondary">
          {error ?? "Something went wrong."}
        </p>
        <Button variant="ghost" onClick={onBack} data-testid="btn-back-builds">
          ← Back to builds
        </Button>
      </div>
    );
  }

  return (
    <motion.article
      data-testid="region-compare"
      aria-label={`Risk comparison of ${result.builds.length} builds`}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
      className="flex flex-col gap-8"
    >
      <header className="flex items-center justify-between">
        <h2 className="font-display text-heading text-text-primary">
          Risk comparison
        </h2>
        <Button variant="ghost" onClick={onBack} data-testid="btn-back-builds">
          ← Back to builds
        </Button>
      </header>

      <section className="flex flex-col gap-3">
        <p className="font-data text-micro uppercase tracking-[2px] text-text-muted">
          Where each build wins, loses, or draws
        </p>
        <motion.div
          className="flex flex-col gap-3"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: { transition: { staggerChildren: stagger.normal } },
          }}
        >
          {result.bosses.map((boss) => (
            <motion.div
              key={boss.label}
              variants={{
                hidden: { opacity: 0, y: 12 },
                visible: { opacity: 1, y: 0, transition: springs.smooth },
              }}
            >
              <RiskHeadlineCard boss={boss} builds={result.builds} />
            </motion.div>
          ))}
        </motion.div>
      </section>

      <section className="flex flex-col gap-4 items-center">
        <p className="font-data text-micro uppercase tracking-[2px] text-text-muted self-start">
          Stat overlay
        </p>
        <PentagonOverlay result={result} />
      </section>

      <section
        data-testid="region-gemma-compare"
        aria-label="Gemma's comparison analysis"
        className="bg-bp-mid border border-border-subtle rounded-xl p-6 border-l-[3px] border-l-accent-insight"
      >
        <p className="font-data text-micro uppercase tracking-[2px] text-accent-insight mb-3">
          Gemma's comparison
        </p>
        {summary ? (
          <p className="font-body text-body text-text-primary leading-relaxed">
            {summary}
          </p>
        ) : (
          <motion.div
            animate={{ opacity: [0.4, 0.9, 0.4] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
            className="font-body text-body text-text-muted"
          >
            Reading the tradeoffs…
          </motion.div>
        )}
      </section>
    </motion.article>
  );
}
