/**
 * Variante B: resolución de fase UI (verifying → license_ready → features_ready / offline).
 * El caché local nunca eleva privilegios por encima del tier confirmado por licencia.
 */
import type { LicenseState } from "./licenseUtils";
import type { FeatureFlags, ModulesStatus } from "../types";
import {
  TIER_ARCHITECT,
  TIER_BETA,
  TIER_TESTER,
  featureFromModules,
  hasFeature,
  normalizeTier,
  type FeatureFlags as EntFeatureFlags,
} from "./entitlements";
import { cacheTierMismatch } from "./modulesCache";

export type EntitlementPhase =
  | "verifying"
  | "no_license"
  | "license_ready"
  | "features_ready"
  | "offline_cache";

export type EntitlementBanner = "verifying" | "modules_loading" | "offline" | "none";

export type FeatureAccess = "granted" | "pending" | "denied";

/** Features que requieren confirmación de /api/modules/status (salvo tier Beta). */
export const ADVANCED_MODULE_FEATURES: (keyof FeatureFlags)[] = [
  "api_locust",
  "legacy_recording",
  "team_memory_crypto",
  "publishers_enterprise",
];

export type EntitlementInput = {
  licenseLoading: boolean;
  license: LicenseState | null;
  modulesLoading: boolean;
  modules: ModulesStatus | null;
  modulesFetchFailed: boolean;
  cachedModules: ModulesStatus | null;
};

export type EntitlementResolution = {
  phase: EntitlementPhase;
  features: FeatureFlags;
  banner: EntitlementBanner;
  showTierUpsell: boolean;
  shouldInvalidateCache: boolean;
};

const ALL_FEATURE_KEYS: (keyof FeatureFlags)[] = [
  "web_recording",
  "api_http_single",
  "doc_to_bdd",
  "api_postman_suites",
  "api_locust",
  "mobile_recording",
  "legacy_recording",
  "publishers_standard",
  "publishers_enterprise",
  "team_memory_crypto",
];

export function emptyFeatureFlags(): FeatureFlags {
  const out: FeatureFlags = {};
  for (const k of ALL_FEATURE_KEYS) out[k] = false;
  return out;
}

/** Espejo de core/entitlements.get_tier_flags para LicenseReady sin esperar módulos. */
export function tierFeatureFlags(tier: string | null | undefined): FeatureFlags {
  const norm = normalizeTier(tier ?? "");
  if (!norm) return emptyFeatureFlags();
  if (norm === TIER_BETA || norm === TIER_ARCHITECT) {
    const out = emptyFeatureFlags();
    for (const k of ALL_FEATURE_KEYS) out[k] = true;
    return out;
  }
  if (norm === TIER_TESTER) {
    return {
      ...emptyFeatureFlags(),
      web_recording: true,
      api_http_single: true,
      doc_to_bdd: true,
      api_postman_suites: true,
      mobile_recording: true,
      publishers_standard: true,
    };
  }
  return emptyFeatureFlags();
}

export function isBetaLicense(license: LicenseState | null): boolean {
  if (!license) return false;
  if (license.is_beta) return true;
  return normalizeTier(license.tier ?? "") === TIER_BETA;
}

export function licenseTierFeatures(license: LicenseState): FeatureFlags {
  if (license.features && typeof license.features === "object") {
    return featureFromModules({ ...license.features } as EntFeatureFlags);
  }
  return tierFeatureFlags(license.tier);
}

export function modulesToFeatureFlags(modules: ModulesStatus): FeatureFlags {
  return featureFromModules({
    web_recording: modules.features?.web_recording ?? true,
    api_http_single: modules.api_http_single ?? modules.api_testing ?? modules.features?.api_http_single,
    doc_to_bdd: modules.doc_to_bdd ?? modules.features?.doc_to_bdd,
    api_postman_suites: modules.api_postman_suites ?? modules.features?.api_postman_suites,
    api_locust: modules.api_locust ?? modules.features?.api_locust,
    mobile_recording: modules.mobile_recording ?? modules.features?.mobile_recording,
    legacy_recording: modules.legacy_recording ?? modules.features?.legacy_recording,
    publishers_standard: modules.publishers_standard ?? modules.features?.publishers_standard,
    publishers_enterprise: modules.publishers_enterprise ?? modules.features?.publishers_enterprise,
    team_memory_crypto: modules.team_memory_crypto ?? modules.features?.team_memory_crypto,
  });
}

/** Intersección: la licencia es techo máximo; el caché/servidor no eleva tier. */
export function intersectFeatureFlags(cap: FeatureFlags, other: FeatureFlags): FeatureFlags {
  const out: FeatureFlags = {};
  for (const k of ALL_FEATURE_KEYS) {
    out[k] = Boolean(cap[k]) && Boolean(other[k]);
  }
  return out;
}

export function resolveEntitlements(input: EntitlementInput): EntitlementResolution {
  const { licenseLoading, license, modulesLoading, modules, modulesFetchFailed, cachedModules } = input;

  if (licenseLoading) {
    return {
      phase: "verifying",
      features: emptyFeatureFlags(),
      banner: "verifying",
      showTierUpsell: false,
      shouldInvalidateCache: false,
    };
  }

  if (!license || !license.can_run_jobs) {
    return {
      phase: "no_license",
      features: emptyFeatureFlags(),
      banner: "none",
      showTierUpsell: false,
      shouldInvalidateCache: false,
    };
  }

  const shouldInvalidateCache = cacheTierMismatch(license.tier, cachedModules);
  const cap = licenseTierFeatures(license);

  if (modulesFetchFailed) {
    const cacheFlags = cachedModules && !shouldInvalidateCache ? modulesToFeatureFlags(cachedModules) : cap;
    return {
      phase: "offline_cache",
      features: intersectFeatureFlags(cap, cacheFlags),
      banner: "offline",
      showTierUpsell: true,
      shouldInvalidateCache,
    };
  }

  if (modulesLoading || !modules) {
    return {
      phase: "license_ready",
      features: cap,
      banner: "modules_loading",
      showTierUpsell: true,
      shouldInvalidateCache,
    };
  }

  return {
    phase: "features_ready",
    features: intersectFeatureFlags(cap, modulesToFeatureFlags(modules)),
    banner: "none",
    showTierUpsell: true,
    shouldInvalidateCache,
  };
}

export function getFeatureAccess(
  phase: EntitlementPhase,
  feature: keyof FeatureFlags,
  features: FeatureFlags,
  license: LicenseState | null,
): FeatureAccess {
  if (phase === "verifying") return "pending";
  if (phase === "no_license") return "denied";

  const grantedByTier = hasFeature(features, feature);
  if (!grantedByTier) return "denied";

  if (
    phase === "license_ready" &&
    !isBetaLicense(license) &&
    ADVANCED_MODULE_FEATURES.includes(feature)
  ) {
    return "pending";
  }

  return "granted";
}

export function shouldShowTierUpsell(
  phase: EntitlementPhase,
  access: FeatureAccess,
  showTierUpsell: boolean,
): boolean {
  if (!showTierUpsell) return false;
  if (phase === "verifying" || phase === "no_license") return false;
  return access === "denied";
}

export function canExecuteHomeActions(phase: EntitlementPhase, canRunJobs: boolean): boolean {
  return canRunJobs && phase !== "verifying" && phase !== "no_license";
}

export function isUiVerifying(phase: EntitlementPhase): boolean {
  return phase === "verifying";
}

export function isNoLicense(phase: EntitlementPhase): boolean {
  return phase === "no_license";
}
