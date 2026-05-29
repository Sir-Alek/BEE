import type { LicenseStatusResponse } from "../api";

export type LicenseState = {
  can_run_jobs: boolean;
  message: string;
  activated: boolean;
  machine_fingerprint: string;
  reason?: string;
  expires_at?: number | null;
  duration_code?: string | null;
  tier?: string | null;
  tier_label?: string | null;
  is_beta?: boolean;
  upgrade_email?: string;
};

export function licenseFromApi(l: LicenseStatusResponse): LicenseState {
  return {
    can_run_jobs: l.can_run_jobs,
    message: l.message,
    activated: l.activated,
    machine_fingerprint: l.machine_fingerprint,
    reason: l.reason,
    expires_at: l.expires_at ?? null,
    duration_code: l.duration_code ?? null,
    tier: l.tier ?? null,
    tier_label: l.tier_label ?? null,
    is_beta: l.is_beta,
    upgrade_email: l.upgrade_email,
  };
}

export function formatLicenseExpiryDate(expiresAtSec: number): string {
  return new Date(expiresAtSec * 1000).toLocaleDateString("es-MX", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/** Texto breve para la tarjeta Licencia en Configuración. */
export function formatLicenseStatusLabel(license: LicenseState): string {
  if (license.reason === "skip") {
    return "Desarrollo (licencia omitida).";
  }
  if (license.reason === "killed") {
    return "Inactiva — no disponible en este equipo.";
  }
  if (!license.can_run_jobs) {
    if (license.reason === "not_activated") {
      return "Sin activar — introduce la clave de licencia.";
    }
    if (license.reason === "license_expired") {
      return "Inactiva — licencia caducada.";
    }
    if (license.reason === "beta_expired") {
      return "Beta finalizada — adquiere suscripción.";
    }
    if (license.reason === "clock_tamper") {
      return "Bloqueada — reloj del sistema inválido.";
    }
    return license.message;
  }
  if (license.activated) {
    if (license.expires_at == null) {
      return "Licencia permanente.";
    }
    const days = Math.max(0, (license.expires_at * 1000 - Date.now()) / 86400000);
    return `Licencia temporal: expira el ${formatLicenseExpiryDate(license.expires_at)} (≈ ${Math.ceil(days)} día(s)).`;
  }
  return license.message;
}

/** Aviso de activación (solo sin licencia activada). */
export function licenseNeedsActivationBanner(license: LicenseState): boolean {
  return license.reason === "not_activated";
}

/** Aviso de caducidad próxima (licencia temporal activa). */
export function licenseNeedsExpiryBanner(license: LicenseState): boolean {
  if (!license.activated || license.expires_at == null) {
    return false;
  }
  const daysLeft = (license.expires_at * 1000 - Date.now()) / 86400000;
  return daysLeft <= 7;
}
