/** Constantes de tiers (espejo de core/entitlements.py). */

export const TIER_BASIC = "basic";
export const TIER_PROFESSIONAL = "professional";
export const TIER_ENTERPRISE = "enterprise";
export const TIER_BETA = "beta";

export const UPGRADE_CONTACT_EMAIL = "elia.qa.software+contacto@gmail.com";

export type FeatureFlags = {
  web_recording?: boolean;
  api_http_single?: boolean;
  api_testing?: boolean;
  doc_to_bdd?: boolean;
  api_postman_suites?: boolean;
  api_locust?: boolean;
  mobile_recording?: boolean;
  legacy_recording?: boolean;
  publishers_standard?: boolean;
  publishers_enterprise?: boolean;
  team_memory_crypto?: boolean;
};

export function tierDisplayName(tier: string): string {
  const labels: Record<string, string> = {
    basic: "Basic",
    professional: "Professional",
    enterprise: "Enterprise",
    beta: "Beta",
  };
  return labels[tier] ?? tier;
}

export function upsellBenefits(tier: string): string[] {
  if (tier === TIER_PROFESSIONAL) {
    return [
      "Inteligencia de Requerimientos (Doc-to-BDD)",
      "Automatización Móvil (Appium)",
      "Pruebas API en cadena (Postman / suites)",
      "Publishers Git y Jira Vanilla",
    ];
  }
  if (tier === TIER_ENTERPRISE) {
    return [
      "Automatización Legacy (pywinauto)",
      "Publishers Xray, Value Edge y Azure DevOps",
      "Team Memory Crypto (export/import seguro)",
      "Performance Testing con Locust y reportes PDF",
    ];
  }
  return [];
}

export function hasFeature(modules: FeatureFlags | null | undefined, key: keyof FeatureFlags): boolean {
  if (!modules) return false;
  if (key in modules && typeof modules[key] === "boolean") return Boolean(modules[key]);
  return false;
}

export function featureFromModules(modules: FeatureFlags | null | undefined): FeatureFlags {
  return {
    web_recording: modules?.web_recording ?? true,
    api_http_single: modules?.api_http_single ?? modules?.api_testing ?? false,
    doc_to_bdd: modules?.doc_to_bdd ?? false,
    api_postman_suites: modules?.api_postman_suites ?? false,
    api_locust: modules?.api_locust ?? false,
    mobile_recording: modules?.mobile_recording ?? false,
    legacy_recording: modules?.legacy_recording ?? false,
    publishers_standard: modules?.publishers_standard ?? false,
    publishers_enterprise: modules?.publishers_enterprise ?? false,
    team_memory_crypto: modules?.team_memory_crypto ?? false,
  };
}
