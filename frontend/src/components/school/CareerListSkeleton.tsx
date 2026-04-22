import { GemmaSpinner } from "@/components/ui/GemmaSpinner";

export function CareerListSkeleton() {
  return (
    <div
      className="grid grid-cols-1 tablet:grid-cols-2 desktop:grid-cols-3 gap-3"
      aria-label="Loading career paths"
      data-testid="career-list-skeleton"
    >
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className="flex flex-col items-center justify-center gap-3 rounded-xl border border-border-subtle bg-bp-mid p-8 min-h-[140px] animate-pulse"
          aria-hidden="true"
        >
          <GemmaSpinner size={28} />
          <span className="font-body text-small text-text-muted/50">
            Loading careers…
          </span>
        </div>
      ))}
    </div>
  );
}
