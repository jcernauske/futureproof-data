import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { FrameProgressDots } from "./FrameProgressDots";
import { WrappedFrame } from "./WrappedFrame";
import { Button } from "@/components/ui/Button";
import type { WrappedFrameInfo } from "@/api/wrapped";

interface WrappedViewerProps {
  frames: WrappedFrameInfo[];
  onDone: () => void;
  onDownloadFrame: (index: number) => void;
  onDownloadAll: () => void;
}

export function WrappedViewer({
  frames,
  onDone,
  onDownloadFrame,
  onDownloadAll,
}: WrappedViewerProps) {
  const [current, setCurrent] = useState(0);
  const [direction, setDirection] = useState<1 | -1>(1);

  const total = frames.length;
  const goForward = useCallback(() => {
    if (current < total - 1) {
      setDirection(1);
      setCurrent((i) => i + 1);
    }
  }, [current, total]);

  const goBack = useCallback(() => {
    if (current > 0) {
      setDirection(-1);
      setCurrent((i) => i - 1);
    }
  }, [current]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") goForward();
      if (e.key === "ArrowLeft") goBack();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [goForward, goBack]);

  const frame = frames[current];

  return (
    <div
      data-testid="region-wrapped-viewer"
      role="article"
      aria-label={`Your build story — frame ${current + 1} of ${total}`}
      className="min-h-screen w-full bg-bp-void flex flex-col items-center justify-between py-6 px-4"
    >
      <div className="w-full max-w-[420px] flex justify-center">
        <FrameProgressDots total={total} current={current} />
      </div>

      <div
        className="relative w-full max-w-[420px] rounded-[28px] overflow-hidden shadow-lg"
        style={{
          aspectRatio: "9 / 16",
          background:
            "radial-gradient(ellipse at 50% 50%, rgba(18,19,31,1) 0%, rgba(0,0,0,0.85) 100%)",
        }}
      >
        <AnimatePresence custom={direction} initial={false} mode="popLayout">
          <motion.div
            key={current}
            custom={direction}
            initial={{ x: direction === 1 ? "100%" : "-100%", opacity: 0.4 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: direction === 1 ? "-100%" : "100%", opacity: 0.4 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="absolute inset-0"
          >
            {frame ? (
              <WrappedFrame
                src={frame.url}
                index={frame.index}
                label={`Frame ${frame.index + 1}`}
              />
            ) : null}
          </motion.div>
        </AnimatePresence>

        {/* Illumination wipe — a thrive-tinted band (forward) or a
            muted band (backward) that passes across the newly-arrived
            frame at t=120ms. Per design vision §3, this is the detail
            that makes the carousel feel "activated" instead of static. */}
        <motion.div
          key={`wipe-${current}-${direction}`}
          aria-hidden="true"
          initial={{ x: direction === 1 ? "-110%" : "110%", opacity: 1 }}
          animate={{ x: direction === 1 ? "110%" : "-110%", opacity: 0 }}
          transition={{ duration: 0.55, ease: "easeOut", delay: 0.12 }}
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              direction === 1
                ? "linear-gradient(90deg, transparent 35%, rgba(125, 212, 163, 0.22) 50%, transparent 65%)"
                : "linear-gradient(90deg, transparent 35%, rgba(196, 191, 176, 0.08) 50%, transparent 65%)",
          }}
        />

        <button
          type="button"
          data-testid="btn-frame-back"
          aria-label="Previous frame"
          onClick={goBack}
          disabled={current === 0}
          className="absolute top-0 left-0 w-[30%] h-full z-10 focus-visible:outline-2 focus-visible:outline-accent-info rounded-l-[28px]"
          style={{ background: "transparent" }}
        />
        <button
          type="button"
          data-testid="btn-frame-forward"
          aria-label="Next frame"
          onClick={goForward}
          disabled={current === total - 1}
          className="absolute top-0 right-0 w-[70%] h-full z-10 focus-visible:outline-2 focus-visible:outline-accent-info rounded-r-[28px]"
          style={{ background: "transparent" }}
        />

        <div
          aria-hidden="true"
          className="absolute bottom-3 right-4 z-20 font-data text-small text-text-muted"
        >
          {current + 1} / {total}
        </div>
      </div>

      <div className="w-full max-w-[420px] flex flex-col gap-2 mt-4">
        <Button
          variant="primary"
          onClick={() => onDownloadFrame(current)}
          data-testid="btn-download-frame"
          aria-label="Download this frame as image"
        >
          Download this frame
        </Button>
        <Button
          variant="secondary"
          onClick={onDownloadAll}
          data-testid="btn-download-all"
          aria-label="Download all 6 frames"
        >
          Download all frames
        </Button>
        <button
          type="button"
          data-testid="btn-done"
          aria-label="Continue to menu"
          onClick={onDone}
          className="mt-2 font-body text-body text-text-muted hover:text-text-primary transition-colors py-3"
        >
          Done →
        </button>
      </div>
    </div>
  );
}
