import { motion } from "framer-motion";
import { springs } from "@/styles/motion";

export interface Segment<T extends string | number> {
  value: T;
  label: string;
  shortLabel?: string;
  subtext?: string;
}

interface SegmentedControlProps<T extends string | number> {
  segments: Segment<T>[];
  value: T;
  onChange: (value: T) => void;
  activeColor?: string;
  warningValues?: T[];
  warningColor?: string;
  ariaLabel: string;
}

export function SegmentedControl<T extends string | number>({
  segments,
  value,
  onChange,
  activeColor = "bg-accent-thrive",
  warningValues = [],
  warningColor = "bg-accent-caution",
  ariaLabel,
}: SegmentedControlProps<T>) {
  const selectedIndex = segments.findIndex((s) => s.value === value);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      const next = Math.min(selectedIndex + 1, segments.length - 1);
      onChange(segments[next]!.value);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      const prev = Math.max(selectedIndex - 1, 0);
      onChange(segments[prev]!.value);
    }
  }

  return (
    <div
      className="relative flex bg-bp-surface rounded-md p-1 gap-1"
      role="radiogroup"
      aria-label={ariaLabel}
      onKeyDown={handleKeyDown}
    >
      {segments.map((segment) => {
        const isSelected = segment.value === value;
        const isWarning =
          isSelected && warningValues.includes(segment.value);
        const bg = isWarning ? warningColor : activeColor;

        return (
          <button
            key={String(segment.value)}
            role="radio"
            aria-checked={isSelected}
            tabIndex={isSelected ? 0 : -1}
            className={`relative flex-1 flex flex-col items-center gap-0.5 py-2.5 px-2 rounded-sm z-10 transition-colors duration-fast cursor-pointer ${
              isSelected
                ? "text-text-primary font-semibold"
                : "text-text-secondary"
            }`}
            onClick={() => onChange(segment.value)}
          >
            {isSelected && (
              <motion.div
                className={`absolute inset-0 ${bg} rounded-sm`}
                layoutId="segment-active"
                transition={springs.snappy}
                style={{ zIndex: -1 }}
              />
            )}
            <span className="text-sm mobile:hidden">{segment.shortLabel ?? segment.label}</span>
            <span className="text-sm hidden mobile:inline">{segment.label}</span>
            {segment.subtext && (
              <span
                className={`text-xs ${isSelected ? "text-text-primary/70" : "text-text-muted"}`}
              >
                {segment.subtext}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
