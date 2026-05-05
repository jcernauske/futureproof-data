interface TreeFallbackProps {
  careerTitle: string;
}

export function TreeFallback({ careerTitle }: TreeFallbackProps) {
  return (
    <div
      className="text-center mt-6"
      role="status"
      aria-label="No branch data available"
      data-testid="region-fallback"
    >
      <h2 className="font-display text-heading font-semibold text-text-primary">
        The future is uncertain.
      </h2>
      <p className="font-body text-body-lg text-text-secondary mt-2">
        Sorry, but we don't have enough data to make projections for {careerTitle}.
      </p>
    </div>
  );
}
