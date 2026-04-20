import type { CareerOutcome } from "@/types/build";

interface CareerListProps {
  careers: CareerOutcome[];
  pickedSoc: string | null;
  onSelect: (career: CareerOutcome) => void;
}

/**
 * Minimalist career preview list for the Set Your Course screen.
 *
 * Matches the mockup's `.career-list` shape — a bulleted row of role
 * titles in insight-colored rounded tiles with a ▸ prefix. Replaces
 * the explore-gesture `CareerTierSection` on this surface because the
 * unified screen prioritizes a fast-to-scan "what does this lead to"
 * read over per-tile interaction. Clicking a row still commits the
 * selected career via the commit path.
 */
export function CareerList({ careers, pickedSoc, onSelect }: CareerListProps) {
  if (careers.length === 0) {
    return (
      <p className="font-body text-small italic text-text-muted">
        Gemma didn't surface any grounded paths here yet. Push back with a
        chip below.
      </p>
    );
  }
  return (
    <ul
      className="flex flex-col gap-3 list-none"
      data-testid="career-list"
    >
      {careers.map((career) => {
        const picked = career.soc_code === pickedSoc;
        return (
          <li key={career.soc_code}>
            <button
              type="button"
              onClick={() => onSelect(career)}
              aria-pressed={picked}
              data-testid={`career-row-${career.soc_code}`}
              className={[
                "w-full flex items-center gap-3 px-4 py-3",
                "rounded-lg border",
                "font-body text-body-sm font-semibold text-left",
                "transition-colors duration-normal cursor-pointer",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]",
                picked
                  ? "border-accent-thrive/40 bg-accent-thrive/15 text-accent-thrive"
                  : "border-border-subtle bg-bp-mid text-accent-info hover:bg-bp-surface hover:text-text-primary",
              ].join(" ")}
            >
              <span
                aria-hidden="true"
                className="font-data text-data-sm text-accent-info"
              >
                ▸
              </span>
              {/* SOC code — a subtle data-font receipt for students who
                  want to see the taxonomy. Fades into the background via
                  font-data + text-muted; title remains the primary read. */}
              <span
                aria-label="Standard Occupational Classification code"
                className="font-data text-micro text-text-muted tracking-[0.5px] tabular-nums"
              >
                {career.soc_code}
              </span>
              <span className="flex-1">{career.occupation_title}</span>
              {picked ? (
                <span
                  aria-hidden="true"
                  className="font-data text-micro uppercase tracking-[2px] text-accent-thrive"
                >
                  Picked
                </span>
              ) : null}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
