import type { MobilePreflightItem } from "./api";

export const EMULATOR_MISSING_WARNING =
  "No se detectó Android Emulator: solo podrás usar dispositivo físico. Instala Android Emulator o define ANDROID_HOME.";

const CORE_PREFLIGHT_IDS = new Set(["android_sdk", "adb", "emulator", "appium", "device"]);

const PATH_ITEM_IDS = new Set(["android_sdk", "adb", "emulator"]);

/** Oculta el segmento Users/<usuario> y acorta rutas largas. */
export function truncatePathForDisplay(raw: string): string {
  if (!raw || raw === "No detectado" || raw === "No encontrado" || raw === "Ninguno") {
    return raw;
  }
  const normalized = raw.replace(/\\/g, "/");
  const afterUser = normalized.match(/^[A-Za-z]:\/Users\/[^/]+\/(.+)$/);
  if (afterUser) {
    return `…/${afterUser[1]}`;
  }
  if (normalized.length > 52) {
    const parts = normalized.split("/").filter(Boolean);
    if (parts.length >= 2) {
      return `…/${parts.slice(-3).join("/")}`;
    }
  }
  return raw;
}

export function formatPreflightItemMessage(item: MobilePreflightItem): string {
  if (PATH_ITEM_IDS.has(item.id) && item.ok && /[:/\\]/.test(item.message)) {
    return truncatePathForDisplay(item.message);
  }
  return item.message;
}

export function mobilePreflightSummary(items: MobilePreflightItem[]): { ok: number; total: number } {
  const core = items.filter((item) => CORE_PREFLIGHT_IDS.has(item.id));
  return {
    ok: core.filter((item) => item.ok).length,
    total: core.length,
  };
}

export function normalizeMobileWarnings(warnings: string[]): string[] {
  const out: string[] = [];
  let emulatorCovered = false;

  for (const warning of warnings) {
    const lower = warning.toLowerCase();
    if (lower.includes("emulator no encontrado") || lower.includes("no se detectó android emulator")) {
      if (!emulatorCovered) {
        out.push(EMULATOR_MISSING_WARNING);
        emulatorCovered = true;
      }
      continue;
    }
    if (!out.includes(warning)) {
      out.push(warning);
    }
  }
  return out;
}

export function shouldAutoOpenMobileEnv(
  preflight: { ok: boolean; errors: string[]; items: MobilePreflightItem[] } | null,
): boolean {
  if (!preflight) return false;
  if (!preflight.ok || preflight.errors.length > 0) return true;
  return preflight.items.some((item) => item.id === "emulator" && !item.ok);
}

export function friendlyAvdsError(error: string | null): string | null {
  if (!error) return null;
  if (/emulator no encontrado/i.test(error)) return null;
  return error;
}
