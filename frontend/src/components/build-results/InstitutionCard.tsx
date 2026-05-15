import { useT } from "@/i18n/useT";

interface InstitutionCardProps {
  schoolName: string;
  narrative: string;
}

export function InstitutionCard({ schoolName, narrative }: InstitutionCardProps) {
  const t = useT();
  const paragraphs = narrative ? narrative.split("\n").filter((p) => p.trim()) : [];

  return (
    <div
      className="flex flex-col rounded-[20px] border border-border-subtle bg-bp-mid h-full"
      style={{ padding: 24 }}
    >
      {/* Section label */}
      <div
        className="font-data font-bold uppercase text-accent-info"
        style={{ fontSize: 11, letterSpacing: 2, marginBottom: 16 }}
      >
        {t("build.aboutSchool")}
      </div>

      <div className="font-display font-bold text-text-primary" style={{ fontSize: 22 }}>
        {schoolName}
      </div>

      <div className="mt-4 flex-1">
        {paragraphs.length > 0 ? (
          paragraphs.map((p, i) => (
            <p
              key={i}
              className="font-body text-text-secondary"
              style={{ fontSize: 15, lineHeight: 1.65, marginBottom: 12 }}
            >
              {p}
            </p>
          ))
        ) : (
          <div data-testid="guidance-loading" aria-label="Loading guidance">
            <div className="flex items-center gap-2 mb-4">
              <div
                className="rounded-full flex-shrink-0"
                style={{
                  width: 16,
                  height: 16,
                  border: "2px solid rgba(255,255,255,0.08)",
                  borderTopColor: "var(--color-accent-insight)",
                  animation: "guidanceSpin 0.8s linear infinite",
                }}
              />
              <span
                className="font-body text-text-muted"
                style={{ fontSize: 14, animation: "guidancePulse 2s ease-in-out infinite" }}
              >
                Writing…
              </span>
            </div>
            {[85, 100, 70].map((w, i) => (
              <div
                key={i}
                className="rounded"
                style={{
                  height: 12,
                  width: `${w}%`,
                  background: "rgba(255,255,255,0.04)",
                  marginBottom: 10,
                  animation: `guidancePulse 2s ease-in-out ${i * 0.3}s infinite`,
                }}
              />
            ))}
          </div>
        )}
      </div>

      <div
        className="font-data text-text-muted mt-4"
        style={{ fontSize: 11, letterSpacing: "0.5px" }}
      >
        {t("build.writtenByGemma")}
      </div>

      <style>{`
        @keyframes guidancePulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.7; }
        }
        @keyframes guidanceSpin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
