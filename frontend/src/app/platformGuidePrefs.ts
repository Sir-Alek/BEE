const GUIDE_DISMISS_PREFIX = "elia.guide.";

export type QuickGuidePlatform = "mobile" | "legacy";

export function platformQuickGuideDismissKey(platform: QuickGuidePlatform): string {
  return `${GUIDE_DISMISS_PREFIX}${platform}.dismiss`;
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
  } catch {
    /* ignore quota / private mode */
  }
}
