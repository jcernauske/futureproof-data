import { useReducedMotion } from "framer-motion";

/**
 * Section E — Terminal (SVG)
 * Real text, zoomable, copy-pasteable per §2 Decision 7.
 * See spec §3.8 (Terminal content table).
 */
export function TerminalSVG() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <figure
      id="landing-ollama-terminal"
      aria-label="Terminal showing ollama pull gemma4:e4b and local launch commands"
      className="bg-bp-void border border-border rounded-lg shadow-glow-thrive p-6 font-data text-small"
    >
      <div className="flex items-center gap-2 mb-4">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-3 h-3 rounded-full bg-text-muted opacity-40"
            aria-hidden
          />
        ))}
      </div>
      <div className="space-y-2 text-text-primary leading-relaxed">
        <p>
          <span className="font-bold text-accent-thrive">$</span>{" "}
          ollama pull gemma4:e4b
        </p>
        <p>
          <span className="font-bold text-accent-thrive">✓</span> complete
        </p>
        <p className="h-3" />
        <p>
          <span className="font-bold text-accent-thrive">$</span>{" "}
          INFERENCE_BACKEND=ollama npm run dev
        </p>
        <p>
          <span className="font-bold text-accent-thrive">✓</span> ready at :5173
        </p>
        <p className="pt-2">
          <span
            className={`inline-block w-[9px] h-[16px] align-middle bg-text-primary ${
              prefersReducedMotion ? "" : "animate-terminal-cursor"
            }`}
            aria-hidden
          />
        </p>
      </div>
    </figure>
  );
}
