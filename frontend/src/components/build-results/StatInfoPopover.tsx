import { useEffect, useRef } from "react";
import { STAT_INFO, STAT_COLORS } from "./bossData";

interface StatInfoPopoverProps {
  stat: string;
  isOpen: boolean;
  onClose: () => void;
}

export function StatInfoPopover({ stat, isOpen, onClose }: StatInfoPopoverProps) {
  const ref = useRef<HTMLDivElement>(null);
  const info = STAT_INFO[stat];
  const colors = STAT_COLORS[stat];

  useEffect(() => {
    if (!isOpen) return;

    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }

    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [isOpen, onClose]);

  if (!isOpen || !info || !colors) return null;

  return (
    <div
      ref={ref}
      id={`info-${stat}`}
      role="region"
      className="rounded-[14px] bg-bp-raised border border-border-default"
      style={{
        padding: 20,
        borderLeft: `3px solid ${colors.text}`,
        boxShadow: "var(--shadow-lg, 0 8px 32px rgba(27,29,48,0.7))",
        animation: "popoverIn 180ms cubic-bezier(0.34, 1.4, 0.64, 1) both",
        marginTop: 8,
      }}
    >
      <div className="font-display font-semibold text-text-primary" style={{ fontSize: 14 }}>
        {info.title}
      </div>
      <p className="font-body text-text-secondary mt-2" style={{ fontSize: 14, lineHeight: 1.5 }}>
        {info.definition}
      </p>
      <div className="font-data text-text-muted" style={{ fontSize: 11, letterSpacing: "0.5px", marginTop: 10 }}>
        Source: {info.source}
      </div>

      <style>{`
        @keyframes popoverIn {
          from { opacity: 0; transform: translateY(-6px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
