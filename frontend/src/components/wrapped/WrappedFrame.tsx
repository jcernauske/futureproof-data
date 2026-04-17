import { useState } from "react";

interface WrappedFrameProps {
  src: string;
  index: number;
  label: string;
}

const FRAME_LABELS: Record<number, string> = {
  0: "Identity — your build's name and school",
  1: "Pentagon — your five stats in radar form",
  2: "Boss gauntlet — five career threats and your verdict",
  3: "Standout — your strongest stat",
  4: "Biggest risk — the fight that hit hardest",
  5: "Your turn — invite your friends to build theirs",
};

export function WrappedFrame({ src, index, label }: WrappedFrameProps) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div
        role="img"
        data-testid={`frame-${index}`}
        aria-label={`Frame ${index + 1} failed to load`}
        className="w-full h-full flex items-center justify-center bg-bp-void p-8"
      >
        <p className="text-body text-accent-alert text-center">
          This frame didn't develop. Tap Retry below.
        </p>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full bg-bp-void overflow-hidden">
      {!loaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-bp-void">
          <div
            className="w-16 h-16 rounded-full"
            style={{
              background:
                "radial-gradient(circle, rgba(125,212,163,0.35) 0%, transparent 70%)",
            }}
          />
        </div>
      )}
      <img
        src={src}
        alt={FRAME_LABELS[index] || label}
        data-testid={`frame-${index}`}
        onLoad={() => setLoaded(true)}
        onError={() => setFailed(true)}
        className="w-full h-full object-cover"
        style={{ opacity: loaded ? 1 : 0, transition: "opacity 180ms ease-out" }}
      />
    </div>
  );
}
