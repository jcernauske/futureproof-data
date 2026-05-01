import { useEffect } from "react";
import { useProfileStore } from "@/store/profileStore";
import { localeDirection } from "./locales";

/**
 * Syncs the active locale to the <html> element's `lang` and `dir`
 * attributes. Mount once near the root so the whole tree gets correct
 * direction-aware layout (flex row reversal, scrollbar side, default
 * text alignment) when the student switches to Arabic.
 */
export function useDocumentLocale(): void {
  const locale = useProfileStore((s) => s.locale);

  useEffect(() => {
    const root = document.documentElement;
    root.lang = locale;
    root.dir = localeDirection(locale);
  }, [locale]);
}
