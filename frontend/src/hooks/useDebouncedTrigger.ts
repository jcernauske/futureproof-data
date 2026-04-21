import { useCallback, useEffect, useRef } from "react";

export interface UseDebouncedTriggerOptions<TKey> {
  delayMs: number;
  immediateOnKeyChange?: TKey;
}

export function useDebouncedTrigger<TArgs extends readonly unknown[], TKey = void>(
  callback: (...args: TArgs) => void,
  options: UseDebouncedTriggerOptions<TKey>,
): (...args: TArgs) => void {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevKeyRef = useRef(options.immediateOnKeyChange);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return useCallback(
    (...args: TArgs) => {
      if (timerRef.current) clearTimeout(timerRef.current);

      const keyChanged =
        prevKeyRef.current !== undefined &&
        options.immediateOnKeyChange !== undefined &&
        prevKeyRef.current !== options.immediateOnKeyChange;
      prevKeyRef.current = options.immediateOnKeyChange;

      if (keyChanged) {
        callbackRef.current(...args);
        return;
      }

      timerRef.current = setTimeout(() => {
        callbackRef.current(...args);
      }, options.delayMs);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [options.delayMs, options.immediateOnKeyChange],
  );
}
