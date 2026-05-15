import { useCallback } from "react";
import { useProfileStore } from "@/store/profileStore";
import { getString } from "./strings";

/**
 * Localized string lookup hook.
 *
 * Pass `vars` as the second arg to substitute `{name}` placeholders in the
 * resolved template. Numeric and string values are stringified; missing
 * placeholders are left intact (`{name}`) so problems are visible during dev.
 *
 *   const t = useT();
 *   t("compare.callout.lowestPressure");                       // "Lowest pressure"
 *   t("compare.unitOf10", { value: "8.4" });                   // "8.4/10"
 *   t("compare.regionLabel", { n: 3 });                        // "Comparison of 3 builds"
 */
export function useT() {
  const locale = useProfileStore((s) => s.locale);
  return useCallback(
    (key: string, vars?: Record<string, string | number>) =>
      getString(key, locale, vars),
    [locale],
  );
}
