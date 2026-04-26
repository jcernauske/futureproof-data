import { create } from "zustand";
import type { AppLocale } from "@/i18n/locales";
import { DEFAULT_LOCALE, normalizeLocale } from "@/i18n/locales";

interface ProfileState {
  profileName: string | null;
  animalEmoji: string | null;
  animalName: string | null;
  homeState: string | null;
  locale: AppLocale;
  setProfile: (name: string, emoji: string, animal: string) => void;
  setHomeState: (state: string) => void;
  setLocale: (locale: AppLocale) => void;
  clearProfile: () => void;
  hydrateFromSession: (data: {
    profileName: string;
    animalEmoji: string;
    animalName: string;
    homeState: string | null;
    locale?: string;
  }) => void;
}

export const useProfileStore = create<ProfileState>((set) => ({
  profileName: null,
  animalEmoji: null,
  animalName: null,
  homeState: null,
  locale: DEFAULT_LOCALE,
  setProfile: (name, emoji, animal) =>
    set({ profileName: name, animalEmoji: emoji, animalName: animal }),
  setHomeState: (state) => set({ homeState: state || null }),
  setLocale: (locale) => set({ locale: normalizeLocale(locale) }),
  clearProfile: () =>
    set({
      profileName: null,
      animalEmoji: null,
      animalName: null,
      homeState: null,
      locale: DEFAULT_LOCALE,
    }),
  hydrateFromSession: (data) =>
    set({
      profileName: data.profileName,
      animalEmoji: data.animalEmoji,
      animalName: data.animalName,
      homeState: data.homeState,
      locale: normalizeLocale(data.locale),
    }),
}));
