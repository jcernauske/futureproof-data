/**
 * HorizonSilhouette — muted variant of HorizonFooter.
 *
 * Renders a single 180px-tall horizon image at 60% opacity behind the
 * share card on /app/save. Locked to a build's `horizonIndex` so user
 * device-screenshots are stable across remounts. No caption, no chrome,
 * no rotation. Purely atmospheric.
 *
 * Spec: docs/specs/feature-horizon-footer.md §3
 */

import { useHorizonAt } from "@/hooks/useHorizonPick";

function imageUrl(
  basename: string,
  size: 1400 | 2048,
  ext: "avif" | "webp",
): string {
  return `/campus/${encodeURIComponent(basename)}-${size}.${ext}`;
}

export interface HorizonSilhouetteProps {
  /** 0..47, locked at build commit. */
  index: number;
  className?: string;
}

export function HorizonSilhouette({ index, className }: HorizonSilhouetteProps) {
  const pick = useHorizonAt(index);

  return (
    <div
      id="horizon-silhouette"
      role="presentation"
      className={`relative w-full overflow-hidden rounded-xl ${className ?? ""}`}
      style={{
        height: "180px",
        opacity: 0.6,
        WebkitMaskImage:
          "linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.5) 28%, rgba(0, 0, 0, 1) 70%)",
        maskImage:
          "linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.5) 28%, rgba(0, 0, 0, 1) 70%)",
      }}
    >
      <picture>
        <source
          media="(min-width: 1200px)"
          type="image/avif"
          srcSet={imageUrl(pick.basename, 2048, "avif")}
        />
        <source
          media="(min-width: 1200px)"
          type="image/webp"
          srcSet={imageUrl(pick.basename, 2048, "webp")}
        />
        <source
          type="image/avif"
          srcSet={imageUrl(pick.basename, 1400, "avif")}
        />
        <source
          type="image/webp"
          srcSet={imageUrl(pick.basename, 1400, "webp")}
        />
        <img
          src={imageUrl(pick.basename, 1400, "webp")}
          alt=""
          role="presentation"
          loading="eager"
          decoding="async"
          className="block w-full h-full object-cover"
          style={{ objectPosition: "center 35%" }}
        />
      </picture>
    </div>
  );
}
