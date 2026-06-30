/** Constantes de tiers (espejo de core/entitlements.py). */

export const TIER_TESTER = "tester";
export const TIER_ARCHITECT = "architect";
export const TIER_BETA = "beta";

/** @deprecated Usar TIER_TESTER */
export const TIER_BASIC = "basic";
/** @deprecated Usar TIER_TESTER */
export const TIER_PROFESSIONAL = "professional";
/** @deprecated Usar TIER_ARCHITECT */
export const TIER_ENTERPRISE = "enterprise";

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

const LEGACY_SLUG_LABELS: Record<string, string> = {
  basic: TIER_TESTER,
  professional: TIER_TESTER,
  enterprise: TIER_ARCHITECT,
};

export function normalizeTier(tier: string): string {
  const raw = (tier || "").trim().toLowerCase();
  if (!raw) return "";
  if (raw === TIER_BETA) return TIER_BETA;
  if (raw in LEGACY_SLUG_LABELS) return LEGACY_SLUG_LABELS[raw];
  if (raw === TIER_TESTER || raw === TIER_ARCHITECT) return raw;
  return "";
}

export function tierDisplayName(tier: string): string {
  const norm = normalizeTier(tier) || tier;
  const labels: Record<string, string> = {
    tester: "ELIA Tester",
    architect: "ELIA Architect",
    beta: "Beta",
    basic: "ELIA Tester",
    professional: "ELIA Tester",
    enterprise: "ELIA Architect",
  };
  return labels[norm] ?? tier;
}

export function tierAudience(tier: string): string {
  const norm = normalizeTier(tier);
  if (norm === TIER_ARCHITECT) {
    return "Bancos, financieras, grandes corporativos y arquitectos de automatización con infraestructura pesada.";
  }
  if (norm === TIER_TESTER) {
    return "Testers independientes, equipos medianos y células de desarrollo ágil estándar.";
  }
  return "";
}

export function upsellBenefits(tier: string): string[] {
  const norm = normalizeTier(tier);
  if (norm === TIER_TESTER) {
    return [
      "Grabación web y cliente HTTP API",
      "Pruebas API en cadena (cliente y suites)",
      "Inteligencia Doc-to-BDD (IA local desde el día uno)",
      "Automatización móvil (Appium)",
      "Publishers Git y Jira Vanilla",
    ];
  }
  if (norm === TIER_ARCHITECT) {
    return [
      "Todo lo incluido en ELIA Tester",
      "Orquestación automática de AVD locales (un clic)",
      "Automatización Legacy (escritorio / pywinauto)",
      "Pruebas de carga Locust, reportes PDF/HTML y SLA",
      "Controladores lógicos (If/Loop), gRPC, JDBC y carga distribuida local",
      "Publishers Xray, Value Edge y Azure DevOps",
      "Team Memory Crypto (seguridad asimétrica local-first)",
    ];
  }
  return [];
}

export function avdOrchestrationAllowed(
  license: { tier?: string | null; is_beta?: boolean } | null | undefined,
): boolean {
  if (!license) return false;
  if (license.is_beta) return true;
  return normalizeTier(license.tier ?? "") === TIER_ARCHITECT;
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
