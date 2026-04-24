import { useEffect, useState } from "react";
import { getSession } from "@/api/session";
import { useProfileStore } from "@/store/profileStore";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { useGauntletStore } from "@/store/gauntletStore";
import type { SessionResponse } from "@/types/session";

export function useSessionResume(): {
  resumeScreen: string | null;
  isLoading: boolean;
  session: SessionResponse | null;
} {
  const [resumeScreen, setResumeScreen] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [session, setSession] = useState<SessionResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    getSession()
      .then((resp) => {
        if (cancelled || !resp) {
          setIsLoading(false);
          return;
        }

        setSession(resp);

        if (resp.profile_data) {
          useProfileStore.getState().hydrateFromSession(resp.profile_data);
        }

        if (resp.build_input_data) {
          useBuildInputStore.getState().hydrateFromSession(resp.build_input_data);
        }

        if (resp.build || resp.tiered_careers_data || resp.selected_career_data) {
          useBuildStore.getState().hydrateFromSession({
            build: resp.build ?? undefined,
            tieredCareers: resp.tiered_careers_data ?? undefined,
            selectedCareer: resp.selected_career_data ?? undefined,
          });
        }

        if (resp.gauntlet_data) {
          useGauntletStore.getState().hydrateFromSession(resp.gauntlet_data);
        }

        setResumeScreen(resp.last_screen);
        setIsLoading(false);
      })
      .catch(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return { resumeScreen, isLoading, session };
}
