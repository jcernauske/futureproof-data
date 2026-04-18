import { useRef, useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { apiPost } from "@/api/client";
import { GemmaStar } from "@/components/ui/GemmaStar";
import { GemmaThinking } from "@/components/ui/GemmaThinking";
import type {
  IntentResult,
  MajorSelection,
  ProgramResult,
  SchoolSelection,
} from "@/types/buildInput";

interface MajorInputProps {
  school: SchoolSelection;
  programs: ProgramResult[];
  onConfirm: (major: MajorSelection) => void;
}

type MajorPhase =
  | "input"
  | "thinking"
  | "match"
  | "clarify"
  | "audit_fail"
  | "fallback";

export function MajorInput({ school, programs, onConfirm }: MajorInputProps) {
  const [rawText, setRawText] = useState("");
  const [phase, setPhase] = useState<MajorPhase>("input");
  const [intentResult, setIntentResult] = useState<IntentResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const uniquePrograms = programs.filter(
    (p, i, arr) => arr.findIndex((x) => x.cipcode === p.cipcode) === i,
  );

  async function resolveIntent(text: string) {
    setPhase("thinking");
    setError(null);

    try {
      const programDicts = programs.map((p) => ({
        cipcode: p.cipcode,
        program_name: p.program_name,
      }));

      const result = await apiPost<IntentResult>("/intent/", {
        school_name: school.name,
        unitid: school.unitid,
        major_text: text,
        programs: programDicts,
      });

      setIntentResult(result);

      if (result.audit_flag === "hard_reject") {
        setPhase("audit_fail");
      } else if (result.needs_clarification) {
        setPhase("clarify");
      } else {
        setPhase("match");
      }
    } catch {
      setError(
        "Gemma couldn't match that — pick from the list below.",
      );
      setPhase("fallback");
    }
  }

  function handleSubmit() {
    const text = rawText.trim();
    if (!text) return;
    resolveIntent(text);
  }

  function handleConfirm() {
    if (!intentResult) return;

    apiPost("/intent/confirm", {
      school_name: school.name,
      unitid: school.unitid,
      major_text: rawText.trim(),
      matched_cip: intentResult.matched_cip,
      matched_title: intentResult.matched_title,
    }).catch(() => {});

    onConfirm({
      cipCode: intentResult.matched_cip,
      cipTitle: intentResult.matched_title,
      rawText: rawText.trim(),
      careersPreview: intentResult.careers_preview,
      substitutionApplied: intentResult.parent_cip !== "",
    });
  }

  function handleNotQuite() {
    setPhase("clarify");
  }

  function handleProgramPick(program: ProgramResult) {
    onConfirm({
      cipCode: program.cipcode,
      cipTitle: program.program_name,
      rawText: rawText.trim(),
      careersPreview: [],
      substitutionApplied: false,
    });
  }

  function handleStartOver() {
    setRawText("");
    setPhase("input");
    setIntentResult(null);
    setError(null);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  const inputDimmed = phase === "clarify" || phase === "fallback";

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
    >
      <h2 className="font-display text-subheading font-bold text-text-primary mb-4">
        What do you want to study?
      </h2>

      {/* Text input — dims when clarify/fallback is active */}
      <motion.div
        className="flex gap-2"
        animate={{ opacity: inputDimmed ? 0.4 : 1 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        style={{ pointerEvents: inputDimmed ? "none" : "auto" }}
      >
        <input
          ref={inputRef}
          type="text"
          value={rawText}
          onChange={(e) => {
            setRawText(e.target.value);
            if (phase === "audit_fail") {
              setPhase("input");
              setIntentResult(null);
            }
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSubmit();
          }}
          placeholder="Type anything — 'pre-med', 'CS', 'business'..."
          disabled={phase === "thinking"}
          className={`flex-1 bg-bp-deep text-text-primary font-body text-body px-4 py-3 h-12 rounded-md border border-border focus:border-accent-info focus:shadow-[0_0_0_3px_var(--color-focus-ring)] focus:outline-none transition-all duration-normal placeholder:text-text-muted disabled:opacity-60 ${
            phase === "thinking" ? "text-text-muted" : ""
          }`}
          aria-label="What do you want to study?"
        />
        <motion.button
          onClick={handleSubmit}
          disabled={!rawText.trim() || phase === "thinking"}
          className="bg-accent-thrive text-text-inverse font-bold h-12 w-12 rounded-md cursor-pointer hover:bg-[#6bc494] hover:shadow-glow-thrive transition-all duration-normal disabled:opacity-40 disabled:cursor-not-allowed"
          whileTap={{ scale: 0.97 }}
          transition={springs.snappy}
          aria-label="Submit major"
        >
          →
        </motion.button>
      </motion.div>

      {/* Thinking indicator */}
      <AnimatePresence>
        {phase === "thinking" && (
          <motion.div
            className="mt-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.4 }}
            transition={{ duration: 0.25, ease: "easeIn" }}
          >
            <GemmaThinking message="Gemma is matching your input..." />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Match + Clarify card — single container that transforms */}
      <AnimatePresence>
        {(phase === "match" || phase === "clarify") && intentResult && (
          <motion.div
            className={`mt-4 bg-bp-mid rounded-xl p-6 border border-[rgba(255,255,255,0.5)] border-l-[3px] ${
              phase === "clarify"
                ? "border-l-accent-info animate-[card-breathe-info_4s_ease-in-out_infinite]"
                : intentResult.confidence === "low"
                  ? "border-l-accent-caution animate-[card-breathe-caution_4s_ease-in-out_infinite]"
                  : "border-l-accent-insight animate-[card-breathe_4s_ease-in-out_infinite]"
            }`}
            initial={{ opacity: 0, scale: 0.85, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, y: -12, scale: 0.98 }}
            transition={springs.bouncy}
          >
            <AnimatePresence mode="wait">
              {phase === "match" && (
                <MatchContent
                  key="match"
                  intentResult={intentResult}
                  rawText={rawText}
                  onConfirm={handleConfirm}
                  onNotQuite={handleNotQuite}
                />
              )}
              {phase === "clarify" && (
                <ClarifyContent
                  key="clarify"
                  school={school}
                  programs={uniquePrograms}
                  onPick={handleProgramPick}
                  onStartOver={handleStartOver}
                />
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Audit fail */}
      <AnimatePresence>
        {phase === "audit_fail" && intentResult?.audit_message && (
          <motion.div
            className="mt-4 bg-bp-mid rounded-xl p-6 border border-accent-caution/20"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={springs.smooth}
            role="alert"
          >
            <p className="text-small text-text-primary leading-relaxed">
              ⚠️ {intentResult.audit_message}
            </p>
            <button
              onClick={handleStartOver}
              className="mt-3 bg-accent-caution text-text-inverse font-semibold py-2 px-4 rounded-md cursor-pointer"
            >
              Try again
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Fallback — Gemma errored, just show program list */}
      <AnimatePresence>
        {phase === "fallback" && (
          <motion.div
            className="mt-4 bg-bp-mid rounded-xl p-6 border border-border-subtle"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={springs.smooth}
          >
            {error && (
              <p className="text-small text-text-muted mb-4">{error}</p>
            )}
            {uniquePrograms.length > 0 ? (
              <ClarifyContent
                school={school}
                programs={uniquePrograms}
                onPick={handleProgramPick}
                onStartOver={handleStartOver}
              />
            ) : (
              <p className="text-small text-text-muted">
                No programs available. Please go back and try a different
                school.
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ================================================================
   Match Content — shown inside the card when Gemma has a match
   ================================================================ */

function MatchContent({
  intentResult,
  rawText,
  onConfirm,
  onNotQuite,
}: {
  intentResult: IntentResult;
  rawText: string;
  onConfirm: () => void;
  onNotQuite: () => void;
}) {
  const isLowConfidence = intentResult.confidence === "low";
  const [confirming, setConfirming] = useState(false);
  const confirmTimerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (confirmTimerRef.current) window.clearTimeout(confirmTimerRef.current);
    };
  }, []);

  function handleConfirmClick() {
    if (confirming) return;
    setConfirming(true);
    // Brief reward flash (title + CTA glow thrive) before handing off.
    confirmTimerRef.current = window.setTimeout(() => onConfirm(), 320);
  }

  // Gemma matches wear their voice in color: insight by default, caution when
  // confidence is low, thrive briefly on confirm (the "you chose well" moment).
  const titleColor = confirming
    ? "var(--color-accent-thrive)"
    : isLowConfidence
      ? "var(--color-accent-caution)"
      : "var(--color-accent-insight)";

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
    >
      {/* Attribution — raw input echoes the match color so Gemma's voice reads in content. */}
      <div className="flex items-center gap-2 mb-3">
        <GemmaStar size={14} />
        <span className="text-small text-text-muted">
          Gemma matched "<span
            className={`font-semibold ${
              isLowConfidence ? "text-accent-caution" : "text-accent-insight"
            }`}
          >{rawText}</span>"
        </span>
      </div>

      {/* Program title */}
      <motion.div
        initial={{ opacity: 0, x: -8 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ ...springs.smooth, delay: 0.15 }}
      >
        <motion.h3
          className="font-display text-subheading font-semibold mb-1"
          initial={{ color: "var(--color-text-muted)" }}
          animate={{ color: titleColor }}
          transition={{ duration: confirming ? 0.2 : 0.4, delay: confirming ? 0 : 0.3, ease: "easeOut" }}
        >
          {intentResult.matched_title}
        </motion.h3>
        <div className="flex items-center gap-2 mb-4">
          <span className="font-data text-data-sm text-text-muted">
            CIP {intentResult.matched_cip}
          </span>
          {isLowConfidence && (
            <span className="inline-flex items-center bg-[rgba(242,212,119,0.15)] text-accent-caution rounded-full px-3 py-0.5 text-micro font-semibold">
              best guess
            </span>
          )}
        </div>
      </motion.div>

      {/* Career preview */}
      {intentResult.careers_preview.length > 0 && (
        <motion.div
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: { transition: { staggerChildren: 0.05, delayChildren: 0.4 } },
          }}
        >
          <span className="font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info mb-2.5 block">
            Where this leads
          </span>
          <div className="flex flex-col gap-0.5">
            {intentResult.careers_preview.slice(0, 5).map((career) => (
              <motion.div
                key={career}
                className="flex items-center gap-2 py-2 px-3 rounded-md hover:bg-bp-surface transition-colors duration-fast group"
                variants={{
                  hidden: { opacity: 0, y: 12 },
                  visible: { opacity: 1, y: 0, transition: springs.smooth },
                }}
              >
                <span className="text-accent-info/60 text-[10px] group-hover:text-accent-info transition-colors duration-fast">
                  ▸
                </span>
                <span className="font-body text-body-sm font-semibold text-accent-info group-hover:text-text-primary transition-colors duration-fast">
                  {career}
                </span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Playful warning */}
      {intentResult.audit_flag === "playful_warning" &&
        intentResult.audit_message && (
          <div className="border-t border-border-subtle pt-3 mt-4">
            <p className="text-small text-accent-caution italic">
              {intentResult.audit_message}
            </p>
          </div>
        )}

      {/* Actions */}
      <motion.div
        className="mt-5 flex gap-3 flex-col mobile:flex-row"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...springs.smooth, delay: 0.7 }}
      >
        <motion.button
          onClick={handleConfirmClick}
          disabled={confirming}
          className="flex-1 bg-accent-thrive text-text-inverse font-body text-cta font-bold h-12 px-[28px] rounded-lg cursor-pointer hover:bg-[#6bc494] hover:shadow-glow-thrive transition-all duration-normal disabled:cursor-default"
          animate={confirming ? { boxShadow: "0 0 24px rgba(125, 212, 163, 0.45)" } : { boxShadow: "0 0 0px rgba(125, 212, 163, 0)" }}
          whileTap={{ scale: 0.97 }}
          transition={springs.snappy}
        >
          {isLowConfidence ? "Close enough" : "That's right"}
        </motion.button>
        <motion.button
          onClick={onNotQuite}
          disabled={confirming}
          className={`mobile:flex-none font-body text-cta font-bold h-12 px-6 rounded-lg cursor-pointer transition-all duration-normal disabled:cursor-default ${
            isLowConfidence
              ? "text-text-primary hover:bg-[rgba(255,255,255,0.05)]"
              : "text-text-secondary hover:text-text-primary hover:bg-[rgba(255,255,255,0.05)]"
          }`}
          whileTap={{ scale: 0.97 }}
          transition={springs.snappy}
        >
          Not quite
        </motion.button>
      </motion.div>
    </motion.div>
  );
}

/* ================================================================
   Clarify Content — searchable program picker, no second Gemma call
   ================================================================ */

function ClarifyContent({
  school,
  programs,
  onPick,
  onStartOver,
}: {
  school: SchoolSelection;
  programs: ProgramResult[];
  onPick: (p: ProgramResult) => void;
  onStartOver: () => void;
}) {
  const [filter, setFilter] = useState("");
  const [hoverIndex, setHoverIndex] = useState(-1);

  const filtered = filter
    ? programs.filter((p) =>
        p.program_name.toLowerCase().includes(filter.toLowerCase()),
      )
    : programs;

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: 0.08, delayChildren: 0.15 } },
      }}
    >
      {/* Header */}
      <motion.div
        className="flex items-center gap-2 mb-4"
        variants={{
          hidden: { opacity: 0, y: 16 },
          visible: { opacity: 1, y: 0, transition: springs.smooth },
        }}
      >
        <GemmaStar size={14} />
        <span className="text-small text-text-secondary">
          Let's find the right one
        </span>
      </motion.div>

      {/* Search filter */}
      <motion.div
        className="relative mb-3"
        variants={{
          hidden: { opacity: 0, y: 16 },
          visible: { opacity: 1, y: 0, transition: springs.smooth },
        }}
      >
        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted text-body-sm pointer-events-none">
          ⌕
        </span>
        <input
          type="text"
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value);
            setHoverIndex(-1);
          }}
          placeholder="Filter programs..."
          className="w-full bg-bp-deep text-text-primary font-body text-body-sm h-[44px] pl-10 pr-4 rounded-md border border-border focus:border-accent-info focus:shadow-[0_0_0_3px_var(--color-focus-ring)] focus:outline-none transition-all duration-normal placeholder:text-text-muted"
          autoFocus
        />
      </motion.div>

      {/* Program list */}
      <motion.div
        variants={{
          hidden: { opacity: 0, y: 16 },
          visible: { opacity: 1, y: 0, transition: springs.smooth },
        }}
      >
        <span className="font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info mb-2 block">
          {school.name}
        </span>

        {filtered.length > 0 ? (
          <ul className="max-h-[288px] overflow-y-auto rounded-lg border border-border-subtle overflow-hidden">
            {filtered.map((program, i) => (
              <li key={program.cipcode}>
                <button
                  onClick={() => onPick(program)}
                  onMouseEnter={() => setHoverIndex(i)}
                  onMouseLeave={() => setHoverIndex(-1)}
                  className={`w-full text-left flex justify-between items-center px-[18px] py-3 cursor-pointer transition-[background] duration-fast border-b border-border-subtle last:border-b-0 border-l-[3px] ${
                    i === hoverIndex
                      ? "bg-[rgba(125,212,163,0.1)] border-l-accent-thrive text-text-primary"
                      : "border-l-transparent text-text-secondary hover:bg-bp-surface hover:text-text-primary"
                  }`}
                >
                  <span className="font-body text-body-sm font-semibold">
                    {program.program_name}
                  </span>
                  <span className="font-data text-data-sm text-text-muted ml-3 shrink-0">
                    {program.cipcode}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-body-sm text-text-muted text-center py-8">
            No programs match — try a shorter search
          </p>
        )}
      </motion.div>

      {/* Start over */}
      <motion.button
        className="w-full mt-3 font-body text-small font-semibold text-text-muted hover:text-text-secondary cursor-pointer transition-colors duration-normal text-center py-2"
        onClick={onStartOver}
        variants={{
          hidden: { opacity: 0, y: 16 },
          visible: { opacity: 1, y: 0, transition: springs.smooth },
        }}
      >
        Start over
      </motion.button>
    </motion.div>
  );
}
