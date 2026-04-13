import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiPost } from "./client";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

beforeEach(() => {
  fetchMock.mockReset();
});

describe("apiPost", () => {
  it("returns parsed JSON on success", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ profile_name: "bold swift fox" }),
    });
    const result = await apiPost("/profile");
    expect(result).toEqual({ profile_name: "bold swift fox" });
  });

  it("throws with detail message on error", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ detail: "Internal error" }),
    });
    await expect(apiPost("/profile")).rejects.toThrow("Internal error");
  });

  it("throws generic message when error response has no detail", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: () => Promise.reject(new Error("not json")),
    });
    await expect(apiPost("/profile")).rejects.toThrow("API error: 503");
  });
});
