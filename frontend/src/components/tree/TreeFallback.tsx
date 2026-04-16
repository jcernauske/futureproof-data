interface TreeFallbackProps {
  careerTitle: string;
}

export function TreeFallback({ careerTitle }: TreeFallbackProps) {
  return (
    <div
      className="text-center mt-6"
      role="status"
      aria-label="Branch data coming soon"
      data-testid="region-fallback"
    >
      <p className="font-body text-body-lg text-text-secondary">
        We're mapping career branches for {careerTitle}. Check back soon.
      </p>
    </div>
  );
}
