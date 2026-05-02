import { useCallback, useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";
import { useT } from "@/i18n/useT";

export type CompanionMode = "peeked" | "open" | "focus";

export const RAIL_WIDTH_PEEKED = 64;
export const RAIL_WIDTH_OPEN = 440;

/**
 * Computes the focus-mode rail width from the current viewport.
 * `min(720px, 60vw)` — generous enough for serious chat, capped so
 * the tree never disappears entirely. Re-evaluated on resize.
 */
export function focusWidth(viewportWidth: number): number {
  return Math.min(720, Math.round(viewportWidth * 0.6));
}

/**
 * Map a mode → live width in pixels. Caller passes viewport width
 * because focus is viewport-relative.
 */
export function railWidth(mode: CompanionMode, viewportWidth: number): number {
  switch (mode) {
    case "peeked":
      return RAIL_WIDTH_PEEKED;
    case "open":
      return RAIL_WIDTH_OPEN;
    case "focus":
      return focusWidth(viewportWidth);
  }
}

interface CompanionRailProps {
  mode: CompanionMode;
  onModeChange: (next: CompanionMode) => void;
  /** Title shown rotated 90° on the peek strip. */
  peekTitle: string;
  /** True while Gemma has unread output the user hasn't seen. */
  hasUnread?: boolean;
  /** Fires once the rail has finished animating to a new width — used by the
   *  tree pane to re-fit React Flow. */
  onWidthSettle?: (width: number) => void;
  /** Header content (Save & Share, back link). */
  headerSlot: React.ReactNode;
  /** Body content (selected card + chat). Rendered when mode !== peeked. */
  children: React.ReactNode;
}

/**
 * Right-edge slide-over rail housing the SelectedNodeCard + Ask Gemma
 * chat on desktop. Three states: peeked (~64px chevron strip), open
 * (440px), focus (~720px / 60vw, with tree dimmed underneath). Designed
 * by @fp-design-visionary 2026-05-01 — see §3 of
 * `feature-future-companion-rail.md` (proposal-tier spec).
 *
 * The rail does NOT cover the tree at any state — even in focus mode
 * the tree stays visible behind a 40% scrim so the student keeps
 * spatial context. Mobile uses FutureChatSheet; this is desktop-only.
 */
export function CompanionRail({
  mode,
  onModeChange,
  peekTitle,
  hasUnread,
  onWidthSettle,
  headerSlot,
  children,
}: CompanionRailProps) {
  const t = useT();
  const reducedMotion = useReducedMotion() ?? false;

  const [viewportWidth, setViewportWidth] = useState(() =>
    typeof window === "undefined" ? 1280 : window.innerWidth,
  );
  useEffect(() => {
    const update = () => setViewportWidth(window.innerWidth);
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  const width = railWidth(mode, viewportWidth);
  const lastSettledWidth = useRef<number | null>(null);

  // Notify parent whenever the rail finishes animating to a new width.
  // The tree pane subscribes to this to re-fit React Flow.
  const handleAnimationComplete = useCallback(() => {
    if (lastSettledWidth.current !== width) {
      lastSettledWidth.current = width;
      onWidthSettle?.(width);
    }
  }, [width, onWidthSettle]);

  const cyclePeekedOpen = useCallback(() => {
    onModeChange(mode === "peeked" ? "open" : "peeked");
  }, [mode, onModeChange]);

  const cycleOpenFocus = useCallback(() => {
    if (mode === "focus") onModeChange("open");
    else onModeChange("focus");
  }, [mode, onModeChange]);

  const collapseOne = useCallback(() => {
    if (mode === "focus") onModeChange("open");
    else if (mode === "open") onModeChange("peeked");
  }, [mode, onModeChange]);

  // Keyboard shortcuts: Cmd+/ toggle peeked↔open; Cmd+. toggle focus;
  // Esc collapse one level. Don't fire while the user is typing in an
  // input/textarea (chat textarea would steal Esc otherwise).
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const isTyping =
        !!target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable);
      if (e.metaKey && !e.shiftKey && !e.altKey && !e.ctrlKey) {
        if (e.key === "/") {
          e.preventDefault();
          cyclePeekedOpen();
          return;
        }
        if (e.key === ".") {
          e.preventDefault();
          cycleOpenFocus();
          return;
        }
      }
      if (e.key === "Escape" && mode !== "peeked" && !isTyping) {
        e.preventDefault();
        collapseOne();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [mode, cyclePeekedOpen, cycleOpenFocus, collapseOne]);

  const transition = reducedMotion ? { duration: 0.12 } : springs.cozy;

  return (
    <>
      {/* Focus-mode scrim sits over the tree, dimming it but keeping
       *   it visible. Click to collapse back to open. */}
      {mode === "focus" && (
        <motion.div
          aria-hidden="true"
          className="fixed inset-0 z-[40] cursor-pointer"
          style={{ background: "rgba(15, 17, 41, 0.4)" }}
          initial={reducedMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18, ease: "easeOut" }}
          onClick={() => onModeChange("open")}
          data-testid="companion-rail-scrim"
        />
      )}
      <motion.aside
        data-testid="companion-rail"
        data-mode={mode}
        aria-label={t("future.companion.aria")}
        className="fixed right-0 top-14 z-[50] flex flex-row bg-bp-mid border-l border-border-default shadow-lg"
        style={{
          height: "calc(100vh - 56px)",
        }}
        initial={false}
        animate={{ width }}
        transition={transition}
        onAnimationComplete={handleAnimationComplete}
      >
        {/* Peek strip — always present, sits as the leftmost 64px. */}
        <button
          type="button"
          data-testid="companion-rail-peek"
          aria-label={
            mode === "peeked"
              ? t("future.companion.openAria")
              : t("future.companion.peekAria")
          }
          aria-expanded={mode !== "peeked"}
          onClick={cyclePeekedOpen}
          className="relative flex-shrink-0 flex flex-col items-center justify-between py-4 cursor-pointer bg-transparent border-0 hover:bg-bp-surface/40 transition-colors"
          style={{ width: RAIL_WIDTH_PEEKED }}
        >
          {/* Top: chevron toggle + unread dot */}
          <span
            aria-hidden="true"
            className="relative w-8 h-8 flex items-center justify-center text-text-secondary"
          >
            <span className="font-data text-[18px] leading-none select-none">
              {mode === "peeked" ? "‹" : "›"}
            </span>
            {hasUnread && mode === "peeked" && (
              <span
                data-testid="companion-rail-unread-dot"
                className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-accent-info shadow-[0_0_6px_rgba(123,184,224,0.7)]"
              />
            )}
          </span>
          {/* Middle: rotated title (only when peeked) */}
          {mode === "peeked" && peekTitle && (
            <span
              className="font-display font-semibold text-small text-text-secondary whitespace-nowrap select-none overflow-hidden"
              style={{
                writingMode: "vertical-rl",
                transform: "rotate(180deg)",
                maxHeight: "calc(100vh - 56px - 120px)",
                textOverflow: "ellipsis",
              }}
            >
              {peekTitle}
            </span>
          )}
          {/* Bottom: focus toggle (only meaningful when not peeked) */}
          {mode !== "peeked" && (
            <span
              role="button"
              tabIndex={0}
              aria-label={
                mode === "focus"
                  ? t("future.companion.exitFocusAria")
                  : t("future.companion.enterFocusAria")
              }
              onClick={(e) => {
                e.stopPropagation();
                cycleOpenFocus();
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  e.stopPropagation();
                  cycleOpenFocus();
                }
              }}
              className="font-data text-[14px] leading-none text-text-muted hover:text-accent-info cursor-pointer select-none px-2 py-1 rounded"
            >
              {mode === "focus" ? "⤡" : "⤢"}
            </span>
          )}
        </button>

        {/* Body — header + scrollable content. Hidden in peeked mode. */}
        {mode !== "peeked" && (
          <div className="flex-1 min-w-0 flex flex-col">
            <header className="flex-shrink-0 px-4 py-3 border-b border-border-subtle bg-bp-surface/50">
              {headerSlot}
            </header>
            <div
              className="flex-1 overflow-y-auto px-4 py-3"
              data-testid="companion-rail-body"
            >
              {children}
            </div>
          </div>
        )}
      </motion.aside>
    </>
  );
}
