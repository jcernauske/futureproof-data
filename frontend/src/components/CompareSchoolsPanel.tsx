import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  fetchSchoolsByCipAndSoc,
  fetchSchoolsBySoc,
} from "@/api/careers";
import { useT } from "@/i18n/useT";
import { fmtMoney, statRoiColorClass } from "@/lib/format";
import type {
  ConfidenceTier,
  LeaderboardMode,
  SchoolForCareerRow,
  SchoolsForCareerResponse,
} from "@/types/build";

// Anchor descriptor for the build the panel is "for". `unitid` + `cipcode`
// identify the row; the optional `*Stat*` + display fields let the panel
// render a synthetic anchor row when the build's CIP-substituted program
// has no entry in the leaderboard universe (the backend returns
// `anchor_estimated_rank` and the frontend builds the row from these).
export interface CompareSchoolsAnchor {
  unitid: number;
  cipcode: string;
  statErn?: number | null;
  statRoi?: number | null;
  institutionName?: string;
  institutionControl?: string | null;
  programName?: string;
  stateAbbr?: string | null;
  earnings1yrMedian?: number | null;
  netPriceAnnual?: number | null;
  // Residency-aware 4-year sticker — what the FINANCES card shows.
  // When the build's (unitid, cipcode) is absent from the leaderboard
  // universe and the panel renders a synthetic anchor row, this drives
  // the "Cost (4 yr)" column so the value matches the FINANCES card.
  publishedCost4yr?: number | null;
}

export interface CompareSchoolsPanelProps {
  mode: LeaderboardMode;
  enclosure: "sheet" | "inline";
  socCode: string;
  cipcode?: string;
  occupationTitle: string;
  programName?: string;
  anchor?: CompareSchoolsAnchor;
  // Two-letter US state code for the student's home state. When set,
  // each row's stat_roi and published_cost_4yr are residency-adjusted
  // by the backend so the leaderboard is apples-to-apples with the
  // anchor build's FINANCES card (spec roi-net-lifetime-value followup).
  homeState?: string | null;
  // Sheet only.
  open?: boolean;
  onClose?: () => void;
  // Inline only.
  defaultExpanded?: boolean;
  // Optional: when provided, each row gets a "build at this school" action.
  // The host owns the actual build-spawn logic + sheet close.
  onBuildAtRow?: (row: SchoolForCareerRow) => void;
  // When true, slide the sheet left by the Ask Gemma drawer's 360px
  // tablet+ width and clamp max-width so the panel doesn't overflow into
  // the chat surface. No-op below the tablet breakpoint where chat is a
  // full-screen modal. Sheet-enclosure only.
  chatOpen?: boolean;
}

function interpolate(
  template: string,
  values: Record<string, string | number>,
): string {
  return Object.entries(values).reduce(
    (acc, [k, v]) => acc.replace(`{${k}}`, String(v)),
    template,
  );
}

function shortenProgramName(name: string): string {
  const cut = name.split(/[.—]/, 1)[0] ?? name;
  return cut.trim();
}

interface PanelDataState {
  status: "idle" | "loading" | "ok" | "empty" | "error";
  response: SchoolsForCareerResponse | null;
  error: string | null;
}

const INITIAL: PanelDataState = { status: "idle", response: null, error: null };

export function CompareSchoolsPanel(props: CompareSchoolsPanelProps) {
  const { enclosure, open, onClose, defaultExpanded, chatOpen } = props;
  const isOpen = enclosure === "sheet" ? Boolean(open) : true;
  const [expanded, setExpanded] = useState<boolean>(
    enclosure === "inline" ? Boolean(defaultExpanded) : true,
  );
  const showBody = enclosure === "sheet" ? isOpen : expanded;

  // Mode is now an in-sheet filter, not a fixed prop. The prop seeds the
  // initial mode; the user toggles between BY CAREER (all majors) and
  // BY MAJOR + CAREER (their major) via a chip pair in the header. The
  // chip pair is only meaningful when both a cipcode AND a programName
  // are available — otherwise we lock to the seeded mode.
  const canToggleMode = Boolean(props.cipcode && props.programName);
  const [activeMode, setActiveMode] = useState<LeaderboardMode>(props.mode);

  // Lift data + filter state into the parent so the inline disclosure
  // toggle does NOT unmount/remount the body and force a refetch.
  const [data, setData] = useState<PanelDataState>(INITIAL);
  const [minConfidence, setMinConfidence] = useState<ConfidenceTier>("medium");
  // Generation counter to discard stale fetches when filters change rapidly.
  const reqIdRef = useRef(0);
  const fetchedKeyRef = useRef<string>("");

  const load = useCallback(
    async (mode: LeaderboardMode, confidence: ConfidenceTier) => {
      const myId = ++reqIdRef.current;
      setData({ status: "loading", response: null, error: null });
      try {
        const a = props.anchor;
        const opts = {
          limit: 10,
          minConfidence: confidence,
          buildUnitid: a?.unitid,
          buildCipcode: a?.cipcode,
          // Forward home_state so each row's published_cost_4yr and
          // stat_roi are residency-aware (matches the FINANCES card).
          homeState: props.homeState ?? undefined,
          // Send build-time stats so the backend can compute
          // anchor_estimated_rank when the (unitid, cipcode) is absent
          // from the filtered universe. Both must be present and finite.
          anchorStatErn:
            typeof a?.statErn === "number" ? a.statErn : undefined,
          anchorStatRoi:
            typeof a?.statRoi === "number" ? a.statRoi : undefined,
        };
        const response =
          mode === "by_cip_and_soc" && props.cipcode
            ? await fetchSchoolsByCipAndSoc(props.cipcode, props.socCode, opts)
            : await fetchSchoolsBySoc(props.socCode, opts);
        if (myId !== reqIdRef.current) return; // stale — newer fetch is in flight
        if (response.rows.length === 0) {
          setData({ status: "empty", response, error: null });
        } else {
          setData({ status: "ok", response, error: null });
        }
      } catch (err) {
        if (myId !== reqIdRef.current) return;
        const message = err instanceof Error ? err.message : "fetch failed";
        setData({ status: "error", response: null, error: message });
      }
    },
    [
      props.socCode,
      props.cipcode,
      props.anchor?.unitid,
      props.anchor?.cipcode,
      props.anchor?.statErn,
      props.anchor?.statRoi,
    ],
  );

  // Fetch only on first reveal per (soc, cip, anchor) tuple OR when the
  // user toggles activeMode / minConfidence in the sheet.
  useEffect(() => {
    if (!showBody) return;
    const key = [
      activeMode,
      props.socCode,
      props.cipcode ?? "",
      props.anchor?.unitid ?? "",
      props.anchor?.cipcode ?? "",
      props.homeState ?? "",
      minConfidence,
    ].join("|");
    if (fetchedKeyRef.current === key) return;
    fetchedKeyRef.current = key;
    load(activeMode, minConfidence);
  }, [
    showBody,
    activeMode,
    minConfidence,
    props.socCode,
    props.cipcode,
    props.anchor?.unitid,
    props.anchor?.cipcode,
    props.homeState,
    load,
  ]);

  // Invalidate any in-flight request on unmount.
  useEffect(() => () => { reqIdRef.current++; }, []);

  const showAll = useCallback(() => {
    setMinConfidence("low");
  }, []);

  const restoreDefault = useCallback(() => {
    setMinConfidence("medium");
  }, []);

  // When the backend returned an estimated rank for an anchor that
  // isn't in the filtered universe, splice a synthetic anchor row built
  // from the build's own stats into the response. PanelTable's
  // anchor-row rendering (highlight + divider + "Ranked X of Y" callout)
  // works off `is_anchor` flags on rows, so this is the smallest seam.
  const displayData = useMemo<PanelDataState>(() => {
    if (data.status !== "ok" || !data.response) return data;
    const r = data.response;
    if (r.anchor_estimated_rank == null) return data;
    if (r.rows.some((row) => row.is_anchor)) return data;
    const a = props.anchor;
    if (!a || a.statErn == null || a.statRoi == null) return data;
    const synthRow: SchoolForCareerRow = {
      rank: r.anchor_estimated_rank,
      unitid: a.unitid,
      institution_name: a.institutionName ?? "Your school",
      institution_control: a.institutionControl ?? null,
      state_abbr: a.stateAbbr ?? null,
      cipcode: a.cipcode,
      program_name: a.programName ?? "—",
      soc_code: r.soc_code,
      occupation_title: r.occupation_title,
      stat_ern: a.statErn,
      stat_roi: a.statRoi,
      earnings_1yr_median: a.earnings1yrMedian ?? null,
      net_price_annual: a.netPriceAnnual ?? null,
      cost_of_attendance_annual: null,
      tuition_in_state: null,
      tuition_out_of_state: null,
      // Use the build's residency-aware 4-year sticker (already
      // computed by the backend stat_engine for the user's anchor).
      // Falls back to null if the host didn't pass it; the cost cell
      // then renders "—" rather than a wrong value.
      published_cost_4yr: a.publishedCost4yr ?? null,
      stat_roi_in_state: null,
      roi_residency_adjusted: false,
      overall_confidence: "low",
      confidence_tier_program: null,
      match_quality: "estimated",
      family_size: 1,
      is_anchor: true,
    };
    return {
      ...data,
      response: { ...r, rows: [...r.rows, synthRow] },
    };
  }, [data, props.anchor]);

  const body = (
    <PanelBody
      mode={activeMode}
      occupationTitle={props.occupationTitle}
      programName={props.programName}
      data={displayData}
      minConfidence={minConfidence}
      onShowAll={showAll}
      onRestoreDefault={restoreDefault}
      onRetry={() => load(activeMode, minConfidence)}
      canToggleMode={canToggleMode}
      onModeChange={setActiveMode}
      onBuildAtRow={props.onBuildAtRow}
    />
  );

  if (enclosure === "sheet") {
    // Render the sheet through a portal so a parent's CSS transform
    // (e.g., the sectionFadeIn animation on BuildResultsScreen) doesn't
    // create a containing block that shrinks position:fixed to that
    // parent's box. The portal mounts at <body> root, so fixed
    // positioning resolves to the viewport.
    const portalTarget = typeof document !== "undefined" ? document.body : null;
    const sheetTree = (
      <AnimatePresence>
        {isOpen ? (
          <SheetEnclosure
            onClose={onClose ?? (() => undefined)}
            chatOpen={chatOpen ?? false}
          >
            {body}
          </SheetEnclosure>
        ) : null}
      </AnimatePresence>
    );
    return portalTarget ? createPortal(sheetTree, portalTarget) : sheetTree;
  }

  return (
    <InlineEnclosure
      expanded={expanded}
      onToggle={() => setExpanded((v) => !v)}
      props={props}
    >
      {showBody ? body : null}
    </InlineEnclosure>
  );
}

function SheetEnclosure({
  children,
  onClose,
  chatOpen,
}: {
  children: React.ReactNode;
  onClose: () => void;
  chatOpen: boolean;
}) {
  const reduce = useReducedMotion();
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    // Anchor focus inside the dialog on mount — minimum-viable focus
    // management for screen readers (per code-review Finding 5).
    closeBtnRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const t = useT();
  return (
    <>
      <motion.div
        className="fixed inset-0 bg-bp-void/55 backdrop-blur-sm z-40"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: reduce ? 0 : 0.18 }}
        onClick={onClose}
        aria-hidden="true"
      />
      <motion.aside
        role="dialog"
        aria-modal="true"
        aria-label={t("compareSchools.toggle")}
        data-testid="panel-compare-schools"
        // Sheet slides in from the right and is pinned to the right edge.
        // When chatOpen, offset by 360px (the Ask Gemma drawer's tablet+
        // width) so the leaderboard isn't covered. The `max-w-[calc(...)]`
        // clamp prevents the panel from extending past where the chat
        // drawer starts on narrow desktops. Below the tablet breakpoint
        // chat is a full-screen modal, so no offset is needed.
        className={`fixed inset-y-0 w-full sm:w-[640px] lg:w-[880px] xl:w-[980px] bg-bp-mid shadow-lg z-50 flex flex-col transition-[right,max-width] duration-200 ease-out ${
          chatOpen
            ? "right-0 tablet:right-[360px] max-w-full tablet:max-w-[calc(100vw-360px)]"
            : "right-0 max-w-full"
        }`}
        initial={{ x: reduce ? 0 : "100%", opacity: reduce ? 0 : 1 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: reduce ? 0 : "100%", opacity: reduce ? 0 : 1 }}
        transition={{ duration: reduce ? 0 : 0.22, ease: [0.32, 0.72, 0, 1] }}
      >
        {children}
        <button
          ref={closeBtnRef}
          type="button"
          onClick={onClose}
          aria-label={t("compareSchools.close")}
          className="absolute top-4 right-4 z-20 shrink-0 w-9 h-9 rounded-full bg-bp-surface hover:bg-bp-raised text-text-primary flex items-center justify-center transition-colors duration-normal cursor-pointer"
        >
          ✕
        </button>
      </motion.aside>
    </>
  );
}

function InlineEnclosure({
  expanded,
  onToggle,
  props,
  children,
}: {
  expanded: boolean;
  onToggle: () => void;
  props: CompareSchoolsPanelProps;
  children: React.ReactNode;
}) {
  const t = useT();
  return (
    <section
      role="region"
      aria-label={
        props.programName
          ? interpolate(t("compareSchools.byCipSoc.title"), {
              programNameShort: shortenProgramName(props.programName),
              occupationTitle: props.occupationTitle,
            })
          : interpolate(t("compareSchools.bySoc.title"), {
              occupationTitlePlural: props.occupationTitle,
            })
      }
      data-testid="panel-compare-schools"
      className="rounded-xl bg-bp-mid border border-border-subtle"
    >
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
        className="w-full text-left px-5 py-4 flex items-start gap-3 hover:bg-bp-surface"
      >
        <span className="flex-1">
          <span className="block text-small text-text-secondary">
            {t("compareSchools.byCipSoc.lead")}
          </span>
          <span className="block text-body text-text-primary font-medium">
            {t("compareSchools.byCipSoc.trigger")}
          </span>
        </span>
        <span
          aria-hidden="true"
          className="text-text-muted text-subheading leading-none mt-1"
        >
          {expanded ? "▾" : "▸"}
        </span>
      </button>
      {children}
    </section>
  );
}

interface PanelBodyProps {
  mode: LeaderboardMode;
  occupationTitle: string;
  programName?: string;
  data: PanelDataState;
  minConfidence: ConfidenceTier;
  onShowAll: () => void;
  onRestoreDefault: () => void;
  onRetry: () => void;
  canToggleMode: boolean;
  onModeChange: (next: LeaderboardMode) => void;
  onBuildAtRow?: (row: SchoolForCareerRow) => void;
}

function PanelBody({
  mode,
  occupationTitle,
  programName,
  data,
  minConfidence,
  onShowAll,
  onRestoreDefault,
  onRetry,
  canToggleMode,
  onModeChange,
  onBuildAtRow,
}: PanelBodyProps) {
  const t = useT();

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <PanelHeader
        mode={mode}
        occupationTitle={occupationTitle}
        programName={programName}
        canToggleMode={canToggleMode}
        onModeChange={onModeChange}
      />

      {minConfidence === "low" && data.status !== "loading" ? (
        <div
          role="status"
          className="px-5 py-3 bg-accent-caution/10 border-b border-accent-caution/30 text-small text-text-secondary flex items-center justify-between gap-3"
        >
          <span>{t("compareSchools.fallback.notice")}</span>
          <button
            type="button"
            onClick={onRestoreDefault}
            className="text-accent-info hover:underline whitespace-nowrap"
          >
            {t("compareSchools.fallback.restore")}
          </button>
        </div>
      ) : null}

      <div className="flex-1 overflow-y-auto px-5 py-4">
        {data.status === "loading" || data.status === "idle" ? (
          <LoadingSkeleton rows={8} />
        ) : data.status === "error" ? (
          <ErrorState message={data.error ?? ""} onRetry={onRetry} />
        ) : data.status === "empty" ? (
          <EmptyState mode={mode} onShowAll={onShowAll} />
        ) : data.response ? (
          <PanelTable response={data.response} onBuildAtRow={onBuildAtRow} />
        ) : null}
      </div>
    </div>
  );
}

function PanelHeader({
  mode,
  occupationTitle,
  programName,
  canToggleMode,
  onModeChange,
}: {
  mode: LeaderboardMode;
  occupationTitle: string;
  programName?: string;
  canToggleMode: boolean;
  onModeChange: (next: LeaderboardMode) => void;
}) {
  const t = useT();
  const chipText =
    mode === "by_soc"
      ? t("compareSchools.bySoc.modeChip")
      : t("compareSchools.byCipSoc.modeChip");
  const chipColor =
    mode === "by_soc"
      ? "text-accent-insight border-accent-insight/40 bg-accent-insight/10"
      : "text-accent-info border-accent-info/40 bg-accent-info/10";
  const title =
    mode === "by_soc"
      ? interpolate(t("compareSchools.bySoc.title"), {
          occupationTitlePlural: occupationTitle,
        })
      : interpolate(t("compareSchools.byCipSoc.title"), {
          programNameShort: shortenProgramName(programName ?? ""),
          occupationTitle,
        });
  const subtitle =
    mode === "by_soc"
      ? t("compareSchools.bySoc.subtitle")
      : t("compareSchools.byCipSoc.subtitle");
  const programShort = shortenProgramName(programName ?? "");
  return (
    <div className="px-5 pt-5 pb-4 pr-16 border-b border-border-subtle sticky top-0 bg-bp-mid z-10">
      <span
        role="status"
        data-testid="chip-leaderboard-mode"
        className={`inline-block font-data text-micro tracking-widest uppercase px-2 py-0.5 border rounded-full ${chipColor}`}
      >
        {chipText}
      </span>
      <h2 className="mt-2 text-subheading font-medium text-text-primary leading-snug">
        {title}
      </h2>
      <p className="mt-1 text-small text-text-secondary">{subtitle}</p>
      {canToggleMode ? (
        <div
          role="tablist"
          aria-label={t("compareSchools.modeFilter.label")}
          className="mt-3 inline-flex items-center gap-1 p-1 rounded-full bg-bp-deep border border-border-subtle"
        >
          <ModeChip
            active={mode === "by_soc"}
            label={t("compareSchools.modeFilter.allMajors")}
            testId="chip-mode-all-majors"
            onClick={() => onModeChange("by_soc")}
            accent="insight"
          />
          <ModeChip
            active={mode === "by_cip_and_soc"}
            label={interpolate(t("compareSchools.modeFilter.thisMajor"), {
              programNameShort: programShort,
            })}
            testId="chip-mode-this-major"
            onClick={() => onModeChange("by_cip_and_soc")}
            accent="info"
          />
        </div>
      ) : null}
    </div>
  );
}

function ModeChip({
  active,
  label,
  testId,
  onClick,
  accent,
}: {
  active: boolean;
  label: string;
  testId: string;
  onClick: () => void;
  accent: "insight" | "info";
}) {
  const activeClass =
    accent === "insight"
      ? "bg-accent-insight/15 text-accent-insight"
      : "bg-accent-info/15 text-accent-info";
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      data-testid={testId}
      onClick={onClick}
      className={[
        "px-3 py-1 rounded-full font-display text-small transition-colors",
        active ? activeClass : "text-text-secondary hover:text-text-primary",
      ].join(" ")}
    >
      {label}
    </button>
  );
}

function PanelTable({
  response,
  onBuildAtRow,
}: {
  response: SchoolsForCareerResponse;
  onBuildAtRow?: (row: SchoolForCareerRow) => void;
}) {
  const t = useT();
  const reduce = useReducedMotion();
  const { rows, anchor_in_top_n, total_qualifying_programs } = response;
  const anchorRow = rows.find((r) => r.is_anchor);
  const isEstimated = anchorRow?.match_quality === "estimated";
  return (
    <div>
      {anchorRow ? (
        <div
          data-testid="anchor-rank-callout"
          data-estimated={isEstimated || undefined}
          className="mb-4 px-4 py-3 rounded-xl bg-accent-thrive/10 border-l-2 border-accent-thrive"
        >
          <p className="font-data text-body text-text-primary">
            <span className="text-text-secondary">◆ </span>
            {interpolate(
              t(isEstimated
                ? "compareSchools.yourRankEstimated"
                : "compareSchools.yourRank"),
              {
                institutionName: anchorRow.institution_name,
                rank: `#${anchorRow.rank}`,
                total: total_qualifying_programs.toLocaleString(),
              },
            )}
          </p>
          {isEstimated ? (
            <p className="mt-1 text-small text-text-secondary">
              {t("compareSchools.estimatedNote")}
            </p>
          ) : null}
        </div>
      ) : null}
      {/* Tablet+ desktop: 8-column CSS grid table.
          Columns: rank | school/program | state | campuses | ern | roi | earnings | cost4yr.
          Spec: feature-branch-campus-suppression.md. */}
      <div
        role="grid"
        aria-label={t("compareSchools.toggle")}
        data-testid="compare-grid"
        className="hidden tablet:grid gap-x-4 gap-y-2 text-small"
        style={{
          gridTemplateColumns:
            "auto minmax(0, 1fr) auto auto auto auto auto auto",
        }}
      >
        <RowHeader />
        {rows.map((row, idx) => {
          const isAppendedAnchor =
            row.is_anchor && !anchor_in_top_n && idx === rows.length - 1;
          return (
            <motion.div
              key={`${row.unitid}-${row.cipcode}-${row.rank}-${idx}`}
              className="contents"
              initial={reduce ? { opacity: 1 } : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                delay: reduce
                  ? 0
                  : isAppendedAnchor
                    ? 0.22 + 0.08 * idx
                    : 0.05 * idx,
                duration: reduce ? 0 : 0.22,
              }}
            >
              {isAppendedAnchor ? <YourSchoolDivider /> : null}
              <DataRow row={row} onBuildAtRow={onBuildAtRow} />
            </motion.div>
          );
        })}
      </div>

      {/* Mobile (<768px): card-stack — preserves every data point except
          the confidence label. Spec: feature-compare-schools-for-career.md §3.D. */}
      <div data-testid="compare-card-stack" className="tablet:hidden">
        {rows.map((row, idx) => {
          const isAppendedAnchor =
            row.is_anchor && !anchor_in_top_n && idx === rows.length - 1;
          return (
            <motion.div
              key={`card-${row.unitid}-${row.cipcode}-${row.rank}-${idx}`}
              initial={reduce ? { opacity: 1 } : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                delay: reduce
                  ? 0
                  : isAppendedAnchor
                    ? 0.22 + 0.08 * idx
                    : 0.05 * idx,
                duration: reduce ? 0 : 0.22,
              }}
            >
              {isAppendedAnchor ? <CardStackDivider /> : null}
              <CardRow row={row} onBuildAtRow={onBuildAtRow} />
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

function CardRow({
  row,
  onBuildAtRow,
}: {
  row: SchoolForCareerRow;
  onBuildAtRow?: (row: SchoolForCareerRow) => void;
}) {
  const t = useT();
  const isAnchor = row.is_anchor;
  const isEstimated = row.match_quality === "estimated";
  const showBuildAction = Boolean(onBuildAtRow) && !isAnchor;
  const buildLabel = interpolate(t("compareSchools.row.buildHere"), {
    institutionName: row.institution_name,
    programName: row.program_name,
  });
  const cardClass = isAnchor
    ? "rounded-lg p-4 mb-3 bg-accent-thrive/[0.06] border border-border-subtle border-l-[3px] border-l-accent-thrive"
    : "rounded-lg p-4 mb-3 bg-bp-mid border border-border-subtle";
  const rankPillClass = isAnchor
    ? "bg-accent-thrive text-text-inverse"
    : "bg-bp-surface text-text-secondary";
  return (
    <div
      role="row"
      data-testid={
        isAnchor ? `card-anchor-${row.unitid}-${row.cipcode}` : undefined
      }
      data-anchor={isAnchor || undefined}
      className={cardClass}
    >
      {/* Top row: rank pill (left) + school name (center) + state (right) */}
      <div className="flex items-start gap-3">
        <div
          aria-hidden="true"
          className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center font-data text-data-sm font-bold ${rankPillClass}`}
        >
          {row.rank}
        </div>
        <div className="flex-1 min-w-0">
          <span className="block font-body text-body font-semibold text-text-primary truncate">
            {isAnchor ? "◆ " : ""}
            {row.institution_name}
            {isEstimated ? (
              <span
                data-testid="card-estimated-pill"
                className="ml-2 align-middle inline-block px-1.5 py-0.5 rounded font-data text-micro uppercase tracking-wider bg-accent-thrive/15 text-accent-thrive"
                title={t("compareSchools.estimatedNote")}
              >
                {t("compareSchools.estimatedPill")}
              </span>
            ) : null}
          </span>
          <span className="block font-body text-small text-text-secondary truncate mt-1">
            {row.program_name}
          </span>
          {/* Multi-campus family size on the mobile card — always rendered
              so the educational signal carries to the card stack. Spec:
              feature-branch-campus-suppression.md. */}
          <span
            className="block font-data text-micro uppercase tracking-wider text-text-muted mt-1"
            data-testid={`card-campuses-${row.unitid}-${row.cipcode}`}
          >
            {t("compareSchools.column.campuses")}: {row.family_size}
          </span>
        </div>
        <span className="shrink-0 font-data text-text-secondary">
          {row.state_abbr ?? "—"}
        </span>
      </div>

      {/* Stats bar: ERN block | hairline divider | ROI block */}
      <div className="flex items-stretch gap-4 mt-3">
        <div className="flex flex-col">
          <span className="font-data text-micro uppercase tracking-wider text-text-muted">
            {t("compareSchools.column.ern")}
          </span>
          <span className="font-data text-data font-bold text-stat-ern">
            {row.stat_ern ?? "—"}
          </span>
        </div>
        <span
          aria-hidden="true"
          className="w-px self-stretch bg-border-subtle"
        />
        <div className="flex flex-col">
          <span className="font-data text-micro uppercase tracking-wider text-text-muted">
            {t("compareSchools.column.roi")}
          </span>
          <span
            className={`font-data text-data font-bold ${statRoiColorClass(row.stat_roi)}`}
          >
            {row.stat_roi ?? "—"}
          </span>
        </div>
      </div>

      {/* Cost row: EARNINGS (left) + NET PRICE (right) */}
      <div className="flex items-end justify-between gap-4 mt-3">
        <div className="flex flex-col min-w-0">
          <span className="font-data text-micro uppercase tracking-wider text-text-muted">
            {t("compareSchools.column.earnings")}
          </span>
          <span className="font-data text-data text-text-primary truncate">
            {fmtMoney(row.earnings_1yr_median)}
          </span>
        </div>
        <div className="flex flex-col items-end min-w-0">
          <span className="font-data text-micro uppercase tracking-wider text-text-muted">
            {t("compareSchools.column.cost4yr")}
          </span>
          <span className="font-data text-data text-text-secondary truncate">
            {fmtMoney(row.published_cost_4yr)}
          </span>
        </div>
      </div>

      {showBuildAction ? (
        <button
          type="button"
          data-testid={`btn-card-build-at-${row.unitid}-${row.cipcode}`}
          onClick={() => onBuildAtRow?.(row)}
          aria-label={buildLabel}
          className="mt-3 w-full px-3 py-2 rounded-md text-text-secondary hover:text-accent-insight bg-bp-surface hover:bg-accent-insight/10 transition-colors font-data text-small"
        >
          <span aria-hidden="true" className="mr-1">↗</span>
          {t("compareSchools.row.buildHereShort")}
        </button>
      ) : null}
    </div>
  );
}

function CardStackDivider() {
  const t = useT();
  return (
    <div className="mt-2 mb-3 flex items-center gap-3 text-micro uppercase tracking-wider text-text-muted">
      <span
        aria-hidden="true"
        className="flex-1 border-t border-dashed border-border-subtle"
      />
      <span>{t("compareSchools.yourSchoolDivider")}</span>
      <span
        aria-hidden="true"
        className="flex-1 border-t border-dashed border-border-subtle"
      />
    </div>
  );
}

function RowHeader() {
  const t = useT();
  return (
    <>
      <Cell head>{t("compareSchools.column.rank")}</Cell>
      <Cell head>{t("compareSchools.column.school")}</Cell>
      <Cell head>{t("compareSchools.column.state")}</Cell>
      <Cell head>{t("compareSchools.column.campuses")}</Cell>
      <Cell head>{t("compareSchools.column.ern")}</Cell>
      <Cell head>{t("compareSchools.column.roi")}</Cell>
      <Cell head>{t("compareSchools.column.earnings")}</Cell>
      <Cell head>{t("compareSchools.column.cost4yr")}</Cell>
    </>
  );
}

function DataRow({
  row,
  onBuildAtRow,
}: {
  row: SchoolForCareerRow;
  onBuildAtRow?: (row: SchoolForCareerRow) => void;
}) {
  const t = useT();
  // Anchor row visual: thrive background tint + 3px inset left edge per
  // §3.C. Using `box-shadow: inset 3px 0 0 0 ...` instead of border-left
  // because the parent uses display:contents and CSS borders do not render
  // on contents elements (per design audit F3).
  const anchorBg = row.is_anchor ? "bg-accent-thrive/10" : "";
  const anchorShadow = row.is_anchor
    ? { boxShadow: "inset 3px 0 0 0 var(--color-accent-thrive)" }
    : undefined;
  // Don't show the build affordance on the student's own anchor row —
  // they're already building at that school.
  const showBuildAction = Boolean(onBuildAtRow) && !row.is_anchor;
  const buildLabel = interpolate(t("compareSchools.row.buildHere"), {
    institutionName: row.institution_name,
    programName: row.program_name,
  });
  return (
    <div
      role="row"
      data-testid={
        row.is_anchor ? `row-anchor-${row.unitid}-${row.cipcode}` : undefined
      }
      data-anchor={row.is_anchor || undefined}
      className="contents"
    >
      <Cell tone={anchorBg} style={anchorShadow}>
        <span className="font-data text-text-secondary">{row.rank}</span>
      </Cell>
      <Cell tone={anchorBg}>
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex-1 min-w-0">
            <span className="block text-text-primary truncate">
              {row.is_anchor ? "◆ " : ""}
              {row.institution_name}
              {row.match_quality === "estimated" ? (
                <span
                  data-testid="estimated-pill"
                  className="ml-2 align-middle inline-block px-1.5 py-0.5 rounded font-data text-micro uppercase tracking-wider bg-accent-thrive/15 text-accent-thrive"
                  title={t("compareSchools.estimatedNote")}
                >
                  {t("compareSchools.estimatedPill")}
                </span>
              ) : null}
            </span>
            <span className="block text-small text-text-muted truncate">
              {row.program_name}
            </span>
          </div>
          {showBuildAction ? (
            <button
              type="button"
              data-testid={`btn-build-at-${row.unitid}-${row.cipcode}`}
              onClick={() => onBuildAtRow?.(row)}
              aria-label={buildLabel}
              title={buildLabel}
              className="shrink-0 px-2 py-1 rounded-md text-text-muted hover:text-accent-insight hover:bg-accent-insight/10 transition-colors"
            >
              <span aria-hidden="true" className="font-data text-body">↗</span>
            </button>
          ) : null}
        </div>
      </Cell>
      <Cell tone={anchorBg}>
        <span className="font-data text-text-secondary">
          {row.state_abbr ?? "—"}
        </span>
      </Cell>
      <Cell tone={anchorBg}>
        {/* Multi-campus family size. Spec: feature-branch-campus-suppression.md.
            Always render the integer — the asymmetry of mostly-1s with the
            occasional larger number is itself the visual signal. */}
        <span
          className="font-data text-text-primary"
          data-testid={`row-campuses-${row.unitid}-${row.cipcode}`}
        >
          {row.family_size}
        </span>
      </Cell>
      <Cell tone={anchorBg}>
        <span className="font-data text-stat-ern">
          {row.stat_ern ?? "—"}
        </span>
      </Cell>
      <Cell tone={anchorBg}>
        <span className={`font-data ${statRoiColorClass(row.stat_roi)}`}>
          {row.stat_roi ?? "—"}
        </span>
      </Cell>
      <Cell tone={anchorBg}>
        <span className="font-data text-text-primary">
          {fmtMoney(row.earnings_1yr_median)}
        </span>
      </Cell>
      <Cell tone={anchorBg}>
        <span className="font-data text-text-primary">
          {fmtMoney(row.published_cost_4yr)}
        </span>
      </Cell>
    </div>
  );
}

function Cell({
  children,
  head,
  tone,
  style,
}: {
  children: React.ReactNode;
  head?: boolean;
  tone?: string;
  style?: React.CSSProperties;
}) {
  const className = head
    ? "text-micro uppercase tracking-wider text-text-muted py-1"
    : "py-2";
  return (
    <div className={`${className} ${tone ?? ""}`} style={style}>
      {children}
    </div>
  );
}

function YourSchoolDivider() {
  const t = useT();
  return (
    <div className="col-span-8 mt-3 mb-1 flex items-center gap-3 text-micro uppercase tracking-wider text-text-muted">
      <span
        aria-hidden="true"
        className="flex-1 border-t border-dashed border-border-subtle"
      />
      <span>{t("compareSchools.yourSchoolDivider")}</span>
      <span
        aria-hidden="true"
        className="flex-1 border-t border-dashed border-border-subtle"
      />
    </div>
  );
}

function LoadingSkeleton({ rows }: { rows: number }) {
  const t = useT();
  return (
    <div role="status" aria-live="polite" className="space-y-2">
      <span className="sr-only">{t("compareSchools.loading")}</span>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-8 rounded bg-bp-surface animate-pulse"
          aria-hidden="true"
        />
      ))}
    </div>
  );
}

function EmptyState({
  mode,
  onShowAll,
}: {
  mode: LeaderboardMode;
  onShowAll: () => void;
}) {
  const t = useT();
  return (
    <div
      role="status"
      data-testid="empty-compare-schools"
      className="text-center py-8"
    >
      <p className="text-body text-text-primary mb-2">
        {t("compareSchools.empty.title")}
      </p>
      <p className="text-small text-text-secondary mb-4 max-w-sm mx-auto">
        {mode === "by_soc"
          ? t("compareSchools.empty.subBySoc")
          : t("compareSchools.empty.subByCipSoc")}
      </p>
      <button
        type="button"
        onClick={onShowAll}
        className="px-4 py-2 rounded bg-accent-info/15 text-accent-info hover:bg-accent-info/25"
      >
        {t("compareSchools.empty.cta")}
      </button>
    </div>
  );
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  const t = useT();
  return (
    <div role="alert" className="text-center py-8 space-y-3">
      <p className="text-small text-accent-alert">
        {t("compareSchools.error")}
        {message ? ` (${message})` : ""}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="px-3 py-1.5 rounded border border-border-subtle text-text-secondary hover:text-text-primary"
      >
        Retry
      </button>
    </div>
  );
}
