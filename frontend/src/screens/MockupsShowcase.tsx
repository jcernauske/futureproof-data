/**
 * Mockups Showcase — Horizon shape A vs shape B
 *
 * Route: /mockups/horizon
 *
 * Reads like a paper mat: two mockups, stacked on narrow viewports,
 * side-by-side on desktop. Each mockup sits in a rounded panel with a
 * small caption header (emotion + what it does) so Jeff can compare
 * structure + feel without digging through code.
 *
 * No real API — each mockup stubs its own data inline.
 */
import { PageContainer } from "@/components/ui/PageContainer";
import { HorizonStripMockup } from "@/components/horizon/HorizonStripMockup";
import { ChapterBookMockup } from "@/components/horizon/ChapterBookMockup";

function PanelHeader({
  eyebrow,
  title,
  feeling,
  body,
}: {
  eyebrow: string;
  title: string;
  feeling: string;
  body: string;
}) {
  return (
    <div className="flex flex-col gap-2">
      <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-info">
        {eyebrow}
      </p>
      <h2 className="font-display text-display font-semibold text-text-primary leading-snug">
        {title}
      </h2>
      <p className="font-body text-body text-text-secondary">
        <span className="font-bold text-accent-thrive">Feeling: </span>
        <span className="italic">{feeling}</span>
      </p>
      <p className="font-body text-body text-text-secondary max-w-[52ch]">
        {body}
      </p>
    </div>
  );
}

export function MockupsShowcase() {
  return (
    <div className="min-h-screen relative pt-14 pb-16">
      <PageContainer variant="centered" className="py-10">
        <header className="max-w-[640px] mb-10">
          <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-info mb-2">
            Design exploration
          </p>
          <h1 className="font-display text-hero font-semibold text-text-primary leading-tight">
            Where does this take you?
          </h1>
          <p className="font-body text-body-lg text-text-secondary mt-3 max-w-[52ch]">
            Two shapes for showing the arc past the first job. Same data, same
            voice — different commitment level from the student.
          </p>
        </header>

        <div className="grid grid-cols-1 wide:grid-cols-2 gap-8 wide:gap-10 items-start">
          {/* Shape A — Horizon Strip */}
          <section
            aria-label="Shape A — Horizon Strip"
            className="flex flex-col gap-6 rounded-xl bg-bp-deep/60 border border-border-subtle p-6 tablet:p-8"
          >
            <PanelHeader
              eyebrow="Shape A"
              title="Horizon Strip"
              feeling="scan-able relief"
              body="The common list stays intact. Tap any row to reveal a four-point time strip in place: Today → Early → Mid → Senior. Tap a dot to hear what changes. Grad-degree gates show as knowledge points, not walls. At most one strip open at a time so the list never stacks into a brick."
            />
            <div className="flex-1 min-h-0">
              <HorizonStripMockup />
            </div>
          </section>

          {/* Shape B — Chapter Book */}
          <section
            aria-label="Shape B — Chapter Book"
            className="flex flex-col gap-6 rounded-xl bg-bp-deep/60 border border-border-subtle p-6 tablet:p-8"
          >
            <PanelHeader
              eyebrow="Shape B"
              title="Chapter Book"
              feeling="contemplative depth"
              body="Tap a career and the list steps back — the pick becomes the book's title page. Chapters flow top-to-bottom, linked by a thread. Locked chapters (grad-degree gates) read as informational, not punitive. Careers that cap out get a calm 'this is the ceiling' final chapter — no broken-data feel."
            />
            <div className="flex-1 min-h-0">
              <ChapterBookMockup />
            </div>
          </section>
        </div>

        <footer className="mt-16 pt-8 border-t border-border-subtle max-w-[640px]">
          <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-info mb-2">
            Notes for the spec
          </p>
          <ul className="font-body text-body text-text-secondary flex flex-col gap-2 list-disc pl-5">
            <li>
              Both shapes consume the same data shape
              (<span className="font-data text-data-sm">career_branches</span>
              {" "}with <span className="font-data text-data-sm">experience_tier</span>,
              <span className="font-data text-data-sm"> experience_years</span>,
              <span className="font-data text-data-sm"> unlock</span>, and delta
              fields). Swappable at the render layer.
            </li>
            <li>
              Grad-degree gates use accent-insight, not thrive or alert. The
              message is "a door" not "a trophy" and not "a wall."
            </li>
            <li>
              All motion gated on <span className="font-data text-data-sm">useReducedMotion()</span>. No
              looping animations in either mockup.
            </li>
          </ul>
        </footer>
      </PageContainer>
    </div>
  );
}
