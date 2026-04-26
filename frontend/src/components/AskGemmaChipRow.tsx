import { motion, useReducedMotion } from "framer-motion";
import { elevatedChipPulse, springs } from "@/styles/motion";
import type { CareerPickChip } from "@/types/careerPick";

interface AskGemmaChipRowProps {
  chips: CareerPickChip[];
  activeChipId: string | null;
  onChipClick: (chip: CareerPickChip) => void;
  /** DOM id of the visually-hidden elevation hint. Rendered by parent. */
  elevationHintId: string;
  ariaLabel?: string;
  className?: string;
}

interface ChipProps {
  chip: CareerPickChip;
  active: boolean;
  reducedMotion: boolean;
  onClick: () => void;
  elevationHintId: string;
}

function HelpCircleIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function Chip({
  chip,
  active,
  reducedMotion,
  onClick,
  elevationHintId,
}: ChipProps) {
  const base =
    "inline-flex items-center gap-2 px-4 py-2 rounded-full " +
    "font-body text-small font-semibold whitespace-nowrap " +
    "transition-colors duration-normal cursor-pointer " +
    "focus-visible:outline-none focus-visible:ring-2 " +
    "focus-visible:ring-[color:var(--color-focus-ring)]";

  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClick();
    }
  };

  if (chip.elevated) {
    const elevatedStyle =
      "border " +
      (active
        ? "bg-[rgba(244,169,126,0.25)] border-[rgba(244,169,126,0.60)] text-accent-alert"
        : "bg-[rgba(244,169,126,0.15)] border-[rgba(244,169,126,0.45)] text-accent-alert hover:bg-[rgba(244,169,126,0.22)]");

    const staticShadow = reducedMotion
      ? { boxShadow: "0 0 16px rgba(244, 169, 126, 0.30)" }
      : undefined;

    return (
      <motion.button
        type="button"
        role="button"
        tabIndex={0}
        aria-describedby={elevationHintId}
        data-testid="ask-gemma-chip"
        data-elevated="true"
        data-active={active ? "true" : "false"}
        onClick={onClick}
        onKeyDown={handleKeyDown}
        whileTap={{ scale: 0.96 }}
        transition={springs.snappy}
        animate={reducedMotion ? undefined : elevatedChipPulse.animate}
        style={staticShadow}
        {...(reducedMotion
          ? {}
          : { transition: elevatedChipPulse.transition })}
        className={`${base} ${elevatedStyle}`}
      >
        <span
          aria-hidden="true"
          className="w-2 h-2 rounded-full bg-accent-alert"
        />
        {chip.label}
      </motion.button>
    );
  }

  const baseStyle =
    "border " +
    (active
      ? "bg-[rgba(123,184,224,0.22)] border-[rgba(123,184,224,0.60)] text-text-primary shadow-[0_0_14px_rgba(123,184,224,0.25)]"
      : "bg-[rgba(123,184,224,0.10)] border-[rgba(123,184,224,0.22)] text-accent-info hover:bg-[rgba(123,184,224,0.18)] hover:border-[rgba(123,184,224,0.35)]");

  return (
    <motion.button
      type="button"
      role="button"
      tabIndex={0}
      data-testid="ask-gemma-chip"
      data-elevated="false"
      data-active={active ? "true" : "false"}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      whileTap={{ scale: 0.96 }}
      transition={springs.snappy}
      className={`${base} ${baseStyle}`}
    >
      {chip.terminal_title ? (
        <span className="text-accent-info" aria-hidden="true">
          <HelpCircleIcon />
        </span>
      ) : null}
      {chip.label}
    </motion.button>
  );
}

export function AskGemmaChipRow({
  chips,
  activeChipId,
  onChipClick,
  elevationHintId,
  ariaLabel = "Ask Gemma about this screen",
  className = "py-1 px-6 tablet:px-8",
}: AskGemmaChipRowProps) {
  const reducedMotion = useReducedMotion() ?? false;

  if (chips.length === 0) return null;

  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={`flex items-center gap-3 overflow-x-auto ${className}`}
    >
      {chips.map((chip) => (
        <Chip
          key={chip.id}
          chip={chip}
          active={chip.id === activeChipId}
          reducedMotion={reducedMotion}
          onClick={() => onChipClick(chip)}
          elevationHintId={elevationHintId}
        />
      ))}
    </div>
  );
}
