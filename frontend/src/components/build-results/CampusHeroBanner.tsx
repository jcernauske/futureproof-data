import { useHorizonPick } from "@/hooks/useHorizonPick";

function imageUrl(basename: string, size: 1400 | 2048, ext: "avif" | "webp"): string {
  return `/campus/${encodeURIComponent(basename)}-${size}.${ext}`;
}

export function CampusHeroBanner() {
  const pick = useHorizonPick("desktop");

  return (
    <div
      className="relative w-full overflow-hidden"
      style={{ height: "280px" }}
      role="img"
      aria-label="Campus atmosphere"
    >
      {pick ? (
        <picture
          className="block w-full h-full"
          style={{ animation: "heroFadeIn 0.8s ease-out both" }}
        >
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
          <source type="image/avif" srcSet={imageUrl(pick.basename, 1400, "avif")} />
          <source type="image/webp" srcSet={imageUrl(pick.basename, 1400, "webp")} />
          <img
            src={imageUrl(pick.basename, 1400, "webp")}
            alt=""
            role="presentation"
            loading="eager"
            decoding="async"
            className="block w-full h-full object-cover object-[center_40%]"
          />
        </picture>
      ) : (
        <div className="w-full h-full bg-bp-surface" style={{ animation: "shimmer 1.5s ease-in-out infinite" }} />
      )}

      {/* 180px 3-stop gradient fade */}
      <div
        aria-hidden="true"
        className="absolute bottom-0 left-0 right-0 pointer-events-none"
        style={{
          height: "180px",
          background: "linear-gradient(to bottom, transparent 0%, rgba(27,29,48,0.5) 35%, #1B1D30 100%)",
        }}
      />

      <style>{`
        @keyframes heroFadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        @media (max-width: 767px) {
          [role="img"][aria-label="Campus atmosphere"] { height: 200px !important; }
        }
      `}</style>
    </div>
  );
}
