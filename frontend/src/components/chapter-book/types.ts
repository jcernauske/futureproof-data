/**
 * Chapter Book — shared types.
 *
 * Spec: docs/specs/feature-chapter-book.md §4 Data Model Changes.
 *
 * Consumers: ChapterBook.tsx, ChapterCard.tsx, bucketBranches.ts, tests.
 */
import type { CareerOutcome } from "@/types/build";
import type { StatKey } from "@/data/statExplanations";

export type ChapterKind = "anchor" | "role" | "locked" | "ceiling";

export type ChapterTier = "entry" | "early" | "mid" | "senior";

export interface Chapter {
  number: 1 | 2 | 3 | 4;
  // Final wording owned by @fp-design-visionary in §3; ranges must match
  // the Silver canonical tiers (feature-chapter-book Decision #14).
  years_label: string;
  tier: ChapterTier;
  kind: ChapterKind;
  // Role title (or ceiling headline for kind === "ceiling").
  title: string;
  // null on pure ceiling chapters.
  soc: string | null;
  // One-to-three sentences. Anchor and ceiling pull from chapterCopy.ts.
  what_changes: string;
  // Composed display string from the backend; pass through.
  unlock: string | null;
  // Typed education-level signal (feature-chapter-book Decision #12).
  related_education_level: string | null;
  // Derived from related_education_level (primary) or unlock (fallback).
  requires_grad_degree: boolean;
  // Stat deltas; zeros stripped so the pill row never renders a "+0".
  deltas: Partial<Record<StatKey, number>>;
  // Populated only on the anchor chapter — the parent career's full
  // five-stat pentagon, shown as "STATS TODAY" instead of deltas.
  stats_snapshot?: Partial<Record<StatKey, number>>;
}

export interface ChapterBookProps {
  career: CareerOutcome;
  onBack: () => void;
}
