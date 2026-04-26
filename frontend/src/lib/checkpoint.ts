import { saveCheckpoint } from "@/api/session";
import { useProfileStore } from "@/store/profileStore";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { useGauntletStore } from "@/store/gauntletStore";

export function fireCheckpoint(screen: string) {
  const profile = useProfileStore.getState();
  const buildInput = useBuildInputStore.getState();
  const buildStore = useBuildStore.getState();
  const gauntlet = useGauntletStore.getState();

  saveCheckpoint({
    screen,
    profile_data: {
      profileName: profile.profileName,
      animalEmoji: profile.animalEmoji,
      animalName: profile.animalName,
      homeState: profile.homeState,
      locale: profile.locale,
    },
    build_input_data: {
      phase: buildInput.phase,
      school: buildInput.school,
      programs: buildInput.programs,
      major: buildInput.major,
      effort: buildInput.effort,
      loans: buildInput.loans,
      initialResolution: buildInput.initialResolution,
      currentResolution: buildInput.currentResolution,
    },
    build_id: buildStore.build?.build_id ?? null,
    gauntlet_data: {
      phase: gauntlet.phase,
      currentFightIndex: gauntlet.currentFightIndex,
      fightPhase: gauntlet.fightPhase,
      selectedSkillIds: Array.from(gauntlet.selectedSkillIds),
    },
    tiered_careers_data: buildStore.tieredCareers ?? null,
    selected_career_data: buildStore.selectedCareer ?? null,
  }).catch(console.warn);
}
