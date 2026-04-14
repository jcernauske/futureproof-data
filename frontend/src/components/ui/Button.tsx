import type { HTMLMotionProps } from "framer-motion";
import { motion } from "framer-motion";
import { springs } from "@/styles/motion";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "icon";

interface ButtonProps extends HTMLMotionProps<"button"> {
  variant?: ButtonVariant;
  loading?: boolean;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-accent-thrive text-text-inverse font-bold text-cta h-12 px-[28px] hover:bg-[#6bc494] hover:shadow-glow-thrive",
  secondary:
    "bg-transparent text-accent-info border border-accent-info h-[44px] px-6 text-body-sm hover:bg-accent-info/10",
  ghost:
    "bg-transparent text-text-secondary h-10 px-4 text-small hover:text-text-primary hover:bg-white/5",
  danger:
    "bg-accent-alert/15 text-accent-alert h-[44px] px-6 text-body-sm hover:bg-accent-alert/25",
  icon:
    "bg-bp-surface text-text-primary w-10 h-10 !rounded-full text-body-lg !px-0 hover:bg-bp-raised",
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
