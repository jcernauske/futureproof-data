import { TerminalSVG } from "./TerminalSVG";

/**
 * Section E — Run It Yourself (Gemma + Ollama)
 *
 * Three columns: terminal / body copy / hardware-spec callout. Per visual
 * critique §3 item 15 option (b) the plush-laptop illustration slot ships
 * a receipt-styled hardware-spec callout instead of an empty column.
 *
 * The Ollama data-residency claim is scoped per §2 Decision 8 — the full
 * "When a school runs FutureProof on Ollama, no student data leaves the
 * building" clause always ships together.
 *
 * Motion wrappers removed 2026-04-18 — see ProblemSection for context.
 */
export function OllamaSection() {
  return (
    <section
      id="landing-section-ollama"
      className="relative px-6 tablet:px-10 py-16 tablet:py-20 desktop:py-32 overflow-hidden"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.55]"
        style={{
          background:
            "repeating-linear-gradient(transparent, transparent 3px, rgba(125, 212, 163, 0.025) 3px, rgba(125, 212, 163, 0.025) 4px)",
        }}
      />
      <div className="relative mx-auto max-w-[1280px]">
        <p className="font-data text-micro tracking-[0.2em] uppercase text-accent-thrive mb-4">
          Cost
        </p>
        <h2 className="font-display font-bold text-heading tablet:text-title text-text-primary max-w-[760px] mb-12 tablet:mb-16">
          Any school can run this on their own hardware.
          <br />
          Forever. At zero cost.
        </h2>

        <div className="grid grid-cols-1 desktop:grid-cols-12 gap-10 desktop:gap-12 items-start">
          <div className="desktop:col-span-7">
            <TerminalSVG />
          </div>

          <div className="desktop:col-span-5 space-y-8">
            <div className="space-y-5 font-body text-body tablet:text-body-lg text-text-secondary leading-relaxed">
              <p>
                FutureProof runs on Gemma 4 through Ollama. Flip one environment
                variable and the whole stack — stats, fights, the Guide's coaching,
                the branch tree — works on a school's own server.
              </p>
              <p>
                When a school runs FutureProof on Ollama, no student data leaves
                the building. No cloud bill. No ongoing cost.
              </p>
            </div>

            <aside
              id="landing-ollama-specs"
              className="bg-bp-mid border border-border-subtle rounded-xl p-6 shadow-md"
            >
            <p className="font-data font-bold text-[11px] tracking-[2px] uppercase text-accent-thrive">
              Runs locally on
            </p>
            <dl className="mt-5 space-y-4">
              <div>
                <dt className="font-body font-semibold text-body-sm text-text-primary">
                  Apple Silicon
                </dt>
                <dd className="font-data text-small text-text-muted mt-0.5">
                  M1 · M2 · M3 · M4
                </dd>
              </div>
              <div>
                <dt className="font-body font-semibold text-body-sm text-text-primary">
                  Memory
                </dt>
                <dd className="font-data text-small text-text-muted mt-0.5">
                  8&nbsp;GB minimum, 16&nbsp;GB recommended
                </dd>
              </div>
              <div>
                <dt className="font-body font-semibold text-body-sm text-text-primary">
                  Model
                </dt>
                <dd className="font-data text-small text-text-muted mt-0.5">
                  gemma4:e4b (4.1&nbsp;GB download)
                </dd>
              </div>
              <div>
                <dt className="font-body font-semibold text-body-sm text-text-primary">
                  Cold start
                </dt>
                <dd className="font-data text-small text-text-muted mt-0.5">
                  ~8&nbsp;s on M2, ~12&nbsp;s on M1
                </dd>
              </div>
            </dl>
            <p className="mt-6 pt-4 border-t border-border-subtle font-body text-small text-text-secondary leading-relaxed">
              One env var: <code className="font-data text-small text-accent-thrive">INFERENCE_BACKEND=ollama</code>.
              The rest of the stack doesn't change.
            </p>
          </aside>
          </div>
        </div>
      </div>
    </section>
  );
}
