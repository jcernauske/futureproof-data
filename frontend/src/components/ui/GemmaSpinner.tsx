import { motion } from "framer-motion";

interface GemmaSpinnerProps {
  size?: number;
  className?: string;
}

export function GemmaSpinner({ size = 40, className = "" }: GemmaSpinnerProps) {
  return (
    <div
      className={`relative inline-flex items-center justify-center ${className}`}
      style={{ width: size, height: size }}
    >
      {/* Background glow */}
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          background: "radial-gradient(circle, rgba(184, 169, 232, 0.15) 0%, transparent 70%)",
        }}
        animate={{ opacity: [0.4, 0.8, 0.4], scale: [0.9, 1.1, 0.9] }}
        transition={{ duration: 2, ease: "easeInOut", repeat: Infinity }}
      />

      <motion.svg
        viewBox="0 0 40 40"
        width={size}
        height={size}
        animate={{ rotate: 360 }}
        transition={{ duration: 4, ease: "linear", repeat: Infinity }}
      >
        {/* Circle ring */}
        <motion.circle
          cx="20"
          cy="20"
          r="14"
          fill="none"
          stroke="var(--color-accent-insight)"
          strokeWidth="0.8"
          opacity="0.3"
          animate={{ opacity: [0.2, 0.4, 0.2] }}
          transition={{ duration: 2, ease: "easeInOut", repeat: Infinity }}
        />

        {/* Crosshair lines */}
        <g stroke="var(--color-accent-insight)" strokeWidth="0.6" opacity="0.25">
          <line x1="20" y1="2" x2="20" y2="38" />
          <line x1="2" y1="20" x2="38" y2="20" />
        </g>

        {/* Four-pointed star */}
        <motion.path
          d="M 20 4 C 20 14, 14 20, 4 20 C 14 20, 20 26, 20 36 C 20 26, 26 20, 36 20 C 26 20, 20 14, 20 4 Z"
          fill="url(#gemma-gradient)"
          animate={{ scale: [0.95, 1.05, 0.95] }}
          transition={{ duration: 2, ease: "easeInOut", repeat: Infinity }}
          style={{ transformOrigin: "50% 50%" }}
        />

        {/* Inner star (smaller, brighter) */}
        <motion.path
          d="M 20 10 C 20 16, 16 20, 10 20 C 16 20, 20 24, 20 30 C 20 24, 24 20, 30 20 C 24 20, 20 16, 20 10 Z"
          fill="url(#gemma-gradient-inner)"
          animate={{ scale: [1.05, 0.95, 1.05], opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 2, ease: "easeInOut", repeat: Infinity }}
          style={{ transformOrigin: "50% 50%" }}
        />

        <defs>
          <linearGradient id="gemma-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--color-accent-info)" stopOpacity="0.6" />
            <stop offset="50%" stopColor="var(--color-accent-insight)" stopOpacity="0.4" />
            <stop offset="100%" stopColor="var(--color-accent-info)" stopOpacity="0.6" />
          </linearGradient>
          <linearGradient id="gemma-gradient-inner" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--color-accent-info)" />
            <stop offset="100%" stopColor="var(--color-accent-insight)" />
          </linearGradient>
        </defs>
      </motion.svg>
    </div>
  );
}
