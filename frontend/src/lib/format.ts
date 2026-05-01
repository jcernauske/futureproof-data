export function fmtMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `$${Math.round(value).toLocaleString()}`;
}

export function roiColorClass(dte: number | null): string {
  if (dte === null) return "text-text-muted";
  if (dte <= 0.5) return "text-accent-thrive";
  if (dte <= 1.0) return "text-accent-caution";
  return "text-accent-alert";
}

/** Map a stat_roi 1–10 score to a Brightpath accent color class.
 * Thresholds per feature-compare-schools-for-career.md §3.C:
 * roi >= 7 → thrive, roi >= 4 → caution, else alert. */
export function statRoiColorClass(roi: number | null | undefined): string {
  if (roi == null) return "text-text-muted";
  if (roi >= 7) return "text-accent-thrive";
  if (roi >= 4) return "text-accent-caution";
  return "text-accent-alert";
}
