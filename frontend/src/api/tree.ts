import { apiGet } from "@/api/client";
import { mockGetTree } from "@/api/mockTree";
import type { TreeResponse } from "@/types/tree";

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === "true";

export async function getTree(
  buildId: string,
  maxDepth: number = 3,
): Promise<TreeResponse> {
  if (USE_MOCK) return mockGetTree();
  return apiGet<TreeResponse>(`/tree/${buildId}?max_depth=${maxDepth}`);
}
