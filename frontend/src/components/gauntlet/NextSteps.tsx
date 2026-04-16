import { motion } from "framer-motion";
import { springs, staggerContainer, staggerItem, stagger } from "@/styles/motion";
import { Button } from "@/components/ui/Button";

interface NextStepsProps {
  content: string | null;
  error: boolean;
  loading: boolean;
  profileEmoji: string;
  onRetry: () => void;
  onBranches: () => void;
  onSave: () => void;
  onBackToBuild: () => void;
}

const SECTION_ICONS: Record<string, string> = {
  "Questions to Ask Your Guidance Counselor": "\u{1F393}",
  "Questions to Ask College Recruiters": "\u{1F3EB}",
  "Things to Verify on Your Own": "\u{1F50D}",
  "Points to Discuss with Your Parents": "\u{1F46A}",
};

function parseNextStepsSections(
  markdown: string,
): Array<{ title: string; content: string }> {
  const sections: Array<{ title: string; content: string }> = [];
  const parts = markdown.split(/^## /m).filter(Boolean);
  for (const part of parts) {
    const newlineIdx = part.indexOf("\n");
    if (newlineIdx === -1) continue;
    const title = part.slice(0, newlineIdx).trim();
    const content = part.slice(newlineIdx + 1).trim();
    sections.push({ title, content });
  }
  return sections;
}

export function NextSteps({
  content,
  error,
  loading,
  profileEmoji,
  onRetry,
  onBranches,
  onSave,
  onBackToBuild,
}: NextStepsProps) {
  // Loading state
  if (loading) {
    return (
      <motion.div
        id="region-next-steps-loading"
        role="status"
        aria-label="Generating your action plan"
        className="flex flex-col items-center justify-center min-h-[40vh] text-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <motion.div
          className="text-[48px] mb-4"
          animate={{ y: [0, -8, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        >
          {profileEmoji || "\u{1F43B}"}
        </motion.div>
        <p className="font-body text-body-lg text-text-primary">
          Gemma is writing your action plan...
        </p>
      </motion.div>
    );
  }

  // Error state
  if (error) {
    return (
      <motion.div
        className="flex flex-col items-center text-center gap-4 py-12"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <p className="font-body text-body text-text-secondary max-w-sm">
          Gemma couldn't generate your action plan right now. You can still
          explore your branches and compare builds.
        </p>
        <div className="flex gap-3">
          <Button variant="secondary" onClick={onRetry}>
            Try Again
          </Button>
          <Button variant="primary" onClick={onBranches}>
            Continue {"\u2192"}
          </Button>
        </div>
      </motion.div>
    );
  }

  // Content
  if (!content) return null;
  const sections = parseNextStepsSections(content);

  // Fallback for malformed markdown (no parseable sections)
  if (sections.length === 0) {
    return (
      <motion.div className="w-full" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <span className="font-data text-[11px] text-text-muted uppercase tracking-[2px] block text-center mb-4">
          YOUR NEXT STEPS
        </span>
        <div className="bg-bp-mid border border-border-subtle rounded-xl p-6">
          <p className="font-body text-body text-text-primary whitespace-pre-line">
            {content}
          </p>
        </div>
        <motion.div
          className="flex flex-col items-center gap-3 mt-10"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springs.smooth, delay: 0.3 }}
        >
          <Button id="btn-branches" variant="primary" onClick={onBranches}>
            See Where This Path Leads {"\u2192"}
          </Button>
        </motion.div>
      </motion.div>
    );
  }

  return (
    <motion.div className="w-full">
      <span className="font-data text-[11px] text-text-muted uppercase tracking-[2px] block text-center mb-4">
        YOUR NEXT STEPS
      </span>
      <p className="font-body text-body-lg text-text-secondary text-center max-w-md mx-auto mb-8">
        No more bosses. No more stats. Here's what you actually do next.
      </p>

      <motion.div
        className="space-y-4"
        variants={staggerContainer(0.2, stagger.normal)}
        initial="hidden"
        animate="visible"
      >
        {sections.map((section, i) => {
          const icon = SECTION_ICONS[section.title] ?? "\u{1F4CB}";
          return (
            <motion.section
              key={i}
              id={`region-checklist-${i}`}
              role="article"
              aria-label={section.title}
              className="bg-bp-mid border border-border-subtle rounded-xl p-6"
              variants={staggerItem}
            >
              <h3 className="font-display font-semibold text-heading text-text-primary flex items-center gap-2">
                <span>{icon}</span>
                {section.title}
              </h3>
              <div className="font-body text-body text-text-primary mt-4 leading-relaxed whitespace-pre-line">
                {section.content}
              </div>
            </motion.section>
          );
        })}
      </motion.div>

      {/* CTA area */}
      <motion.div
        className="flex flex-col items-center gap-3 mt-10"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...springs.smooth, delay: 0.5 }}
      >
        <Button
          id="btn-branches"
          variant="primary"
          onClick={onBranches}
          aria-label="See where this path leads"
        >
          See Where This Path Leads {"\u2192"}
        </Button>
        <Button variant="secondary" onClick={onSave}>
          Save & Share
        </Button>
        <Button variant="ghost" onClick={onBackToBuild}>
          Back to My Build
        </Button>
      </motion.div>
    </motion.div>
  );
}
