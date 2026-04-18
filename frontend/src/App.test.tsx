import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, beforeEach } from "vitest";
import { AppRoutes } from "./App";
import { useProfileStore } from "@/store/profileStore";

describe("App routes", () => {
  beforeEach(() => {
    useProfileStore.setState({
      profileName: null,
      animalEmoji: null,
      animalName: null,
    });
  });

  it("marketing Landing is rendered at /", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(document.getElementById("landing-root")).toBeInTheDocument();
    expect(document.getElementById("landing-hero-cta")).toBeInTheDocument();
  });

  it("in-app LandingScreen is rendered at /app", () => {
    render(
      <MemoryRouter initialEntries={["/app"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(
      screen.getByText(/A college degree isn't a destination/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Start building your future" }),
    ).toBeInTheDocument();
  });
});

describe("AppHeader visibility by route", () => {
  beforeEach(() => {
    useProfileStore.setState({
      profileName: null,
      animalEmoji: null,
      animalName: null,
    });
  });

  it("does not render on marketing landing /", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    // AppHeader renders a <header> with wordmark + buttons; on / it should return null.
    expect(document.querySelector("header")).not.toBeInTheDocument();
  });

  it("renders Start ✦ affordance on in-app /app", () => {
    render(
      <MemoryRouter initialEntries={["/app"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    // The header wordmark + Start ✦ button both render only on /app.
    expect(document.querySelector("header")).toBeInTheDocument();
    expect(screen.getByText("Start ✦")).toBeInTheDocument();
  });
});

describe("Profile-guard redirects land on /app, not /", () => {
  beforeEach(() => {
    useProfileStore.setState({
      profileName: null,
      animalEmoji: null,
      animalName: null,
    });
  });

  it("MenuScreen redirects to /app when no profile is set", () => {
    render(
      <MemoryRouter initialEntries={["/menu"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    // The redirect targets /app, which renders in-app LandingScreen copy.
    expect(
      screen.getByText(/A college degree isn't a destination/),
    ).toBeInTheDocument();
  });

  it("ProfileScreen redirects to /app when no profile is set", () => {
    render(
      <MemoryRouter initialEntries={["/profile"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(
      screen.getByText(/A college degree isn't a destination/),
    ).toBeInTheDocument();
  });

  it("SchoolMajorScreen redirects to /app when no profile is set", () => {
    render(
      <MemoryRouter initialEntries={["/school"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(
      screen.getByText(/A college degree isn't a destination/),
    ).toBeInTheDocument();
  });
});
