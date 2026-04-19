/**
 * Captions paired to horizon images by `index % 3`.
 * All numbers verified against current consumable.program_career_paths Iceberg snapshot
 * (see fp-marketing-reviewer agent run a383427f8787dc9e3 for the verification trail).
 */
export const HORIZON_CAPTIONS = [
  "700K data points · 50 states · 7 public datasets · Every number has a receipt.",
  "2,500 schools · 355 majors · 634 occupations · One pentagon each.",
  "5 stats · 6 boss fights · 626K paths · Every value ties back to a public dataset.",
] as const satisfies readonly [string, string, string];
