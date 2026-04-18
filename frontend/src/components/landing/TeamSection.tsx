/**
 * Section H — Team / About
 * Centered single paragraph. No headshot. Restraint is the register.
 * See spec §3.11.
 *
 * Motion wrappers removed 2026-04-18 — see ProblemSection for context.
 */
export function TeamSection() {
  return (
    <section
      id="landing-section-team"
      className="relative px-6 tablet:px-10 py-16 tablet:py-20 desktop:py-24"
    >
      <div
        aria-hidden
        className="absolute left-1/2 top-0 h-[80px] w-px -translate-x-1/2 bg-gradient-to-b from-border-subtle to-transparent"
      />
      <div className="mx-auto max-w-[640px] text-center">
        <h2 className="font-display font-bold text-heading text-text-primary">
          Who built this.
        </h2>
        <p className="mt-6 font-body text-body tablet:text-body-lg text-text-secondary leading-relaxed max-w-[62ch] mx-auto">
          FutureProof was built for the Gemma 4 Good hackathon by a one-person
          team. The data pipeline runs on{" "}
          <a
            id="landing-team-brightsmith-link"
            href="https://github.com/jcernauske/brightsmith"
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent-info hover:underline underline-offset-4"
          >
            Brightsmith
          </a>
          , an open-source framework for governed data products. The code is
          MIT-licensed and the public data is public.
        </p>
      </div>
    </section>
  );
}
