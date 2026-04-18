import type { CareerBranch } from "@/types/build";

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const MOCK_BRANCHES: Record<string, CareerBranch[]> = {
  "13-2051": [
    {
      from_soc: "13-2051",
      to_soc: "11-3031",
      to_title: "Financial Manager",
      delta_ern: 2,
      delta_roi: 1,
      delta_res: 0,
      delta_grw: 1,
      delta_hmn: 1,
      unlock: "Bachelor's + 5yr experience",
      relatedness: 0.92,
    },
    {
      from_soc: "13-2051",
      to_soc: "11-1011",
      to_title: "Chief Executive",
      delta_ern: 3,
      delta_roi: 2,
      delta_res: -1,
      delta_grw: 0,
      delta_hmn: 2,
      unlock: "Master's preferred · 10+ yrs",
      relatedness: 0.78,
    },
  ],
};

export async function mockGetBranchesForSoc(
  soc: string,
): Promise<CareerBranch[]> {
  await delay(500);
  return MOCK_BRANCHES[soc] ?? [];
}
