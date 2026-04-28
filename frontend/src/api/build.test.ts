import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

/**
 * build.ts API client tests
 *
 * Two important contracts to lock down:
 *   1. normalizeTiers uses an EXACT-MATCH allowlist — bare string matching
 *      like `.includes("common")` was how "less common" careers silently
 *      got routed to "common" (§8 code review minor #5).
 *   2. When USE_MOCK=false, real endpoints are hit with the right payload.
 *   3. Mock handlers return shape-compatible fixtures (so the real/mock
 *      swap works as advertised).
 *
 * Implementation detail: USE_MOCK is read at module load from
 * import.meta.env.VITE_USE_MOCK_API. We import().meta.env.stub before
 * the module is imported, then import it dynamically so the constant
 * is captured from the stubbed env.
 */

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

beforeEach(() => {
  fetchMock.mockReset();
});

afterEach(() => {
  vi.resetModules();
  vi.unstubAllEnvs();
});

describe("build.ts — getTieredCareers (real API)", () => {
  it("POSTs outcomes payload to /build/tier", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { getTieredCareers } = await import("./build");

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ "Common paths": [] }),
    });

    await getTieredCareers(
      [{ soc_code: "15-1252" }] as never,
      "UC Berkeley",
      "Computer Science",
      "11.0701",
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toContain("/build/tier");
    expect(init.method).toBe("POST");
    const body = JSON.parse(init.body);
    expect(body).toMatchObject({
      school_name: "UC Berkeley",
      program_name: "Computer Science",
      cipcode: "11.0701",
    });
    expect(body.outcomes).toHaveLength(1);
  });

  // Exact-match allowlist: each canonical backend key must route to the right
  // tier — and crucially, must NOT raise the "unknown key" warning. If the
  // allowlist entry gets corrupted, the warn-then-fallback path fires and
  // this test fails loud.
  it.each([
    ["Common paths", "common"],
    ["Less common but realistic", "less_common"],
    ["Stretch paths", "stretch"],
  ] as const)(
    "routes backend tier key %s -> %s without warning",
    async (backendKey, tierField) => {
      vi.stubEnv("VITE_USE_MOCK_API", "false");
      const { getTieredCareers } = await import("./build");
      const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            [backendKey]: [{ soc_code: "15-1252" }],
          }),
      });

      const result = await getTieredCareers([] as never, "S", "P", "11");

      expect(warnSpy).not.toHaveBeenCalled();
      expect(result[tierField as keyof typeof result]).toHaveLength(1);
      // The other two tiers must be empty — confirms no wrong-bucket routing.
      const otherTiers = (
        ["common", "less_common", "stretch"] as const
      ).filter((k) => k !== tierField);
      for (const k of otherTiers) {
        expect(result[k as keyof typeof result]).toHaveLength(0);
      }
      warnSpy.mockRestore();
    },
  );

  it("routes fallback 'all career paths' sentinel to common", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { getTieredCareers } = await import("./build");

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          "All career paths": [
            { soc_code: "15-1252" },
            { soc_code: "15-2051" },
          ],
        }),
    });

    const result = await getTieredCareers([] as never, "S", "P", "11");
    expect(result.common).toHaveLength(2);
    expect(result.less_common).toHaveLength(0);
    expect(result.stretch).toHaveLength(0);
  });

  it("console.warns and routes to common on unknown tier key", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { getTieredCareers } = await import("./build");
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          "Wildcard tier the backend invented": [{ soc_code: "99-9999" }],
        }),
    });

    const result = await getTieredCareers([] as never, "S", "P", "11");

    expect(warnSpy).toHaveBeenCalledTimes(1);
    const [msg] = warnSpy.mock.calls[0]!;
    expect(String(msg)).toContain("unknown tier key");
    expect(String(msg)).toContain("Wildcard tier the backend invented");
    // Unknown tier still routes to common so the UI doesn't lose careers.
    expect(result.common).toHaveLength(1);
    warnSpy.mockRestore();
  });

  it("does NOT misroute 'Less common but realistic' to common", async () => {
    // The whole point of switching from `.includes()` to an allowlist:
    // the string "less common" contains "common". The OLD matcher would
    // match either tier depending on order. This test would fail if the
    // code reverted.
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { getTieredCareers } = await import("./build");

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          "Less common but realistic": [{ soc_code: "15-2051" }],
        }),
    });

    const result = await getTieredCareers([] as never, "S", "P", "11");
    expect(result.less_common).toHaveLength(1);
    expect(result.common).toHaveLength(0);
  });
});

describe("build.ts — getTieredCareers intent fields", () => {
  it("forwards studentMajorText and intentKeywords in POST body", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { getTieredCareers } = await import("./build");

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ "Common paths": [] }),
    });

    await getTieredCareers(
      [{ soc_code: "29-1071" }] as never,
      "Indiana University",
      "Biology",
      "26.0101",
      "biology pre-med",
      ["pre-med", "doctor"],
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0]!;
    const body = JSON.parse(init.body);
    expect(body.student_major_text).toBe("biology pre-med");
    expect(body.intent_keywords).toEqual(["pre-med", "doctor"]);
  });

  it("sends null student_major_text and empty intent_keywords when omitted", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { getTieredCareers } = await import("./build");

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ "Common paths": [] }),
    });

    // Call without the optional intent args
    await getTieredCareers(
      [] as never,
      "Test U",
      "Marketing",
      "52.14",
    );

    const [, init] = fetchMock.mock.calls[0]!;
    const body = JSON.parse(init.body);
    expect(body.student_major_text).toBeNull();
    expect(body.intent_keywords).toEqual([]);
  });
});

describe("build.ts — AbortSignal forwarding", () => {
  it("getOutcomes forwards AbortSignal to apiPost", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { getOutcomes } = await import("./build");
    const controller = new AbortController();

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    });

    await getOutcomes(151351, "52.14", "balanced", 0.5, undefined, undefined, controller.signal);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0]!;
    expect(init.signal).toBe(controller.signal);
  });

  it("getTieredCareers forwards AbortSignal to apiPost", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { getTieredCareers } = await import("./build");
    const controller = new AbortController();

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ "Common paths": [] }),
    });

    await getTieredCareers(
      [{ soc_code: "15-1252" }] as never,
      "UC Berkeley",
      "CS",
      "11.0701",
      undefined,
      undefined,
      controller.signal,
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0]!;
    expect(init.signal).toBe(controller.signal);
  });

  it("aborted fetch raises AbortError", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { getOutcomes } = await import("./build");
    const controller = new AbortController();
    controller.abort();

    fetchMock.mockImplementation((_url: string, init: RequestInit) => {
      if (init.signal?.aborted) {
        return Promise.reject(new DOMException("The operation was aborted.", "AbortError"));
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
    });

    await expect(
      getOutcomes(151351, "52.14", "balanced", 0.5, undefined, undefined, controller.signal),
    ).rejects.toThrow("The operation was aborted");
  });
});

// ---------------------------------------------------------------------------
// Streaming build creation (P2)
// ---------------------------------------------------------------------------

/**
 * Helper: encode an SSE event string into a Uint8Array chunk.
 * The backend emits: "event: <type>\ndata: <json>\n\n"
 */
function sseFrame(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

/**
 * Create a mock ReadableStream reader that yields Uint8Array chunks
 * from the provided SSE frames. Each frame string is encoded as a
 * separate chunk, simulating network delivery.
 */
function mockReader(frames: string[]) {
  const encoder = new TextEncoder();
  let idx = 0;
  return {
    read: vi.fn(async () => {
      if (idx < frames.length) {
        return { done: false, value: encoder.encode(frames[idx++]) };
      }
      return { done: true, value: undefined };
    }),
    releaseLock: vi.fn(),
  };
}

function mockStreamResponse(frames: string[]) {
  const reader = mockReader(frames);
  return {
    ok: true,
    body: { getReader: () => reader },
    json: () => Promise.resolve({}),
  };
}

const SKELETON_BUILD = {
  build_id: "iu-marketing-001",
  created_at: "2026-04-27T12:00:00Z",
  school_name: "Indiana University",
  unitid: 151351,
  major_text: "Marketing",
  cipcode: "52.14",
  program_name: "Marketing",
  effort: "balanced",
  loan_pct: 1.0,
  career: {
    unitid: 151351,
    institution_name: "Indiana University",
    cipcode: "52.14",
    program_name: "Marketing",
    soc_code: "13-1161",
    occupation_title: "Market Research Analysts",
    stats: { ern: 7, roi: 8, res: 5, grw: 6, hmn: 7 },
    bosses: { ai: 6, loans: 8, market: 7, burnout: 5, ceiling: 4 },
    median_annual_wage: 68230,
  },
  gauntlet: {
    fights: [
      {
        boss: "ai", label: "Fight AI", result: "win",
        raw_score: 16, threshold_win: 14, threshold_draw: 10,
        reason: "Strong", narrative: "",
      },
    ],
    wins: 1, losses: 0, draws: 0, unknown: 0, verdict: "SOLID",
  },
  branches: [],
  skill_recs: [],
  guidance: "",
  skills_crafted: [],
  skill_pool: [],
};

const STREAM_PARAMS = {
  profile_name: "bold bear",
  school_name: "Indiana University",
  unitid: 151351,
  cipcode: "52.14",
  cip_title: "Marketing",
  major_text: "Marketing",
  effort: "balanced",
  loan_pct: 1.0,
  selected_soc: "13-1161",
  selected_title: "Market Research Analysts",
  student_major: null,
  student_cip: null,
  home_state: null,
  school_state: null,
  animal_emoji: null,
  locale: "en",
};

describe("build.ts — createBuildStream SSE parsing", () => {
  it("parses a single-event-per-chunk stream correctly", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { createBuildStream } = await import("./build");

    const frames = [
      sseFrame("skeleton", SKELETON_BUILD),
      sseFrame("boss_narrative", { boss_id: "ai", narrative: "You won." }),
      sseFrame("skill_recs", [{ title: "R", stat_impact: "ERN+1", rationale: "R" }]),
      sseFrame("skill_pool", [{ id: "s1", title: "S", rationale: "S", targets: ["ai"] }]),
      sseFrame("guidance", { narrative: "Your guidance." }),
      sseFrame("done", { build_id: "iu-marketing-001" }),
    ];

    fetchMock.mockResolvedValueOnce(mockStreamResponse(frames));

    const events: Array<{ type: string; [key: string]: unknown }> = [];
    await createBuildStream(STREAM_PARAMS, (e) => events.push(e));

    expect(events).toHaveLength(6);
    expect(events[0]!.type).toBe("skeleton");
    expect((events[0] as { type: string; build: typeof SKELETON_BUILD }).build.build_id).toBe("iu-marketing-001");
    expect(events[1]!.type).toBe("boss_narrative");
    expect((events[1] as unknown as { boss_id: string }).boss_id).toBe("ai");
    expect(events[2]!.type).toBe("skill_recs");
    expect(events[3]!.type).toBe("skill_pool");
    expect(events[4]!.type).toBe("guidance");
    expect((events[4] as unknown as { narrative: string }).narrative).toBe("Your guidance.");
    expect(events[5]!.type).toBe("done");
    expect((events[5] as unknown as { build_id: string }).build_id).toBe("iu-marketing-001");
  });

  it("handles multi-event buffer (two events in one chunk)", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { createBuildStream } = await import("./build");

    // Two SSE frames concatenated into a single network chunk.
    // This simulates TCP coalescing — the reader delivers both events
    // in one read() call, so the parser must split on \n\n.
    const combined =
      sseFrame("skeleton", SKELETON_BUILD) +
      sseFrame("boss_narrative", { boss_id: "ai", narrative: "Win!" });

    const frames = [
      combined,
      sseFrame("done", { build_id: "iu-marketing-001" }),
    ];

    fetchMock.mockResolvedValueOnce(mockStreamResponse(frames));

    const events: Array<{ type: string }> = [];
    await createBuildStream(STREAM_PARAMS, (e) => events.push(e));

    expect(events).toHaveLength(3);
    expect(events[0]!.type).toBe("skeleton");
    expect(events[1]!.type).toBe("boss_narrative");
    expect(events[2]!.type).toBe("done");
  });

  it("handles split frame across two chunks", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { createBuildStream } = await import("./build");

    // An SSE frame split across two network reads. The first chunk
    // has the event: line but the data: line arrives in the second chunk.
    const full = sseFrame("skeleton", SKELETON_BUILD);
    const splitPoint = Math.floor(full.length / 2);
    const chunk1 = full.slice(0, splitPoint);
    const chunk2 = full.slice(splitPoint);

    const frames = [
      chunk1,
      chunk2 + sseFrame("done", { build_id: "iu-marketing-001" }),
    ];

    fetchMock.mockResolvedValueOnce(mockStreamResponse(frames));

    const events: Array<{ type: string }> = [];
    await createBuildStream(STREAM_PARAMS, (e) => events.push(e));

    expect(events).toHaveLength(2);
    expect(events[0]!.type).toBe("skeleton");
    expect(events[1]!.type).toBe("done");
  });

  it("throws on error event", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { createBuildStream } = await import("./build");

    const frames = [
      sseFrame("error", { detail: "No data for this career" }),
    ];

    fetchMock.mockResolvedValueOnce(mockStreamResponse(frames));

    await expect(
      createBuildStream(STREAM_PARAMS, () => {}),
    ).rejects.toThrow("No data for this career");
  });

  it("throws on HTTP error response", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { createBuildStream } = await import("./build");

    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: () => Promise.resolve({ detail: "Validation failed" }),
    });

    await expect(
      createBuildStream(STREAM_PARAMS, () => {}),
    ).rejects.toThrow();
  });

  it("throws when response body is null", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { createBuildStream } = await import("./build");

    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: null,
      json: () => Promise.resolve({}),
    });

    await expect(
      createBuildStream(STREAM_PARAMS, () => {}),
    ).rejects.toThrow("no body");
  });

  it("calls releaseLock in finally block", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { createBuildStream } = await import("./build");

    const frames = [
      sseFrame("skeleton", SKELETON_BUILD),
      sseFrame("done", { build_id: "iu-marketing-001" }),
    ];

    const reader = mockReader(frames);
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: { getReader: () => reader },
      json: () => Promise.resolve({}),
    });

    await createBuildStream(STREAM_PARAMS, () => {});

    expect(reader.releaseLock).toHaveBeenCalledTimes(1);
  });

  it("calls releaseLock even when error event throws", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "false");
    const { createBuildStream } = await import("./build");

    const frames = [
      sseFrame("error", { detail: "Something broke" }),
    ];

    const reader = mockReader(frames);
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: { getReader: () => reader },
      json: () => Promise.resolve({}),
    });

    await expect(
      createBuildStream(STREAM_PARAMS, () => {}),
    ).rejects.toThrow("Something broke");

    expect(reader.releaseLock).toHaveBeenCalledTimes(1);
  });

  it("in mock mode, emits skeleton + done without fetch", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "true");
    const { createBuildStream } = await import("./build");

    const events: Array<{ type: string }> = [];
    await createBuildStream(STREAM_PARAMS, (e) => events.push(e));

    expect(events).toHaveLength(2);
    expect(events[0]!.type).toBe("skeleton");
    expect(events[1]!.type).toBe("done");
    // Mock mode must not call fetch
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("build.ts — mock fixtures", () => {
  it("mockGetTieredCareers returns shape-compatible tiers with all three keys", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", "true");
    const { getTieredCareers } = await import("./build");

    const result = await getTieredCareers([] as never, "", "", "");

    expect(Array.isArray(result.common)).toBe(true);
    expect(Array.isArray(result.less_common)).toBe(true);
    expect(Array.isArray(result.stretch)).toBe(true);
    expect(result.common.length + result.less_common.length + result.stretch.length)
      .toBeGreaterThan(0);

    // Shape check — this is the reason the mock exists. If these fields drift
    // from Pydantic, the mock→real swap breaks on day one.
    const firstCareer = result.common[0]!;
    expect(firstCareer).toHaveProperty("soc_code");
    expect(firstCareer).toHaveProperty("occupation_title");
    expect(firstCareer).toHaveProperty("stats");
    expect(firstCareer.stats).toHaveProperty("ern");
    expect(firstCareer.stats).toHaveProperty("roi");
    expect(firstCareer.stats).toHaveProperty("res");
    expect(firstCareer.stats).toHaveProperty("grw");
    expect(firstCareer.stats).toHaveProperty("hmn");
    expect(firstCareer).toHaveProperty("bosses");
    expect(firstCareer.bosses).toHaveProperty("ai");
    expect(firstCareer.bosses).toHaveProperty("loans");
    expect(firstCareer.bosses).toHaveProperty("market");
    expect(firstCareer.bosses).toHaveProperty("burnout");
    expect(firstCareer.bosses).toHaveProperty("ceiling");
    // Mock must NOT call fetch — short-circuits at USE_MOCK branch.
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
