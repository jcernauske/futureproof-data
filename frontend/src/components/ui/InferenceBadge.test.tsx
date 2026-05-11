import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("@/api/health", () => ({
  fetchHealth: vi.fn().mockResolvedValue({
    status: "ok",
    project: "futureproof",
    version: "0.1.0",
    inference_backend: "ollama",
    inference_model: "gemma4:e4b",
    model_reachable: true,
  }),
}));

import { InferenceBadge, extractParameterSize } from "./InferenceBadge";
import { useInferenceStore } from "@/store/inferenceStore";

function resetStore() {
  useInferenceStore.setState({
    backend: "unknown",
    model: null,
    modelReachable: true,
    loading: false,
    error: null,
  });
}

describe("extractParameterSize", () => {
  it("pulls 4B from the Ollama default tag gemma4:e4b", () => {
    expect(extractParameterSize("gemma4:e4b")).toBe("4B");
  });

  it("pulls 26B (the total, not the active 4B) from the OpenRouter MoE slug", () => {
    expect(extractParameterSize("google/gemma-4-26b-a4b-it")).toBe("26B");
  });

  it("handles plain Gemma 4 27B-style slugs", () => {
    expect(extractParameterSize("google/gemma-4-27b-it")).toBe("27B");
  });

  it("handles non-Gemma slugs", () => {
    expect(extractParameterSize("mistral-7b-instruct")).toBe("7B");
  });

  it("returns null when no parameter size is present", () => {
    expect(extractParameterSize("some-mystery-model")).toBeNull();
    expect(extractParameterSize("")).toBeNull();
    expect(extractParameterSize(null)).toBeNull();
    expect(extractParameterSize(undefined)).toBeNull();
  });
});

describe("InferenceBadge rendering", () => {
  beforeEach(() => {
    resetStore();
  });

  it("renders nothing while backend is still unknown", () => {
    const { container } = render(<InferenceBadge />);
    // The first paint happens before refresh() resolves; nothing to show yet.
    expect(container.firstChild).toBeNull();
  });

  it("renders Ollama label + size when store says ollama + gemma4:e4b", () => {
    useInferenceStore.setState({
      backend: "ollama",
      model: "gemma4:e4b",
      modelReachable: true,
      loading: false,
      error: null,
    });
    render(<InferenceBadge />);
    const badge = screen.getByTestId("inference-badge");
    expect(badge).toHaveAttribute("data-backend", "ollama");
    expect(badge).toHaveAttribute("data-model-size", "4B");
    expect(badge.textContent).toContain("Ollama");
    expect(badge.textContent).toContain("4B");
  });

  it("renders OpenRouter label + 26B for the cloud Gemma slug", () => {
    useInferenceStore.setState({
      backend: "openrouter",
      model: "google/gemma-4-26b-a4b-it",
      modelReachable: true,
      loading: false,
      error: null,
    });
    render(<InferenceBadge />);
    const badge = screen.getByTestId("inference-badge");
    expect(badge).toHaveAttribute("data-backend", "openrouter");
    expect(badge).toHaveAttribute("data-model-size", "26B");
    expect(badge.textContent).toContain("OpenRouter");
    expect(badge.textContent).toContain("26B");
  });

  it("omits the size segment when the model string has no Nb pattern", () => {
    useInferenceStore.setState({
      backend: "ollama",
      model: "some-mystery-tag",
      modelReachable: true,
      loading: false,
      error: null,
    });
    render(<InferenceBadge />);
    const badge = screen.getByTestId("inference-badge");
    expect(badge).toHaveAttribute("data-model-size", "");
    expect(badge.textContent).toContain("Ollama");
    expect(badge.textContent).not.toMatch(/\d+B/);
  });
});
