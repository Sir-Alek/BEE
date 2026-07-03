import type { ModulesStatus } from "../types";

/** Arranque inicial pendiente: mantener splash hasta licencia + módulos resueltos. */
export function isInitialBootPending(
  licenseLoading: boolean,
  canRunJobs: boolean,
  modulesLoading: boolean,
  modules: ModulesStatus | null,
): boolean {
  if (licenseLoading) return true;
  if (!canRunJobs) return false;
  if (modulesLoading) return true;
  if (modules === null) return true;
  return false;
}

export function areModulesReadyForBoot(
  canRunJobs: boolean,
  modulesLoading: boolean,
  modules: ModulesStatus | null,
): boolean {
  if (!canRunJobs) return true;
  return !modulesLoading && modules !== null;
}
