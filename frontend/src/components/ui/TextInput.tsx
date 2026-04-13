interface TextInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export function TextInput({ label, className = "", ...props }: TextInputProps) {
  return (
    <input
      className={`bg-bp-mid text-text-primary font-body text-body px-4 py-3 rounded-md border border-border-subtle focus:border-border-strong focus:outline-none transition-colors duration-normal placeholder:text-text-muted ${className}`}
      aria-label={label}
      {...props}
    />
  );
}
