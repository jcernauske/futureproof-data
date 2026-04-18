import { Link } from "react-router-dom";
import { PageContainer } from "@/components/ui/PageContainer";

export function PlaceholderScreen({ label }: { label: string }) {
  return (
    <div className="min-h-screen pt-14">
      <PageContainer variant="centered">
        <div className="min-h-[calc(100vh-56px)] flex flex-col items-center justify-center gap-6">
          <p className="font-body text-heading text-text-secondary">{label}</p>
          <Link
            to="/app"
            className="font-body text-body text-accent-thrive underline underline-offset-4"
          >
            Back to start
          </Link>
        </div>
      </PageContainer>
    </div>
  );
}
