import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { apiPost } from "@/api/client";
import { GemmaSpinner } from "@/components/ui/GemmaSpinner";
import { GemmaStar } from "@/components/ui/GemmaStar";
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
  | "audit_fail"
  | "clarify"
  | "fallback";

export function MajorInput({ school, programs, onConfirm }: MajorInputProps) {
  const [rawText, setRawText] = useState("");
  const [phase, setPhase] = useState<MajorPhase>("input");
  const [intentResult, setIntentResult] = useState<IntentResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [clarifyText, setClarifyText] = useState("");
  const [clarifyRounds, setClarifyRounds] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  async function resolveIntent(text: string, isClarification = false) {
    setPhase("thinking");
    setError(null);
    const startTime = Date.now();

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

      const elapsed = Date.now() - startTime;
      if (elapsed < 200) {
        handleIntentResult(result);
        return;
      }

      setIntentResult(result);

      if (result.audit_flag === "hard_reject") {
        setPhase("audit_fail");
      } else if (result.needs_clarification && !isClarification) {
        setPhase("clarify");
      } else {
        setPhase("match");
      }
    } catch {
      setError(
        "Gemma couldn't match that — try a different description, or pick from the list below.",
      );
      setPhase("fallback");
    }
  }

  function handleIntentResult(result: IntentResult) {
    if (result.audit_flag === "hard_reject") {
      setIntentResult(result);
      setPhase("audit_fail");
      return;
    }
    setIntentResult(result);
    setPhase("match");
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
    if (clarifyRounds >= 2) {
      setPhase("fallback");
      return;
    }
    setClarifyRounds((r) => r + 1);
    setPhase("clarify");
    setClarifyText("");
  }

  function handleClarifySubmit() {
    const text = clarifyText.trim();
    if (!text) return;
    resolveIntent(text, true);
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

  function handleTryAgain() {
    setRawText("");
    setPhase("input");
    setIntentResult(null);
    setError(null);
    setClarifyRounds(0);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
    >
      <h2 className="font-display text-subheading font-bold text-text-primary mb-4">
        What do you want to study?
      </h2>

      {/* Text input */}
      <div className="flex gap-2">
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
        <button
          onClick={handleSubmit}
          disabled={!rawText.trim() || phase === "thinking"}
          className="bg-bp-surface text-text-secondary px-4 rounded-md border border-border-subtle hover:border-accent-insight transition-colors duration-fast disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          aria-label="Submit major"
        >
          →
        </button>
      </div>

      {/* Thinking indicator — collapses on exit to transfer energy to card */}
      <AnimatePresence>
        {phase === "thinking" && (
          <motion.div
            className="mt-4 flex items-center gap-3"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.4 }}
            transition={{ duration: 0.25, ease: "easeIn" }}
          >
            <GemmaSpinner size={28} />
            <span className="text-small text-text-secondary">
              Gemma is matching your input...
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Match card — arrives with energy from collapsed spinner */}
      <AnimatePresence>
        {phase === "match" && intentResult && (
          <MatchCard
            intentResult={intentResult}
            rawText={rawText}
            onConfirm={handleConfirm}
            onNotQuite={handleNotQuite}
          />
        )}
      </AnimatePresence>

      {/* Audit fail */}
      <AnimatePresence>
        {phase === "audit_fail" && intentResult?.audit_message && (
          <motion.div
            className="mt-4 bg-bp-raised rounded-lg p-5 border border-accent-caution/30"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={springs.smooth}
            role="alert"
          >
            <p className="text-sm text-text-primary leading-relaxed">
              ⚠️ {intentResult.audit_message}
            </p>
            <button
              onClick={handleTryAgain}
              className="mt-3 bg-accent-caution text-text-inverse font-semibold py-2 px-4 rounded-md cursor-pointer"
            >
              Try again
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Clarification round */}
      <AnimatePresence>
        {phase === "clarify" && (
          <motion.div
            className="mt-4 bg-bp-raised rounded-lg p-5 border border-border-subtle"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={springs.smooth}
          >
            <p className="text-sm text-text-secondary mb-3">
              Tell us more — what career are you thinking about?
            </p>
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={clarifyText}
                onChange={(e) => setClarifyText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleClarifySubmit();
                }}
                placeholder="e.g., 'I want to be a doctor'"
                className="flex-1 bg-bp-deep text-text-primary font-body text-body px-4 py-2.5 h-12 rounded-md border border-border focus:border-accent-info focus:shadow-[0_0_0_3px_var(--color-focus-ring)] focus:outline-none transition-all duration-normal placeholder:text-text-muted"
                aria-label="Clarify your major choice"
              />
              <button
                onClick={handleClarifySubmit}
                disabled={!clarifyText.trim()}
                className="bg-accent-thrive text-text-inverse font-bold py-2.5 px-4 rounded-md cursor-pointer hover:bg-[#6bc494] hover:shadow-glow-thrive transition-all duration-normal disabled:opacity-40 disabled:cursor-not-allowed"
              >
                →
              </button>
            </div>

            {programs.length > 0 && (
              <>
                <p className="text-sm text-text-muted mb-2">
                  Or pick from {school.name}'s programs:
                </p>
                <ProgramList
                  programs={programs}
                  onPick={handleProgramPick}
                />
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Fallback program picker */}
      <AnimatePresence>
        {phase === "fallback" && (
          <motion.div
            className="mt-4"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={springs.smooth}
          >
            {error && (
              <p className="text-sm text-text-muted mb-3">{error}</p>
            )}
            {programs.length > 0 ? (
              <>
                <p className="text-sm text-text-secondary mb-2">
                  Pick from {school.name}'s programs:
                </p>
                <ProgramList
                  programs={programs}
                  onPick={handleProgramPick}
                />
              </>
            ) : (
              <p className="text-sm text-text-muted">
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

function ProgramList({
  programs,
  onPick,
}: {
  programs: ProgramResult[];
  onPick: (p: ProgramResult) => void;
}) {
  const unique = programs.filter(
    (p, i, arr) =>
      arr.findIndex((x) => x.cipcode === p.cipcode) === i,
  );

  return (
    <ul className="max-h-[240px] overflow-y-auto space-y-0.5 rounded-md border border-border-subtle bg-bp-surface">
      {unique.map((program) => (
        <li key={program.cipcode}>
          <button
            onClick={() => onPick(program)}
            className="w-full text-left px-4 py-2.5 text-sm text-text-secondary hover:bg-bp-mid hover:text-text-primary transition-colors duration-fast cursor-pointer"
          >
            {program.program_name}
          </button>
        </li>
      ))}
    </ul>
  );
}

function MatchCard({
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

  return (
    <motion.div
      className={`mt-4 bg-bp-mid rounded-xl p-6 border border-[rgba(255,255,255,0.5)] ${
        isLowConfidence
          ? "animate-[card-breathe-caution_4s_ease-in-out_infinite]"
          : "animate-[card-breathe_4s_ease-in-out_infinite]"
      }`}
      initial={{
        opacity: 0,
        scale: 0.85,
        y: 12,
      }}
      animate={{
        opacity: 1,
        scale: 1,
        y: 0,
      }}
      exit={{ opacity: 0, y: -12, scale: 0.98 }}
      transition={springs.bouncy}
    >
      {/* Zone A: Attribution */}
      <div className="flex items-center gap-2 mb-3">
        <GemmaStar size={14} />
        <span className="text-small text-text-muted">
          Gemma matched "<span className="font-semibold text-text-secondary">{rawText}</span>"
        </span>
      </div>

      {/* Zone B: Program title — slides in and brightens */}
      <motion.div
        initial={{ opacity: 0, x: -8 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ ...springs.smooth, delay: 0.15 }}
      >
        <motion.h3
          className="font-display text-subheading font-semibold mb-1"
          initial={{ color: "var(--color-text-muted)" }}
          animate={{ color: "var(--color-text-primary)" }}
          transition={{ duration: 0.4, delay: 0.3, ease: "easeOut" }}
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

      {/* Zone C: Career preview — staggers in */}
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
                <span className="text-accent-info/50 text-[10px] group-hover:text-accent-info transition-colors duration-fast">
                  ▸
                </span>
                <span className="font-body text-body-sm font-semibold text-text-secondary group-hover:text-text-primary transition-colors duration-fast">
                  {career}
                </span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Zone D: Playful warning (conditional) */}
      {intentResult.audit_flag === "playful_warning" &&
        intentResult.audit_message && (
          <div className="border-t border-border-subtle pt-3 mt-4">
            <p className="text-small text-accent-caution italic">
              {intentResult.audit_message}
            </p>
          </div>
        )}

      {/* Zone E: Actions — delayed entrance */}
      <motion.div
        className="mt-5 flex gap-3 flex-col mobile:flex-row"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...springs.smooth, delay: 0.7 }}
      >
        <motion.button
          onClick={onConfirm}
          className="flex-1 bg-accent-thrive text-text-inverse font-body text-cta font-bold h-12 px-[28px] rounded-lg cursor-pointer hover:bg-[#6bc494] hover:shadow-glow-thrive transition-all duration-normal"
          whileTap={{ scale: 0.97 }}
          transition={springs.snappy}
        >
          {isLowConfidence ? "Close enough" : "That's right"}
        </motion.button>
        <motion.button
          onClick={onNotQuite}
          className={`mobile:flex-none font-body text-cta font-bold h-12 px-6 rounded-lg cursor-pointer transition-all duration-normal ${
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
