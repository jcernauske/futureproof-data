import { motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { Button } from "@/components/ui/Button";

interface GauntletCTAProps {
  onBranches: () => void;
  onSave: () => void;
  onBackToBuild: () => void;
}

export function GauntletCTA({
  onBranches,
  onSave,
  onBackToBuild,
}: GauntletCTAProps) {
  return (
    <motion.div
      className="flex flex-col items-center gap-3 mt-10"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
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
  );
}
