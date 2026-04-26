import { useCallback } from "react";
import { useProfileStore } from "@/store/profileStore";
import { getString } from "./strings";

export function useT() {
  const locale = useProfileStore((s) => s.locale);
  return useCallback((key: string) => getString(key, locale), [locale]);
}
