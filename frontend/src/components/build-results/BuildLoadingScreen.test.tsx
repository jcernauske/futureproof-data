import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BuildLoadingScreen } from "./BuildLoadingScreen";

vi.mock("@/i18n/useT", () => ({
  useT: () => (key: string) => key,
}));

const BASE_PROPS = {
  animalEmoji: "\u{1F43B}",
  profileName: "Bear_Explorer_42",
  schoolName: "Indiana State University",
  majorTitle: "Finance",
  buildingStage: 0,
  buildingTotal: 0,
  error: null,
  onRetry: vi.fn(),
  onGoBack: vi.fn(),
};

describe("BuildLoadingScreen", () => {
  it("renders the animal emoji", () => {
    render(<BuildLoadingScreen {...BASE_PROPS} />);
    expect(screen.getByText("\u{1F43B}")).toBeInTheDocument();
  });

  it("renders profile name and school", () => {
    render(<BuildLoadingScreen {...BASE_PROPS} />);
    expect(screen.getByText("Bear_Explorer_42")).toBeInTheDocument();
    expect(screen.getByText("Finance at Indiana State University")).toBeInTheDocument();
  });

  it("renders stat name and verb-prefixed loading text at current progress", () => {
    const { container } = render(
      <BuildLoadingScreen
        {...BASE_PROPS}
        buildingTotal={10}
        buildingStage={3}
      />,
    );
    expect(container.textContent).toContain("forge.stat.roi.name");
    expect(container.textContent).toContain("forge.stat.roi.loading");
  });

  it("shows error overlay with retry and go-back buttons", () => {
    const onRetry = vi.fn();
    const onGoBack = vi.fn();
    render(
      <BuildLoadingScreen
        {...BASE_PROPS}
        error="Build failed"
        onRetry={onRetry}
        onGoBack={onGoBack}
      />,
    );
    expect(screen.getByText("build.error")).toBeInTheDocument();

    fireEvent.click(screen.getByText("build.tryAgain"));
    expect(onRetry).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByText("build.goBack"));
    expect(onGoBack).toHaveBeenCalledOnce();
  });
});
