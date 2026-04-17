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

  it("throws with field + msg when FastAPI returns 422 detail array", async () => {
    // FastAPI validation errors come back as { detail: [{loc, msg, type}, ...] }.
    // Before the fix, apiPost did `${detail}` which stringifies the array to
    // "[object Object],[object Object]" — useless to the user.
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: () =>
        Promise.resolve({
          detail: [
            {
              loc: ["body", "unitid"],
              msg: "Input should be a valid integer",
              type: "int_parsing",
            },
            {
              loc: ["body", "cipcode"],
              msg: "field required",
              type: "value_error.missing",
            },
          ],
        }),
    });

    await expect(
      apiPost("/build/outcomes", { cipcode: "bogus" }),
    ).rejects.toThrowError(
      // Field path (minus leading "body") + msg must both appear so the
      // developer can tell which field the backend rejected.
      /unitid: Input should be a valid integer.*cipcode: field required/s,
    );
  });
});
