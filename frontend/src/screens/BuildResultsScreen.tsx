import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import { useBuildsCountStore } from "@/store/buildsCountStore";
import { useInferenceStore } from "@/store/inferenceStore";
import { createBuild, createBuildStream } from "@/api/build";
import type { BuildParams, BuildStreamEvent } from "@/api/build";
import type { Build } from "@/types/build";
import { clearSession } from "@/api/session";
import { PentagonChart } from "@/components/PentagonChart";
import { CampusHeroBanner } from "@/components/build-results/CampusHeroBanner";
import { HeroIdentity } from "@/components/build-results/HeroIdentity";
import { PathCard } from "@/components/build-results/PathCard";
import { FinancesCard } from "@/components/build-results/FinancesCard";
import { InstitutionCard } from "@/components/build-results/InstitutionCard";
import { StatInfoPopover } from "@/components/build-results/StatInfoPopover";
import { BossBand } from "@/components/build-results/BossBand";
import { BuildLoadingScreen } from "@/components/build-results/BuildLoadingScreen";
import { VerdictBadge } from "@/components/build-results/VerdictBadge";
import { BOSS_META, STAT_COLORS, STAT_INFO } from "@/components/build-results/bossData";
import { GemmaChat } from "@/components/menu/GemmaChat";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { PageContainer } from "@/components/ui/PageContainer";
import { ExportPdfButton } from "@/components/build-results/ExportPdfButton";
import { CompareSchoolsPanel } from "@/components/CompareSchoolsPanel";
import { fetchSchoolsByCipAndSoc, fetchSchoolsBySoc } from "@/api/careers";
import { spawnBuildFromRow } from "@/lib/buildSpawn";
import type { SchoolForCareerRow } from "@/types/build";
import type { AskScope, AskStatTarget } from "@/api/menu";
import type { StatKey } from "@/data/statExplanations";
import { STAT_EXPLANATIONS } from "@/data/statExplanations";
import { fireCheckpoint } from "@/lib/checkpoint";
import { useT } from "@/i18n/useT";
import type { BossFightResult, BossId, BossOutcome } from "@/types/build";

function publishedCost4yrForSchool(
  school: {
    institutionControl: string | null;
    stateAbbr: string | null;
    costOfAttendanceAnnual: number | null;
    tuitionInState: number | null;
    tuitionOutOfState: number | null;
  },
  homeState: string | null,
): number | null {
  const coa = school.costOfAttendanceAnnual;
  if (coa === null || coa <= 0) return null;
  if (!school.institutionControl?.startsWith("Public")) return coa * 4;
  if (!homeState || !school.stateAbbr) return coa * 4;
  if (homeState === school.stateAbbr) return coa * 4;
  const inState = school.tuitionInState;
  const outState = school.tuitionOutOfState;
  if (inState === null || outState === null) return coa * 4;
  const gap = outState - inState;
  return gap > 0 ? (coa + gap) * 4 : coa * 4;
}

// i18n keys for per-boss scope chip text. Mirrors the alias table in
// docs/specs/feature-ask-gemma.md §3. Resolved through `t(...)` so the
// chip prefix follows the active locale. `unknown` falls back to the
// `draw` copy ("borderline risk") in every locale.
const BOSS_CHIP_PREFIX_KEY: Record<BossOutcome, string> = {
  win: "build.askBoss.win",
  lose: "build.askBoss.lose",
  draw: "build.askBoss.draw",
  unknown: "build.askBoss.draw",
};

// i18n keys for Ask-Gemma scope-chip text. Resolved through `t(...)` at
// render time so the chips follow the active locale. Keep the lookups
// shallow — these are tiny maps that change rarely.
const STAT_STARTER_KEYS = [
  "build.askGemma.stat.improve",
  "build.askGemma.stat.compare",
];

const BOSS_LOSS_CHIP_KEYS: Record<BossId, string> = {
  ai: "build.askGemma.boss.lose.ai",
  loans: "build.askGemma.boss.lose.loans",
  market: "build.askGemma.boss.lose.market",
  burnout: "build.askGemma.boss.lose.burnout",
  ceiling: "build.askGemma.boss.lose.ceiling",
};

const BOSS_WIN_CHIP_KEYS: Record<BossId, string> = {
  ai: "build.askGemma.boss.win.ai",
  loans: "build.askGemma.boss.win.loans",
  market: "build.askGemma.boss.win.market",
  burnout: "build.askGemma.boss.win.burnout",
  ceiling: "build.askGemma.boss.win.ceiling",
};

const BOSS_DRAW_CHIP_KEYS: Record<BossId, string> = {
  ai: "build.askGemma.boss.draw.ai",
  loans: "build.askGemma.boss.draw.loans",
  market: "build.askGemma.boss.draw.market",
  burnout: "build.askGemma.boss.draw.burnout",
  ceiling: "build.askGemma.boss.draw.ceiling",
};

function bossStarters(
  outcome: BossOutcome,
  bossId: BossId,
  t: (key: string) => string,
): string[] {
  const chips: string[] = [];
  if (outcome === "win") {
    chips.push(t(BOSS_WIN_CHIP_KEYS[bossId]));
  } else if (outcome === "lose") {
    chips.push(t(BOSS_LOSS_CHIP_KEYS[bossId]));
  } else {
    chips.push(t(BOSS_DRAW_CHIP_KEYS[bossId]));
  }
  if (outcome !== "win") {
    chips.push(t("build.askGemma.skill.pickToWin"));
  }
  return chips;
}

const SKILL_STARTER_KEYS = ["build.askGemma.skill.where"];

// Build-scope chips when running on Ollama (E4B). Tool calling on
// gemma4:e4b is unreliable; the cloud STARTERS in GemmaChat were
// engineered to fire 2-3 tool calls each, which sets up visible
// failures on E4B. These five answer purely from the build context
// block already injected by ask_gemma.py — same surfaces shown
// elsewhere on the page (PentagonChart, FinancesCard, BossBand,
// Gemma's Summary).
const BUILD_STARTERS_E4B = [
  "What's the strongest part of this build?",
  "Where is this build weakest?",
  "Walk me through how my debt compares to year-1 salary.",
  "Which of my five stats is doing the heaviest lifting?",
  "Summarize this build in two sentences.",
];

const STAT_KEYS: StatKey[] = ["ern", "roi", "res", "grw", "aura"];

export function BuildResultsScreen() {
  const navigate = useNavigate();
  const { school, major, effort, loans } = useBuildInputStore();
  const { profileName, animalEmoji, homeState, locale } = useProfileStore();
  const inferenceBackend = useInferenceStore((s) => s.backend);
  const {
    selectedCareer, build, setBuild, updateBuild, isBuilding, setIsBuilding,
    buildingStage, buildingTotal,
  } = useBuildStore();
  const t = useT();

  const [error, setError] = useState<string | null>(null);
  const [openPopover, setOpenPopover] = useState<string | null>(null);
  const [highlightStat, setHighlightStat] = useState<StatKey | null>(null);
  const [fights, setFights] = useState<BossFightResult[]>([]);
  const [consumedSkillIds, setConsumedSkillIds] = useState<Set<string>>(new Set());
  const [chatOpen, setChatOpen] = useState(false);
  const [chatScope, setChatScope] = useState<AskScope | null>(null);
  const [chatChipText, setChatChipText] = useState<string>("");
  // ERN explain-this-stat spike — when set, the slide-in chat fires this
  // opener automatically. Cleared on close so a manual reopen doesn't
  // replay the explanation. ERN-only for now.
  const [chatOpenerPrompt, setChatOpenerPrompt] = useState<string | null>(null);
  const [chatStarters, setChatStarters] = useState<string[] | undefined>();
  const [compareOpen, setCompareOpen] = useState(false);
  const [skillPoolLoading, setSkillPoolLoading] = useState(false);
  // Rank-of-school summary surfaced above the "See other schools..." CTA.
  // Fetched at limit=1 because the backend always appends the anchor row
  // (or returns anchor_estimated_rank) regardless of limit, and the result
  // is cached server-side so the sheet's later fetch is essentially free.
  const [rankSummary, setRankSummary] = useState<
    { rank: number; total: number } | null
  >(null);
  const careerSoc = build?.career?.soc_code;
  const careerCip = build?.career?.cipcode;
  const careerUnitid = build?.career?.unitid;
  const careerStatErn = build?.career?.stats?.ern;
  const careerStatRoi = build?.career?.stats?.roi;
  useEffect(() => {
    if (!careerSoc || careerUnitid == null) {
      setRankSummary(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const opts = {
          limit: 1,
          minConfidence: "medium" as const,
          buildUnitid: careerUnitid,
          buildCipcode: careerCip,
          homeState: homeState ?? undefined,
          anchorStatErn:
            typeof careerStatErn === "number" ? careerStatErn : undefined,
          anchorStatRoi:
            typeof careerStatRoi === "number" ? careerStatRoi : undefined,
        };
        const response = careerCip
          ? await fetchSchoolsByCipAndSoc(careerCip, careerSoc, opts)
          : await fetchSchoolsBySoc(careerSoc, opts);
        if (cancelled) return;
        const anchorRow = response.rows.find((r) => r.is_anchor);
        const rank = anchorRow?.rank ?? response.anchor_estimated_rank ?? null;
        if (rank !== null && response.total_qualifying_programs > 0) {
          setRankSummary({ rank, total: response.total_qualifying_programs });
        } else {
          setRankSummary(null);
        }
      } catch {
        if (!cancelled) setRankSummary(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [careerSoc, careerCip, careerUnitid, careerStatErn, careerStatRoi, homeState]);

  const openChat = useCallback(
    (scope: AskScope, chipText: string, openerPrompt?: string, starters?: string[]) => {
      setChatScope(scope);
      setChatChipText(chipText);
      setChatOpenerPrompt(openerPrompt ?? null);
      setChatStarters(starters);
      setChatOpen(true);
    },
    [],
  );
  const closeChat = useCallback(() => {
    setChatOpen(false);
    setChatOpenerPrompt(null);
  }, []);

  // Explain-this-stat handler — triggers the structured-receipt path
  // for any registered stat (ERN, ROI, RES, GRW).
  const handleExplainStat = useCallback((statKey: string) => {
    if (!build) return;
    const code = statKey.toUpperCase();
    const info = STAT_INFO[statKey];
    const label = info?.title ?? code;
    openChat(
      {
        kind: "stat",
        build_ids: [build.build_id],
        target_id: code as AskStatTarget,
      },
      t("build.askPrefix").replace("{label}", label),
      `[explain-this:${code}]`,
    );
  }, [build, openChat, t]);

  const handleAskStat = useCallback(
    (statLowercase: string) => {
      if (!build) return;
      const target = statLowercase.toUpperCase() as AskStatTarget;
      const info = STAT_INFO[statLowercase];
      const label = info?.title ?? statLowercase.toUpperCase();
      openChat(
        { kind: "stat", build_ids: [build.build_id], target_id: target },
        t("build.askPrefix").replace("{label}", label),
        undefined,
        STAT_STARTER_KEYS.map((k) => t(k)),
      );
    },
    [build, openChat, t],
  );

  const handleAskBoss = useCallback(
    (bossId: BossId) => {
      if (!build) return;
      const fight = fights.find((f) => f.boss === bossId);
      const result: BossOutcome = fight?.result ?? "unknown";
      const meta = BOSS_META[bossId];
      const prefix = t(BOSS_CHIP_PREFIX_KEY[result]);
      openChat(
        { kind: "boss", build_ids: [build.build_id], target_id: bossId },
        `${prefix}: ${t(meta.shortNameKey)}`,
        undefined,
        bossStarters(result, bossId, t),
      );
    },
    [build, fights, openChat, t],
  );

  const handleAskSkill = useCallback(
    (skillId: string) => {
      if (!build) return;
      const allSkills = [
        ...(build.skills_crafted ?? []),
        ...(build.skill_pool ?? []),
      ];
      const skill = allSkills.find((s) => s.id === skillId);
      const title = skill?.title ?? "this skill";
      const truncated = title.length > 40 ? title.slice(0, 39).trimEnd() + "…" : title;
      // Auto-fire a question so the student gets an answer immediately
      // instead of facing a single chip + empty input. Same UX shape as
      // the boss "Why this is X" buttons. The opener is sent over the
      // wire to Gemma but never shown to the student — only the
      // assistant response renders.
      openChat(
        { kind: "skill", build_ids: [build.build_id], target_id: skillId },
        t("build.askPrefix").replace("{label}", truncated),
        `Where can I learn ${title}, and how would it help my career?`,
        SKILL_STARTER_KEYS.map((k) => t(k)),
      );
    },
    [build, openChat, t],
  );

  const handleAskBuild = useCallback(() => {
    if (!build) return;
    const starters =
      inferenceBackend === "ollama" ? BUILD_STARTERS_E4B : undefined;
    openChat(
      { kind: "build", build_ids: [build.build_id] },
      t("build.askWholeBuild"),
      undefined,
      starters,
    );
  }, [build, inferenceBackend, openChat, t]);

  // Save button is pure UX feedback — the build is already autosaved
  // server-side when the SSE build flow finishes. The spinner exists to
  // give the user a tactile "I saved it" moment.
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const savedResetTimerRef = useRef<number | null>(null);
  const handleSave = useCallback(async () => {
    if (!build) return;
    if (saveState === "saving") return;
    if (savedResetTimerRef.current !== null) {
      window.clearTimeout(savedResetTimerRef.current);
      savedResetTimerRef.current = null;
    }
    setSaveState("saving");
    await new Promise((resolve) => setTimeout(resolve, 600));
    setSaveState("saved");
    savedResetTimerRef.current = window.setTimeout(() => {
      setSaveState("idle");
      savedResetTimerRef.current = null;
    }, 1500);
  }, [build, saveState]);
  useEffect(() => {
    return () => {
      if (savedResetTimerRef.current !== null) {
        window.clearTimeout(savedResetTimerRef.current);
      }
    };
  }, []);

  const cancelledRef = useRef(false);
  // Fire-once guard for the build-trigger effect below. Prevents StrictMode's
  // simulated mount→unmount→mount from POSTing /build twice and persisting two
  // separate build_ids for the same screen visit.
  const buildTriggeredRef = useRef(false);

  // Boss band reveal state
  const [revealedBands, setRevealedBands] = useState<Set<string>>(new Set());
  const [vsActiveBands, setVsActiveBands] = useState<Set<string>>(new Set());
  const [vsDoneBands, setVsDoneBands] = useState<Set<string>>(new Set());
  const [visibleBands, setVisibleBands] = useState<Set<string>>(new Set());
  const bandRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const animatingRef = useRef<string | null>(null);
  const pendingQueueRef = useRef<string[]>([]);
  // Refs mirroring state for observer callbacks (avoids observer recreation)
  const revealedBandsRef = useRef(revealedBands);
  revealedBandsRef.current = revealedBands;
  const vsActiveBandsRef = useRef(vsActiveBands);
  vsActiveBandsRef.current = vsActiveBands;
  const timeoutsRef = useRef<Map<string, number[]>>(new Map());

  // Nav guard — skip when a build is already loaded (e.g. from /builds menu)
  useEffect(() => {
    if (build) return;
    if (!selectedCareer || !school || !major) {
      sessionStorage.setItem("fp-nav-hint", "session-expired");
      navigate("/set-your-course", { replace: true });
    }
  }, [build, selectedCareer, school, major, navigate]);

  // Build trigger
  useEffect(() => {
    cancelledRef.current = false;
    return () => { cancelledRef.current = true; };
  }, []);

  function mergeBossNarrative(prev: Build, bossId: string, narrative: string): Build {
    return {
      ...prev,
      gauntlet: {
        ...prev.gauntlet,
        fights: prev.gauntlet.fights.map((f) =>
          f.boss === bossId ? { ...f, narrative } : f,
        ),
      },
    };
  }

  const runBuild = useCallback(async () => {
    if (!selectedCareer || !school || !major || !profileName) return;
    setIsBuilding(true);
    setSkillPoolLoading(false);
    setError(null);

    const lookupCip = major.parentCip || major.cipCode;
    const studentCip = major.parentCip ? major.cipCode : undefined;
    const publishedCost4yr = publishedCost4yrForSchool(school, homeState ?? null);

    const params: BuildParams = {
      profile_name: profileName,
      school_name: school.name,
      unitid: school.unitid,
      cipcode: lookupCip,
      cip_title: major.cipTitle,
      major_text: major.rawText,
      effort: effort.level,
      loan_pct: loans.percentage / 100,
      selected_soc: selectedCareer.soc_code,
      selected_title: selectedCareer.occupation_title,
      student_major: major.rawText,
      student_cip: studentCip ?? null,
      home_state: homeState ?? null,
      school_state: school.stateAbbr ?? null,
      published_cost_4yr: publishedCost4yr,
      animal_emoji: animalEmoji ?? null,
      locale: locale ?? "en",
      // Forward the same intent_keywords /build/outcomes used to populate
      // the career list. Without this, SOC expansion picks (e.g.
      // 41-3011 for an Advertising major) survive on /outcomes but
      // disappear on /build → 404 LookupError.
      intent_keywords: major.intentKeywords ?? [],
    };

    const onEvent = (event: BuildStreamEvent) => {
      if (cancelledRef.current) return;
      const store = useBuildStore.getState();
      switch (event.type) {
        case "skeleton": {
          setBuild(event.build);
          setFights(event.build.gauntlet.fights);
          setSkillPoolLoading(true);
          const total = event.build.gauntlet.fights.length + 4;
          store.setBuildingTotal(total);
          store.setBuildingStage(1);
          store.addCompletedStep("skeleton");
          useBuildsCountStore.getState().refresh();
          fireCheckpoint("/my-build");
          break;
        }
        case "boss_narrative":
          updateBuild((prev) => mergeBossNarrative(prev, event.boss_id, event.narrative));
          store.setBuildingStage((prev: number) => prev + 1);
          store.addCompletedStep(`boss_${event.boss_id}`);
          break;
        case "skill_recs":
          updateBuild((prev) => ({ ...prev, skill_recs: event.recs }));
          store.setBuildingStage((prev: number) => prev + 1);
          store.addCompletedStep("skill_recs");
          break;
        case "skill_pool":
          setSkillPoolLoading(false);
          updateBuild((prev) => ({ ...prev, skill_pool: event.pool }));
          store.setBuildingStage((prev: number) => prev + 1);
          store.addCompletedStep("skill_pool");
          break;
        case "guidance":
          updateBuild((prev) => ({ ...prev, guidance: event.narrative }));
          store.setBuildingStage((prev: number) => prev + 1);
          store.addCompletedStep("guidance");
          break;
        case "done":
          setSkillPoolLoading(false);
          setIsBuilding(false);
          break;
      }
    };

    try {
      await createBuildStream(params, onEvent);
    } catch {
      if (cancelledRef.current) return;
      // SSE failed — fall back to blocking build
      try {
        const minDisplayTime = new Promise<void>((r) => setTimeout(r, 1000));
        const [result] = await Promise.all([
          createBuild(
            profileName, school.name, school.unitid, lookupCip,
            major.cipTitle, major.rawText, effort.level,
            loans.percentage / 100, selectedCareer.soc_code,
            selectedCareer.occupation_title, major.rawText, studentCip,
            homeState ?? undefined, school.stateAbbr ?? undefined,
            publishedCost4yr,
            animalEmoji ?? undefined, locale,
            // Forward intent_keywords so the /build call sees the same
            // SOC-expansion universe /build/outcomes saw — see api/build.ts.
            major.intentKeywords ?? [],
          ),
          minDisplayTime,
        ]);
        if (cancelledRef.current) return;
        setBuild(result);
        setFights(result.gauntlet.fights);
        setSkillPoolLoading(false);
        setIsBuilding(false);
        useBuildsCountStore.getState().refresh();
        fireCheckpoint("/my-build");
      } catch (fallbackErr) {
        if (cancelledRef.current) return;
        setError(fallbackErr instanceof Error ? fallbackErr.message : "Build failed");
        setSkillPoolLoading(false);
        setIsBuilding(false);
      }
    }
  }, [selectedCareer, school, major, profileName, effort, loans, homeState, locale, animalEmoji, setBuild, updateBuild, setIsBuilding]);

  useEffect(() => {
    if (buildTriggeredRef.current) return;
    buildTriggeredRef.current = true;
    if (!build && !isBuilding && selectedCareer) {
      runBuild();
    } else if (build) {
      setFights(build.gauntlet.fights);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync streaming narrative updates from store into local fights state.
  // Rerolled fights keep local state; non-rerolled fights take store version.
  useEffect(() => {
    if (!build) return;
    setFights((prev) => {
      if (prev.length === 0) return build.gauntlet.fights;
      return prev.map((f) => {
        if (f.rerolled) return f;
        const storeFight = build.gauntlet.fights.find((sf) => sf.boss === f.boss);
        return storeFight ?? f;
      });
    });
  }, [build]); // eslint-disable-line react-hooks/exhaustive-deps

  // Reveal queue system
  const clearBandTimeouts = useCallback((bossId: string) => {
    const ids = timeoutsRef.current.get(bossId);
    if (ids) {
      ids.forEach((id) => window.clearTimeout(id));
      timeoutsRef.current.delete(bossId);
    }
  }, []);

  const skipToRevealed = useCallback((bossId: string) => {
    clearBandTimeouts(bossId);
    setVsActiveBands((p) => { const n = new Set(p); n.delete(bossId); return n; });
    setVsDoneBands((p) => new Set(p).add(bossId));
    setRevealedBands((p) => new Set(p).add(bossId));
    if (animatingRef.current === bossId) {
      animatingRef.current = null;
    }
  }, [clearBandTimeouts]);

  const processNext = useCallback(() => {
    if (animatingRef.current) return;
    const next = pendingQueueRef.current.shift();
    if (!next) return;
    animatingRef.current = next;

    const ids: number[] = [];

    // Phase 1: VS active
    ids.push(window.setTimeout(() => {
      setVsActiveBands((p) => new Set(p).add(next));
    }, 200));

    // Phase 2: VS done
    ids.push(window.setTimeout(() => {
      setVsDoneBands((p) => new Set(p).add(next));
    }, 1200));

    // Phase 3: Reveal
    ids.push(window.setTimeout(() => {
      setVsActiveBands((p) => { const n = new Set(p); n.delete(next); return n; });
      setRevealedBands((p) => new Set(p).add(next));
      animatingRef.current = null;
      processNext();
    }, 1350));

    timeoutsRef.current.set(next, ids);
  }, []);

  const triggerReveal = useCallback((bossId: string) => {
    if (revealedBandsRef.current.has(bossId) || vsActiveBandsRef.current.has(bossId)) return;
    if (pendingQueueRef.current.includes(bossId)) return;

    pendingQueueRef.current.push(bossId);
    if (!animatingRef.current) {
      processNext();
    }
  }, [processNext]);

  // IntersectionObserver setup
  useEffect(() => {
    if (!build || fights.length === 0) return;

    const visibilityObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const bossId = (entry.target as HTMLElement).dataset.boss;
          if (!bossId) return;
          if (entry.isIntersecting) {
            setVisibleBands((p) => new Set(p).add(bossId));
          }
        });
      },
      { threshold: 0.1 },
    );

    const centerObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const bossId = (entry.target as HTMLElement).dataset.boss;
          if (!bossId) return;
          if (entry.isIntersecting) {
            triggerReveal(bossId);
          } else if (!entry.isIntersecting) {
            // Fast-scroll skip — read refs to avoid stale closures
            if (
              (vsActiveBandsRef.current.has(bossId) || pendingQueueRef.current.includes(bossId)) &&
              !revealedBandsRef.current.has(bossId)
            ) {
              skipToRevealed(bossId);
              const idx = pendingQueueRef.current.indexOf(bossId);
              if (idx !== -1) pendingQueueRef.current.splice(idx, 1);
            }
          }
        });
      },
      { threshold: 0.15, rootMargin: "-20% 0px -20% 0px" },
    );

    bandRefs.current.forEach((el) => {
      visibilityObserver.observe(el);
      centerObserver.observe(el);
    });

    return () => {
      visibilityObserver.disconnect();
      centerObserver.disconnect();
    };
  // `isBuilding` is included so the observer re-runs when the loading
  // screen unmounts and boss-band refs become available.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [build, fights, isBuilding, triggerReveal, skipToRevealed]);

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      timeoutsRef.current.forEach((ids) => ids.forEach((id) => window.clearTimeout(id)));
    };
  }, []);

  // Reroll handlers
  const handleRerollComplete = useCallback((updated: BossFightResult) => {
    setFights((prev) =>
      prev.map((f) => (f.boss === updated.boss ? updated : f)),
    );
  }, []);

  const handleSkillsConsumed = useCallback((usedIds: string[]) => {
    setConsumedSkillIds((prev) => {
      const next = new Set(prev);
      usedIds.forEach((id) => next.add(id));
      return next;
    });
  }, []);

  // Derived state
  const availableSkillPool = useMemo(() => {
    if (!build) return [];
    return build.skill_pool.filter((s) => !consumedSkillIds.has(s.id));
  }, [build, consumedSkillIds]);

  const verdictCounts = useMemo(() => {
    let rawWins = 0;
    let equippedWins = 0;
    let losses = 0;
    let draws = 0;
    let unknowns = 0;
    fights.forEach((f) => {
      if (f.result === "win") {
        if (f.rerolled) equippedWins++;
        else rawWins++;
      } else if (f.result === "lose") {
        losses++;
      } else if (f.result === "draw") {
        draws++;
      } else if (f.result === "unknown") {
        unknowns++;
      }
    });
    return { rawWins, equippedWins, losses, draws, unknowns };
  }, [fights]);

  // Guards
  if (!build && (!selectedCareer || !school || !major)) return null;

  return (
    <>
    <AnimatePresence mode="wait">
      {(isBuilding || !build) ? (
        <motion.div
          key="loading"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          <BuildLoadingScreen
            animalEmoji={animalEmoji ?? "🐻"}
            profileName={profileName || "Adventurer"}
            schoolName={school?.name ?? ""}
            majorTitle={major?.cipTitle ?? ""}
            buildingStage={buildingStage}
            buildingTotal={buildingTotal}
            error={error}
            onRetry={runBuild}
            onGoBack={() => navigate("/set-your-course")}
          />
        </motion.div>
      ) : (() => {
        const career = build.career;
        return (
          <motion.div
            key={build.build_id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
    <div className="min-h-screen pt-14 pb-32">
      {/* Section 1: Campus Hero Banner */}
      <CampusHeroBanner />

      {/* Hero Identity */}
      <HeroIdentity
        profileName={build.profile_name || profileName || "Adventurer"}
        animalEmoji={build.animal_emoji || animalEmoji || "🐻"}
        schoolName={school?.name ?? build.school_name}
        programName={major?.cipTitle ?? build.program_name}
      />

      {/* Content column */}
      <div className="max-w-[1280px] mx-auto px-4 tablet:px-6 desktop:px-8">

        {/* Adjust / Start over links + Export PDF */}
        <div className="flex justify-end items-center gap-4 flex-wrap" style={{ marginTop: 16 }}>
          <ExportPdfButton
            buildId={build.build_id}
            schoolName={build.school_name}
            programName={career.program_name || build.program_name || career.occupation_title}
          />
          <button
            type="button"
            className="font-body text-text-muted hover:text-text-secondary hover:underline transition-colors duration-150 bg-transparent border-none cursor-pointer"
            style={{ fontSize: 14 }}
            onClick={() => {
              // Fire-and-forget by design: clearSession is best-effort
              // server-side cleanup. The user is already navigating away;
              // awaiting it would block the redirect on a network outage
              // and trap them on this screen. Do not "fix" to await.
              clearSession().catch(console.warn);
              useBuildInputStore.getState().reset();
              useBuildStore.setState({ build: null, selectedCareer: null });
              navigate("/set-your-course");
            }}
          >
            {t("build.startOver")}
          </button>
          <button
            type="button"
            className="font-body text-accent-info hover:underline hover:brightness-125 transition-colors duration-150 bg-transparent border-none cursor-pointer"
            style={{ fontSize: 14 }}
            onClick={() => {
              useBuildStore.setState({ build: null });
              navigate("/set-your-course", { state: { adjustMode: true } });
            }}
          >
            {t("build.adjustEffort")}
          </button>
        </div>

        {/* Section 2: Path + Institution grid */}
        <div
          className="path-institution-grid grid gap-6 items-stretch"
          style={{
            gridTemplateColumns: "1fr 1.6fr",
            marginTop: 32,
            animation: "sectionFadeIn 0.5s cubic-bezier(0.25, 1, 0.5, 1) 0.2s both",
          }}
        >
          <div className="flex flex-col gap-6">
            <PathCard
              programName={career.program_name || major?.cipTitle || build.program_name}
              cipCode={career.cipcode}
              careerName={career.occupation_title}
              socCode={career.soc_code}
              stats={career.stats}
            />
            <FinancesCard
              career={career}
              loanPct={career.loan_pct}
              isInState={career.is_out_of_state != null ? !career.is_out_of_state : (homeState && school?.stateAbbr ? homeState === school.stateAbbr : null)}
            />
          </div>
          <InstitutionCard
            schoolName={build.school_name}
            narrative={build.guidance}
          />
        </div>

        {/* Section 2.5: Compare schools trigger — directly under the
            Path + Institution grid. Single sheet trigger; mode is filterable
            inside the sheet. */}
        <div
          style={{ marginTop: 48, animation: "sectionFadeIn 0.5s cubic-bezier(0.25, 1, 0.5, 1) 0.3s both" }}
          data-testid="compare-schools-host"
        >
          <h2 className="font-display font-bold text-text-primary mb-4" style={{ fontSize: 32 }}>
            {t("compareSchools.sectionHeader")}
          </h2>
          <button
            type="button"
            data-testid="btn-compare-schools"
            onClick={() => setCompareOpen(true)}
            className="w-full flex items-center gap-3 min-h-12 py-3 px-4 rounded-xl bg-bp-mid hover:bg-bp-surface border-l-2 border-accent-insight font-display text-body text-text-primary transition-colors text-left"
          >
            <span className="flex-1 min-w-0">
              {rankSummary && (
                <span
                  data-testid="compare-rank-lead"
                  className="block text-body text-text-primary"
                >
                  {t("compareSchools.rankLead")
                    .replace(
                      "{institutionName}",
                      career.institution_name || build.school_name,
                    )
                    .replace("{rank}", `#${rankSummary.rank}`)
                    .replace(
                      "{total}",
                      rankSummary.total.toLocaleString(),
                    )
                    .replace(
                      "{programNameShort}",
                      career.program_name || build.program_name,
                    )}
                </span>
              )}
              <span
                className={
                  rankSummary
                    ? "block text-small text-text-secondary mt-1"
                    : "block truncate"
                }
              >
                {t("compareSchools.bySoc.trigger").replace(
                  "{occupationTitle}",
                  career.occupation_title,
                )}
              </span>
            </span>
            <span aria-hidden="true" className="text-text-muted">›</span>
          </button>
          <CompareSchoolsPanel
            mode="by_soc"
            enclosure="sheet"
            socCode={career.soc_code}
            cipcode={career.cipcode}
            occupationTitle={career.occupation_title}
            programName={career.program_name || build.program_name}
            anchor={{
              unitid: career.unitid,
              cipcode: career.cipcode,
              statErn: career.stats.ern,
              statRoi: career.stats.roi,
              institutionName: career.institution_name || build.school_name,
              institutionControl: career.institution_control ?? null,
              programName: career.program_name || build.program_name,
              stateAbbr: school?.stateAbbr ?? null,
              earnings1yrMedian: career.earnings_1yr_median,
              netPriceAnnual: career.net_price_annual,
              // Residency-aware 4-yr sticker for the synthetic anchor
              // row's "Cost (4 yr)" cell — matches the FINANCES card.
              publishedCost4yr: career.published_cost_4yr,
            }}
            // Forward the user's home state so each leaderboard row's
            // cost + ROI come back residency-aware (matches FINANCES card).
            homeState={homeState ?? null}
            open={compareOpen}
            // Slide the leaderboard left when Ask Gemma is open so the
            // chat drawer doesn't cover the right-side columns.
            chatOpen={chatOpen}
            onClose={() => setCompareOpen(false)}
            onBuildAtRow={(row: SchoolForCareerRow) => {
              if (!profileName) return;
              setCompareOpen(false);
              void spawnBuildFromRow(row, {
                profileName,
                effort,
                loans,
                homeState: homeState ?? null,
                animalEmoji: animalEmoji ?? null,
                locale: locale ?? "en",
              });
            }}
          />
        </div>

        {/* Section 3: Build Stats (Pentagon + Legend) */}
        <div style={{ marginTop: 48, animation: "sectionFadeIn 0.5s cubic-bezier(0.25, 1, 0.5, 1) 0.4s both" }}>
          <h2 className="font-display font-bold text-text-primary" style={{ fontSize: 32 }}>
            {t("build.buildStats")}
          </h2>

          <div
            className="rounded-[20px] border border-border-subtle bg-bp-mid mt-4"
            style={{ padding: 32 }}
          >
            <div className="flex gap-12 items-center flex-wrap">
              <div>
                <PentagonChart
                  stats={career.stats}
                  size={320}
                  animated
                  delay={0.3}
                  highlightStat={highlightStat}
                  onHoverStat={setHighlightStat}
                />
              </div>

              {/* Stat legend */}
              <div className="flex-1" style={{ minWidth: 240 }}>
                {STAT_KEYS.map((key) => {
                  const stat = STAT_EXPLANATIONS.find((s) => s.key === key)!;
                  const colors = STAT_COLORS[key];
                  const value = career.stats[key];

                  return (
                    <div key={key}>
                      <div
                        className="flex items-center gap-3 cursor-pointer transition-colors duration-150"
                        style={{
                          padding: "14px 0",
                          borderBottom: "1px solid rgba(255,255,255,0.06)",
                        }}
                        onMouseEnter={() => setHighlightStat(key)}
                        onMouseLeave={() => setHighlightStat(null)}
                      >
                        {/* Dot */}
                        <div
                          className="flex-shrink-0 rounded-full"
                          style={{ width: 12, height: 12, background: colors?.text }}
                        />
                        {/* Abbreviation */}
                        <span className="font-data text-text-muted" style={{ fontSize: 12, width: 32 }}>
                          {stat.abbreviation}
                        </span>
                        {/* Name + explanation */}
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span
                              className="font-display font-semibold transition-colors duration-150"
                              style={{
                                fontSize: 15,
                                color: highlightStat === key ? colors?.text : "var(--color-text-primary)",
                                animation: highlightStat === key ? "statPulse 1.2s ease-in-out infinite" : undefined,
                              }}
                            >
                              {t(stat.nameKey)}
                            </span>
                            {/* Info trigger */}
                            <button
                              type="button"
                              className="flex-shrink-0 rounded-full flex items-center justify-center font-body font-bold transition-all duration-150"
                              style={{
                                width: 18,
                                height: 18,
                                fontSize: 11,
                                border: openPopover === key
                                  ? `1.5px solid var(--color-accent-info)`
                                  : "1.5px solid var(--color-border-default)",
                                color: openPopover === key ? "var(--color-accent-info)" : undefined,
                                background: openPopover === key ? "rgba(123,184,224,0.08)" : undefined,
                                opacity: openPopover === key ? 1 : 0.6,
                              }}
                              aria-expanded={openPopover === key}
                              aria-controls={`info-${key}`}
                              aria-label={`What is ${stat.name}?`}
                              onClick={() => setOpenPopover(openPopover === key ? null : key)}
                            >
                              ?
                            </button>
                          </div>
                          <p className="font-body text-text-secondary" style={{ fontSize: 13, lineHeight: 1.5, marginTop: 4 }}>
                            {t(stat.explanationKey)}
                          </p>
                          {/* Explain-this-stat trigger — available for all
                             five stats. AURA gated on stats.aura !== null. */}
                          {(key === "ern" || key === "roi" || key === "res" || key === "grw" || (key === "aura" && value != null)) && (
                            <button
                              type="button"
                              onClick={() => handleExplainStat(key)}
                              data-testid={`btn-explain-${key}`}
                              aria-label={t("build.statHover.explainAria", { label: STAT_INFO[key]?.title ?? key.toUpperCase() })}
                              disabled={chatOpen}
                              className="inline-flex items-center gap-1.5 mt-2 px-2 py-1 -mx-2 rounded-md font-body font-semibold transition-colors duration-fast cursor-pointer hover:bg-state-loading active:scale-[0.97] focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-none disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent"
                              style={{ fontSize: 12, color: colors?.text }}
                            >
                              <span aria-hidden>✦</span>
                              {t("build.statHover.explainAffordance")}
                            </button>
                          )}
                        </div>
                        {/* Score */}
                        <div className="flex-shrink-0 text-right">
                          <span className="font-data font-bold" style={{ fontSize: 18, color: colors?.text }}>
                            {value ?? "—"}
                          </span>
                          <span className="font-data" style={{ fontSize: 13, fontWeight: 400, opacity: 0.45, color: colors?.text }}>
                            /10
                          </span>
                        </div>
                      </div>

                      {/* Popover */}
                      <StatInfoPopover
                        stat={key}
                        isOpen={openPopover === key}
                        onClose={() => setOpenPopover(null)}
                        onAsk={(statKey) => {
                          setOpenPopover(null);
                          handleAskStat(statKey);
                        }}
                        chatOpen={chatOpen}
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Section 4: Boss Fight Results (The Gauntlet) */}
        <div style={{ marginTop: 48, animation: "sectionFadeIn 0.5s cubic-bezier(0.25, 1, 0.5, 1) 0.6s both" }}>
          <h2 className="font-display font-bold text-text-primary" style={{ fontSize: 32 }}>
            {t("build.gauntlet")}
          </h2>
          <p className="font-body text-text-secondary" style={{ fontSize: 16, marginTop: 4 }}>
            {t("build.gauntletDesc")}
          </p>

          <div
            className="flex flex-col gap-12 mt-6"
            style={{ scrollSnapType: "y proximity" }}
          >
            {fights.map((fight) => (
              <div
                key={fight.boss}
                ref={(el) => {
                  if (el) bandRefs.current.set(fight.boss, el);
                  else bandRefs.current.delete(fight.boss);
                }}
                data-boss={fight.boss}
                onClick={() => {
                  if (!revealedBands.has(fight.boss)) triggerReveal(fight.boss);
                }}
                onKeyDown={(e) => {
                  if (
                    !revealedBands.has(fight.boss) &&
                    (e.key === "Enter" || e.key === " ")
                  ) {
                    e.preventDefault();
                    triggerReveal(fight.boss);
                  }
                }}
                role={!revealedBands.has(fight.boss) ? "button" : undefined}
                tabIndex={!revealedBands.has(fight.boss) ? 0 : undefined}
                aria-label={
                  !revealedBands.has(fight.boss)
                    ? t("build.bossSealed.revealAria")
                        .replace(
                          "{bossName}",
                          t(BOSS_META[fight.boss].shortNameKey),
                        )
                    : undefined
                }
              >
                <BossBand
                  fight={fight}
                  buildId={build.build_id}
                  playerEmoji={animalEmoji ?? "🐻"}
                  playerName={profileName ?? "Adventurer"}
                  skillPool={availableSkillPool}
                  skillPoolLoading={skillPoolLoading}
                  onRerollComplete={handleRerollComplete}
                  onSkillsConsumed={handleSkillsConsumed}
                  isRevealed={revealedBands.has(fight.boss)}
                  isSealed={!revealedBands.has(fight.boss)}
                  isVsActive={vsActiveBands.has(fight.boss)}
                  isVsDone={vsDoneBands.has(fight.boss)}
                  isSealedVisible={visibleBands.has(fight.boss)}
                  onReveal={() => triggerReveal(fight.boss)}
                  onAskBoss={handleAskBoss}
                  onAskSkill={handleAskSkill}
                  chatOpen={chatOpen}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Section 5: Verdict */}
        <div style={{ marginTop: 48, animation: "sectionFadeIn 0.5s cubic-bezier(0.25, 1, 0.5, 1) 0.8s both" }}>
          <VerdictBadge
            rawWins={verdictCounts.rawWins}
            equippedWins={verdictCounts.equippedWins}
            losses={verdictCounts.losses}
            draws={verdictCounts.draws}
            unknowns={verdictCounts.unknowns}
          />
        </div>

        {/* Section 6 (Save CTA + See the future link) lifted into the
            sticky bottom action bar below — outside this content column. */}
      </div>

      {/* Responsive overrides + shared keyframes */}
      <style>{`
        @keyframes sectionFadeIn {
          from { opacity: 0; transform: translateY(24px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes statPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
        @media (max-width: 899px) {
          .path-institution-grid { grid-template-columns: 1fr !important; }
        }
        @media (max-width: 767px) {
          .pentagon-flex { flex-direction: column !important; }
          .pentagon-sticky { position: static !important; }
          .section-gaps { margin-top: 32px !important; }
          .save-section { margin-top: 32px !important; margin-bottom: 48px !important; }
        }
      `}</style>

    </div>
          </motion.div>
        );
      })()}
    </AnimatePresence>

      <AnimatePresence>
        {!chatOpen && build !== null && !isBuilding && (
          <motion.div
            key="my-build-action-bar"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            transition={springs.smooth}
            className="fixed inset-x-0 bottom-0 z-40 bg-bp-deep/85 backdrop-blur-lg"
            style={{
              boxShadow:
                "inset 0 1px 0 0 rgba(245, 240, 232, 0.06), 0 -12px 32px -8px rgba(0, 0, 0, 0.45), 0 -1px 0 0 rgba(0, 0, 0, 0.4)",
            }}
            data-testid="my-build-action-bar"
          >
            <PageContainer variant="centered" className="py-4">
              <div
                className="grid grid-cols-2 gap-3 tablet:grid-cols-[2fr_1fr_1fr] tablet:gap-3"
                style={{ paddingBottom: "max(0px, env(safe-area-inset-bottom))" }}
              >
                <motion.button
                  onClick={handleSave}
                  disabled={saveState === "saving"}
                  aria-live="polite"
                  aria-busy={saveState === "saving"}
                  className="w-full h-12 rounded-lg font-body font-bold text-cta cursor-pointer flex items-center justify-center gap-2 bg-accent-thrive text-text-inverse hover:bg-[#6bc494] hover:shadow-glow-thrive disabled:cursor-wait disabled:opacity-90"
                  whileTap={saveState === "idle" || saveState === "error" ? { scale: 0.97 } : undefined}
                  transition={springs.snappy}
                  data-testid="btn-save-build-bar"
                >
                  <span className="w-5 h-5 flex-none flex items-center justify-center">
                    {saveState === "saving" && (
                      <svg viewBox="0 0 20 20" className="w-5 h-5 animate-spin" fill="none" aria-hidden>
                        <circle cx="10" cy="10" r="7" stroke="currentColor" strokeOpacity="0.25" strokeWidth="2" />
                        <path d="M17 10a7 7 0 0 0-7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                      </svg>
                    )}
                    {saveState === "saved" && (
                      <svg viewBox="0 0 20 20" className="w-5 h-5" fill="none" aria-hidden>
                        <path d="M5 10.5l3.5 3.5L15 7" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                    {saveState === "error" && (
                      <svg viewBox="0 0 20 20" className="w-5 h-5" fill="none" aria-hidden>
                        <path d="M6 6l8 8M14 6l-8 8" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
                      </svg>
                    )}
                  </span>
                  <span className="min-w-[5.5rem] text-center">
                    {saveState === "saving"
                      ? t("build.savingBuild")
                      : saveState === "saved"
                        ? t("build.savedBuild")
                        : saveState === "error"
                          ? t("build.retryBuild")
                          : t("build.saveBuild")}
                  </span>
                </motion.button>

                <motion.button
                  onClick={() => navigate("/future")}
                  className="w-full h-12 rounded-lg font-body font-bold text-cta cursor-pointer flex items-center justify-center gap-2 bg-bp-raised text-text-primary border border-border-subtle hover:bg-bp-elevated hover:border-border-strong"
                  whileTap={{ scale: 0.97 }}
                  transition={springs.snappy}
                  data-testid="btn-see-future-bar"
                >
                  {t("build.seeFuture")}
                </motion.button>

                <motion.button
                  onClick={handleAskBuild}
                  aria-label={t("chat.askAboutBuild")}
                  className="w-full h-12 rounded-lg font-body font-bold text-cta cursor-pointer flex items-center justify-center gap-2 bg-accent-insight/15 text-accent-insight border border-accent-insight/40 hover:bg-accent-insight/25 hover:border-accent-insight/70 hover:shadow-glow-insight"
                  whileTap={{ scale: 0.97 }}
                  transition={springs.snappy}
                  data-testid="btn-ask-build"
                >
                  <span aria-hidden className="font-display text-[18px] leading-none">
                    ✦
                  </span>
                  {t("build.askGemma")}
                </motion.button>
              </div>
            </PageContainer>
          </motion.div>
        )}
      </AnimatePresence>

      <GemmaChat
        open={chatOpen}
        build={null}
        scope={chatScope ?? undefined}
        chipText={chatChipText}
        starters={chatStarters}
        openerPrompt={chatOpenerPrompt ?? undefined}
        onClose={closeChat}
      />
    </>
  );
}
