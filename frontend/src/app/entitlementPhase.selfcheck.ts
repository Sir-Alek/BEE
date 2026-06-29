/**
 * Autocheck de resolveEntitlements / getFeatureAccess (Variante B).
 * Ejecutar: npx --yes tsx src/app/entitlementPhase.selfcheck.ts
 */
import type { LicenseState } from "./licenseUtils";
import type { ModulesStatus } from "../types";
import {
  canExecuteHomeActions,
  getFeatureAccess,
  resolveEntitlements,
  shouldShowTierUpsell,
} from "./entitlementPhase";
import { cacheTierMismatch } from "./modulesCache";

function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error(msg);
}

const testerLicense = {
  tier: "tester",
  can_run_jobs: true,
  message: "",
  expires_at: null,
  is_beta: false,
  activated: true,
  machine_fingerprint: "test",
} satisfies LicenseState;

const architectLicense = {
  tier: "architect",
  can_run_jobs: true,
  message: "",
  expires_at: null,
  is_beta: false,
  activated: true,
  machine_fingerprint: "test",
} satisfies LicenseState;

const betaLicense = {
  tier: "beta",
  can_run_jobs: true,
  message: "",
  expires_at: null,
  is_beta: true,
  activated: true,
  machine_fingerprint: "test",
} satisfies LicenseState;

const architectModules = {
  tier: "architect",
  api_http_single: true,
  api_locust: true,
  legacy_recording: true,
  team_memory_crypto: true,
  mobile_recording: true,
  doc_to_bdd: true,
  api_testing: true,
} satisfies ModulesStatus;

// Frame 0: verifying — sin upsell
const verifying = resolveEntitlements({
  licenseLoading: true,
  license: null,
  modulesLoading: false,
  modules: null,
  modulesFetchFailed: false,
  cachedModules: null,
});
assert(verifying.phase === "verifying", "verifying phase");
assert(!verifying.showTierUpsell, "no upsell while verifying");
assert(
  !shouldShowTierUpsell("verifying", "denied", true),
  "shouldShowTierUpsell false on verifying",
);

// Sin licencia
const noLic = resolveEntitlements({
  licenseLoading: false,
  license: { ...testerLicense, can_run_jobs: false },
  modulesLoading: false,
  modules: null,
  modulesFetchFailed: false,
  cachedModules: architectModules,
});
assert(noLic.phase === "no_license", "no_license phase");
assert(!noLic.features.api_locust, "cache must not elevate without license");

// License ready (tester): core on, advanced pending
const licReady = resolveEntitlements({
  licenseLoading: false,
  license: testerLicense,
  modulesLoading: true,
  modules: null,
  modulesFetchFailed: false,
  cachedModules: null,
});
assert(licReady.phase === "license_ready", "license_ready");
assert(licReady.features.api_http_single === true, "tester gets http from tier cap");
assert(licReady.banner === "modules_loading", "modules_loading banner");
assert(
  getFeatureAccess("license_ready", "api_locust", licReady.features, testerLicense) === "denied",
  "locust denied for tester (not in tier cap)",
);
const architectReady = resolveEntitlements({
  licenseLoading: false,
  license: architectLicense,
  modulesLoading: true,
  modules: null,
  modulesFetchFailed: false,
  cachedModules: null,
});
assert(
  getFeatureAccess("license_ready", "api_locust", architectReady.features, architectLicense) === "pending",
  "locust pending for architect while modules load",
);
assert(
  getFeatureAccess("license_ready", "api_http_single", licReady.features, testerLicense) === "granted",
  "http granted for tester during module load",
);

// Beta: advanced granted without waiting modules
const betaReady = resolveEntitlements({
  licenseLoading: false,
  license: betaLicense,
  modulesLoading: true,
  modules: null,
  modulesFetchFailed: false,
  cachedModules: null,
});
assert(
  getFeatureAccess("license_ready", "api_locust", betaReady.features, betaLicense) === "granted",
  "beta skips advanced pending",
);

// Features ready: intersection
const ready = resolveEntitlements({
  licenseLoading: false,
  license: testerLicense,
  modulesLoading: false,
  modules: { ...architectModules, tier: "tester" },
  modulesFetchFailed: false,
  cachedModules: null,
});
assert(ready.phase === "features_ready", "features_ready");
assert(ready.features.api_locust !== true, "tester cap blocks locust even if modules say true");

// Offline cache: stale architect cache + tester license
const offline = resolveEntitlements({
  licenseLoading: false,
  license: testerLicense,
  modulesLoading: false,
  modules: null,
  modulesFetchFailed: true,
  cachedModules: architectModules,
});
assert(offline.phase === "offline_cache", "offline_cache");
assert(offline.banner === "offline", "offline banner");
assert(offline.features.api_locust !== true, "offline intersects with tier cap");
assert(offline.features.api_http_single === true, "offline keeps allowed features");

// Downgrade: cache tier mismatch
assert(cacheTierMismatch("tester", architectModules), "tier mismatch detected");
const downgrade = resolveEntitlements({
  licenseLoading: false,
  license: testerLicense,
  modulesLoading: false,
  modules: null,
  modulesFetchFailed: true,
  cachedModules: architectModules,
});
assert(downgrade.shouldInvalidateCache, "should invalidate on mismatch");

// Actions
assert(!canExecuteHomeActions("verifying", true), "no actions while verifying");
assert(canExecuteHomeActions("license_ready", true), "actions during license_ready");
assert(!canExecuteHomeActions("no_license", true), "no actions without license");

console.log("entitlementPhase.selfcheck: OK");
