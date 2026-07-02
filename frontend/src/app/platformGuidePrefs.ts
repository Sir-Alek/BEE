const GUIDE_DISMISS_PREFIX = "elia.guide.";
const QUICK_GUIDES_ENABLED_KEY = "elia.guide.quick.enabled";
export const QUICK_GUIDE_PREFS_CHANGED = "elia-quick-guide-prefs-changed";

export type QuickGuidePlatform = "mobile" | "legacy";

export function platformQuickGuideDismissKey(platform: QuickGuidePlatform): string {
  return `${GUIDE_DISMISS_PREFIX}${platform}.dismiss`;
}

export function areQuickGuidesEnabled(): boolean {
  try {
    const raw = localStorage.getItem(QUICK_GUIDES_ENABLED_KEY);
    if (raw === null) return true;
    return raw !== "0";
  } catch {
    return true;
  }
}

export function setQuickGuidesEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(QUICK_GUIDES_ENABLED_KEY, enabled ? "1" : "0");
    notifyQuickGuidePrefsChanged();
  } catch {
    /* ignore */
  }
}

export function isPlatformQuickGuideDismissed(platform: QuickGuidePlatform): boolean {
  try {
    return localStorage.getItem(platformQuickGuideDismissKey(platform)) === "1";
  } catch {
    return false;
  }
}

export function dismissPlatformQuickGuide(platform: QuickGuidePlatform): void {
  try {
    localStorage.setItem(platformQuickGuideDismissKey(platform), "1");
    notifyQuickGuidePrefsChanged();
  } catch {
    /* ignore quota / private mode */
  }
}

export function resetPlatformQuickGuideDismiss(platform: QuickGuidePlatform): void {
  try {
    localStorage.removeItem(platformQuickGuideDismissKey(platform));
    notifyQuickGuidePrefsChanged();
  } catch {
    /* ignore */
  }
}

export function resetAllQuickGuideDismissCards(): void {
  for (const platform of ["mobile", "legacy"] as const) {
    resetPlatformQuickGuideDismiss(platform);
  }
}

export function notifyQuickGuidePrefsChanged(): void {
  try {
    window.dispatchEvent(new Event(QUICK_GUIDE_PREFS_CHANGED));
  } catch {
    /* ignore */
  }
}
