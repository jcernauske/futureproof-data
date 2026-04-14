import { Link } from "react-router-dom";

export function PlaceholderScreen({ label }: { label: string }) {
  return (
    <div className="min-h-screen bg-bp-deep flex flex-col items-center justify-center gap-6 pt-14">
      <p className="font-body text-heading text-text-secondary">{label}</p>
      <Link
        to="/"
        className="font-body text-body text-accent-thrive underline underline-offset-4"
      >
        Back to start
      </Link>
    </div>
  );
}
