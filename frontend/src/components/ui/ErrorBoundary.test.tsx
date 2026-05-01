import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

function ThrowOnRender({ message = "kaboom" }: { message?: string }): never {
  throw new Error(message);
}

describe("ErrorBoundary", () => {
  let errorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // React logs caught errors to console.error during render. Silence it
    // so the test output stays readable. The spy also lets us assert the
    // dev-mode log path fires.
    errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    errorSpy.mockRestore();
  });

  it("renders children when no error is thrown", () => {
    render(
      <ErrorBoundary>
        <div data-testid="happy-path">Hello</div>
      </ErrorBoundary>,
    );
    expect(screen.getByTestId("happy-path")).toHaveTextContent("Hello");
    expect(
      screen.queryByTestId("error-boundary-fallback"),
    ).not.toBeInTheDocument();
  });

  it("renders the fallback panel when a child throws during render", () => {
    render(
      <ErrorBoundary>
        <ThrowOnRender />
      </ErrorBoundary>,
    );
    const panel = screen.getByTestId("error-boundary-fallback");
    expect(panel).toBeInTheDocument();
    expect(panel).toHaveAttribute("role", "alert");
    expect(panel).toHaveAttribute("aria-live", "assertive");
    expect(screen.getByText("Something went sideways")).toBeInTheDocument();
  });

  it("refresh button calls window.location.reload", () => {
    const reloadSpy = vi.fn();
    const original = window.location;
    Object.defineProperty(window, "location", {
      configurable: true,
      writable: true,
      value: { ...original, reload: reloadSpy, href: original.href },
    });

    try {
      render(
        <ErrorBoundary>
          <ThrowOnRender />
        </ErrorBoundary>,
      );
      const refresh = screen.getByTestId("error-boundary-refresh");
      refresh.click();
      expect(reloadSpy).toHaveBeenCalledTimes(1);
    } finally {
      Object.defineProperty(window, "location", {
        configurable: true,
        writable: true,
        value: original,
      });
    }
  });

  it("back-to-home button sets window.location.href to /", () => {
    const original = window.location;
    const setHref = vi.fn();
    Object.defineProperty(window, "location", {
      configurable: true,
      writable: true,
      value: {
        ...original,
        reload: () => {},
        get href() {
          return original.href;
        },
        set href(value: string) {
          setHref(value);
        },
      },
    });

    try {
      render(
        <ErrorBoundary>
          <ThrowOnRender />
        </ErrorBoundary>,
      );
      const home = screen.getByTestId("error-boundary-home");
      home.click();
      expect(setHref).toHaveBeenCalledWith("/");
    } finally {
      Object.defineProperty(window, "location", {
        configurable: true,
        writable: true,
        value: original,
      });
    }
  });

  it("shows technical details in DEV mode", () => {
    // vitest defaults import.meta.env.DEV to true; assert the dev surface.
    render(
      <ErrorBoundary>
        <ThrowOnRender message="dev-stack-marker" />
      </ErrorBoundary>,
    );
    expect(screen.getByTestId("error-boundary-details")).toBeInTheDocument();
  });

  it("hides technical details when DEV is false", () => {
    const env = import.meta.env as Record<string, unknown>;
    const original = env.DEV;
    env.DEV = false;
    try {
      render(
        <ErrorBoundary>
          <ThrowOnRender />
        </ErrorBoundary>,
      );
      expect(
        screen.queryByTestId("error-boundary-details"),
      ).not.toBeInTheDocument();
    } finally {
      env.DEV = original;
    }
  });

  it("does not console.error from componentDidCatch in production mode", () => {
    // Production deploys (Railway) must not leak [ErrorBoundary] component
    // stacks to the browser console. The DEV-gate in componentDidCatch is
    // the only thing standing between a render-time exception and a noisy
    // browser console — pin it so a refactor that drops the gate is caught.
    //
    // React itself still logs the caught error (that's React's own behavior
    // and out of scope here), so we filter for the ErrorBoundary's own log
    // line specifically rather than asserting console.error was never hit.
    const env = import.meta.env as Record<string, unknown>;
    const original = env.DEV;
    env.DEV = false;
    try {
      render(
        <ErrorBoundary>
          <ThrowOnRender message="prod-leak-marker" />
        </ErrorBoundary>,
      );
      const ourCalls = errorSpy.mock.calls.filter(
        (args) =>
          typeof args[0] === "string" && args[0].includes("[ErrorBoundary]"),
      );
      expect(ourCalls).toHaveLength(0);
      // Sanity check: the fallback still rendered — DEV=false doesn't
      // break the user-facing recovery path, only the dev console log.
      expect(screen.getByTestId("error-boundary-fallback")).toBeInTheDocument();
    } finally {
      env.DEV = original;
    }
  });

  it("logs from componentDidCatch in DEV mode (sanity check on the gate)", () => {
    // Counter-test to the production-mode test above: confirms the gate is
    // actually doing something (would catch a refactor that hard-coded
    // false or removed the call entirely).
    render(
      <ErrorBoundary>
        <ThrowOnRender message="dev-log-marker" />
      </ErrorBoundary>,
    );
    const ourCalls = errorSpy.mock.calls.filter(
      (args) =>
        typeof args[0] === "string" && args[0].includes("[ErrorBoundary]"),
    );
    expect(ourCalls.length).toBeGreaterThan(0);
  });
});
