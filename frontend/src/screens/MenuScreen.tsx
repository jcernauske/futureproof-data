import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";
import { Button } from "@/components/ui/Button";
import { useProfileStore } from "@/store/profileStore";
import { useBuildStore } from "@/store/buildStore";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildsCountStore } from "@/store/buildsCountStore";
import { listBuilds, type BuildSummary } from "@/api/menu";
import { deleteBuild, getBuild } from "@/api/build";
import { BuildCard } from "@/components/menu/BuildCard";
import { CompareView } from "@/components/menu/CompareView";
import { VERDICT_TIERS } from "@/components/build-results/bossData";

import { PageContainer } from "@/components/ui/PageContainer";
import { useT } from "@/i18n/useT";

type Mode = "list" | "select" | "compare";

// Status filter values mirror VERDICT_TIERS — matching is by `min` so the
// filter picks builds whose `wins` resolve to that exact tier.
type StatusFilter = "all" | (typeof VERDICT_TIERS)[number]["wordShortKey"];

function buildStatusKey(wins: number): (typeof VERDICT_TIERS)[number]["wordShortKey"] {
  const tier = VERDICT_TIERS.find((t) => wins >= t.min)
    ?? VERDICT_TIERS[VERDICT_TIERS.length - 1]!;
  return tier.wordShortKey;
}

export function MenuScreen() {
  const navigate = useNavigate();
  const t = useT();
  const profileName = useProfileStore((s) => s.profileName);
  const animalEmoji = useProfileStore((s) => s.animalEmoji);
  const setBuild = useBuildStore((s) => s.setBuild);
  const resetInputs = useBuildInputStore((s) => s.resetInputs);
  const clearProfile = useProfileStore((s) => s.clearProfile);

  const [builds, setBuilds] = useState<BuildSummary[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("list");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [navigatingId, setNavigatingId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  // Lock as a ref so a fast double-click can't race two getBuild calls
  // and land at /my-build with the wrong build's payload.
  const navigatingRef = useRef<string | null>(null);
  // Set when handleCompareGo initiates a select→compare transition.
  // React Router defers the URL update via startTransition while the
  // local mode/compareIds updates apply urgently, so without this guard
  // the auto-enter-select effect below sees the stale ?select=1 URL and
  // bounces the user back into select mode with an empty selection.
  const enteringCompareRef = useRef(false);

  useEffect(() => {
    if (!profileName) navigate("/set-your-course", { replace: true });
  }, [profileName, navigate]);

  useEffect(() => {
    if (!profileName) return;
    let cancelled = false;
    setLoadingList(true);
    setListError(null);
    listBuilds()
      .then((res) => {
        if (cancelled) return;
        setBuilds(res);
        // Sync the count from the same payload the on-screen list uses, and
        // clear `loading` so a concurrent AppHeader mount fetch (which sets
        // loading:true on dispatch) is reset.
        useBuildsCountStore.setState({
          count: res.length,
          loading: false,
          error: null,
        });
      })
      .catch((e) => {
        if (cancelled) return;
        setListError(e instanceof Error ? e.message : "Couldn't load builds.");
      })
      .finally(() => {
        if (!cancelled) setLoadingList(false);
      });
    return () => {
      cancelled = true;
    };
  }, [profileName]);

  const mostRecentId = useMemo(() => {
    if (builds.length === 0) return null;
    // listBuilds returns newest first, so position 0 is the most recent.
    return builds[0]!.build_id;
  }, [builds]);

  // Filter builds by free-text search (school OR career, case-insensitive
  // substring) and by build status (verdict tier). Builds with zero
  // scored fights collapse into the lowest tier (VULNERABLE) — same
  // grouping the BuildCard verdict label uses, but they are kept out of
  // *all* status-tier filters except "all" so a fresh build doesn't get
  // tagged as VULNERABLE in the filter pills.
  const filteredBuilds = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return builds.filter((b) => {
      if (query) {
        const inSchool = b.school_name.toLowerCase().includes(query);
        const inCareer = b.career_title.toLowerCase().includes(query);
        if (!inSchool && !inCareer) return false;
      }
      if (statusFilter !== "all") {
        const totalScored = b.wins + b.losses + b.draws;
        if (totalScored === 0) return false;
        if (buildStatusKey(b.wins) !== statusFilter) return false;
      }
      return true;
    });
  }, [builds, searchQuery, statusFilter]);

  const filtersActive = searchQuery.trim().length > 0 || statusFilter !== "all";

  const clearFilters = useCallback(() => {
    setSearchQuery("");
    setStatusFilter("all");
  }, []);

  const handleViewBuild = useCallback(
    async (build: BuildSummary) => {
      if (mode === "select") {
        setSelectedIds((current) => {
          if (current.includes(build.build_id)) {
            return current.filter((id) => id !== build.build_id);
          }
          if (current.length >= 4) return current;
          return [...current, build.build_id];
        });
        return;
      }
      if (navigatingRef.current !== null) return;
      navigatingRef.current = build.build_id;
      setNavigatingId(build.build_id);

      try {
        const full = await getBuild(build.build_id);
        setBuild(full);
        navigate("/my-build");
      } catch (e) {
        setListError(e instanceof Error ? e.message : "Couldn't load build.");
        setNavigatingId(null);
        navigatingRef.current = null;
      }
    },
    [mode, navigate, setBuild],
  );

  const handleNewBuild = useCallback(() => {
    clearProfile();
    resetInputs();
    useBuildStore.getState().resetBuild();
    navigate("/profile");
  }, [clearProfile, navigate, resetInputs]);

  const [searchParams, setSearchParams] = useSearchParams();

  const handleCancelSelect = useCallback(() => {
    setMode("list");
    setSelectedIds([]);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete("select");
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  // Auto-enter select mode when AppHeader's Compare button drops us at
  // /builds?select=1, so the user only has to pick which builds to compare.
  // Runs from any mode (including `compare`) so the header Compare button
  // always returns the user to the picker, even from the results view.
  useEffect(() => {
    if (enteringCompareRef.current) {
      if (searchParams.get("select") !== "1") {
        enteringCompareRef.current = false;
      }
      return;
    }
    if (searchParams.get("select") !== "1") return;
    if (builds.length < 2) return;
    if (mode === "select") return;
    setMode("select");
    setSelectedIds([]);
    setCompareIds([]);
  }, [searchParams, builds.length, mode]);

  // Reset to plain list when AppHeader's My Builds icon drops us back at
  // /builds with no query — without this, lingering select/compare mode
  // keeps the selection dots or the compare view alive.
  useEffect(() => {
    const isCompareView = searchParams.get("view") === "compare";
    const isSelectMode = searchParams.get("select") === "1";
    if (isCompareView || isSelectMode) return;
    if (mode === "list") return;
    setMode("list");
    setSelectedIds([]);
    setCompareIds([]);
  }, [searchParams, mode]);

  const handleCompareGo = useCallback(() => {
    if (selectedIds.length < 2 || selectedIds.length > 4) return;
    enteringCompareRef.current = true;
    setCompareIds(selectedIds);
    setMode("compare");
    setSearchParams({ view: "compare" }, { replace: true });
  }, [selectedIds, setSearchParams]);

  const handleBackFromCompare = useCallback(() => {
    setMode("list");
    setSelectedIds([]);
    setCompareIds([]);
    setSearchParams({}, { replace: true });
  }, [setSearchParams]);

  const handleDeleteBuild = useCallback(async (buildId: string) => {
    try {
      await deleteBuild(buildId);
      setBuilds((prev) => {
        const next = prev.filter((b) => b.build_id !== buildId);
        // Optimistic count update — keep the badge in lockstep with the
        // on-screen list. refresh() below provides eventual-consistency
        // safety in case the backend disagrees.
        useBuildsCountStore.setState({ count: next.length, error: null });
        return next;
      });
      setSelectedIds((prev) => prev.filter((id) => id !== buildId));
      useBuildsCountStore.getState().refresh();
    } catch (e) {
      setListError(e instanceof Error ? e.message : "Couldn't delete build.");
    }
  }, []);


  if (!profileName) return null;

  return (
    <>
      <AnimatePresence mode="wait">
        {mode === "compare" && compareIds.length > 0 ? (
          <motion.div
            key="compare-container"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, transition: { duration: 0.25 } }}
            exit={{ opacity: 0, transition: { duration: 0.18, ease: "easeIn" } }}
          >
            <PageContainer variant="grid" testId="screen-menu" className="pt-24 pb-16">
              <div className="col-span-12 desktop:col-span-10 desktop:col-start-2">
                <CompareView buildIds={compareIds} onBack={handleBackFromCompare} />
              </div>
            </PageContainer>
          </motion.div>
        ) : (
          <motion.div
            key="list-container"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0, transition: springs.smooth }}
            exit={{ opacity: 0, y: -8, transition: { duration: 0.18, ease: "easeIn" } }}
          >
          <PageContainer variant="centered" testId="screen-menu" className="pt-24 pb-32">
            <div className="flex flex-col gap-8">
            <header className="flex flex-col gap-2">
              <p className="font-data text-micro uppercase tracking-[2px] text-text-muted">
                {t("menu.kicker")}
              </p>
              <AnimatePresence mode="wait">
                <motion.h1
                  key={mode === "select" ? "heading-select" : "heading-list"}
                  className="font-display text-display text-text-primary"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.15 }}
                >
                  {mode === "select" ? t("menu.headingCompare") : t("menu.headingView")}
                </motion.h1>
              </AnimatePresence>
              <p className="font-body text-body text-text-secondary">
                {t("menu.subtitle")}
              </p>
            </header>

            <section
              data-testid="region-saved-builds"
              aria-label={t("menu.savedAria")}
              className="flex flex-col gap-3"
            >
              {loadingList && (
                <p className="font-body text-body text-text-muted">
                  {t("menu.loadingBuilds")}
                </p>
              )}
              {!loadingList && listError && (
                <p className="font-body text-body text-accent-alert">{listError}</p>
              )}
              {!loadingList && !listError && builds.length === 0 && (
                <div className="flex flex-col items-center gap-4 py-12 text-center">
                  <p className="font-display text-heading text-text-primary">
                    {t("menu.emptyTitle")}
                  </p>
                  <p className="font-body text-body text-text-secondary">
                    {t("menu.emptyDescription")}
                  </p>
                  <Button variant="primary" onClick={handleNewBuild} data-testid="btn-new-build">
                    {t("menu.startFirstBuild")}
                  </Button>
                </div>
              )}
              {!loadingList && !listError && builds.length > 0 && (
                <div
                  data-testid="builds-filters"
                  role="search"
                  aria-label={t("menu.filterStatusAria")}
                  className="flex flex-col gap-3 mb-3"
                >
                  <div
                    role="radiogroup"
                    aria-label={t("menu.filterStatusAria")}
                    className="flex flex-wrap items-center gap-2"
                  >
                    <input
                      type="search"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder={t("menu.filterSearchPlaceholder")}
                      data-testid="input-builds-filter-search"
                      className="h-9 px-4 bg-bp-deep border border-border-subtle rounded-md font-body text-body text-text-primary placeholder:text-text-muted focus:border-accent-info focus:outline-none focus:shadow-[0_0_0_3px_rgba(123,184,224,0.15)] transition-all duration-normal flex-1 min-w-[200px]"
                    />
                    {(["all", ...VERDICT_TIERS.map((tt) => tt.wordShortKey)] as const).map((value) => {
                      const isActive = statusFilter === value;
                      const isAll = value === "all";
                      const tier = isAll
                        ? null
                        : VERDICT_TIERS.find((tt) => tt.wordShortKey === value)!;
                      const label = isAll
                        ? t("menu.filterStatusAll")
                        : t(tier!.wordShortKey);
                      const accent = tier?.accentClass ?? "text-text-primary";
                      return (
                        <button
                          key={value}
                          type="button"
                          role="radio"
                          aria-checked={isActive}
                          data-testid={`filter-status-${isAll ? "all" : tier!.wordShortKey.split(".").pop()}`}
                          onClick={() =>
                            setStatusFilter(value as StatusFilter)
                          }
                          className={`px-3 py-1.5 rounded-full font-data font-bold uppercase border transition-colors duration-normal cursor-pointer ${
                            isActive
                              ? `${accent} border-current bg-bp-surface`
                              : "text-text-muted border-border-subtle hover:text-text-secondary hover:border-border"
                          }`}
                          style={{ fontSize: 11, letterSpacing: 1 }}
                        >
                          {label}
                        </button>
                      );
                    })}
                    {filtersActive && (
                      <button
                        type="button"
                        onClick={clearFilters}
                        data-testid="btn-clear-filters"
                        className="ml-auto px-3 py-1.5 rounded-full font-body text-small text-text-secondary hover:text-text-primary cursor-pointer"
                      >
                        {t("menu.filterClear")}
                      </button>
                    )}
                  </div>
                  {filtersActive && (
                    <p
                      data-testid="builds-filter-count"
                      className="font-data text-micro text-text-muted"
                    >
                      {t("menu.filterCount")
                        .replace("{count}", String(filteredBuilds.length))
                        .replace("{total}", String(builds.length))}
                    </p>
                  )}
                </div>
              )}
              {!loadingList && !listError && builds.length > 0 && filteredBuilds.length === 0 && (
                <div
                  className="flex flex-col items-center gap-3 py-12 text-center"
                  data-testid="builds-filter-empty"
                >
                  <p className="font-display text-heading text-text-primary">
                    {t("menu.filterEmptyTitle")}
                  </p>
                  <p className="font-body text-body text-text-secondary">
                    {t("menu.filterEmptyDescription")}
                  </p>
                  <Button
                    variant="secondary"
                    onClick={clearFilters}
                    data-testid="btn-clear-filters-empty"
                  >
                    {t("menu.filterClear")}
                  </Button>
                </div>
              )}
              {!loadingList && !listError && filteredBuilds.length > 0 && (
                <motion.div
                  className="flex flex-col gap-2"
                  initial="hidden"
                  animate="visible"
                  variants={{
                    hidden: {},
                    visible: { transition: { staggerChildren: stagger.normal } },
                  }}
                >
                  {filteredBuilds.map((build) => (
                    <motion.div
                      key={build.build_id}
                      variants={{
                        hidden: { opacity: 0, y: 8 },
                        visible: { opacity: 1, y: 0, transition: springs.smooth },
                      }}
                    >
                      <BuildCard
                        build={build}
                        emoji={build.animal_emoji ?? animalEmoji ?? "✦"}
                        isMostRecent={build.build_id === mostRecentId}
                        selectMode={mode === "select"}
                        selected={selectedIds.includes(build.build_id)}
                        onTap={() => handleViewBuild(build)}
                        onDelete={handleDeleteBuild}
                      />
                      {navigatingId === build.build_id && (
                        <p className="px-5 mt-1 font-body text-micro text-text-muted">
                          {t("menu.loadingBuild")}
                        </p>
                      )}
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </section>

            {/* In-flow footer actions removed — list-mode actions now live in
                the sticky bottom bar below (outside this PageContainer so
                fixed positioning isn't trapped by ancestor transforms). */}
            </div>
          </PageContainer>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sticky bottom action bar — list-mode and select-mode actions for
          /builds. Hidden in compare view (CompareView has its own back) and
          in empty state (the hero card owns that surface). */}
      <AnimatePresence>
        {mode === "select" && (
          <motion.div
            key="builds-action-bar"
            initial={{ y: 80, opacity: 0 }}
            animate={{ y: 0, opacity: 1, transition: springs.smooth }}
            exit={{ y: 80, opacity: 0, transition: { duration: 0.15, ease: "easeIn" } }}
            className="fixed inset-x-0 bottom-0 z-40 bg-bp-deep/85 backdrop-blur-lg"
            style={{
              boxShadow:
                "inset 0 1px 0 0 rgba(245, 240, 232, 0.06), 0 -12px 32px -8px rgba(0, 0, 0, 0.45), 0 -1px 0 0 rgba(0, 0, 0, 0.4)",
            }}
            data-testid="builds-action-bar"
          >
            <PageContainer variant="centered" className="py-4">
              <div
                className="grid gap-3 grid-cols-[1fr_3fr]"
                style={{ paddingBottom: "max(0px, env(safe-area-inset-bottom))" }}
              >
                <motion.button
                  onClick={handleCancelSelect}
                  className="w-full h-12 rounded-lg font-body font-bold text-cta cursor-pointer flex items-center justify-center gap-2 bg-bp-raised text-text-primary border border-border-subtle hover:bg-bp-elevated hover:border-border-strong"
                  whileTap={{ scale: 0.97 }}
                  transition={springs.snappy}
                  data-testid="btn-cancel-select"
                >
                  {t("menu.cancel")}
                </motion.button>

                <motion.button
                  onClick={handleCompareGo}
                  disabled={selectedIds.length < 2 || selectedIds.length > 4}
                  className="w-full h-12 rounded-lg font-body font-bold text-cta cursor-pointer flex items-center justify-center gap-2 border disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 bg-accent-thrive text-text-inverse border-transparent hover:bg-[#6bc494]"
                  whileTap={
                    selectedIds.length >= 2 && selectedIds.length <= 4
                      ? { scale: 0.97 }
                      : undefined
                  }
                  transition={springs.snappy}
                  data-testid="btn-compare"
                >
                  {t("menu.compareCount").replace("{count}", String(selectedIds.length))}
                </motion.button>

              </div>
            </PageContainer>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
