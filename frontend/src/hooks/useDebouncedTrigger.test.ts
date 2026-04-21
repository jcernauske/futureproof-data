import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import React from "react";
import { useDebouncedTrigger } from "./useDebouncedTrigger";

afterEach(() => {
  vi.useRealTimers();
});

describe("useDebouncedTrigger", () => {
  it("fires after delayMs of quiet", () => {
    vi.useFakeTimers();
    const callback = vi.fn();
    const { result } = renderHook(() =>
      useDebouncedTrigger(callback, { delayMs: 250 }),
    );

    act(() => {
      result.current("a");
    });
    expect(callback).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(249);
    });
    expect(callback).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(callback).toHaveBeenCalledTimes(1);
    expect(callback).toHaveBeenCalledWith("a");
  });

  it("fires immediately when override key changes", () => {
    vi.useFakeTimers();
    const callback = vi.fn();
    let key = "cip-A";

    const { result, rerender } = renderHook(() =>
      useDebouncedTrigger(callback, {
        delayMs: 250,
        immediateOnKeyChange: key,
      }),
    );

    act(() => {
      result.current();
    });
    expect(callback).not.toHaveBeenCalled();

    key = "cip-B";
    rerender();

    act(() => {
      result.current();
    });
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it("cancels pending fire on unmount", () => {
    vi.useFakeTimers();
    const callback = vi.fn();
    const { result, unmount } = renderHook(() =>
      useDebouncedTrigger(callback, { delayMs: 250 }),
    );

    act(() => {
      result.current();
    });
    unmount();

    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(callback).not.toHaveBeenCalled();
  });

  it("react strict-mode safe — effect double-fire does not produce duplicate invocations", () => {
    vi.useFakeTimers();
    const callback = vi.fn();

    function strictWrapper({ children }: { children: React.ReactNode }) {
      return React.createElement(React.StrictMode, null, children);
    }

    const { result } = renderHook(
      () => useDebouncedTrigger(callback, { delayMs: 250 }),
      { wrapper: strictWrapper },
    );

    act(() => {
      result.current();
    });

    act(() => {
      vi.advanceTimersByTime(250);
    });
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it("resets debounce timer on rapid calls — only last call fires", () => {
    vi.useFakeTimers();
    const callback = vi.fn();
    const { result } = renderHook(() =>
      useDebouncedTrigger(callback, { delayMs: 250 }),
    );

    act(() => {
      result.current("first");
    });
    act(() => {
      vi.advanceTimersByTime(100);
    });
    act(() => {
      result.current("second");
    });
    act(() => {
      vi.advanceTimersByTime(100);
    });
    act(() => {
      result.current("third");
    });
    act(() => {
      vi.advanceTimersByTime(250);
    });

    expect(callback).toHaveBeenCalledTimes(1);
    expect(callback).toHaveBeenCalledWith("third");
  });

  it("immediate fire cancels any pending debounced call", () => {
    vi.useFakeTimers();
    const callback = vi.fn();
    let key = "cip-A";

    const { result, rerender } = renderHook(() =>
      useDebouncedTrigger(callback, {
        delayMs: 250,
        immediateOnKeyChange: key,
      }),
    );

    act(() => {
      result.current("debounced-arg");
    });
    expect(callback).not.toHaveBeenCalled();

    key = "cip-B";
    rerender();

    act(() => {
      result.current("immediate-arg");
    });
    expect(callback).toHaveBeenCalledTimes(1);
    expect(callback).toHaveBeenCalledWith("immediate-arg");

    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(callback).toHaveBeenCalledTimes(1);
  });
});
