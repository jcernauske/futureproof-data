import { create } from "zustand";

interface ProfileState {
  profileName: string | null;
  animalEmoji: string | null;
  animalName: string | null;
  setProfile: (name: string, emoji: string, animal: string) => void;
  clearProfile: () => void;
}

export const useProfileStore = create<ProfileState>((set) => ({
  profileName: null,
  animalEmoji: null,
  animalName: null,
  setProfile: (name, emoji, animal) =>
    set({ profileName: name, animalEmoji: emoji, animalName: animal }),
  clearProfile: () =>
    set({ profileName: null, animalEmoji: null, animalName: null }),
}));
