/**
 * Section I — Footer
 * Wordmark + Live app link + disclaimer + data-line echo.
 *
 * Motion wrappers removed 2026-04-18 — see ProblemSection for context.
 * Other nav items return as §11 follow-up once destinations exist.
 */
export function LandingFooter() {
  return (
    <footer
      id="landing-footer"
      className="bg-bp-deep border-t border-border-subtle py-16 px-6 tablet:px-10"
    >
      <div className="mx-auto max-w-[1280px] space-y-8">
        <div className="flex flex-col tablet:flex-row tablet:items-start tablet:justify-between gap-6">
          <span className="font-display font-bold text-heading text-text-primary">
            FutureProof
          </span>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <a
              id="landing-footer-live-app"
              href="/app"
              className="font-body text-body text-text-secondary hover:text-text-primary hover:underline underline-offset-4"
            >
              Live app
            </a>
          </div>
        </div>

        <p className="font-body text-small text-text-muted max-w-[720px]">
          AI-estimated. Not a substitute for professional career counseling.
        </p>

        <p className="font-data text-micro text-text-muted tracking-widest opacity-40 leading-relaxed">
          700K rows · 280 DQ rules · 7 public datasets · Every number has a
          receipt.
        </p>
      </div>
    </footer>
  );
}
