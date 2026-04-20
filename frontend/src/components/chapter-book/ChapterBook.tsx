/**
 * Chapter Book — container.
 *
 * Spec: docs/specs/feature-chapter-book.md §3.3. Props: career + onBack.
 * Fetches branches, buckets them via bucketBranches, renders chapters
 * inside the book surface.
 *
 * Loading/empty/error states per §3.6.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { stagger, staggerContainer } from "@/styles/motion";
import { getBranchesForSoc } from "@/api/tree";
import { socEmoji } from "@/data/socEmoji";
import { Button } from "@/components/ui/Button";
import type { CareerBranch } from "@/types/build";
import type { Chapter, ChapterBookProps } from "./types";
import { bucketBranches } from "./bucketBranches";
import { chapterCopy } from "./chapterCopy";
import { ChapterCard } from "./ChapterCard";

type FetchState =
  | { status: "loading" }
  | { status: "ready"; branches: CareerBranch[] }
  | { status: "error"; message: string };

export function ChapterBook({ career, onBack }: ChapterBookProps) {
  const reducedMotion = useReducedMotion();
  const [fetchState, setFetchState] = useState<FetchState>({ status: "loading" });
  const [retryToken, setRetryToken] = useState(0);
  const backButtonRef = useRef<HTMLButtonElement>(null);
  const bookRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setFetchState({ status: "loading" });
    getBranchesForSoc(career.soc_code)
      .then((branches) => {
        if (cancelled) return;
        setFetchState({ status: "ready", branches });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message =
          err instanceof Error
            ? err.message
            : "The data source was briefly unreachable. Try again in a moment.";
        setFetchState({ status: "error", message });
      });
    return () => {
      cancelled = true;
    };
  }, [career.soc_code, retryToken]);

  // Land focus on the back button once the book mounts (§3.2 focus
  // management). Skipped under reduced motion so screen readers don't
  // fight the student's own focus placement.
  useEffect(() => {
    backButtonRef.current?.focus();
  }, [career.soc_code]);

  // Esc anywhere inside the book closes it.
  useEffect(() => {
    const node = bookRef.current;
    if (!node) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onBack();
      }
    };
    node.addEventListener("keydown", handler);
    return () => node.removeEventListener("keydown", handler);
  }, [onBack]);

  const handleRetry = useCallback(() => {
    setRetryToken((n) => n + 1);
  }, []);

  const chapters: Chapter[] = useMemo(() => {
    if (fetchState.status !== "ready") return [];
    return bucketBranches(career, fetchState.branches);
  }, [career, fetchState]);

  const first = chapters[0];
  const last = chapters[chapters.length - 1];
  const liveAnnouncement =
    fetchState.status === "ready" && first !== undefined && last !== undefined
      ? `Reading the arc for ${career.occupation_title}. ${chapters.length} ${chapters.length === 1 ? "chapter" : "chapters"}, ${first.years_label} through ${last.years_label}.`
      : "";

  return (
    <section
      ref={bookRef}
      role="region"
      aria-labelledby={`chapter-book-title-${career.soc_code}`}
      className="bg-bp-mid/60 border border-border rounded-xl shadow-lg"
      data-testid={`chapter-book-${career.soc_code}`}
    >
      {/* Screen-reader-only live region. Silent while loading. */}
      <div
        aria-live="polite"
        className="sr-only"
        data-testid="chapter-book-live-region"
      >
        {liveAnnouncement}
      </div>

      {/* Title page */}
      <header className="flex items-start justify-between gap-3 px-6 pt-6 pb-5 border-b border-border-subtle">
        <div className="flex-1">
          <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-info">
            {chapterCopy.titlePage.eyebrow}
          </p>
          <div className="mt-2 flex items-baseline gap-3 flex-wrap">
            <span
              className="text-[28px] leading-none"
              aria-hidden="true"
            >
              {socEmoji(career.soc_code)}
            </span>
            <h2
              id={`chapter-book-title-${career.soc_code}`}
              data-testid={`chapter-book-title-${career.soc_code}`}
              className="font-display text-heading font-semibold text-text-primary"
            >
              {career.occupation_title}
            </h2>
          </div>
          <p className="mt-2 font-body text-body text-text-secondary max-w-[52ch]">
            {chapterCopy.titlePage.subtitle}
          </p>
        </div>
        <button
          type="button"
          ref={backButtonRef}
          onClick={onBack}
          aria-label={chapterCopy.back.ariaLabel}
          data-testid="chapter-book-back"
          className="shrink-0 inline-flex items-center gap-1 rounded-md px-2 py-1 font-body text-small text-text-muted hover:text-text-secondary cursor-pointer transition-colors duration-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]"
        >
          {chapterCopy.back.label}
        </button>
      </header>

      {/* Chapter stack — loading / error / ready */}
      {fetchState.status === "loading" ? (
        <ChapterSkeleton />
      ) : fetchState.status === "error" ? (
        <ChapterError message={fetchState.message} onRetry={handleRetry} onBack={onBack} />
      ) : (
        <motion.div
          variants={reducedMotion ? undefined : staggerContainer(0, stagger.normal)}
          initial={reducedMotion ? undefined : "hidden"}
          animate={reducedMotion ? undefined : "visible"}
          className="relative px-6 pt-6 pb-6 flex flex-col gap-4"
          data-testid="chapter-stack"
        >
          {/* Thread line */}
          <span
            aria-hidden="true"
            className="pointer-events-none absolute left-[28px] top-6 bottom-6 w-px bg-gradient-to-b from-accent-thrive/60 via-border to-border-subtle"
          />
          {chapters.map((chapter, idx) => (
            <ChapterCard
              key={`chapter-${chapter.number}`}
              chapter={chapter}
              isLast={idx === chapters.length - 1}
            />
          ))}
        </motion.div>
      )}
    </section>
  );
}

function ChapterSkeleton() {
  return (
    <div
      className="relative px-6 pt-6 pb-6 flex flex-col gap-4"
      data-testid="chapter-book-skeleton"
      aria-busy={true}
      aria-label="Loading the arc"
    >
      <span
        aria-hidden="true"
        className="pointer-events-none absolute left-[28px] top-6 bottom-6 w-px bg-border-subtle"
      />
      {[1, 2, 3].map((n) => (
        <div
          key={n}
          className="relative bg-bp-mid border border-border-subtle rounded-xl p-5"
        >
          <span className="absolute -left-[7px] top-6 w-3 h-3 rounded-full ring-2 ring-bp-deep bg-text-muted/40 animate-pulse" />
          <div className="h-3 w-28 bg-text-muted/20 rounded animate-pulse" />
          <div className="mt-3 h-4 w-1/2 bg-text-muted/20 rounded animate-pulse" />
          <div className="mt-3 h-3 w-[90%] bg-text-muted/20 rounded animate-pulse" />
          <div className="mt-2 h-3 w-[70%] bg-text-muted/20 rounded animate-pulse" />
          <div className="mt-4 h-5 w-[40%] bg-text-muted/20 rounded-full animate-pulse" />
        </div>
      ))}
    </div>
  );
}

function ChapterError({
  message,
  onRetry,
  onBack,
}: {
  message: string;
  onRetry: () => void;
  onBack: () => void;
}) {
  return (
    <div
      className="px-6 py-8 flex flex-col items-start gap-4"
      role="alert"
      data-testid="chapter-book-error"
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="text-accent-alert text-heading"
        >
          ⚠
        </span>
        <p className="font-body text-body text-text-secondary max-w-[52ch]">
          We couldn't load the arc for this role. {message}
        </p>
      </div>
      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          onClick={onRetry}
          data-testid="chapter-book-retry"
        >
          Retry
        </Button>
        <button
          type="button"
          onClick={onBack}
          aria-label={chapterCopy.back.ariaLabel}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 font-body text-small text-text-muted hover:text-text-secondary cursor-pointer transition-colors duration-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]"
        >
          {chapterCopy.back.label}
        </button>
      </div>
    </div>
  );
}
