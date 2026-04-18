import { useState } from "react";

/**
 * `<picture>` + WebP/PNG fallback with a skeleton placeholder that renders
 * when both sources fail to load. Mirrors the `OllamaSection` laptop probe
 * pattern so the landing never ships a browser broken-image icon if the
 * Week 2 screenshot capture slips. See spec §6 Deviation (onError fallback).
 */
interface ScreenshotWithFallbackProps {
  slug: string; // e.g. "01-reveal" — resolves to /assets/screenshots/landing/{slug}.webp and .png
  alt: string;
  id?: string;
  className?: string;
}

export function ScreenshotWithFallback({
  slug,
  alt,
  id,
  className,
}: ScreenshotWithFallbackProps) {
  const [available, setAvailable] = useState(true);

  if (!available) {
    return (
      <div
        id={id}
        role="img"
        aria-label={alt}
        className={`${className ?? ""} bg-bp-surface border border-border-subtle flex items-center justify-center`}
      >
        <span className="font-data text-[11px] tracking-[2px] uppercase text-text-muted opacity-60">
          Screenshot pending capture
        </span>
      </div>
    );
  }

  return (
    <picture>
      <source
        type="image/webp"
        srcSet={`/assets/screenshots/landing/${slug}.webp`}
      />
      <img
        id={id}
        src={`/assets/screenshots/landing/${slug}.png`}
        alt={alt}
        loading="lazy"
        decoding="async"
        className={className}
        onError={() => setAvailable(false)}
      />
    </picture>
  );
}
