import { motion } from "framer-motion";
import { springs } from "@/styles/motion";

interface BuildSummaryBarProps {
  schoolName: string;
  majorTitle: string;
}

export function BuildSummaryBar({
  schoolName,
  majorTitle,
}: BuildSummaryBarProps) {
  return (
    <motion.div
      className="w-full bg-bp-mid rounded-bp-sm px-4 py-2.5 flex items-center gap-2 text-sm overflow-hidden"
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      transition={springs.smooth}
    >
      <span className="shrink-0">🏫</span>
      <span className="text-text-primary font-semibold truncate">
        {schoolName}
      </span>
      <span className="text-text-muted">·</span>
      <span className="shrink-0">📚</span>
      <span className="text-text-secondary truncate">{majorTitle}</span>
    </motion.div>
  );
}
