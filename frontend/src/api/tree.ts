import { apiGet } from "@/api/client";
import { mockGetBranchesForSoc } from "@/api/mockBranches";
import { mockGetTree } from "@/api/mockTree";
import type { CareerBranch } from "@/types/build";
import type { TreeResponse } from "@/types/tree";

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === "true";

export async function getTree(
  buildId: string,
  maxDepth: number = 3,
): Promise<TreeResponse> {
  if (USE_MOCK) return mockGetTree();
  return apiGet<TreeResponse>(`/tree/${buildId}?max_depth=${maxDepth}`);
}

export async function getBranchesForSoc(
  soc: string,
): Promise<CareerBranch[]> {
  if (USE_MOCK) return mockGetBranchesForSoc(soc);
  return apiGet<CareerBranch[]>(`/branches/${soc}`);
}
