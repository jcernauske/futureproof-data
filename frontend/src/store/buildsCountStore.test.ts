import { describe, it, expect, beforeEach, vi } from "vitest";

const listBuildsMock = vi.fn();

vi.mock("@/api/menu", () => ({
  listBuilds: (...args: unknown[]) => listBuildsMock(...args),
}));

import { useBuildsCountStore } from "./buildsCountStore";

describe("buildsCountStore", () => {
  beforeEach(() => {
    listBuildsMock.mockReset();
    useBuildsCountStore.setState({ count: null, loading: false, error: null });
  });

  it("refreshes count from listBuilds API", async () => {
    listBuildsMock.mockResolvedValueOnce([
      { build_id: "a" },
      { build_id: "b" },
      { build_id: "c" },
    ]);
    await useBuildsCountStore.getState().refresh();
    expect(useBuildsCountStore.getState().count).toBe(3);
    expect(useBuildsCountStore.getState().loading).toBe(false);
    expect(useBuildsCountStore.getState().error).toBeNull();
  });

  it("returns 0 when there are no builds", async () => {
    listBuildsMock.mockResolvedValueOnce([]);
    await useBuildsCountStore.getState().refresh();
    expect(useBuildsCountStore.getState().count).toBe(0);
  });

  it("handles listBuilds error without throwing", async () => {
    listBuildsMock.mockRejectedValueOnce(new Error("boom"));
    await expect(
      useBuildsCountStore.getState().refresh(),
    ).resolves.toBeUndefined();
    expect(useBuildsCountStore.getState().loading).toBe(false);
    expect(useBuildsCountStore.getState().error).toBe("boom");
    expect(useBuildsCountStore.getState().count).toBeNull();
  });

  it("preserves previous count when a refresh errors", async () => {
    listBuildsMock.mockResolvedValueOnce([{ build_id: "a" }]);
    await useBuildsCountStore.getState().refresh();
    expect(useBuildsCountStore.getState().count).toBe(1);

    listBuildsMock.mockRejectedValueOnce(new Error("network down"));
    await useBuildsCountStore.getState().refresh();
    expect(useBuildsCountStore.getState().count).toBe(1);
    expect(useBuildsCountStore.getState().error).toBe("network down");
  });

  it("sets loading=true while in flight", async () => {
    let resolve: ((value: unknown[]) => void) | undefined;
    listBuildsMock.mockReturnValueOnce(
      new Promise((r) => {
        resolve = r;
      }),
    );
    const promise = useBuildsCountStore.getState().refresh();
    expect(useBuildsCountStore.getState().loading).toBe(true);
    resolve!([{ build_id: "a" }, { build_id: "b" }]);
    await promise;
    expect(useBuildsCountStore.getState().loading).toBe(false);
    expect(useBuildsCountStore.getState().count).toBe(2);
  });
});
