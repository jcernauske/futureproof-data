/**
 * HorizonFooter — full-bleed cinematic footer.
 *
 * Three-zone composite (sky-bleed + image stage + ground-bleed) plus a
 * three-column dark chrome bar (identity / provenance / studio). Picks a
 * random campus illustration on every page-load via `useHorizonPick`,
 * paired with one of three captions by `index % 3`.
 *
 * Pixel-perfect target: scripts/horizon-mockup.html
 * Spec: docs/specs/feature-horizon-footer.md §3
 */

import { useEffect, useRef } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";
import { useHorizonPick } from "@/hooks/useHorizonPick";

/**
 * Build the asset URL for a campus image variant.
 * The basename can contain parens (e.g. `..._0(1)`); encodeURIComponent
 * preserves the rest of the basename and percent-encodes special chars.
 */
function imageUrl(basename: string, size: 1400 | 2048, ext: "avif" | "webp"): string {
  return `/campus/${encodeURIComponent(basename)}-${size}.${ext}`;
}

interface HorizonPictureProps {
  basename: string;
}

/**
 * <picture> with AVIF → WebP, 1400 default, 2048 above 1200px viewport.
 * Decorative role; alt is intentionally empty per spec §3 Accessibility.
 */
function HorizonPicture({ basename }: HorizonPictureProps) {
  return (
    <picture>
      <source
        media="(min-width: 1200px)"
        type="image/avif"
        srcSet={imageUrl(basename, 2048, "avif")}
      />
      <source
        media="(min-width: 1200px)"
        type="image/webp"
        srcSet={imageUrl(basename, 2048, "webp")}
      />
      <source type="image/avif" srcSet={imageUrl(basename, 1400, "avif")} />
      <source type="image/webp" srcSet={imageUrl(basename, 1400, "webp")} />
      <img
        id="horizon-image"
        src={imageUrl(basename, 1400, "webp")}
        alt=""
        role="presentation"
        loading="lazy"
        decoding="async"
        className="block w-full h-full object-cover object-[center_40%]"
      />
    </picture>
  );
}

/** GemmaStar — 14px four-pointed star with info → insight gradient. */
function GemmaStar({ size = 14 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      aria-hidden="true"
      className="flex-shrink-0"
    >
      <defs>
        <linearGradient id="horizon-gemma-star" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--color-accent-info)" />
          <stop offset="100%" stopColor="var(--color-accent-insight)" />
        </linearGradient>
      </defs>
      <path
        d="M8 0.5 L9.6 6.4 L15.5 8 L9.6 9.6 L8 15.5 L6.4 9.6 L0.5 8 L6.4 6.4 Z"
        fill="url(#horizon-gemma-star)"
      />
    </svg>
  );
}

export function HorizonFooter() {
  const prefersReducedMotion = useReducedMotion();
  const pick = useHorizonPick("desktop");

  // Parallax: 0.85x scroll speed (translate at 0.15x of distance into vh),
  // gated by IntersectionObserver, driven by requestAnimationFrame.
  const stageRef = useRef<HTMLDivElement | null>(null);
  const parallaxRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (prefersReducedMotion) return;
    if (typeof window === "undefined") return;

    const stage = stageRef.current;
    const parallax = parallaxRef.current;
    if (!stage || !parallax) return;

    let isVisible = false;
    let rafHandle: number | null = null;

    const tick = () => {
      rafHandle = null;
      if (!isVisible) return;
      const rect = stage.getBoundingClientRect();
      const vh = window.innerHeight;
      // distance from viewport top to footer top
      const distance = vh - rect.top;
      // translate range: ~ -60px .. +40px
      const t = Math.max(-60, Math.min(40, (distance - vh * 0.5) * 0.15));
      parallax.style.transform = `translate3d(0, ${t.toFixed(2)}px, 0)`;
    };

    const scheduleTick = () => {
      if (rafHandle !== null) return;
      rafHandle = window.requestAnimationFrame(tick);
    };

    let observer: IntersectionObserver | null = null;
    if (typeof window.IntersectionObserver !== "undefined") {
      observer = new IntersectionObserver(
        (entries) => {
          // We only observe a single element (`stage`). Find the matching
          // entry defensively rather than assume `entries[0]` is ours, so a
          // future caller adding a second observe() target won't race on
          // shared `isVisible`.
          const entry = entries.find((e) => e.target === stage);
          if (!entry) return;
          isVisible = entry.isIntersecting;
          if (isVisible) scheduleTick();
        },
        { rootMargin: "0px" },
      );
      observer.observe(stage);
    } else {
      // No IO — assume always visible while mounted.
      isVisible = true;
      scheduleTick();
    }

    window.addEventListener("scroll", scheduleTick, { passive: true });
    window.addEventListener("resize", scheduleTick);

    return () => {
      // Critical cleanup: BOTH the observer AND the RAF handle must tear
      // down. Failing to cancel the RAF leaks a callback under React
      // StrictMode double-mount (arch review §5).
      if (observer) observer.disconnect();
      if (rafHandle !== null) {
        window.cancelAnimationFrame(rafHandle);
      }
      window.removeEventListener("scroll", scheduleTick);
      window.removeEventListener("resize", scheduleTick);
    };
  }, [prefersReducedMotion]);

  // Cold-mount sequence (1.6s total) per §3 Interactions.
  // Reduced motion: opacity-only fade-ins, 240ms.
  const skyBleedMotion = prefersReducedMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, transition: { duration: 0.24 } }
    : {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        transition: { duration: 0.8, ease: "easeOut" as const },
      };

  const imageMotion = prefersReducedMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, transition: { duration: 0.24 } }
    : {
        initial: { opacity: 0, scale: 1.02 },
        animate: { opacity: 1, scale: 1 },
        transition: springs.gentle,
      };

  const captionMotion = prefersReducedMotion
    ? {
        initial: { opacity: 0 },
        animate: { opacity: 0.6 },
        transition: { duration: 0.24 },
      }
    : {
        initial: { opacity: 0 },
        animate: { opacity: 0.6 },
        transition: { duration: 0.4, delay: 0.6, ease: "easeOut" as const },
      };

  const chromeContainerMotion = prefersReducedMotion
    ? {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        transition: { duration: 0.24 },
      }
    : {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        transition: {
          duration: 0.6,
          delay: 0.8,
          ease: "easeOut" as const,
          staggerChildren: stagger.normal,
        },
      };

  const chromeItemMotion = prefersReducedMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, transition: { duration: 0.24 } }
    : {
        initial: { opacity: 0, y: 8 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.6, ease: "easeOut" as const },
      };

  // Skeleton (pre-mount, hook returns null) — reserve aspect ratio so
  // the chrome bar lands without layout shift.
  const skeleton = (
    <div
      className="block w-full h-full bg-bp-deep"
      aria-hidden="true"
    />
  );

  return (
    <footer
      id="horizon-footer"
      className="relative w-full overflow-hidden isolate mt-20"
    >
      {/* Sky bleed: 120px, bg-deep -> transparent, overlays image top */}
      <motion.div
        aria-hidden="true"
        className="absolute top-0 left-0 right-0 z-[3] pointer-events-none"
        style={{
          height: "120px",
          background:
            "linear-gradient(180deg, var(--color-bg-deep) 0%, color-mix(in srgb, var(--color-bg-deep) 65%, transparent) 45%, transparent 100%)",
        }}
        {...skyBleedMotion}
      />

      {/* Image stage: aspect-ratio reservation prevents CLS */}
      <div
        ref={stageRef}
        className="relative w-full overflow-hidden z-[1] bg-bp-deep horizon-stage"
        style={{
          height: "clamp(220px, 22vw, 480px)",
        }}
      >
        <div
          ref={parallaxRef}
          className="absolute inset-0 will-change-transform"
          style={{ inset: "-8% 0 -8% 0" }}
        >
          {pick ? (
            <motion.div
              key={pick.index}
              className="w-full h-full horizon-image-wrap"
              {...imageMotion}
            >
              <HorizonPicture basename={pick.basename} />
            </motion.div>
          ) : (
            skeleton
          )}
        </div>

        {pick && (
          <motion.p
            className="absolute left-1/2 z-[4] font-data text-micro tracking-widest text-center whitespace-nowrap horizon-caption text-text-primary/60"
            style={{
              bottom: "88px",
              transform: "translateX(-50%)",
              textShadow: "0 1px 2px rgba(18, 19, 31, 0.95)",
              maxWidth: "92vw",
            }}
            {...captionMotion}
          >
            {pick.caption}
          </motion.p>
        )}

        {/* Ground bleed: 60px, transparent -> bg-void, overlays image bottom */}
        <div
          aria-hidden="true"
          className="absolute left-0 right-0 bottom-0 z-[3] pointer-events-none"
          style={{
            height: "60px",
            background:
              "linear-gradient(180deg, transparent 0%, color-mix(in srgb, var(--color-bg-void) 70%, transparent) 55%, var(--color-bg-void) 100%)",
          }}
        />
      </div>

      {/* Chrome bar: three-column desktop, stacks below 840px */}
      <motion.div
        className="relative z-[2] bg-bp-void border-t border-border-subtle px-6 tablet:px-12 py-7"
        {...chromeContainerMotion}
      >
        <div className="mx-auto max-w-[1280px] grid gap-8 horizon-chrome-grid items-start">
          {/* LEFT — identity */}
          <motion.div
            id="horizon-identity"
            className="flex flex-col gap-2 min-w-0"
            {...chromeItemMotion}
          >
            <span className="font-display font-bold text-heading text-text-primary leading-tight">
              FutureProof
            </span>
            <a
              id="horizon-live-app"
              href="/app"
              className="font-body text-body text-text-secondary hover:text-accent-thrive underline underline-offset-4 transition-colors duration-fast w-fit"
              style={{ textDecorationColor: "rgba(196, 191, 176, 0.3)" }}
            >
              Live app
            </a>
          </motion.div>

          {/* CENTER — provenance */}
          <motion.div
            className="flex flex-col gap-2 min-w-0 horizon-chrome-center"
            {...chromeItemMotion}
          >
            <div className="inline-flex items-center gap-2 font-body text-small text-text-secondary">
              <GemmaStar size={14} />
              <span>Built with Gemma 4</span>
            </div>
            <div className="font-data text-micro text-text-muted leading-snug">
              Submitted to Gemma 4 Good · Kaggle / Google DeepMind · 2026
            </div>
            <p className="mt-3 font-body text-small text-text-muted max-w-[420px] leading-snug horizon-disclaimer">
              AI-estimated. Not a substitute for professional career counseling.
            </p>
          </motion.div>

          {/* RIGHT — studio */}
          <motion.address
            id="horizon-studio"
            className="not-italic flex flex-col gap-2 min-w-0 horizon-chrome-right"
            {...chromeItemMotion}
          >
            <div className="inline-flex items-center gap-3">
              {/* TODO: replace with real HyenaStudios logo asset. */}
              <span
                aria-hidden="true"
                className="inline-flex items-center justify-center rounded-full border border-border-subtle font-display text-micro font-semibold text-text-secondary"
                style={{
                  width: "32px",
                  height: "32px",
                  background: "rgba(255, 255, 255, 0.02)",
                  letterSpacing: "0.04em",
                }}
              >
                HS
              </span>
              <span className="font-display font-semibold text-subheading text-text-secondary leading-tight">
                HyenaStudios
              </span>
            </div>
            <span className="font-data text-micro text-text-muted">© 2026</span>
          </motion.address>
        </div>
      </motion.div>

      {/* Scoped responsive CSS that Tailwind utilities can't express
          (object-position swap below 480px, caption hide, chrome stacking). */}
      <style>{`
        .horizon-chrome-grid {
          grid-template-columns: 1fr 1.2fr 1fr;
        }
        .horizon-chrome-center {
          align-items: center;
          text-align: center;
        }
        .horizon-chrome-right {
          align-items: flex-end;
          text-align: right;
        }
        @media (max-width: 839px) {
          .horizon-chrome-grid {
            grid-template-columns: 1fr;
            gap: 24px;
          }
          .horizon-chrome-center,
          .horizon-chrome-right {
            align-items: flex-start;
            text-align: left;
          }
          .horizon-disclaimer { max-width: none; }
        }
        @media (max-width: 480px) {
          .horizon-stage { height: 200px !important; }
          .horizon-image-wrap picture,
          .horizon-image-wrap img {
            object-position: center 30% !important;
          }
          .horizon-caption { display: none !important; }
        }
      `}</style>
    </footer>
  );
}
