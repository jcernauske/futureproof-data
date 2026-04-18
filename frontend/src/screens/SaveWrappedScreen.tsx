import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import {
  getWrapped,
  renderWrapped,
  type WrappedFrameInfo,
} from "@/api/wrapped";
import { SaveConfirmation } from "@/components/wrapped/SaveConfirmation";
import { WrappedViewer } from "@/components/wrapped/WrappedViewer";
import { Button } from "@/components/ui/Button";
import { PageContainer } from "@/components/ui/PageContainer";

type Phase = "save" | "rendering" | "viewer" | "error";

const MIN_SAVE_DISPLAY_MS = 1500;

export function SaveWrappedScreen() {
  const navigate = useNavigate();
  const build = useBuildStore((s) => s.build);
  const profileName = useProfileStore((s) => s.profileName);
  const animalEmoji = useProfileStore((s) => s.animalEmoji);

  const [phase, setPhase] = useState<Phase>("save");
  const [frames, setFrames] = useState<WrappedFrameInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [retryCounter, setRetryCounter] = useState(0);

  // Navigation guard — must have a build
  useEffect(() => {
    if (!build) {
      navigate("/reveal", { replace: true });
    }
  }, [build, navigate]);

  // Orchestrate: save confirmation (min 1.5s) → render → load frames
  useEffect(() => {
    if (!build) return;
    let cancelled = false;

    const start = Date.now();
    (async () => {
      try {
        // Kick off render immediately — it runs in parallel with the
        // save confirmation delay. Playwright takes 6–18s so overlap
        // the wait with the animation the user is already watching.
        const renderPromise = renderWrapped(build.build_id);

        // Wait for the minimum save-confirmation dwell so the user
        // registers the "saved" moment before the viewer replaces it.
        const elapsed = Date.now() - start;
        const remaining = Math.max(0, MIN_SAVE_DISPLAY_MS - elapsed);
        await new Promise((r) => setTimeout(r, remaining));
        if (cancelled) return;

        setPhase("rendering");

        await renderPromise;
        if (cancelled) return;

        const wrapped = await getWrapped(build.build_id);
        if (cancelled) return;

        setFrames(wrapped.frames);
        setPhase("viewer");
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to render wrapped");
        setPhase("error");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [build, retryCounter]);

  const handleDownloadFrame = useCallback(
    (index: number) => {
      const frame = frames.find((f) => f.index === index);
      if (!frame || !build) return;
      const a = document.createElement("a");
      a.href = frame.url;
      a.download = `futureproof-${build.build_id}-frame-${index + 1}.png`;
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    },
    [frames, build],
  );

  const handleDownloadAll = useCallback(() => {
    if (!build) return;
    // Stagger triggers so browsers don't coalesce/ignore them.
    frames.forEach((frame, i) => {
      setTimeout(() => {
        const a = document.createElement("a");
        a.href = frame.url;
        a.download = `futureproof-${build.build_id}-frame-${frame.index + 1}.png`;
        a.rel = "noopener";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }, i * 180);
    });
  }, [frames, build]);

  const handleDone = useCallback(() => {
    navigate("/branches");
  }, [navigate]);

  if (!build) return null;

  return (
    <PageContainer variant="bleed">
    <AnimatePresence mode="wait">
      {phase === "save" && (
        <motion.div
          key="save"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
        >
          <SaveConfirmation
            profileName={profileName ?? ""}
            profileEmoji={animalEmoji ?? "✦"}
            schoolName={build.school_name}
            careerTitle={build.career.occupation_title}
            wins={build.gauntlet.wins}
            draws={build.gauntlet.draws}
            losses={build.gauntlet.losses}
          />
        </motion.div>
      )}

      {phase === "rendering" && (
        <motion.div
          key="rendering"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="min-h-screen w-full flex items-center justify-center"
        >
          <div className="flex flex-col items-center gap-6 text-center px-8">
            <motion.div
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
              className="w-24 h-24 rounded-full"
              style={{
                background:
                  "radial-gradient(circle, rgba(125,212,163,0.35) 0%, transparent 70%)",
              }}
            />
            <p className="font-display text-heading text-text-primary">
              Developing your wrapped
            </p>
            <p className="text-body text-text-secondary max-w-xs">
              Printing six frames of your build. This takes a few seconds.
            </p>
          </div>
        </motion.div>
      )}

      {phase === "viewer" && frames.length > 0 && (
        <motion.div
          key="viewer"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
        >
          <WrappedViewer
            frames={frames}
            onDone={handleDone}
            onDownloadFrame={handleDownloadFrame}
            onDownloadAll={handleDownloadAll}
          />
        </motion.div>
      )}

      {phase === "error" && (
        <motion.div
          key="error"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="min-h-screen w-full flex items-center justify-center px-8"
        >
          <div className="flex flex-col items-center gap-6 text-center max-w-md">
            <p className="font-display text-heading text-accent-alert">
              Your wrapped didn't develop.
            </p>
            <p className="text-body text-text-secondary">
              {error || "Something went wrong while rendering your frames."}
            </p>
            <div className="flex gap-3">
              <Button
                variant="primary"
                onClick={() => {
                  setError(null);
                  setPhase("save");
                  setRetryCounter((c) => c + 1);
                }}
              >
                Try again
              </Button>
              <Button variant="secondary" onClick={handleDone}>
                Skip to menu
              </Button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
    </PageContainer>
  );
}
