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
import { GemmaChat } from "@/components/menu/GemmaChat";
import { PageContainer } from "@/components/ui/PageContainer";
import { useT } from "@/i18n/useT";

type Mode = "list" | "select" | "compare";

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
  const [chatOpen, setChatOpen] = useState(false);
  const [chatBuild, setChatBuild] = useState<BuildSummary | null>(null);
  const [navigatingId, setNavigatingId] = useState<string | null>(null);
  // Lock as a ref so a fast double-click can't race two getBuild calls
  // and land at /my-build with the wrong build's payload.
  const navigatingRef = useRef<string | null>(null);

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

  const handleEnterSelect = useCallback(() => {
    if (builds.length < 2) return;
    setMode("select");
    setSelectedIds([]);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("select", "1");
      return next;
    }, { replace: true });
  }, [builds.length, setSearchParams]);

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
  useEffect(() => {
    if (searchParams.get("select") !== "1") return;
    if (builds.length < 2) return;
    if (mode !== "list") return;
    setMode("select");
    setSelectedIds([]);
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

  const handleAskGemma = useCallback(() => {
    if (!builds.length) return;
    const first = builds[0]!;
    setChatBuild(first);
    setChatOpen(true);
  }, [builds]);

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
                  <div className="flex flex-col tablet:flex-row items-center gap-3">
                    <Button variant="primary" onClick={handleNewBuild} data-testid="btn-new-build">
                      {t("menu.startFirstBuild")}
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={handleNewBuild}
                      data-testid="btn-new-build-set-course"
                    >
                      {t("menu.tryNewFlow")}
                    </Button>
                  </div>
                </div>
              )}
              {!loadingList && !listError && builds.length > 0 && (
                <motion.div
                  className="flex flex-col gap-2"
                  initial="hidden"
                  animate="visible"
                  variants={{
                    hidden: {},
                    visible: { transition: { staggerChildren: stagger.normal } },
                  }}
                >
                  {builds.map((build) => (
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
        {mode !== "compare" && builds.length > 0 && (
          <motion.div
            key="builds-action-bar"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0, transition: springs.smooth }}
            exit={{ opacity: 0, y: 24, transition: { duration: 0.15, ease: "easeIn" } }}
            className="fixed inset-x-0 bottom-0 z-40 bg-bp-deep/85 backdrop-blur-lg"
            style={{
              boxShadow:
                "inset 0 1px 0 0 rgba(245, 240, 232, 0.06), 0 -12px 32px -8px rgba(0, 0, 0, 0.45), 0 -1px 0 0 rgba(0, 0, 0, 0.4)",
            }}
            data-testid="builds-action-bar"
          >
            <PageContainer variant="centered" className="py-4">
              <div
                className="grid grid-cols-3 gap-3"
                style={{ paddingBottom: "max(0px, env(safe-area-inset-bottom))" }}
              >
                {/* Slot 1: Cancel in select mode, blank placeholder otherwise. */}
                <AnimatePresence mode="wait">
                  {mode === "select" ? (
                    <motion.button
                      key="cancel-btn"
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={springs.snappy}
                      onClick={handleCancelSelect}
                      className="w-full h-12 rounded-lg font-body font-bold text-cta cursor-pointer flex items-center justify-center gap-2 bg-bp-raised text-text-primary border border-border-subtle hover:bg-bp-elevated hover:border-border-strong"
                      whileTap={{ scale: 0.97 }}
                      data-testid="btn-cancel-select"
                    >
                      {t("menu.cancel")}
                    </motion.button>
                  ) : (
                    <motion.div
                      key="cancel-placeholder"
                      aria-hidden
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 0 }}
                      exit={{ opacity: 0 }}
                    />
                  )}
                </AnimatePresence>

                {/* Slot 2: Compare. Single button — visual state crossfades
                    via CSS transition; no DOM swap so tests stay stable. */}
                <motion.button
                  onClick={mode === "select" ? handleCompareGo : handleEnterSelect}
                  disabled={
                    mode === "select"
                      ? selectedIds.length < 2 || selectedIds.length > 4
                      : builds.length < 2
                  }
                  className={`w-full h-12 rounded-lg font-body font-bold text-cta cursor-pointer flex items-center justify-center gap-2 border disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 ${
                    mode === "select"
                      ? "bg-accent-thrive text-text-inverse border-transparent hover:bg-[#6bc494]"
                      : "bg-bp-raised text-text-primary border-border-subtle hover:bg-bp-elevated hover:border-border-strong"
                  }`}
                  whileTap={
                    mode === "select"
                      ? selectedIds.length >= 2 && selectedIds.length <= 4
                        ? { scale: 0.97 }
                        : undefined
                      : builds.length >= 2
                        ? { scale: 0.97 }
                        : undefined
                  }
                  transition={springs.snappy}
                  data-testid={mode === "select" ? "btn-compare" : "btn-enter-compare"}
                >
                  {mode === "select"
                    ? t("menu.compareCount").replace("{count}", String(selectedIds.length))
                    : t("menu.compareBuilds")}
                </motion.button>

                {/* Slot 3: Ask Gemma — same in both modes. */}
                <motion.button
                  onClick={handleAskGemma}
                  aria-label={t("menu.askGemma")}
                  className="w-full h-12 rounded-lg font-body font-bold text-cta cursor-pointer flex items-center justify-center gap-2 bg-accent-insight/15 text-accent-insight border border-accent-insight/40 hover:bg-accent-insight/25 hover:border-accent-insight/70"
                  whileTap={{ scale: 0.97 }}
                  transition={springs.snappy}
                  data-testid="btn-ask-gemma"
                >
                  <span aria-hidden className="font-display text-[18px] leading-none">✦</span>
                  {t("menu.askGemma")}
                </motion.button>
              </div>
            </PageContainer>
          </motion.div>
        )}
      </AnimatePresence>

      <GemmaChat
        open={chatOpen}
        build={chatBuild}
        onClose={() => setChatOpen(false)}
      />
    </>
  );
}
