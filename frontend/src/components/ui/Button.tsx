import type { HTMLMotionProps } from "framer-motion";
import { motion } from "framer-motion";
import { springs } from "@/styles/motion";

type ButtonVariant = "primary" | "secondary";

interface ButtonProps extends HTMLMotionProps<"button"> {
  variant?: ButtonVariant;
  loading?: boolean;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-accent-thrive text-text-inverse font-bold text-cta px-10 py-4 hover:shadow-glow-thrive",
  secondary:
    "bg-bp-surface text-text-secondary font-body text-small px-5 py-3",
};

export function Button({
  variant = "primary",
  loading = false,
  disabled,
  children,
  className = "",
  ...props
}: ButtonProps) {
  return (
    <motion.button
      className={`rounded-lg font-body transition-all duration-normal ${variantStyles[variant]} ${
        disabled || loading ? "opacity-60 cursor-not-allowed" : "cursor-pointer"
      } ${className}`}
      disabled={disabled || loading}
      whileHover={disabled || loading ? undefined : { scale: 1.02 }}
      whileTap={disabled || loading ? undefined : { scale: 0.97 }}
      transition={springs.snappy}
      {...props}
    >
      {loading ? (
        <span className="inline-block w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        children
      )}
    </motion.button>
  );
}
