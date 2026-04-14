import { useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { springs } from "@/styles/motion";

export interface SliderStop<T extends string | number> {
  value: T;
  label: string;
}

interface DiscreteSliderProps<T extends string | number> {
  stops: SliderStop<T>[];
  value: T;
  onChange: (value: T) => void;
  /** Left endpoint label */
  labelLeft: string;
  /** Right endpoint label */
  labelRight: string;
  /** CSS gradient for the fill track */
  fillGradient: string;
  ariaLabel: string;
}

export function DiscreteSlider<T extends string | number>({
  stops,
  value,
  onChange,
  labelLeft,
  labelRight,
  fillGradient,
  ariaLabel,
}: DiscreteSliderProps<T>) {
  const selectedIndex = stops.findIndex((s) => s.value === value);
  const fillPercent =
    stops.length > 1 ? (selectedIndex / (stops.length - 1)) * 100 : 0;

  const trackRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);

  const snapToNearest = useCallback(
    (clientX: number) => {
      const track = trackRef.current;
      if (!track || stops.length < 2) return;
      const rect = track.getBoundingClientRect();
      const pct = Math.max(
        0,
        Math.min(1, (clientX - rect.left) / rect.width),
      );
      const nearestIndex = Math.round(pct * (stops.length - 1));
      const stop = stops[nearestIndex];
      if (stop && stop.value !== value) {
        onChange(stop.value);
      }
    },
    [stops, value, onChange],
  );

  function handlePointerDown(e: React.PointerEvent) {
    draggingRef.current = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    snapToNearest(e.clientX);
  }

  function handlePointerMove(e: React.PointerEvent) {
    if (!draggingRef.current) return;
    snapToNearest(e.clientX);
  }

  function handlePointerUp() {
    draggingRef.current = false;
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      const next = Math.min(selectedIndex + 1, stops.length - 1);
      onChange(stops[next]!.value);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      const prev = Math.max(selectedIndex - 1, 0);
      onChange(stops[prev]!.value);
    }
  }

  return (
    <div
      role="slider"
      aria-label={ariaLabel}
      aria-valuemin={0}
      aria-valuemax={stops.length - 1}
      aria-valuenow={selectedIndex}
      aria-valuetext={stops[selectedIndex]?.label}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      className="select-none"
    >
      {/* Track + thumb */}
      <div
        ref={trackRef}
        className="relative h-[6px] bg-bp-deep rounded-full mx-3 cursor-pointer touch-none"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      >
        {/* Fill */}
        <motion.div
          className="absolute top-0 left-0 h-full rounded-full"
          style={{ background: fillGradient }}
          animate={{ width: `${fillPercent}%` }}
          transition={{ duration: 0.1, ease: "easeOut" }}
        />

        {/* Thumb */}
        <motion.div
          className="absolute top-1/2 w-7 h-7 -translate-y-1/2 rounded-full bg-bp-raised border-[3px] border-text-primary z-[2] cursor-grab active:cursor-grabbing"
          style={{
            boxShadow: "0 0 12px rgba(123,184,224,0.25)",
          }}
          animate={{ left: `${fillPercent}%` }}
          transition={springs.snappy}
          whileHover={{
            boxShadow: "0 0 16px rgba(125,212,163,0.35)",
          }}
        />
      </div>

      {/* Endpoint labels */}
      <div className="flex justify-between mt-3 px-3">
        <span className="text-[13px] text-text-muted">{labelLeft}</span>
        <span className="text-[13px] text-text-muted">{labelRight}</span>
      </div>
    </div>
  );
}
