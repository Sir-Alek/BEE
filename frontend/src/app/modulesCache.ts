import type { ModulesStatus } from "../types";
import { normalizeTier } from "./entitlements";

export const MODULES_CACHE_KEY = "elia.modules.cache.v1";

export function readCachedModules(): ModulesStatus | null {
  try {
    const raw = localStorage.getItem(MODULES_CACHE_KEY);
    return raw ? (JSON.parse(raw) as ModulesStatus) : null;
  } catch {
    return null;
  }
}

export function writeCachedModules(m: ModulesStatus): void {
  try {
    localStorage.setItem(MODULES_CACHE_KEY, JSON.stringify(m));
  } catch {
    /* almacenamiento no disponible */
  }
}

export function invalidateModulesCache(): void {
  try {
    localStorage.removeItem(MODULES_CACHE_KEY);
  } catch {
    /* ignore */
  }
}

/** Invalida caché si el tier de licencia ya no coincide (downgrade / cambio de plan). */
export function cacheTierMismatch(licenseTier: string | null | undefined, cached: ModulesStatus | null): boolean {
  if (!cached?.tier) return false;
  const lt = normalizeTier(licenseTier ?? "");
  const ct = normalizeTier(cached.tier ?? "");
  if (!lt || !ct) return false;
  return lt !== ct;
}
