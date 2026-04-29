/**
 * BranchHighlightDriver — parses Gemma's latest assistant response for
 * branch-title matches and emits ``onHighlight(nodeId)`` per match so
 * the tree can flash the corresponding node.
 *
 * Decision #4 (feature-tree-as-map.md §2): bidirectional binding via
 * response-text parsing, not structured tool output. Keeps the prompt
 * simple and the round-trip latency low.
 *
 * Hygiene rules (fp-architect condition #3):
 *   (a) sort candidate titles by descending length so the long match
 *       wins regardless of order in the response.
 *   (b) lookahead/lookbehind anchors restricted to ASCII word chars
 *       so "Analyst" doesn't fire inside "Analytical" / "Analysts'".
 *       NOT JavaScript `\b` — word-boundary fails on titles whose
 *       last char is a regex non-word character (e.g.
 *       "Designers (Industrial)" — the trailing `)` is non-word, the
 *       next space in prose is also non-word, and `\b` requires a
 *       word↔non-word transition. Caught in code review (faang-staff
 *       Finding 1, 2026-04-28).
 *   (c) case-insensitive comparison.
 *   (d) escape regex metacharacters in titles — real O*NET titles
 *       contain `,` `(` `/` and naive regex compilation will throw or
 *       silently mis-match.
 *
 * Dedup: same node fires at most once per 1000ms window (a single
 * Gemma response can name the same branch twice in two sentences).
 *
 * Stagger: when one response names multiple distinct nodes, fires the
 * highlights 200ms apart so the tree reads as a sequence, not a flash
 * mob.
 *
 * Invariant (fp-architect condition #5): ``onHighlight`` MUST be
 * presentational only — wiring it into ``selectedNodeId`` will create
 * an infinite re-fire loop (assistant names branch → highlight fires →
 * selection moves → opener re-fires → assistant names another branch
 * → …).
 */

import { useEffect, useMemo, useRef } from "react";

interface HighlightCandidate {
  /** React Flow node id (e.g. ``career-13-1011-2``). */
  id: string;
  /** Display title used for matching against Gemma's response. */
  title: string;
}

interface BranchHighlightDriverProps {
  nodes: HighlightCandidate[];
  latestResponse: string | null;
  onHighlight: (nodeId: string) => void;
}

const DEDUP_WINDOW_MS = 1000;
const STAGGER_MS = 200;

function escapeRegex(literal: string): string {
  return literal.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function buildMatcher(
  titles: { id: string; title: string }[],
): {
  scan: (text: string) => string[];
} {
  if (titles.length === 0) {
    return { scan: () => [] };
  }
  // Descending-length sort so longest match wins (fp-architect #3a).
  const sorted = [...titles].sort((a, b) => b.title.length - a.title.length);
  // Build an alternation pattern with ASCII-word lookaround anchors +
  // escaped metacharacters (fp-architect #3b/#3d, faang-staff Finding 1).
  // Case-insensitive (#3c). Why not `\b`: JavaScript's `\b` requires a
  // word↔non-word transition. Real-world O*NET titles like
  // "Designers (Industrial)" end in `)` (non-word), and the typical
  // following character in prose is a space (also non-word) — that's
  // non-word→non-word, NOT a `\b`, so the match silently fails. The
  // negative lookarounds below assert "not adjacent to a word
  // character" which works whether the title's edge char is a word
  // char or not.
  const alternation = sorted
    .map((t) => escapeRegex(t.title))
    .join("|");
  const pattern = new RegExp(
    `(?<![A-Za-z0-9_])(?:${alternation})(?![A-Za-z0-9_])`,
    "gi",
  );
  const titleByLower = new Map(
    sorted.map((t) => [t.title.toLowerCase(), t.id]),
  );

  return {
    scan(text: string): string[] {
      if (!text) return [];
      // Replace previously-matched spans with whitespace so a longer
      // match consumes its substring tokens — this guarantees
      // longest-match-wins regardless of textual order.
      let working = text;
      const out: string[] = [];
      const seen = new Set<string>();
      const re = new RegExp(pattern.source, "gi");
      let m: RegExpExecArray | null;
      while ((m = re.exec(working)) !== null) {
        const matched = m[0].toLowerCase();
        const id = titleByLower.get(matched);
        if (id && !seen.has(id)) {
          out.push(id);
          seen.add(id);
        }
        // Replace this span with whitespace so the next iteration
        // doesn't re-match a sub-token.
        working =
          working.slice(0, m.index) +
          " ".repeat(m[0].length) +
          working.slice(m.index + m[0].length);
        re.lastIndex = m.index + m[0].length;
      }
      return out;
    },
  };
}

export function BranchHighlightDriver({
  nodes,
  latestResponse,
  onHighlight,
}: BranchHighlightDriverProps) {
  // Pre-build the regex once per node set so we don't recompile on
  // every response.
  const matcher = useMemo(() => buildMatcher(nodes), [nodes]);

  // Per-node "last fired at" timestamp for dedup.
  const lastFiredRef = useRef<Map<string, number>>(new Map());

  useEffect(() => {
    if (!latestResponse) return;
    const matches = matcher.scan(latestResponse);
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.debug(
        "[BranchHighlightDriver] scan",
        { responseLen: latestResponse.length, candidateCount: nodes.length, matches },
      );
    }
    if (matches.length === 0) return;
    const now = Date.now();
    const timeoutIds: number[] = [];
    let staggerIndex = 0;
    for (const id of matches) {
      const lastFired = lastFiredRef.current.get(id) ?? 0;
      if (now - lastFired < DEDUP_WINDOW_MS) continue;
      lastFiredRef.current.set(id, now);
      const delay = staggerIndex * STAGGER_MS;
      const tid = window.setTimeout(() => {
        onHighlight(id);
      }, delay);
      timeoutIds.push(tid);
      staggerIndex += 1;
    }
    return () => {
      for (const tid of timeoutIds) window.clearTimeout(tid);
    };
  }, [latestResponse, matcher, onHighlight]);

  return null;
}
