import { motion } from "framer-motion";
import { transitions } from "@/styles/motion";
import { Button } from "@/components/ui/Button";

interface StructuralLossProps {
  bossId: string;
  onContinue: () => void;
}

export function StructuralLoss({ bossId, onContinue }: StructuralLossProps) {
  return (
    <motion.div
      id={`region-structural-loss-${bossId}`}
      role="alert"
      aria-label="Structural loss \u2014 all skills exhausted"
      className="bg-bp-mid border border-border-strong rounded-xl p-6 border-l-[3px] border-l-accent-alert"
      {...transitions.fadeInUp}
    >
      <div className="text-center text-[32px] mb-4">{"\u26A0\uFE0F"}</div>
      <p className="font-body text-body-lg text-text-primary leading-relaxed">
        Every available skill for this fight has been equipped, and the result is
        still a loss. That's the most important signal this tool can give you:
        the gap isn't a skill-tree problem. It's structural to this school +
        major + career combination. Worth taking seriously.
      </p>
      <p className="font-body text-small text-text-secondary mt-4">
        This doesn't mean the path is wrong — it means this specific risk needs
        a different strategy. Your Next Steps checklist will address this.
      </p>
      <div className="mt-6 flex justify-center">
        <Button variant="primary" onClick={onContinue}>
          Continue {"\u2192"}
        </Button>
      </div>
    </motion.div>
  );
}
