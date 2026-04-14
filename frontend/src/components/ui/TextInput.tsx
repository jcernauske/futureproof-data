interface TextInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  large?: boolean;
}

export function TextInput({ label, large, className = "", ...props }: TextInputProps) {
  return (
    <input
      className={`bg-bp-deep text-text-primary font-body text-body px-4 py-3 rounded-md border border-border focus:border-accent-info focus:shadow-[0_0_0_3px_var(--color-focus-ring)] focus:outline-none transition-all duration-normal placeholder:text-text-muted ${
        large ? "h-14 text-body-lg rounded-lg" : "h-12"
      } ${className}`}
      aria-label={label}
      {...props}
    />
  );
}
