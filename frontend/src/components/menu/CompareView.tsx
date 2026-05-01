import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";
import { getBuild } from "@/api/build";
import { useBuildStore } from "@/store/buildStore";
import {
  compareBuilds,
  compareInsights,
  type AskScope,
  type CompareResult,
  type CompareInsights,
} from "@/api/menu";
import { PentagonOverlay } from "@/components/menu/PentagonOverlay";
import { RiskHeadlineGrid } from "@/components/menu/RiskHeadlineCard";
import { CharacterCard } from "@/components/menu/CharacterCard";
import { MoneySection } from "@/components/menu/MoneySection";
import { BranchPreview } from "@/components/menu/BranchPreview";
import { CompareWinners } from "@/components/menu/CompareWinners";
import { CompareProsCons } from "@/components/menu/CompareProsCons";
import { Button } from "@/components/ui/Button";
import { GemmaChat } from "@/components/menu/GemmaChat";
import { useT } from "@/i18n/useT";

interface CompareViewProps {
  buildIds: string[];
  onBack: () => void;
}

type Phase = "loading" | "ready" | "error";

const BUILD_COLORS = [
  "var(--color-accent-thrive)",
  "var(--color-accent-info)",
  "var(--color-accent-caution)",
  "var(--color-accent-empathy)",
];

export function CompareView({ buildIds, onBack }: CompareViewProps) {
  const navigate = useNavigate();
  const setBuild = useBuildStore((s) => s.setBuild);
  const t = useT();
  const [phase, setPhase] = useState<Phase>("loading");
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [insights, setInsights] = useState<CompareInsights | null>(null);
  const [highlightIndex, setHighlightIndex] = useState<number | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Compare-scope chip text per docs/specs/feature-ask-gemma.md §3.
  // School names truncated at 24 chars; N≥3 uses summary form.
  const compareChipText = useMemo(() => {
    if (!result?.builds || result.builds.length === 0) return "";
    const names = result.builds.map((b) =>
      b.school_name.length > 24
        ? b.school_name.slice(0, 23).trimEnd() + "…"
        : b.school_name,
    );
    if (names.length === 2) return `Comparing: ${names[0]} vs ${names[1]}`;
    return `Comparing ${names.length} builds`;
  }, [result?.builds]);

  const compareScope: AskScope | undefined = useMemo(() => {
    if (!buildIds || buildIds.length < 2) return undefined;
    return {
      kind: "compare",
      build_ids: buildIds,
    };
  }, [buildIds]);

  const handleMouseOver = useCallback((e: React.MouseEvent) => {
    let target = e.target as HTMLElement | null;
    while (target && target !== containerRef.current) {
      const col = target.getAttribute?.("data-col");
      if (col) {
        setHighlightIndex(parseInt(col, 10) - 1);
        return;
      }
      target = target.parentElement;
    }
    setHighlightIndex(null);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setHighlightIndex(null);
  }, []);

  const handleOpenBuild = useCallback(async (buildId: string) => {
    try {
      const full = await getBuild(buildId);
      setBuild(full);
      navigate("/my-build");
    } catch {
      setError("Couldn't load that build.");
    }
  }, [navigate, setBuild]);

  useEffect(() => {
    if (buildIds.length === 0) {
      setError("No builds selected to compare.");
      setPhase("error");
      return;
    }
    let cancelled = false;
    setPhase("loading");

    const dataPromise = compareBuilds(buildIds);
    const insightsPromise = compareInsights(buildIds);

    (async () => {
      try {
        const data = await dataPromise;
        if (cancelled) return;
        setResult(data);
        setPhase("ready");
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Failed to compare builds");
        setPhase("error");
        return;
      }

      try {
        const ins = await insightsPromise;
        if (!cancelled) setInsights(ins);
      } catch (e) {
        console.warn("Compare insights failed (non-blocking):", e);
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
          Loading comparison…
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
          {error ?? "The comparison didn't load. Try again, or head back to your builds."}
        </p>
        <Button variant="ghost" onClick={onBack} data-testid="btn-back-builds">
          ← Back to builds
        </Button>
      </div>
    );
  }

  const buildCount = result.builds.length;
  const buildColors = BUILD_COLORS.slice(0, buildCount);

  return (
    <motion.article
      ref={containerRef}
      data-testid="region-compare"
      aria-label={`Comparison of ${buildCount} builds`}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
      className="flex flex-col gap-0"
      onMouseOver={handleMouseOver}
      onMouseLeave={handleMouseLeave}
    >
      {/* Header */}
      <header className="text-center pt-8 pb-3">
        <h1 className="font-display font-bold text-4xl tablet:text-[44px] text-text-primary mb-2">
          Compare Builds
        </h1>
        <p className="text-base text-text-secondary max-w-[600px] mx-auto leading-relaxed mb-4">
          {buildCount === 2 ? "Two" : buildCount === 3 ? "Three" : "Four"} paths. One future. Hover any build to spotlight it across every metric.
        </p>
      </header>

      {/* Overlay Pentagon */}
      <div className="mt-4 mb-8 flex justify-center">
        <PentagonOverlay result={result} highlightIndex={highlightIndex} />
      </div>

      {/* School Cards */}
      <div className="mb-8">
        <p className="font-body text-[11px] font-bold tracking-widest uppercase text-text-muted mb-3 pl-1">
          Builds
        </p>
        <motion.div
          className="grid grid-cols-1 tablet:grid-cols-2 desktop:grid-cols-4 gap-4"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: { transition: { staggerChildren: stagger.normal } },
          }}
        >
          {result.builds.map((build, idx) => (
            <motion.div
              key={build.build_id}
              data-col={idx + 1}
              variants={{
                hidden: { opacity: 0, y: 30, scale: 0.95 },
                visible: { opacity: 1, y: 0, scale: 1, transition: springs.smooth },
              }}
            >
              <CharacterCard
                build={build}
                stats={result.stats}
                buildIndex={idx}
                highlighted={highlightIndex === null || highlightIndex === idx}
                onOpen={() => handleOpenBuild(build.build_id)}
              />
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* Boss Gauntlet */}
      <section className="mb-8">
        <p className="font-body text-[11px] font-bold tracking-widest uppercase text-text-muted mb-3 pl-1">
          Boss Gauntlet
        </p>
        <RiskHeadlineGrid
          bosses={result.bosses}
          builds={result.builds}
          buildColors={buildColors}
          highlightIndex={highlightIndex}
        />
      </section>

      {/* Salary */}
      <section className="mb-8">
        <p className="font-body text-[11px] font-bold tracking-widest uppercase text-text-muted mb-3 pl-1">
          Median Early Salary
        </p>
        <MoneySection
          builds={result.builds}
          highlightIndex={highlightIndex}
        />
      </section>

      {/* Branch Preview */}
      {result.branches.some((b) => b.destinations.length > 0) && (
        <section className="mb-16">
          <p className="font-body text-[11px] font-bold tracking-widest uppercase text-text-muted mb-3 pl-1">
            Career Branches
          </p>
          <BranchPreview
            branches={result.branches}
            buildColors={buildColors}
            highlightIndex={highlightIndex}
          />
        </section>
      )}

      {/* Gemma's Take */}
      <section
        data-testid="region-gemma-compare"
        aria-label="Gemma's comparison analysis"
        className="border-t border-border-subtle pt-6"
      >
        <div className="flex items-center justify-center gap-2.5 mb-5">
          <span className="w-8 h-8 rounded-full bg-gradient-to-br from-accent-info/20 to-accent-insight/20 flex items-center justify-center text-base">
            ✦
          </span>
          <span className="font-display font-semibold text-xl text-text-primary">
            Gemma's Take
          </span>
        </div>

        <div className="max-w-[720px] mx-auto flex flex-col gap-5">
          {insights?.compare_summary ? (
            <p className="font-body text-[15px] text-text-secondary leading-relaxed text-center">
              {(() => {
                const trimmed = insights.compare_summary.trim();
                const sentenceMatch = trimmed.match(/^[^.!?]+[.!?]/);
                return sentenceMatch ? sentenceMatch[0] : trimmed;
              })()}
            </p>
          ) : (
            <motion.p
              animate={{ opacity: [0.4, 0.9, 0.4] }}
              transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
              className="font-body text-body text-text-muted text-center"
            >
              Reading the tradeoffs…
            </motion.p>
          )}

          {insights?.pivotal?.meta_tradeoff && (
            <div
              data-testid="pivotal-meta-tradeoff"
              className="self-center inline-flex flex-col items-center gap-1.5 px-5 py-3 rounded-full bg-bp-deep/60 border border-border-subtle"
            >
              <p className="font-data text-[11px] font-bold tracking-widest uppercase text-text-muted">
                The real choice
              </p>
              <p className="font-display text-heading text-text-primary">
                {insights.pivotal.meta_tradeoff}
              </p>
              {insights.pivotal.meta_explanation && (
                <p className="font-body text-small text-text-secondary text-center max-w-[520px] leading-snug">
                  {insights.pivotal.meta_explanation}
                </p>
              )}
            </div>
          )}

          {insights?.pros_cons && insights.pros_cons.length > 0 && (
            <CompareProsCons
              builds={result.builds}
              prosCons={insights.pros_cons}
              highlightIndex={highlightIndex}
            />
          )}

          <p className="font-data text-[11px] font-bold tracking-widest uppercase text-text-muted text-center">
            Where they win
          </p>

          <CompareWinners
            result={result}
            highlightIndex={highlightIndex}
          />

          {insights?.pivotal?.decade_projection && (
            <article
              data-testid="pivotal-decade-projection"
              className="rounded-xl p-5 bg-bp-deep/60 border border-border-subtle relative"
            >
              <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-gradient-to-b from-accent-info to-accent-info/20 rounded-l-xl" />
              <p className="font-data text-[11px] font-bold tracking-widest uppercase text-text-muted mb-2">
                In ten years
              </p>
              <p className="font-body text-[15px] text-text-primary leading-relaxed">
                {insights.pivotal.decade_projection}
              </p>
            </article>
          )}

          {insights?.pivotal?.pivot_question && (
            <article
              data-testid="pivotal-question"
              className="rounded-xl p-5 bg-gradient-to-br from-accent-thrive/10 to-accent-insight/10 border border-accent-thrive/30 relative"
            >
              <p className="font-data text-[11px] font-bold tracking-widest uppercase text-accent-thrive mb-2">
                Sit with this
              </p>
              <p className="font-display text-heading text-text-primary leading-snug">
                {insights.pivotal.pivot_question}
              </p>
            </article>
          )}
        </div>

        {insights?.compare_summary && compareScope && (
          <button
            type="button"
            onClick={() => setChatOpen(true)}
            disabled={chatOpen}
            data-testid="btn-ask-compare"
            aria-label={t("chat.compareEntry")}
            className={[
              "w-full max-w-[420px] mx-auto mt-5 block",
              "inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-lg",
              "bg-accent-thrive text-text-inverse font-body text-cta",
              "hover:bg-[#6bc494]",
              "active:scale-[0.97]",
              "focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-none",
              "disabled:bg-bp-surface disabled:text-text-muted disabled:cursor-not-allowed",
              "transition-colors duration-fast",
              "cursor-pointer",
            ].join(" ")}
          >
            <span aria-hidden className="text-text-inverse text-[16px] leading-none">
              ✦
            </span>
            {t("chat.compareEntry")}
          </button>
        )}
      </section>

      <GemmaChat
        open={chatOpen}
        build={null}
        scope={compareScope}
        chipText={compareChipText}
        onClose={() => setChatOpen(false)}
      />
    </motion.article>
  );
}
