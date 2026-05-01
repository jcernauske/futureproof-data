import { useEffect, useRef, type ReactNode } from "react";
import { motion, useDragControls, type PanInfo } from "framer-motion";

interface FutureChatSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Latest assistant text — shown collapsed as a peek line. */
  preview?: string | null;
  /** Scope chip text shown next to the handle when collapsed. */
  chipText?: string;
  children: ReactNode;
}

/**
 * Mobile bottom-sheet wrapper for the embedded chat on /future.
 *
 * Collapsed (~12vh): drag handle + scope chip + 1-line preview of the
 * latest Gemma response.
 *
 * Expanded (~75vh): chat fills the sheet body. Tap on the handle row
 * or swipe down on the handle to collapse.
 *
 * The drag is intentionally restricted to the handle — the chat body
 * needs its own scroll, and we don't want React Flow's pan/zoom (which
 * lives behind the sheet) to fight a body-wide drag listener.
 */
export function FutureChatSheet({
  open,
  onOpenChange,
  preview,
  chipText,
  children,
}: FutureChatSheetProps) {
  const dragControls = useDragControls();
  const sheetRef = useRef<HTMLDivElement>(null);

  // visualViewport-aware: when the keyboard pops up, recompute the
  // expanded height so the sheet stays inside the viewport. Mobile
  // keyboard otherwise overlaps the input.
  useEffect(() => {
    if (!open) return;
    const vv = window.visualViewport;
    if (!vv) return;
    const update = () => {
      sheetRef.current?.style.setProperty(
        "--future-sheet-vh",
        `${vv.height}px`,
      );
    };
    update();
    vv.addEventListener("resize", update);
    vv.addEventListener("scroll", update);
    return () => {
      vv.removeEventListener("resize", update);
      vv.removeEventListener("scroll", update);
    };
  }, [open]);

  const handlePointerDown = (e: React.PointerEvent) => {
    dragControls.start(e);
  };

  const handleDragEnd = (_: unknown, info: PanInfo) => {
    if (info.offset.y > 60 || info.velocity.y > 400) {
      onOpenChange(false);
    } else if (info.offset.y < -60 || info.velocity.y < -400) {
      onOpenChange(true);
    }
  };

  return (
    <motion.div
      ref={sheetRef}
      data-testid="future-chat-sheet"
      data-open={open ? "true" : undefined}
      drag="y"
      dragControls={dragControls}
      dragListener={false}
      dragConstraints={{ top: 0, bottom: 0 }}
      dragElastic={0.2}
      onDragEnd={handleDragEnd}
      animate={{ y: open ? 0 : "calc(100% - 96px)" }}
      transition={{ type: "spring", stiffness: 320, damping: 32 }}
      className="fixed inset-x-0 bottom-0 z-30 tablet:hidden flex flex-col bg-bp-surface border-t border-border-default rounded-t-2xl shadow-2xl"
      style={{
        height: "var(--future-sheet-vh, 75vh)",
        maxHeight: "85vh",
      }}
    >
      {/* Handle row — the only drag-capable region */}
      <button
        type="button"
        data-testid="future-chat-sheet-handle"
        onPointerDown={handlePointerDown}
        onClick={() => onOpenChange(!open)}
        aria-label={open ? "Collapse chat" : "Expand chat"}
        aria-expanded={open}
        className="w-full px-4 pt-2 pb-3 flex flex-col items-stretch gap-1 cursor-grab active:cursor-grabbing touch-none"
      >
        <span
          aria-hidden
          className="self-center w-10 h-1 rounded-full bg-border-default"
        />
        <div className="flex items-center justify-between gap-3 mt-1">
          {chipText ? (
            <span className="font-mono text-[11px] text-text-muted uppercase tracking-wider truncate">
              {chipText}
            </span>
          ) : (
            <span aria-hidden />
          )}
          {!open && preview && (
            <span className="flex-1 font-body text-small text-text-secondary truncate text-right">
              {preview}
            </span>
          )}
        </div>
      </button>

      {/* Body — scrollable, doesn't capture drags */}
      <div className="flex-1 min-h-0 overflow-y-auto px-2 pb-4">
        {children}
      </div>
    </motion.div>
  );
}
