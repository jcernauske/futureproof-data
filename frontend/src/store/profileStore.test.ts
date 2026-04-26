import { describe, it, expect, beforeEach } from "vitest";
import { useProfileStore } from "./profileStore";

/**
 * profileStore locale tests
 *
 * Covers:
 *   1. Default locale is "en"
 *   2. setLocale("es") updates state
 *   3. clearProfile resets locale to "en"
 *   4. hydrateFromSession with locale restores it
 *   5. hydrateFromSession without locale defaults to "en"
 *   6. normalizeLocale rejects garbage values
 */

beforeEach(() => {
  useProfileStore.setState({
    profileName: null,
    animalEmoji: null,
    animalName: null,
    homeState: null,
    locale: "en",
  });
});

describe("profileStore locale", () => {
  it("defaults to 'en'", () => {
    const state = useProfileStore.getState();
    expect(state.locale).toBe("en");
  });

  it("setLocale('es') updates state to 'es'", () => {
    useProfileStore.getState().setLocale("es");
    expect(useProfileStore.getState().locale).toBe("es");
  });

  it("setLocale('en') keeps state as 'en'", () => {
    useProfileStore.getState().setLocale("es");
    useProfileStore.getState().setLocale("en");
    expect(useProfileStore.getState().locale).toBe("en");
  });

  it("clearProfile resets locale to 'en'", () => {
    useProfileStore.getState().setLocale("es");
    expect(useProfileStore.getState().locale).toBe("es");

    useProfileStore.getState().clearProfile();
    expect(useProfileStore.getState().locale).toBe("en");
  });

  it("clearProfile also clears other profile fields", () => {
    useProfileStore.getState().setProfile("bear", "🐻", "bear");
    useProfileStore.getState().setLocale("es");
    useProfileStore.getState().setHomeState("IN");

    useProfileStore.getState().clearProfile();

    const state = useProfileStore.getState();
    expect(state.profileName).toBeNull();
    expect(state.animalEmoji).toBeNull();
    expect(state.homeState).toBeNull();
    expect(state.locale).toBe("en");
  });

  it("hydrateFromSession with locale='es' restores it", () => {
    useProfileStore.getState().hydrateFromSession({
      profileName: "dancing happy bear",
      animalEmoji: "🐻",
      animalName: "bear",
      homeState: "IN",
      locale: "es",
    });

    const state = useProfileStore.getState();
    expect(state.locale).toBe("es");
    expect(state.profileName).toBe("dancing happy bear");
  });

  it("hydrateFromSession without locale defaults to 'en'", () => {
    // Set locale to "es" first so we can verify hydration resets it
    useProfileStore.getState().setLocale("es");

    useProfileStore.getState().hydrateFromSession({
      profileName: "sneaky fox",
      animalEmoji: "🦊",
      animalName: "fox",
      homeState: null,
      // locale is intentionally omitted
    });

    expect(useProfileStore.getState().locale).toBe("en");
  });

  it("hydrateFromSession with invalid locale normalizes to 'en'", () => {
    useProfileStore.getState().hydrateFromSession({
      profileName: "test",
      animalEmoji: "🐻",
      animalName: "bear",
      homeState: null,
      locale: "fr",
    });

    expect(useProfileStore.getState().locale).toBe("en");
  });

  it("hydrateFromSession with undefined locale normalizes to 'en'", () => {
    useProfileStore.getState().hydrateFromSession({
      profileName: "test",
      animalEmoji: "🐻",
      animalName: "bear",
      homeState: null,
      locale: undefined,
    });

    expect(useProfileStore.getState().locale).toBe("en");
  });
});
