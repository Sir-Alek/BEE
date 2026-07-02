import React from "react";

import { FOLDER_HINT_DISMISS_MS } from "../app/folderOpenHint";

/** Muestra un aviso breve y lo oculta automáticamente tras `delayMs`. */
export function useAutoDismissHint(delayMs = FOLDER_HINT_DISMISS_MS): [string | null, (hint: string | null) => void] {
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
