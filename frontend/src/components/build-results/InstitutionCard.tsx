interface InstitutionCardProps {
  schoolName: string;
  narrative: string;
}

export function InstitutionCard({ schoolName, narrative }: InstitutionCardProps) {
  const paragraphs = narrative.split("\n").filter((p) => p.trim());

  return (
    <div
      className="rounded-[20px] border border-border-subtle bg-bp-mid"
      style={{ padding: 24 }}
    >
      {/* Section label */}
      <div
        className="font-data font-bold uppercase text-accent-info"
        style={{ fontSize: 11, letterSpacing: 2, marginBottom: 16 }}
      >
        About the School
      </div>

      <div className="font-display font-bold text-text-primary" style={{ fontSize: 22 }}>
        {schoolName}
      </div>

      <div className="mt-4">
        {paragraphs.map((p, i) => (
          <p
            key={i}
            className="font-body text-text-secondary"
            style={{ fontSize: 15, lineHeight: 1.65, marginBottom: 12 }}
          >
            {p}
          </p>
        ))}
      </div>

      <div
        className="font-data text-text-muted mt-4"
        style={{ fontSize: 11, letterSpacing: "0.5px" }}
      >
        ✦ Written by Gemma
      </div>
    </div>
  );
}
