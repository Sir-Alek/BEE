import { getApiScriptsGuide, getPlatformQuickGuide } from "../api";
import type { QuickGuidePlatform } from "./platformGuidePrefs";

export type GuidePayload = { title: string; content: string };

const platformCache = new Map<QuickGuidePlatform, GuidePayload>();
const platformInflight = new Map<QuickGuidePlatform, Promise<GuidePayload>>();

let scriptsCache: GuidePayload | null = null;
let scriptsInflight: Promise<GuidePayload> | null = null;

export function peekPlatformQuickGuide(platform: QuickGuidePlatform): GuidePayload | null {
  return platformCache.get(platform) ?? null;
}

export async function fetchPlatformQuickGuideCached(platform: QuickGuidePlatform): Promise<GuidePayload> {
  const hit = platformCache.get(platform);
  if (hit) return hit;

  let pending = platformInflight.get(platform);
  if (!pending) {
    pending = getPlatformQuickGuide(platform).then((r) => {
      platformCache.set(platform, r);
      platformInflight.delete(platform);
      return r;
    });
    platformInflight.set(platform, pending);
  }
  return pending;
}

export function prefetchPlatformQuickGuides(platforms: readonly QuickGuidePlatform[]): void {
  for (const platform of platforms) {
    void fetchPlatformQuickGuideCached(platform);
  }
}

export function peekApiScriptsGuide(): GuidePayload | null {
  return scriptsCache;
}

export async function fetchApiScriptsGuideCached(): Promise<GuidePayload> {
  if (scriptsCache) return scriptsCache;
  if (!scriptsInflight) {
    scriptsInflight = getApiScriptsGuide()
      .then((r) => {
        scriptsCache = r;
        scriptsInflight = null;
        return r;
      })
      .catch((e) => {
        scriptsInflight = null;
        throw e;
      });
  }
  return scriptsInflight;
}

export function prefetchApiScriptsGuide(): void {
  void fetchApiScriptsGuideCached();
}

export function prefetchAllBundledGuides(): void {
  prefetchPlatformQuickGuides(["mobile", "legacy", "api_load"]);
  prefetchApiScriptsGuide();
}
