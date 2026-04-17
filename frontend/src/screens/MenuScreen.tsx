import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";
import { Button } from "@/components/ui/Button";
import { useProfileStore } from "@/store/profileStore";
import { useBuildStore } from "@/store/buildStore";
import { useBuildInputStore } from "@/store/buildInputStore";
import { listBuilds, type BuildSummary } from "@/api/menu";
import { getBuild } from "@/api/build";
import { BuildCard } from "@/components/menu/BuildCard";
import { CompareView } from "@/components/menu/CompareView";
import { GemmaChat } from "@/components/menu/GemmaChat";

type Mode = "list" | "select" | "compare";

export function MenuScreen() {
  const navigate = useNavigate();
  const profileName = useProfileStore((s) => s.profileName);
  const animalEmoji = useProfileStore((s) => s.animalEmoji);
  const setBuild = useBuildStore((s) => s.setBuild);
  const resetInputs = useBuildInputStore((s) => s.resetInputs);

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
  // and land at /reveal with the wrong build's payload.
  const navigatingRef = useRef<string | null>(null);

  // Profile guard — bounce to landing if no profile.
  useEffect(() => {
    if (!profileName) navigate("/", { replace: true });
  }, [profileName, navigate]);

  useEffect(() => {
    if (!profileName) return;
    let cancelled = false;
    setLoadingList(true);
    setListError(null);
    listBuilds(profileName)
      .then((res) => {
        if (cancelled) return;
        setBuilds(res);
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
          if (current.length >= 3) return current;
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
        navigate("/reveal");
      } catch (e) {
        setListError(e instanceof Error ? e.message : "Couldn't load build.");
        setNavigatingId(null);
        navigatingRef.current = null;
      }
    },
    [mode, navigate, setBuild],
  );

  const handleNewBuild = useCallback(() => {
    resetInputs();
    navigate("/school");
  }, [navigate, resetInputs]);

  const handleEnterSelect = useCallback(() => {
    if (builds.length < 2) return;
    setMode("select");
    setSelectedIds([]);
  }, [builds.length]);

  const handleCancelSelect = useCallback(() => {
    setMode("list");
    setSelectedIds([]);
  }, []);

  const handleCompareGo = useCallback(() => {
    if (selectedIds.length < 2 || selectedIds.length > 3) return;
    setCompareIds(selectedIds);
    setMode("compare");
  }, [selectedIds]);

  const handleBackFromCompare = useCallback(() => {
    setMode("list");
    setSelectedIds([]);
    setCompareIds([]);
  }, []);

  const handleAskGemma = useCallback(() => {
    if (!builds.length) return;
    const first = builds[0]!;
    setChatBuild(first);
    setChatOpen(true);
  }, [builds]);

  if (!profileName) return null;

  return (
    <main
      data-testid="screen-menu"
      className="min-h-screen w-full pt-24 pb-16 px-6 tablet:px-8 mx-auto max-w-[800px]"
    >
      <AnimatePresence mode="wait">
        {mode === "compare" && compareIds.length > 0 ? (
          <motion.div
            key="compare"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
            <CompareView buildIds={compareIds} onBack={handleBackFromCompare} />
          </motion.div>
        ) : (
          <motion.div
            key="list"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={springs.smooth}
            className="flex flex-col gap-8"
          >
            <header className="flex flex-col gap-2">
              <p className="font-data text-micro uppercase tracking-[2px] text-text-muted">
                Your builds
              </p>
              <h1 className="font-display text-display text-text-primary">
                Welcome back, {profileName} {animalEmoji ?? ""}
              </h1>
              <p className="font-body text-body text-text-secondary">
                Compare your futures, ask Gemma, or start a new build.
              </p>
            </header>

            <section
              data-testid="region-saved-builds"
              aria-label="Your saved builds"
              className="flex flex-col gap-3"
            >
              {loadingList && (
                <p className="font-body text-body text-text-muted">
                  Loading your builds…
                </p>
              )}
              {!loadingList && listError && (
                <p className="font-body text-body text-accent-alert">{listError}</p>
              )}
              {!loadingList && !listError && builds.length === 0 && (
                <div className="flex flex-col items-center gap-4 py-12 text-center">
                  <p className="font-display text-heading text-text-primary">
                    No builds yet.
                  </p>
                  <p className="font-body text-body text-text-secondary">
                    Start your first one to see it here.
                  </p>
                  <Button variant="primary" onClick={handleNewBuild} data-testid="btn-new-build">
                    Start your first build
                  </Button>
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
                        emoji={animalEmoji ?? "✦"}
                        isMostRecent={build.build_id === mostRecentId}
                        selectMode={mode === "select"}
                        selected={selectedIds.includes(build.build_id)}
                        onTap={() => handleViewBuild(build)}
                      />
                      {navigatingId === build.build_id && (
                        <p className="px-5 mt-1 font-body text-micro text-text-muted">
                          Loading build…
                        </p>
                      )}
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </section>

            {builds.length > 0 && (
              <section
                aria-label="Build actions"
                className="flex flex-col tablet:flex-row gap-3 tablet:items-center tablet:justify-between"
              >
                <Button
                  variant="primary"
                  onClick={handleNewBuild}
                  data-testid="btn-new-build"
                >
                  New Build ✦
                </Button>
                <div className="flex flex-wrap gap-3">
                  {mode === "select" ? (
                    <>
                      <Button
                        variant="primary"
                        onClick={handleCompareGo}
                        disabled={selectedIds.length < 2 || selectedIds.length > 3}
                        data-testid="btn-compare"
                      >
                        Compare {selectedIds.length}/3
                      </Button>
                      <Button variant="ghost" onClick={handleCancelSelect}>
                        Cancel
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button
                        variant="secondary"
                        onClick={handleEnterSelect}
                        disabled={builds.length < 2}
                        data-testid="btn-enter-compare"
                      >
                        Compare Builds
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={handleAskGemma}
                        data-testid="btn-ask-gemma"
                      >
                        Ask Gemma
                      </Button>
                    </>
                  )}
                </div>
              </section>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <GemmaChat
        open={chatOpen}
        build={chatBuild}
        onClose={() => setChatOpen(false)}
      />
    </main>
  );
}
