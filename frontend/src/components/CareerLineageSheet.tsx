import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  AnimatePresence,
  motion,
  useMotionValue,
  useReducedMotion,
} from "framer-motion";
import type { PanInfo } from "framer-motion";
import { getBranchesForSoc } from "@/api/tree";
import { askCareerPickChip } from "@/api/careerPick";
import { AskGemmaChipRow } from "@/components/AskGemmaChipRow";
import { AskGemmaResponseCard } from "@/components/AskGemmaResponseCard";
import { BranchChip } from "@/components/BranchChip";
import { GemmaStar } from "@/components/ui/GemmaStar";
import { GemmaThinking } from "@/components/ui/GemmaThinking";
import {
  sheetDragElastic,
  sheetFlingVelocity,
  sheetSnap,
  stagger,
  staggerContainer,
  staggerItem,
} from "@/styles/motion";
import type { CareerBranch, CareerOutcome } from "@/types/build";
import type {
  AskCareerPickResponse,
  CareerPickChip,
} from "@/types/careerPick";

export type SheetDetent = "compact" | "medium" | "large";

interface CareerLineageSheetProps {
  /** SOC to fetch branches for. When null, the sheet shows its empty state. */
  soc: string | null;
  /** The CareerOutcome the student clicked to populate the sheet. */
  career: CareerOutcome | null;
  /** Current detent — controlled from CareerPickScreen. */
  detent: SheetDetent;
  /** Called on drag / chevron / arrow-key detent change. */
  onDetentChange: (next: SheetDetent) => void;
  /** Preloaded chip set from GET /career-pick/chips. Empty array while loading. */
  chips: CareerPickChip[];
  /** Context fields forwarded to POST /career-pick/ask on chip click. */
  askContext: { cipcode: string; majorText: string; socCodes: string[] };
}

const DETENT_ORDER: SheetDetent[] = ["compact", "medium", "large"];
const DETENT_INDEX: Record<SheetDetent, number> = {
  compact: 0,
  medium: 1,
  large: 2,
};
const DETENT_LABEL: Record<SheetDetent, string> = {
  compact: "compact",
  medium: "medium",
  large: "expanded",
};

const DETENT_VH: Record<SheetDetent, { desktop: number; mobile: number }> = {
  compact: { desktop: 0.33, mobile: 0.45 },
  medium: { desktop: 0.5, mobile: 0.6 },
  large: { desktop: 0.85, mobile: 0.88 },
};

function useViewportHeight(): number {
  const [vh, setVh] = useState(() =>
    typeof window === "undefined" ? 800 : window.innerHeight,
  );
  useEffect(() => {
    if (typeof window === "undefined") return;
    const onResize = () => setVh(window.innerHeight);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return vh;
}

function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() =>
    typeof window === "undefined" ? false : window.innerWidth < 768,
  );
  useEffect(() => {
    if (typeof window === "undefined") return;
    const onResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return isMobile;
}

function detentHeight(
  detent: SheetDetent,
  vh: number,
  mobile: boolean,
): number {
  const fraction = mobile
    ? DETENT_VH[detent].mobile
    : DETENT_VH[detent].desktop;
  return Math.round(vh * fraction);
}

/**
 * Pure resolver — exported for testing the drag-end snap math without
 * needing to drive a real pointer gesture through Framer Motion.
 */
export function resolveDetent(args: {
  current: SheetDetent;
  offsetY: number;
  velocityY: number;
  vh: number;
  mobile: boolean;
}): SheetDetent {
  const { current, offsetY, velocityY, vh, mobile } = args;
  const currentHeight = detentHeight(current, vh, mobile);
  const newHeight = currentHeight - offsetY;

  // Fling velocity: a sharp flick promotes/demotes one step even if
  // the student didn't cross the midpoint.
  if (velocityY < -sheetFlingVelocity) {
    // Dragging up fast → raise.
    const idx = Math.min(DETENT_INDEX[current] + 1, 2);
    return DETENT_ORDER[idx] as SheetDetent;
  }
  if (velocityY > sheetFlingVelocity) {
    const idx = Math.max(DETENT_INDEX[current] - 1, 0);
    return DETENT_ORDER[idx] as SheetDetent;
  }

  // Pick the nearest detent by height.
  let nearest: SheetDetent = "compact";
  let bestDelta = Infinity;
  for (const candidate of DETENT_ORDER) {
    const h = detentHeight(candidate, vh, mobile);
    const delta = Math.abs(h - newHeight);
    if (delta < bestDelta) {
      bestDelta = delta;
      nearest = candidate;
    }
  }
  return nearest;
}

function ChevronUp() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="18 15 12 9 6 15" />
    </svg>
  );
}

function ChevronDown() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function ChevronRightGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="text-text-muted"
    >
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

function currencyOrBlank(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "";
  if (value <= 0) return "";
  return `$${Math.round(value / 1000)}k`;
}

export function CareerLineageSheet({
  soc,
  career,
  detent,
  onDetentChange,
  chips,
  askContext,
}: CareerLineageSheetProps) {
  const reducedMotion = useReducedMotion() ?? false;
  const vh = useViewportHeight();
  const mobile = useIsMobile();
  const [branches, setBranches] = useState<CareerBranch[]>([]);
  const [branchesLoading, setBranchesLoading] = useState(false);
  const [branchesError, setBranchesError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [activeChipId, setActiveChipId] = useState<string | null>(null);
  const [answer, setAnswer] = useState<string | null>(null);
  const [answerLoading, setAnswerLoading] = useState(false);

  const elevationHintId = useId();
  const titleId = useId();
  const lastAskCtrl = useRef<AbortController | null>(null);
  // Token-based cancellation for branch fetches; AbortController doesn't
  // flow through the mock so we track generation via a ref.
  const fetchGen = useRef(0);

  const height = detentHeight(detent, vh, mobile);
  const y = useMotionValue(0);

  // Reset drag offset when detent changes externally.
  useEffect(() => {
    y.set(0);
  }, [detent, y]);

  // Branch fetch lifecycle — cancel in-flight on SOC change.
  useEffect(() => {
    if (soc === null) {
      setBranches([]);
      setBranchesError(null);
      setBranchesLoading(false);
      return;
    }
    const thisGen = ++fetchGen.current;
    setBranchesLoading(true);
    setBranchesError(null);
    getBranchesForSoc(soc)
      .then((result) => {
        if (fetchGen.current !== thisGen) return;
        setBranches(result);
        setBranchesLoading(false);
      })
      .catch((err: unknown) => {
        if (fetchGen.current !== thisGen) return;
        const message =
          err instanceof Error ? err.message : "Couldn't load the lineage.";
        setBranchesError(message);
        setBranchesLoading(false);
      });
    return () => {
      // marker for the next call; the stale response guards on fetchGen
    };
  }, [soc, retryKey]);

  const handleDragEnd = useCallback(
    (_e: unknown, info: PanInfo) => {
      const next = resolveDetent({
        current: detent,
        offsetY: info.offset.y,
        velocityY: info.velocity.y,
        vh,
        mobile,
      });
      y.set(0);
      if (next !== detent) onDetentChange(next);
    },
    [detent, vh, mobile, onDetentChange, y],
  );

  const stepDetent = useCallback(
    (direction: 1 | -1) => {
      const idx = DETENT_INDEX[detent];
      const nextIdx = Math.max(0, Math.min(2, idx + direction));
      const next = DETENT_ORDER[nextIdx] as SheetDetent;
      if (next !== detent) onDetentChange(next);
    },
    [detent, onDetentChange],
  );

  const onHandleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      switch (event.key) {
        case "ArrowUp":
        case "PageUp":
          event.preventDefault();
          stepDetent(1);
          break;
        case "ArrowDown":
        case "PageDown":
          event.preventDefault();
          stepDetent(-1);
          break;
        case "Home":
          event.preventDefault();
          onDetentChange("compact");
          break;
        case "End":
          event.preventDefault();
          onDetentChange("large");
          break;
        default:
          break;
      }
    },
    [stepDetent, onDetentChange],
  );

  const handleChipClick = useCallback(
    (chip: CareerPickChip) => {
      setActiveChipId(chip.id);
      setAnswer(null);
      setAnswerLoading(true);
      if (detent === "compact") onDetentChange("medium");

      // Abort any in-flight chip call (no AbortController support in fetch
      // wrapper — rely on a generational token via ref instead).
      lastAskCtrl.current?.abort?.();
      const ctrl =
        typeof AbortController !== "undefined" ? new AbortController() : null;
      lastAskCtrl.current = ctrl;

      askCareerPickChip({
        chipId: chip.id,
        cipcode: askContext.cipcode,
        majorText: askContext.majorText,
        socCodes: askContext.socCodes,
        selectedSoc: soc,
        terminalTitle: chip.terminal_title,
      })
        .then((response: AskCareerPickResponse) => {
          if (ctrl && ctrl.signal.aborted) return;
          setAnswer(response.answer);
          setAnswerLoading(false);
        })
        .catch((err: unknown) => {
          if (ctrl && ctrl.signal.aborted) return;
          const message =
            err instanceof Error ? err.message : "Gemma couldn't answer.";
          setAnswer(message);
          setAnswerLoading(false);
        });
    },
    [askContext, soc, detent, onDetentChange],
  );

  const handleCloseResponse = useCallback(() => {
    setActiveChipId(null);
    setAnswer(null);
    setAnswerLoading(false);
  }, []);

  const handleRegenerate = useCallback(() => {
    if (!activeChipId) return;
    const chip = chips.find((c) => c.id === activeChipId);
    if (!chip) return;
    handleChipClick(chip);
  }, [activeChipId, chips, handleChipClick]);

  const detentLabel = DETENT_LABEL[detent];
  const detentIndex = DETENT_INDEX[detent];
  const upDisabled = detentIndex === 2;
  const downDisabled = detentIndex === 0;
  const responseVisible = detent !== "compact" && activeChipId !== null;
  const emptyState = soc === null;

  const dragConstraints = useMemo(
    () => ({
      top: -(detentHeight("large", vh, mobile) - height),
      bottom: detentHeight("large", vh, mobile) - height,
    }),
    [vh, mobile, height],
  );

  return (
    <motion.div
      role="dialog"
      aria-modal="false"
      aria-label={`Lineage panel — ${detentLabel}`}
      aria-describedby={titleId}
      className="
        fixed inset-x-0 bottom-0 z-40
        bg-bp-mid border-t border-border
        rounded-t-[20px]
        shadow-[0_-8px_32px_rgba(27,29,48,0.7),inset_0_40px_80px_-40px_rgba(184,169,232,0.12)]
        overflow-hidden
      "
      style={{ height, y }}
      animate={{ height }}
      transition={reducedMotion ? { duration: 0 } : sheetSnap}
    >
      {/* Zone 1: Drag handle row */}
      <div
        role="slider"
        aria-label="Lineage panel height — drag or use arrow keys to resize"
        aria-orientation="vertical"
        aria-valuemin={0}
        aria-valuemax={2}
        aria-valuenow={detentIndex}
        aria-valuetext={detentLabel}
        tabIndex={0}
        onKeyDown={onHandleKeyDown}
        className="
          relative w-full h-10 cursor-grab active:cursor-grabbing
          focus-visible:outline-none focus-visible:ring-2
          focus-visible:ring-[color:var(--color-focus-ring)]
        "
      >
        <motion.div
          drag="y"
          dragConstraints={dragConstraints}
          dragElastic={reducedMotion ? 0 : sheetDragElastic}
          onDragEnd={handleDragEnd}
          style={{ y }}
          className="absolute inset-0"
        >
          <div className="flex items-center justify-center w-full h-full">
            <span
              aria-hidden="true"
              className="w-10 h-1 rounded-full bg-text-muted/40"
            />
          </div>
        </motion.div>
        <div className="absolute right-4 top-1/2 -translate-y-1/2 flex flex-col gap-1 pointer-events-auto z-10">
          <button
            type="button"
            aria-label="Raise lineage panel"
            aria-disabled={upDisabled}
            disabled={upDisabled}
            onClick={() => stepDetent(1)}
            className={`
              w-8 h-8 rounded-full inline-flex items-center justify-center
              transition-colors duration-normal
              focus-visible:outline-none focus-visible:ring-2
              focus-visible:ring-[color:var(--color-focus-ring)]
              ${
                upDisabled
                  ? "bg-bp-surface/50 text-text-muted cursor-not-allowed"
                  : "bg-bp-surface text-text-secondary hover:bg-bp-raised hover:text-text-primary cursor-pointer"
              }
            `}
          >
            <ChevronUp />
          </button>
          <button
            type="button"
            aria-label="Lower lineage panel"
            aria-disabled={downDisabled}
            disabled={downDisabled}
            onClick={() => stepDetent(-1)}
            className={`
              w-8 h-8 rounded-full inline-flex items-center justify-center
              transition-colors duration-normal
              focus-visible:outline-none focus-visible:ring-2
              focus-visible:ring-[color:var(--color-focus-ring)]
              ${
                downDisabled
                  ? "bg-bp-surface/50 text-text-muted cursor-not-allowed"
                  : "bg-bp-surface text-text-secondary hover:bg-bp-raised hover:text-text-primary cursor-pointer"
              }
            `}
          >
            <ChevronDown />
          </button>
        </div>
      </div>

      {/* Zone 2: Title row */}
      <div className="px-6 tablet:px-8 py-2">
        <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-info mb-1">
          Where this career leads
        </p>
        <div className="flex items-center gap-3 flex-wrap">
          <h2
            id={titleId}
            aria-live="polite"
            aria-atomic="true"
            className="font-body text-subheading font-bold text-text-primary"
          >
            {career?.occupation_title ?? "—"}
          </h2>
          {branchesLoading && soc !== null ? (
            <GemmaThinking message="Gemma is loading branches…" size={20} />
          ) : null}
        </div>
      </div>

      {/* Zone 3: Lineage flow */}
      <div className="py-2">
        {emptyState ? (
          <div className="py-8 px-6 text-center font-body text-body text-text-muted italic">
            Pick a career path above to see where it leads.
          </div>
        ) : branchesError ? (
          <div
            role="alert"
            className="
              mx-6 tablet:mx-8 p-4 rounded-lg
              bg-[color:var(--color-state-error)]
              border border-[rgba(244,169,126,0.35)]
              flex items-center justify-between gap-4
            "
          >
            <p className="font-body text-body text-text-primary">
              Couldn't load the lineage. Try again?
            </p>
            <button
              type="button"
              onClick={() => setRetryKey((k) => k + 1)}
              className="
                inline-flex items-center gap-2 h-10 px-4 rounded-lg
                font-body font-bold text-small
                text-accent-info bg-transparent
                hover:bg-white/[0.05]
                focus-visible:outline-none focus-visible:ring-2
                focus-visible:ring-[color:var(--color-focus-ring)]
              "
            >
              Try again
            </button>
          </div>
        ) : branchesLoading ? (
          <div className="flex items-center justify-center py-6">
            <GemmaThinking message="Gemma is loading branches…" />
          </div>
        ) : (
          <motion.div
            className="
              flex items-stretch gap-4 overflow-x-auto overflow-y-hidden
              snap-x snap-mandatory scroll-pl-6 scroll-pr-6
              pl-6 pr-6 tablet:pl-8 tablet:pr-8 py-2
              [mask-image:linear-gradient(to_right,black_92%,transparent)]
            "
            variants={staggerContainer(0, stagger.fast)}
            initial="hidden"
            animate="visible"
          >
            {career ? (
              <motion.article
                aria-label={`Anchor: ${career.occupation_title}`}
                className="
                  shrink-0 min-w-[180px] max-w-[220px] snap-start
                  bg-bp-surface border border-[rgba(125,212,163,0.35)]
                  border-l-[3px] border-l-accent-thrive
                  rounded-xl p-4
                  bg-gradient-to-br from-[rgba(125,212,163,0.10)] to-transparent
                  shadow-[0_0_16px_rgba(125,212,163,0.15)]
                "
              >
                <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-thrive">
                  You are here
                </p>
                <h3 className="mt-1 font-body text-body font-bold text-text-primary line-clamp-2">
                  {career.occupation_title}
                </h3>
                {career.median_annual_wage ? (
                  <p className="mt-2 font-data text-data-sm text-text-secondary">
                    {currencyOrBlank(career.median_annual_wage)}
                  </p>
                ) : null}
              </motion.article>
            ) : null}
            {branches.length > 0 ? (
              <div
                aria-hidden="true"
                className="flex items-center self-center"
              >
                <ChevronRightGlyph />
              </div>
            ) : null}
            {branches.length === 0 && career ? (
              <div className="flex items-center px-4 font-body text-body text-text-muted italic">
                No next-hop data for this career yet.
              </div>
            ) : null}
            {branches.map((branch) => (
              <motion.div key={branch.to_soc} variants={staggerItem}>
                <BranchChip branch={branch} />
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>

      {/* Zone 4: Ask-Gemma chip row */}
      <div className="pt-1 pb-2">
        {activeChipId === null ? (
          <p className="font-body text-small text-text-muted italic pl-6 tablet:pl-8 mb-1">
            Not sure about something? Ask Gemma.
          </p>
        ) : (
          <p
            className="flex items-center gap-2 font-body text-small text-text-muted pl-6 tablet:pl-8 mb-1"
          >
            <GemmaStar size={14} />
            <span>Ask another question.</span>
          </p>
        )}
        <AskGemmaChipRow
          chips={chips}
          activeChipId={activeChipId}
          onChipClick={handleChipClick}
          elevationHintId={elevationHintId}
        />
        <span id={elevationHintId} className="sr-only">
          Gemma thinks this question might be relevant to you based on what
          you searched for.
        </span>
      </div>

      {/* Zone 5: Ask-Gemma response card */}
      <div className="px-6 tablet:px-8 pb-6">
        <AnimatePresence initial={false}>
          {responseVisible ? (
            <AskGemmaResponseCard
              key={activeChipId}
              loading={answerLoading}
              answer={answer}
              onRegenerate={handleRegenerate}
              onClose={handleCloseResponse}
              detent={detent === "large" ? "large" : "medium"}
            />
          ) : null}
        </AnimatePresence>
      </div>

    </motion.div>
  );
}
