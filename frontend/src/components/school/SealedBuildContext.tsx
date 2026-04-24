import type { SchoolSelection } from "@/types/buildInput";
import type { CareerOutcome } from "@/types/build";

interface SealedBuildContextProps {
  school: SchoolSelection;
  resolvedTitle: string;
  cipCode: string;
  career: CareerOutcome;
  onStartOver: () => void;
}

function Badge({
  accentClass,
  label,
  children,
}: {
  accentClass: string;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-bp-mid border border-border-subtle rounded-xl p-5">
      <span
        className={`inline-block font-data font-bold uppercase tracking-[2px] px-3 py-1 rounded-full mb-3 ${accentClass}`}
        style={{ fontSize: 12 }}
      >
        {label}
      </span>
      {children}
    </div>
  );
}

export function SealedBuildContext({
  school,
  resolvedTitle,
  cipCode,
  career,
  onStartOver,
}: SealedBuildContextProps) {
  const location = [school.stateAbbr, school.institutionControl]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 desktop:grid-cols-2 gap-4">
        <Badge accentClass="text-accent-info bg-accent-info/15" label="Your school">
          <p className="font-display text-subheading font-semibold text-text-primary">
            {school.name}
          </p>
          {location && (
            <p className="font-body text-small text-text-muted mt-1">{location}</p>
          )}
        </Badge>

        <Badge accentClass="text-accent-insight bg-accent-insight/15" label="Your field of study">
          <p className="font-display text-subheading font-semibold text-accent-insight">
            {resolvedTitle}
          </p>
          <p className="font-data text-text-muted mt-1" style={{ fontSize: 13 }}>
            CIP {cipCode}
          </p>
        </Badge>
      </div>

      <div
        className="bg-bp-mid border border-border-subtle rounded-xl p-5"
        style={{ borderLeft: "3px solid var(--color-accent-thrive)" }}
      >
        <span
          className="inline-block font-data font-bold uppercase tracking-[2px] text-accent-thrive mb-2"
          style={{ fontSize: 12 }}
        >
          Selected career
        </span>
        <p className="font-display text-subheading font-semibold text-text-primary">
          {career.occupation_title}
        </p>
        <p className="font-data text-text-muted mt-1" style={{ fontSize: 13 }}>
          SOC {career.soc_code}
        </p>
      </div>

      <p className="font-body text-small text-text-muted italic">
        Need to change your school or major?{" "}
        <button
          type="button"
          onClick={onStartOver}
          className="text-accent-info hover:underline cursor-pointer bg-transparent border-none font-body text-small italic"
        >
          Start over
        </button>
        .
      </p>
    </div>
  );
}
