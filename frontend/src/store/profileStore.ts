import { create } from "zustand";

interface ProfileState {
  profileName: string | null;
  animalEmoji: string | null;
  animalName: string | null;
  homeState: string | null;
  setProfile: (name: string, emoji: string, animal: string) => void;
  setHomeState: (state: string) => void;
  clearProfile: () => void;
  hydrateFromSession: (data: {
    profileName: string;
    animalEmoji: string;
    animalName: string;
    homeState: string | null;
  }) => void;
}

export const useProfileStore = create<ProfileState>((set) => ({
  profileName: null,
  animalEmoji: null,
  animalName: null,
  homeState: null,
  setProfile: (name, emoji, animal) =>
    set({ profileName: name, animalEmoji: emoji, animalName: animal }),
  setHomeState: (state) => set({ homeState: state || null }),
  clearProfile: () =>
    set({ profileName: null, animalEmoji: null, animalName: null, homeState: null }),
  hydrateFromSession: (data) =>
    set({
      profileName: data.profileName,
      animalEmoji: data.animalEmoji,
      animalName: data.animalName,
      homeState: data.homeState,
    }),
}));
