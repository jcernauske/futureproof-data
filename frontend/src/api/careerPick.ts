import { apiGet, apiPost } from "@/api/client";
import {
  mockAskCareerPickChip,
  mockGetCareerPickChips,
} from "@/api/mockCareerPick";
import type {
  AskCareerPickResponse,
  CareerPickChip,
} from "@/types/careerPick";
import type { AppLocale } from "@/i18n/locales";

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === "true";

export interface GetChipsArgs {
  cipcode: string;
  majorText: string;
  socCodes: string[];
}

export async function getCareerPickChips(
  args: GetChipsArgs,
): Promise<CareerPickChip[]> {
  if (USE_MOCK) return mockGetCareerPickChips(args);
  const params = new URLSearchParams();
  params.set("cipcode", args.cipcode);
  params.set("major_text", args.majorText);
  for (const soc of args.socCodes) params.append("soc_codes", soc);
  return apiGet<CareerPickChip[]>(`/career-pick/chips?${params.toString()}`);
}

export interface AskChipArgs {
  chipId: string;
  cipcode: string;
  majorText: string;
  socCodes: string[];
  selectedSoc?: string | null;
  terminalTitle?: string | null;
  locale?: AppLocale;
}

export async function askCareerPickChip(
  args: AskChipArgs,
): Promise<AskCareerPickResponse> {
  if (USE_MOCK) return mockAskCareerPickChip({ chipId: args.chipId });
  return apiPost<AskCareerPickResponse>("/career-pick/ask", {
    chip_id: args.chipId,
    cipcode: args.cipcode,
    major_text: args.majorText,
    soc_codes: args.socCodes,
    selected_soc: args.selectedSoc ?? null,
    terminal_title: args.terminalTitle ?? null,
    locale: args.locale ?? "en",
  });
}
