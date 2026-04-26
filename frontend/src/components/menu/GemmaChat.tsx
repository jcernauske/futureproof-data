import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";
import { sendChat, type ChatHistoryItem, type BuildSummary } from "@/api/menu";
import { ChatMessage } from "@/components/menu/ChatMessage";
import { useProfileStore } from "@/store/profileStore";
import { useT } from "@/i18n/useT";

interface GemmaChatProps {
  open: boolean;
  build: BuildSummary | null;
  onClose: () => void;
}

const STARTERS = [
  "What internships should I look for?",
  "Is this career better in-state or out-of-state?",
  "What if I add a minor?",
];

export function GemmaChat({ open, build, onClose }: GemmaChatProps) {
  const t = useT();
  const [history, setHistory] = useState<ChatHistoryItem[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  // Bumps on every panel close (and unmount) so in-flight sendChat
  // resolutions know they're stale and skip their state writes.
  const sessionRef = useRef(0);

  // Reset conversation when the panel closes (chat is ephemeral by spec).
  useEffect(() => {
    if (!open) {
      sessionRef.current += 1;
      setHistory([]);
      setDraft("");
      setError(null);
      setSending(false);
    }
  }, [open]);

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

  async function submit(message: string) {
    if (!build || !message.trim() || sending) return;
    const trimmed = message.trim();
    setDraft("");
    setError(null);

    const userMsg: ChatHistoryItem = { role: "user", content: trimmed };
    const priorHistory = history;
    const nextHistory = [...priorHistory, userMsg];
    setHistory(nextHistory);
    setSending(true);

    const session = sessionRef.current;
    try {
      // Pass the explicit prior-history snapshot rather than relying on
      // the closure-captured `history`, which would be stale if the user
      // races two submissions before the first await resolves.
      const response = await sendChat(
        build.build_id, trimmed, priorHistory,
        useProfileStore.getState().locale,
      );
      if (sessionRef.current !== session) return;
      setHistory([...nextHistory, { role: "assistant", content: response }]);
    } catch (e) {
      if (sessionRef.current !== session) return;
      setError(e instanceof Error ? e.message : "Gemma couldn't respond.");
    } finally {
      if (sessionRef.current === session) setSending(false);
    }
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
                {build && (
                  <span
                    className="font-body text-micro text-text-muted px-2.5 py-1 rounded-sm bg-bp-surface inline-block self-start truncate max-w-full"
                    title={contextLine}
                  >
                    {contextLine}
                  </span>
                )}
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
              {history.length === 0 && !sending && (
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
                    {STARTERS.map((q, i) => (
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

              {history.map((m, i) => (
                <ChatMessage key={i} message={m} />
              ))}

              {sending && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-start gap-2"
                  data-testid="chat-loading"
                >
                  <span
                    aria-hidden
                    className="shrink-0 mt-2 w-6 h-6 rounded-full bg-accent-insight/15 text-accent-insight flex items-center justify-center text-micro"
                  >
                    ✦
                  </span>
                  <div className="px-4 py-3 bg-bp-deep rounded-lg rounded-tl-sm flex items-center gap-1.5">
                    {[0, 1, 2].map((i) => (
                      <motion.span
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-text-secondary"
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{
                          duration: 1.2,
                          repeat: Infinity,
                          delay: i * 0.15,
                        }}
                      />
                    ))}
                  </div>
                </motion.div>
              )}

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
                disabled={!build || sending}
                className="flex-1 h-11 px-4 bg-bp-deep border border-border rounded-md font-body text-body text-text-primary placeholder:text-text-muted focus:border-accent-info focus:outline-none focus:shadow-[0_0_0_3px_rgba(123,184,224,0.15)] transition-all duration-normal"
              />
              <button
                type="submit"
                data-testid="btn-chat-send"
                aria-label="Send message"
                disabled={!draft.trim() || sending || !build}
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
