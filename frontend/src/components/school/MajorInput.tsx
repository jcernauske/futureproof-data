import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { apiPost } from "@/api/client";
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
      <h2 className="font-display text-xl text-text-primary mb-4">
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
          className={`flex-1 bg-bp-surface text-text-primary font-body text-body px-4 py-3 rounded-bp-md border border-border-subtle focus:border-accent-insight focus:outline-none transition-colors duration-normal placeholder:text-text-muted disabled:opacity-60 ${
            phase === "thinking" ? "text-text-muted" : ""
          }`}
          aria-label="What do you want to study?"
        />
        <button
          onClick={handleSubmit}
          disabled={!rawText.trim() || phase === "thinking"}
          className="bg-bp-surface text-text-secondary px-4 rounded-bp-md border border-border-subtle hover:border-accent-insight transition-colors duration-fast disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          aria-label="Submit major"
        >
          →
        </button>
      </div>

      {/* Thinking indicator */}
      <AnimatePresence>
        {phase === "thinking" && (
          <motion.div
            className="mt-3 flex items-center gap-2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="w-1.5 h-1.5 rounded-full bg-accent-insight"
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{
                    duration: 1.2,
                    repeat: Infinity,
                    delay: i * 0.2,
                  }}
                />
              ))}
            </div>
            <span className="text-sm text-text-secondary">
              Matching your input...
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Match card */}
      <AnimatePresence>
        {phase === "match" && intentResult && (
          <motion.div
            className="mt-4 bg-bp-raised rounded-bp-lg p-5 border border-accent-insight/20 shadow-glow-insight"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={springs.smooth}
          >
            <p className="text-sm text-text-muted mb-2">
              Gemma matched "{rawText}" →
            </p>
            <p className="text-lg text-text-primary font-semibold">
              📚 {intentResult.matched_title}
              {intentResult.confidence === "low" && (
                <span className="text-sm text-text-muted font-normal ml-2">
                  (best guess)
                </span>
              )}
            </p>
            <p className="text-xs text-text-muted mt-0.5">
              CIP {intentResult.matched_cip}
            </p>

            {intentResult.careers_preview.length > 0 && (
              <div className="mt-3">
                <p className="text-sm text-text-secondary mb-1">
                  Graduates typically become:
                </p>
                <ul className="space-y-0.5">
                  {intentResult.careers_preview.slice(0, 5).map((career) => (
                    <li
                      key={career}
                      className="text-sm text-text-secondary pl-3"
                    >
                      • {career}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {intentResult.audit_flag === "playful_warning" &&
              intentResult.audit_message && (
                <p className="mt-3 text-sm text-accent-caution">
                  {intentResult.audit_message}
                </p>
              )}

            <div className="mt-4 flex gap-3 flex-col mobile:flex-row">
              <button
                onClick={handleConfirm}
                className="flex-1 bg-accent-thrive text-text-primary font-semibold py-2.5 px-4 rounded-bp-md cursor-pointer hover:shadow-glow-thrive transition-shadow duration-normal"
              >
                ✓ That's right
              </button>
              <button
                onClick={handleNotQuite}
                className="flex-1 bg-bp-surface text-text-secondary py-2.5 px-4 rounded-bp-md cursor-pointer hover:bg-bp-mid transition-colors duration-fast"
              >
                ✎ Not quite
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Audit fail */}
      <AnimatePresence>
        {phase === "audit_fail" && intentResult?.audit_message && (
          <motion.div
            className="mt-4 bg-bp-raised rounded-bp-lg p-5 border border-accent-caution/30"
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
              className="mt-3 bg-accent-caution text-text-inverse font-semibold py-2 px-4 rounded-bp-md cursor-pointer"
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
            className="mt-4 bg-bp-raised rounded-bp-lg p-5 border border-border-subtle"
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
                className="flex-1 bg-bp-surface text-text-primary font-body text-body px-4 py-2.5 rounded-bp-md border border-border-subtle focus:border-accent-insight focus:outline-none transition-colors duration-normal placeholder:text-text-muted"
                aria-label="Clarify your major choice"
              />
              <button
                onClick={handleClarifySubmit}
                disabled={!clarifyText.trim()}
                className="bg-accent-thrive text-text-primary font-semibold py-2.5 px-4 rounded-bp-md cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
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
    <ul className="max-h-[240px] overflow-y-auto space-y-0.5 rounded-bp-md border border-border-subtle bg-bp-surface">
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
