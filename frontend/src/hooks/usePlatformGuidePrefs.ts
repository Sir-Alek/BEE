import React from "react";
import {
  areQuickGuidesEnabled,
  QUICK_GUIDE_PREFS_CHANGED,
  type QuickGuidePlatform,
  isPlatformQuickGuideDismissed,
} from "../app/platformGuidePrefs";

/** Suscripción a preferencias de guías rápidas (localStorage + evento interno). */
export function usePlatformGuidePrefs(): {
  guidesEnabled: boolean;
  isCardDismissed: (platform: QuickGuidePlatform) => boolean;
  revision: number;
} {
  const [guidesEnabled, setGuidesEnabled] = React.useState(() => areQuickGuidesEnabled());
  const [revision, setRevision] = React.useState(0);

  React.useEffect(() => {
    const sync = () => {
      setGuidesEnabled(areQuickGuidesEnabled());
      setRevision((n) => n + 1);
    };
    window.addEventListener(QUICK_GUIDE_PREFS_CHANGED, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(QUICK_GUIDE_PREFS_CHANGED, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const isCardDismissed = React.useCallback(
    (platform: QuickGuidePlatform) => isPlatformQuickGuideDismissed(platform),
    [revision],
  );

  return { guidesEnabled, isCardDismissed, revision };
}
