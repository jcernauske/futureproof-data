import { motion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";
import type { Suggestion } from "@/types/buildInput";

interface CommunitySuggestionsProps {
  suggestions: Suggestion[];
  inputText: string;
  schoolName: string;
  onSelect: (suggestion: Suggestion) => void;
}

/**
 * Renders the community-suggestion cards under the career preview on the
 * Set Your Course screen. Up to 3 cards are shown. Copy is kid-voiced per
 * the voice guide. Returns null when no suggestions are available so the
 * surface is absent (not an empty box) on a cold (school, input) combo.
 */
export function CommunitySuggestions({
  suggestions,
  inputText,
  schoolName,
  onSelect,
}: CommunitySuggestionsProps) {
  if (suggestions.length === 0) return null;

  const visible = suggestions.slice(0, 3);

  return (
    <section
      aria-label="Community suggestions"
      className="rounded-xl border border-border-subtle bg-bp-mid p-5"
      data-testid="community-suggestions"
    >
      <p className="font-body text-small text-text-secondary mb-3">
        Other students searching{" "}
        <span className="font-semibold text-text-primary">
          “{inputText}”
        </span>{" "}
        at{" "}
        <span className="font-semibold text-text-primary">{schoolName}</span>{" "}
        ended up here:
      </p>
      <motion.ul
        initial="hidden"
        animate="visible"
        variants={{
          hidden: {},
          visible: { transition: { staggerChildren: stagger.normal } },
        }}
        className="flex flex-col gap-2"
      >
        {visible.map((suggestion) => (
          <motion.li
            key={`${suggestion.clicked_soc}-${suggestion.canonical_cip4}`}
            variants={{
              hidden: { opacity: 0, y: 6 },
              visible: { opacity: 1, y: 0, transition: springs.smooth },
            }}
          >
            <button
              type="button"
              onClick={() => onSelect(suggestion)}
              className="w-full text-left rounded-lg border border-border-subtle bg-bp-surface px-4 py-3 flex items-center justify-between gap-3 hover:bg-bp-raised hover:border-border cursor-pointer transition-colors duration-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]"
              data-testid={`community-suggestion-${suggestion.clicked_soc}`}
            >
              <span className="font-body text-body font-semibold text-text-primary">
                {suggestion.clicked_career_title}
              </span>
              <span className="font-data text-small text-text-muted shrink-0">
                {suggestion.count}{" "}
                {suggestion.count === 1 ? "student" : "students"}
              </span>
            </button>
          </motion.li>
        ))}
      </motion.ul>
    </section>
  );
}
