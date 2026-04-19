import { useEffect, useState } from "react";
import { Wordmark } from "@/components/ui/Wordmark";

/**
 * Sticky top nav for the marketing landing page. Glass effect (backdrop blur
 * over bp-deep at 70% alpha) so the planetarium gradient continues to read
 * through it. Active-section pill driven by IntersectionObserver across each
 * section's id. Mirrors v3 mockup's editorial chrome.
 */

interface NavItem {
  id: string;
  label: string;
}

const NAV_ITEMS: readonly NavItem[] = [
  { id: "landing-section-problem", label: "Problem" },
  { id: "landing-section-how", label: "How it works" },
  { id: "landing-section-receipts", label: "Receipts" },
  { id: "landing-section-ollama", label: "Cost" },
  { id: "landing-section-data", label: "Sources" },
  { id: "landing-section-team", label: "Team" },
];

export function LandingTopNav() {
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        // Pick the most-visible section that's intersecting.
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]) setActiveId(visible[0].target.id);
      },
      {
        rootMargin: "-30% 0px -55% 0px",
        threshold: [0, 0.25, 0.5, 0.75, 1],
      },
    );

    NAV_ITEMS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  return (
    <nav
      id="landing-top-nav"
      className="sticky top-0 z-50 backdrop-blur-lg bg-bp-deep/90 border-b border-border-subtle/30"
      aria-label="Landing page sections"
    >
      <div className="mx-auto max-w-[1280px] px-6 tablet:px-10 h-14 flex items-center justify-between gap-6">
        <a href="#landing-root" className="shrink-0">
          <Wordmark size="md" />
        </a>

        <ul className="hidden tablet:flex items-center gap-1 desktop:gap-2">
          {NAV_ITEMS.map((item) => {
            const isActive = activeId === item.id;
            return (
              <li key={item.id}>
                <a
                  href={`#${item.id}`}
                  className={`font-body text-small px-3 py-1.5 rounded-full transition-colors duration-fast ${
                    isActive
                      ? "bg-bp-surface text-text-primary"
                      : "text-text-muted hover:text-text-secondary"
                  }`}
                  aria-current={isActive ? "true" : undefined}
                >
                  {item.label}
                </a>
              </li>
            );
          })}
        </ul>

        <a
          href="/app"
          className="font-body font-bold text-small bg-accent-thrive text-text-inverse rounded-full h-9 px-4 inline-flex items-center justify-center transition-all duration-normal hover:brightness-95 active:scale-[0.97] shrink-0"
        >
          Live app
        </a>
      </div>
    </nav>
  );
}
