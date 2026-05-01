export type AppLocale = "en" | "es" | "ar";

export const DEFAULT_LOCALE: AppLocale = "en";

const RTL_LOCALES: ReadonlySet<AppLocale> = new Set<AppLocale>(["ar"]);

export function normalizeLocale(value: unknown): AppLocale {
  if (value === "es") return "es";
  if (value === "ar") return "ar";
  return "en";
}

export function isRtlLocale(locale: AppLocale): boolean {
  return RTL_LOCALES.has(locale);
}

export function localeDirection(locale: AppLocale): "rtl" | "ltr" {
  return isRtlLocale(locale) ? "rtl" : "ltr";
}
