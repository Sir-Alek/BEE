import React from "react";

/** Muestra un aviso breve y lo oculta automáticamente tras `delayMs`. */
export function useAutoDismissHint(delayMs = 6000): [string | null, (hint: string | null) => void] {
  const [hint, setHintState] = React.useState<string | null>(null);
  const timerRef = React.useRef<number | null>(null);

  const setHint = React.useCallback(
    (value: string | null) => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      setHintState(value);
      if (value) {
        timerRef.current = window.setTimeout(() => {
          setHintState(null);
          timerRef.current = null;
        }, delayMs);
      }
    },
    [delayMs],
  );

  React.useEffect(
    () => () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
      }
    },
    [],
  );

  return [hint, setHint];
}
