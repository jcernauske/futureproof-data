import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";
import {
  askGemmaStream,
  sendChat,
  type AskScope,
  type ChatHistoryItem,
  type BuildSummary,
  type ExplainStatReceipt,
} from "@/api/menu";
import { ChatMessage } from "@/components/menu/ChatMessage";
import { ExplainStatReceiptCard } from "@/components/menu/ExplainStatReceipt";
import { GemmaTrace } from "@/components/menu/GemmaTrace";
import { useProfileStore } from "@/store/profileStore";
import { useT } from "@/i18n/useT";
import type { GemmaTraceEvent } from "@/types/gemmaTrace";
import type { CareerDescription } from "@/types/build";

/**
 * Build a `ChatHistoryItem` for an assistant turn. Discriminates on
 * the response shape: a string lands as a plain-text bubble; an
 * `ExplainStatReceipt` lands as the structured receipt card.
 */
function assistantHistoryItem(
  response: string | ExplainStatReceipt,
): ChatHistoryItem {
  if (typeof response === "string") {
    return { role: "assistant", kind: "text", content: response };
  }
  return { role: "assistant", kind: "receipt", payload: response };
}

/**
 * Per-history-index trace events. Indexed by the index in `history`
 * of the assistant message the trace belongs to. Live events bind to
 * the in-flight assistant turn at `history.length`.
 */
type TraceMap = Map<number, GemmaTraceEvent[]>;

interface GemmaChatProps {
  open: boolean;
  build: BuildSummary | null;
  /**
   * When set, the chat routes to POST /chat/ask with this discriminated
   * scope. When undefined, falls back to the legacy POST /build/{id}/chat
   * path (preserving the MenuScreen "Ask Gemma" entry point's behavior).
   */
  scope?: AskScope;
  /**
   * Pre-computed scope-chip text to render in the header (replaces the
   * legacy contextLine when present). The parent screen owns the
   * mapping per the §3 alias table so the chip never breaches the
   * voice contract.
   */
  chipText?: string;
  /**
   * Presentation variant. ``"slide-in"`` (default) renders the existing
   * right-side panel with backdrop and close button. ``"embedded"``
   * renders inline with no slide-in animation, no backdrop, no close
   * button — chat is always visible inside the parent column.
   */
  variant?: "slide-in" | "embedded";
  /**
   * Optional skeleton hint rendered beneath the typing dots while a
   * response is in flight. Used by the embedded variant on first paint
   * to surface the "Gemma is reading your career path…" line.
   */
  skeletonHint?: string;
  /**
   * Optional opener message — when set and the scope changes, the
   * embedded chat auto-fires this message as the first user turn so the
   * screen can drive the bidirectional binding (BranchTreeScreen).
   * Ignored in slide-in mode.
   */
  openerPrompt?: string;
  /**
   * Notified after every assistant response resolves (success or
   * fallback). Lets the parent screen subscribe to chat output for
   * presentational side-channels like BranchHighlightDriver.
   */
  onAssistantResponse?: (text: string) => void;
  starters?: string[];
  /**
   * Optional structured career-description card rendered above the chat
   * history when ``scope.kind === "career"``. Three states:
   *   - null / undefined → not requested → no card.
   *   - "loading"        → render skeleton.
   *   - "error"          → omit card; freeform chat opens as today.
   *   - CareerDescription → render populated header card.
   * Owned by the parent screen (sparkle click handler in
   * SetYourCourseScreen).
   */
  careerDescription?: CareerDescription | "loading" | "error" | null;
  /** Optional close handler. Required for slide-in; ignored in embedded mode. */
  onClose?: () => void;
}

// Pre-baked starter chips. Each one is verified (via curl against
// live Gemma) to fire 2-3 tool calls when tapped, so judges see the
// <GemmaTrace> rail render with multiple rows the moment a chip is
// clicked. Ordered most-likely-tapped first; #5 is the cinematic
// 3-row mixed-icon shot (briefcase + branch + scale).
//
// Geography references are intentionally vague ("a few different
// states", "different cities") — Gemma picks the states herself,
// which keeps the chip set varied rather than mentioning the same
// hardcoded state across multiple chips. See the product partner's
// review of the multi-tool demo set + feature-gemma-trace.md.
const STARTERS = [
  "How would my salary feel in a few different states?",
  "Where could I live most affordably on this starting salary?",
  "What other careers branch off this one, and which ones have better stats?",
  "What other schools give similar results for less cost, and how does cost of living compare in those states?",
  "What are the three highest-paying related careers, and what would I make in those roles in different cities?",
  "What does this work look like 10 years in versus today, and which related careers pay more?",
  "Tell me what this career pays nationally, what other careers branch off it, and how my salary would feel in a few different states.",
];

export function GemmaChat({
  open,
  build,
  scope,
  chipText,
  variant = "slide-in",
  skeletonHint,
  openerPrompt,
  starters: startersProp,
  onAssistantResponse,
  careerDescription,
  onClose,
}: GemmaChatProps) {
  const t = useT();
  const [history, setHistory] = useState<ChatHistoryItem[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Per-assistant-turn trace events. Live trace for the in-flight
  // turn lives at `history.length` while sending; once the answer
  // resolves, the trace stays bound to its assistant message index.
  const [traces, setTraces] = useState<TraceMap>(() => new Map());
  const liveEventsRef = useRef<GemmaTraceEvent[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  // Bumps on every panel close (and unmount) so in-flight sendChat
  // resolutions know they're stale and skip their state writes.
  // In embedded mode, also bumps on every ``scope.target_id`` change
  // so a stale opener for the prior branch is dropped on arrival
  // (fp-architect Concerns: latency budget on the rapid-click path).
  const sessionRef = useRef(0);
  const embedded = variant === "embedded";
  const scopeTargetKey = scope ? `${scope.kind}:${scope.target_id ?? ""}` : "";

  // Reset conversation when the panel closes (chat is ephemeral by spec).
  // In embedded mode the panel is always "open" — bump on scope change
  // instead so rapid branch switches drop stale openers.
  useEffect(() => {
    if (embedded) {
      sessionRef.current += 1;
      setHistory([]);
      setDraft("");
      setError(null);
      setSending(false);
      setTraces(new Map());
      liveEventsRef.current = [];
      return;
    }
    if (!open) {
      sessionRef.current += 1;
      setHistory([]);
      setDraft("");
      setError(null);
      setSending(false);
      setTraces(new Map());
      liveEventsRef.current = [];
    }
  }, [open, embedded, scopeTargetKey]);

  useEffect(() => {
    return () => {
      sessionRef.current += 1;
    };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history, sending]);

  const wlcd = build
    ? `${build.wins}W/${build.losses}L${build.draws ? `/${build.draws}D` : ""}`
    : "";
  const contextLine = build
    ? `Context: ${build.school_name} · ${build.career_title} · ${wlcd}`
    : "";

  // Auto-fire the opener when:
  // - embedded mode: on every scope change (panel always open).
  // - slide-in mode: when the panel transitions open with a scope +
  //   opener. The close-effect above wipes history on open=false, so
  //   reopen starts a fresh session and the opener fires once.
  // The opener prompt is sent over the wire but never shown to the
  // student — only the assistant response renders.
  useEffect(() => {
    if (!scope || !openerPrompt) return;
    if (!embedded && !open) return;
    let cancelled = false;
    const session = sessionRef.current;
    setSending(true);
    setError(null);
    // Live events bind to assistant index 0 (no prior turns in opener).
    liveEventsRef.current = [];
    setTraces((prev) => {
      const next = new Map(prev);
      next.set(0, []);
      return next;
    });
    (async () => {
      try {
        const locale = useProfileStore.getState().locale;
        const result = await askGemmaStream(
          scope,
          openerPrompt,
          [],
          (event) => {
            if (cancelled || sessionRef.current !== session) return;
            liveEventsRef.current = [...liveEventsRef.current, event];
            const snapshot = liveEventsRef.current;
            setTraces((prev) => {
              const next = new Map(prev);
              next.set(0, snapshot);
              return next;
            });
          },
          locale,
        );
        if (cancelled || sessionRef.current !== session) return;
        setHistory([assistantHistoryItem(result.response)]);
        onAssistantResponse?.(
          typeof result.response === "string"
            ? result.response
            : result.response.one_liner,
        );
      } catch (e) {
        if (cancelled || sessionRef.current !== session) return;
        setError(
          e instanceof Error ? e.message : "Gemma couldn't respond.",
        );
      } finally {
        if (!cancelled && sessionRef.current === session) {
          setSending(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // scopeTargetKey re-fires on every scope.target_id change.
    // openerPrompt is included so the screen can re-trigger by passing
    // a new prompt without changing scope. `open` is included so
    // slide-in mode fires on close→open transitions.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [embedded, open, scopeTargetKey, openerPrompt]);

  async function submit(message: string) {
    if (!message.trim() || sending) return;
    // The legacy sendChat path needs a build; the scoped askGemma path
    // does not (compare scope has N build_ids).
    if (!scope && !build) return;
    const trimmed = message.trim();
    setDraft("");
    setError(null);

    const userMsg: ChatHistoryItem = {
      role: "user",
      kind: "text",
      content: trimmed,
    };
    const priorHistory = history;
    const nextHistory = [...priorHistory, userMsg];
    setHistory(nextHistory);
    setSending(true);

    // Index of the assistant message that the live trace will bind to
    // once the answer resolves. We mount the trace UI live at this
    // index while sending.
    const assistantIdx = nextHistory.length;
    liveEventsRef.current = [];
    setTraces((prev) => {
      const next = new Map(prev);
      next.set(assistantIdx, []);
      return next;
    });

    const session = sessionRef.current;
    try {
      // Pass the explicit prior-history snapshot rather than relying on
      // the closure-captured `history`, which would be stale if the user
      // races two submissions before the first await resolves.
      const locale = useProfileStore.getState().locale;
      let response: string | ExplainStatReceipt;
      if (scope) {
        const result = await askGemmaStream(
          scope,
          trimmed,
          priorHistory,
          (event) => {
            if (sessionRef.current !== session) return;
            liveEventsRef.current = [...liveEventsRef.current, event];
            const snapshot = liveEventsRef.current;
            setTraces((prev) => {
              const next = new Map(prev);
              next.set(assistantIdx, snapshot);
              return next;
            });
          },
          locale,
        );
        response = result.response;
      } else if (build) {
        response = await sendChat(build.build_id, trimmed, priorHistory, locale);
      } else {
        return;
      }
      if (sessionRef.current !== session) return;
      setHistory([...nextHistory, assistantHistoryItem(response)]);
      onAssistantResponse?.(
        typeof response === "string" ? response : response.one_liner,
      );
    } catch (e) {
      if (sessionRef.current !== session) return;
      setError(e instanceof Error ? e.message : "Gemma couldn't respond.");
    } finally {
      if (sessionRef.current === session) setSending(false);
    }
  }

  /**
   * Render a chat message paired with its trace (when present). The
   * trace renders ABOVE the assistant message inside the same
   * scrollable feed so reading order matches reasoning order.
   */
  function renderMessageWithTrace(m: ChatHistoryItem, i: number) {
    const events = traces.get(i);
    const showTrace = m.role === "assistant" && events && events.length > 0;
    return (
      <div key={i} className="flex flex-col gap-2">
        {showTrace ? (
          <GemmaTrace events={events!} mode="complete" />
        ) : null}
        {m.kind === "receipt" ? (
          <ExplainStatReceiptCard payload={m.payload} />
        ) : (
          <ChatMessage message={{ role: m.role, content: m.content }} />
        )}
      </div>
    );
  }

  /**
   * Structured "About this career" header card on top of the chat feed
   * for ``scope.kind === "career"``. Three states:
   *   - "loading": skeleton mirroring populated rhythm
   *   - "error":   omit card entirely; freeform chat fills the gap
   *   - CareerDescription: populated header with optional Tier B/C
   *     disclaimer chip below the bullet list
   * Mirrors §3 of feature-career-description-on-pdf.md.
   */
  function renderCareerDescriptionCard(
    desc: CareerDescription | "loading" | "error",
    socCode: string | null | undefined,
  ) {
    if (desc === "error") {
      return null;
    }

    if (desc === "loading") {
      // No skeleton card — the structured layout (title row, summary
      // lines, bullet rhythm) was leaking through as empty formatting
      // before Gemma had anything to show. Render only the small
      // ✦ + typing-dots row so the student knows a response is on its
      // way; the populated card replaces it on resolution.
      return (
        <div
          data-testid="card-career-description-loading"
          role="status"
          aria-live="polite"
          aria-label="Loading career description"
          className="flex items-start gap-2 mb-4"
        >
          <span
            aria-hidden
            className="shrink-0 mt-2 w-6 h-6 rounded-full bg-accent-insight/15 text-accent-insight flex items-center justify-center text-micro"
          >
            ✦
          </span>
          <div className="px-4 py-3 bg-bp-deep rounded-lg rounded-tl-sm flex items-center gap-1.5">
            {[0, 1, 2].map((dotIdx) => (
              <motion.span
                key={dotIdx}
                className="w-1.5 h-1.5 rounded-full bg-text-secondary"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{
                  duration: 1.2,
                  repeat: Infinity,
                  delay: dotIdx * 0.15,
                }}
              />
            ))}
          </div>
        </div>
      );
    }

    // Defensive: bad payloads (test fixtures, API drift) render nothing
    // rather than crashing the chat panel.
    if (
      !desc ||
      typeof desc.summary !== "string" ||
      !Array.isArray(desc.tasks)
    ) {
      return null;
    }

    const occupationTitle = chipText?.replace(/^Asking about: /, "") ?? "";
    const disclaimer =
      desc.anchor_tier === "description_only"
        ? "AI-inferred from the BLS occupation summary."
        : desc.anchor_tier === "title_only"
        ? "AI-inferred from the occupation title only."
        : null;

    return (
      <div
        data-testid="card-career-description"
        className="rounded-xl bg-bp-surface border border-border-subtle p-5 mb-4 shadow-sm"
      >
        <div className="flex items-center gap-2.5 mb-4">
          <span aria-hidden className="text-accent-insight text-base shrink-0">✦</span>
          <h2
            id="career-desc-title"
            className="font-display text-subheading text-text-primary font-bold leading-tight truncate"
          >
            {occupationTitle || "About this career"}
          </h2>
          {socCode ? (
            <span
              data-testid="career-desc-soc"
              aria-label={`Standard Occupational Classification code ${socCode}`}
              className="ml-auto inline-flex items-center px-2.5 py-1 rounded-md bg-bp-mid border border-border-subtle font-data text-micro text-text-secondary shrink-0"
            >
              {socCode}
            </span>
          ) : null}
        </div>
        <p className="font-body text-body text-text-secondary leading-normal mb-4">
          {desc.summary}
        </p>
        <p className="font-body text-micro font-semibold text-text-muted uppercase tracking-[0.08em] mb-2">
          Day-to-day
        </p>
        <ul
          role="list"
          data-testid="career-desc-tasks"
          aria-label={`Day-to-day tasks for ${occupationTitle || "this career"}`}
          className="flex flex-col gap-2"
        >
          {desc.tasks.map((task, i) => (
            <li key={i} className="flex items-start gap-3">
              <span aria-hidden className="text-accent-insight text-base leading-tight pt-0.5">•</span>
              <span className="font-body text-small text-text-secondary leading-relaxed">
                {task}
              </span>
            </li>
          ))}
        </ul>
        {disclaimer ? (
          <span
            data-testid="career-desc-disclaimer"
            aria-label={`Source disclosure: ${disclaimer}`}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-bp-deep border border-border-subtle font-body text-micro italic text-text-muted self-start mt-3"
          >
            <span aria-hidden className="text-accent-insight">✦</span>
            {disclaimer}
          </span>
        ) : null}
      </div>
    );
  }

  /**
   * Render the in-flight loading row including any live trace events
   * for the current sending turn. Pulled out so the JSX stays flat
   * inside the embedded + slide-in returns — Vite's babel parser
   * trips on the inline-IIFE-returning-fragment pattern in some
   * toolchain versions.
   */
  function renderSendingRow(opts?: { compact?: boolean }) {
    const liveEvents = traces.get(history.length);
    const hasLiveTrace = !!liveEvents && liveEvents.length > 0;
    const wrapperMotion = opts?.compact
      ? { initial: { opacity: 0 }, animate: { opacity: 1 } }
      : {
          initial: { opacity: 0, y: 24 },
          animate: { opacity: 1, y: 0 },
          transition: springs.smooth,
        };
    return (
      <>
        {hasLiveTrace ? (
          <GemmaTrace events={liveEvents!} mode="live" />
        ) : null}
        <motion.div
          {...wrapperMotion}
          className={opts?.compact ? "flex items-start gap-2" : "flex flex-col"}
          data-testid={opts?.compact ? "chat-loading" : undefined}
        >
          <div
            className={
              opts?.compact
                ? "contents"
                : "flex items-start gap-2"
            }
            data-testid={opts?.compact ? undefined : "chat-loading"}
          >
            <span
              aria-hidden
              className="shrink-0 mt-2 w-6 h-6 rounded-full bg-accent-insight/15 text-accent-insight flex items-center justify-center text-micro"
            >
              ✦
            </span>
            <div className="px-4 py-3 bg-bp-deep rounded-lg rounded-tl-sm flex items-center gap-1.5">
              {[0, 1, 2].map((dotIdx) => (
                <motion.span
                  key={dotIdx}
                  className="w-1.5 h-1.5 rounded-full bg-text-secondary"
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{
                    duration: 1.2,
                    repeat: Infinity,
                    delay: dotIdx * 0.15,
                  }}
                />
              ))}
            </div>
          </div>
          {!opts?.compact && skeletonHint && (
            <p
              data-testid="skel-chat-opener"
              aria-label="Loading Gemma's read on your career path"
              className="font-body text-small text-text-muted mt-2 ml-9"
            >
              {skeletonHint}
            </p>
          )}
        </motion.div>
      </>
    );
  }

  if (embedded) {
    return (
      <section
        role="region"
        aria-label="Career path conversation with Gemma"
        data-testid="panel-branch-chat"
        className="bg-bp-mid border border-border-subtle rounded-xl flex flex-col h-[70vh] min-h-[400px]"
      >
        <header className="flex items-center justify-between gap-3 px-5 py-4 border-b border-border-subtle">
          <div className="flex flex-col gap-1 min-w-0">
            <h3 className="font-display font-semibold text-subheading text-text-primary">
              Ask Gemma
            </h3>
            {scope && chipText ? (
              <span
                data-testid="chip-chat-scope"
                aria-hidden="true"
                title={chipText}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-bp-surface border border-border-subtle font-body text-micro text-text-secondary self-start max-w-full"
              >
                <span aria-hidden className="text-accent-insight text-micro mr-0.5">
                  ✦
                </span>
                <span className="truncate">{chipText}</span>
              </span>
            ) : null}
          </div>
        </header>

        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-3"
        >
          {scope?.kind === "career" && careerDescription
            ? renderCareerDescriptionCard(careerDescription, scope.target_id)
            : null}

          {history.map((m, i) => renderMessageWithTrace(m, i))}

          {sending && renderSendingRow()}

          {error && (
            <p className="font-body text-small text-accent-alert">{error}</p>
          )}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit(draft);
          }}
          className="border-t border-border-subtle px-5 py-4 flex items-center gap-2"
        >
          <input
            type="text"
            data-testid="input-chat"
            aria-label="Type a question"
            placeholder={t("chat.placeholder")}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            disabled={(!build && !scope) || sending}
            className="flex-1 h-11 px-4 bg-bp-deep border border-border rounded-md font-body text-body text-text-primary placeholder:text-text-muted focus:border-accent-info focus:outline-none focus:shadow-[0_0_0_3px_rgba(123,184,224,0.15)] transition-all duration-normal"
          />
          <button
            type="submit"
            data-testid="btn-chat-send"
            aria-label="Send message"
            disabled={!draft.trim() || sending || (!build && !scope)}
            className={`shrink-0 w-11 h-11 rounded-md flex items-center justify-center font-body text-body-lg transition-colors duration-normal cursor-pointer disabled:cursor-not-allowed ${
              draft.trim() && !sending
                ? "bg-accent-thrive text-text-inverse hover:bg-[#6bc494]"
                : "bg-bp-surface text-text-muted"
            }`}
          >
            ↑
          </button>
        </form>
      </section>
    );
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            key="chat-backdrop"
            className="fixed inset-0 z-[140] bg-bp-void/60 tablet:bg-transparent tablet:pointer-events-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            aria-hidden
          />
          <motion.div
            key="chat-panel"
            role="dialog"
            aria-modal="true"
            aria-label="Ask Gemma about your build"
            data-testid="dialog-chat"
            className="fixed z-[150] bg-bp-mid border-border-subtle flex flex-col
              right-0 top-14 bottom-0 w-full
              tablet:w-[360px] tablet:border-l
              border-t tablet:border-t-0
              tablet:rounded-none rounded-t-xl"
            initial={{ x: 360, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 360, opacity: 0 }}
            transition={springs.smooth}
          >
            <header className="flex items-center justify-between gap-3 px-5 py-4 border-b border-border-subtle">
              <div className="flex flex-col gap-1 min-w-0">
                <h3 className="font-display font-semibold text-subheading text-text-primary">
                  Ask Gemma
                </h3>
                {scope && chipText ? (
                  <span
                    data-testid="chip-chat-scope"
                    aria-hidden="true"
                    title={chipText}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-bp-surface border border-border-subtle font-body text-micro text-text-secondary self-start max-w-full"
                  >
                    <span aria-hidden className="text-accent-insight text-micro mr-0.5">
                      ✦
                    </span>
                    <span className="truncate">{chipText}</span>
                  </span>
                ) : build ? (
                  <span
                    className="font-body text-micro text-text-muted px-2.5 py-1 rounded-sm bg-bp-surface inline-block self-start truncate max-w-full"
                    title={contextLine}
                  >
                    {contextLine}
                  </span>
                ) : null}
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close chat"
                className="shrink-0 w-9 h-9 rounded-full bg-bp-surface hover:bg-bp-raised text-text-primary flex items-center justify-center transition-colors duration-normal cursor-pointer"
              >
                ✕
              </button>
            </header>

            <div
              ref={scrollRef}
              className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-3"
            >
              {scope?.kind === "career" && careerDescription
                ? renderCareerDescriptionCard(careerDescription, scope.target_id)
                : null}

              {history.length === 0 && !sending && !(startersProp && startersProp.length === 0) && (
                <motion.div
                  className="flex flex-col gap-3 mt-6"
                  initial="hidden"
                  animate="visible"
                  variants={{
                    hidden: {},
                    visible: { transition: { staggerChildren: stagger.normal } },
                  }}
                >
                  <p className="font-body text-small text-text-secondary">
                    {t("chat.tryOne")}
                  </p>
                  <div className="flex flex-col gap-2 items-start">
                    {(startersProp && startersProp.length > 0 ? startersProp : STARTERS).map((q, i) => (
                      <motion.button
                        type="button"
                        key={q}
                        data-testid={`btn-starter-${i}`}
                        onClick={() => setDraft(q)}
                        variants={{
                          hidden: { opacity: 0, y: 8 },
                          visible: { opacity: 1, y: 0, transition: springs.smooth },
                        }}
                        className="px-3.5 py-1.5 rounded-full bg-bp-surface border border-border-subtle font-body text-small text-text-secondary hover:text-text-primary hover:bg-bp-raised transition-colors duration-normal cursor-pointer text-left"
                      >
                        {q}
                      </motion.button>
                    ))}
                  </div>
                </motion.div>
              )}

              {history.map((m, i) => renderMessageWithTrace(m, i))}

              {sending && renderSendingRow({ compact: true })}

              {error && (
                <p className="font-body text-small text-accent-alert">{error}</p>
              )}
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                submit(draft);
              }}
              className="border-t border-border-subtle px-5 py-4 flex items-center gap-2"
            >
              <input
                type="text"
                data-testid="input-chat"
                aria-label="Type a question"
                placeholder={t("chat.placeholder")}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                disabled={(!build && !scope) || sending}
                className="flex-1 h-11 px-4 bg-bp-deep border border-border rounded-md font-body text-body text-text-primary placeholder:text-text-muted focus:border-accent-info focus:outline-none focus:shadow-[0_0_0_3px_rgba(123,184,224,0.15)] transition-all duration-normal"
              />
              <button
                type="submit"
                data-testid="btn-chat-send"
                aria-label="Send message"
                disabled={!draft.trim() || sending || (!build && !scope)}
                className={`shrink-0 w-11 h-11 rounded-md flex items-center justify-center font-body text-body-lg transition-colors duration-normal cursor-pointer disabled:cursor-not-allowed ${
                  draft.trim() && !sending
                    ? "bg-accent-thrive text-text-inverse hover:bg-[#6bc494]"
                    : "bg-bp-surface text-text-muted"
                }`}
              >
                ↑
              </button>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
