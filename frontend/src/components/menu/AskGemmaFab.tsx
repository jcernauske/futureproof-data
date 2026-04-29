import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { useT } from "@/i18n/useT";

interface AskGemmaFabProps {
  /** True when the FAB should be visible (chat closed AND a build is loaded). */
  visible: boolean;
  onOpen: () => void;
  /** First-mount entrance delay in seconds (lets boss bands reveal first). */
  initialDelay?: number;
}

/**
 * Sticky FAB on /my-build that opens the scope-aware chat with the
 * whole-build scope. See docs/specs/feature-ask-gemma.md §3 entry
 * point #4. The breathing glow uses the `animate-gemma-fab-breathe`
 * utility added in `index.css` next to the existing `card-breathe`
 * keyframes.
 */
export function AskGemmaFab({
  visible,
  onOpen,
  initialDelay = 0,
}: AskGemmaFabProps) {
  const t = useT();
  const label = t("chat.askAboutBuild");

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="fab-wrap"
          initial={{ opacity: 0, scale: 0.6, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.85, y: 8 }}
          transition={{ ...springs.smooth, delay: initialDelay }}
          className="fixed z-[130] right-5 tablet:right-6 group"
          style={{ bottom: "max(1.25rem, env(safe-area-inset-bottom))" }}
        >
          {/* Tooltip — hover-capable pointers only */}
          <span
            aria-hidden
            className="pointer-events-none absolute right-full mr-3 top-1/2 -translate-y-1/2
                       px-3 py-1.5 rounded-md bg-bp-raised border border-border-subtle
                       font-body text-small font-semibold text-text-primary whitespace-nowrap
                       opacity-0 translate-x-2 group-hover:opacity-100 group-hover:translate-x-0
                       transition-all duration-normal delay-300
                       hidden tablet:block"
          >
            {label}
          </span>

          <button
            type="button"
            onClick={onOpen}
            data-testid="btn-ask-build"
            aria-label={label}
            className={[
              "w-14 h-14 rounded-full",
              "bg-gradient-to-br from-accent-info/90 to-accent-insight/90",
              "border border-border-subtle",
              "shadow-glow-insight animate-gemma-fab-breathe",
              "flex items-center justify-center",
              "transition-all duration-fast",
              "hover:shadow-glow-insight hover:scale-[1.04]",
              "active:scale-[0.94]",
              "focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-none",
              "cursor-pointer",
            ].join(" ")}
          >
            <span
              aria-hidden
              className="font-display text-text-inverse text-[24px] leading-none"
            >
              ✦
            </span>
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
