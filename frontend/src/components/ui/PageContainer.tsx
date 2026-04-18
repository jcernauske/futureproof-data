import type { ReactNode } from "react";

export interface PageContainerProps {
  children: ReactNode;
  /**
   * `centered` — single-column readable content (forms, long-form). Wraps
   * children in a col-span-8 col-start-3 cell on desktop+, col-span-12 on
   * smaller viewports.
   *
   * `grid` — exposes the raw 12-col grid to children. Children pick their
   * own column spans.
   *
   * `bleed` — responsive container max-width only, no grid layer. For
   * full-bleed visualizations.
   *
   * Default: `grid`.
   */
  variant?: "centered" | "grid" | "bleed";
  /** Optional data-testid passthrough. Defaults to "page-container". */
  testId?: string;
  /** Additional classes applied to the container root. */
  className?: string;
}

const GRID_CLASSES =
  "grid grid-cols-12 gap-grid-mobile tablet:gap-grid-tablet desktop:gap-grid-desktop";

export function PageContainer({
  children,
  variant = "grid",
  testId = "page-container",
  className,
}: PageContainerProps) {
  const gridLayer = variant === "bleed" ? "" : GRID_CLASSES;
  const rootClasses = [
    "container mx-auto",
    gridLayer,
    className,
  ]
    .filter(Boolean)
    .join(" ");

  if (variant === "centered") {
    return (
      <div className={rootClasses} data-testid={testId}>
        <div className="col-span-12 desktop:col-span-8 desktop:col-start-3">
          {children}
        </div>
      </div>
    );
  }

  return (
    <div className={rootClasses} data-testid={testId}>
      {children}
    </div>
  );
}
