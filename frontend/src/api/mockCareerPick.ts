import type {
  AskCareerPickResponse,
  CareerPickChip,
} from "@/types/careerPick";

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const BASE_CHIPS: CareerPickChip[] = [
  {
    id: "what_does_this_do",
    label: "What does this career actually do?",
    elevated: false,
    terminal_title: null,
  },
  {
    id: "right_school_for_this",
    label: "Is this the right school for this?",
    elevated: false,
    terminal_title: null,
  },
  {
    id: "why_these_tiers",
    label: "Why are some careers 'Common' and some 'Stretch'?",
    elevated: false,
    terminal_title: null,
  },
];

const PRE_MED_ELEVATED: CareerPickChip = {
  id: "why_no_doctor",
  label: "Why don't I see 'doctor'?",
  elevated: true,
  terminal_title: "doctor",
};

function majorMatchesPreMed(majorText: string): boolean {
  return /\bpre[\s-]?med\b/i.test(majorText);
}

export async function mockGetCareerPickChips(args: {
  cipcode: string;
  majorText: string;
  socCodes: string[];
}): Promise<CareerPickChip[]> {
  await delay(120);
  const elevated: CareerPickChip[] =
    majorMatchesPreMed(args.majorText) &&
    !args.socCodes.some((s) => s.startsWith("29-12") || s === "29-1216")
      ? [PRE_MED_ELEVATED]
      : [];
  return [...elevated, ...BASE_CHIPS];
}

const MOCK_ANSWERS: Record<string, string> = {
  why_no_doctor:
    "Doctor doesn't show up here because this screen lists first jobs right after a bachelor's degree, and becoming a doctor usually takes four more years of medical school. Your major is a standard pre-med path — the careers on this screen are what graduates often do before or instead of med school. You're on the right road. Financial Analyst is one solid example of where biology grads go when they don't head straight to med school.",
  what_does_this_do:
    "A person in this role spends most of their day with spreadsheets, databases, and meetings. They pull data from company systems, check it for mistakes, and build charts that explain trends. They work closely with managers who ask a lot of questions — often urgent ones. The hard part is switching between tools all day without losing focus.",
  right_school_for_this:
    "This screen is built from graduates of THIS school's program, not a national average — so it's a close signal for your situation. First-year earnings for this major's graduates sit in a realistic range for the careers shown. Small programs can skew the numbers, so treat these as a ballpark, not a promise.",
  why_these_tiers:
    "Common means graduates from this major most often end up in that occupation. Stretch means it's possible but atypical — often takes more school, a pivot, or extra experience. The tiers come from real graduate outcome data, not opinion. Think of them as a hint about where the current flows, not a ceiling.",
};

export async function mockAskCareerPickChip(args: {
  chipId: string;
}): Promise<AskCareerPickResponse> {
  await delay(900);
  const answer =
    MOCK_ANSWERS[args.chipId] ??
    "Couldn't load a live answer — here's the fallback.";
  return {
    chip_id: args.chipId,
    answer,
    fallback_fired: false,
  };
}
