import { ELIA_UI_BC } from "./constants";
import { isReloadNavigation } from "./navigationUtils";
import { checkAndConsumeSkipExit, isHomeTabOwner, releasePrimaryTabClaim } from "./sessionGuard";

export type EliaJobFinishedPayload = {
  jobId?: string;
  platform?: string;
  project?: string;
};

/** Extrae plataforma y nombre de proyecto desde una ruta behave/{platform}/{project}. */
export function inferBehaveProjectFromDir(dir: string): { platform?: string; project?: string } {
  const norm = dir.replace(/\\/g, "/");
  const m = norm.match(/behave\/(web|mobile|legacy)\/([^/]+)\/?$/i);
  if (!m) return {};
  return { platform: m[1].toLowerCase(), project: decodeURIComponent(m[2]) };
}

export function inferBehaveProjectFromProgress(
  progress?: Record<string, unknown> | null,
): { platform?: string; project?: string } {
  if (!progress) return {};
  const dir = progress.output_dir ?? progress.project_dir;
  if (typeof dir === "string" && dir.trim()) {
    return inferBehaveProjectFromDir(dir);
  }
  return {};
}

/** True cuando la pestaña se descarga por recarga (F5), no por cierre real. */
export { isReloadNavigation } from "./navigationUtils";

export function notifyHomeJobFinished(payload?: EliaJobFinishedPayload): void {
  try {
    const bc = new BroadcastChannel(ELIA_UI_BC);
    bc.postMessage({
      type: "elia_job_finished",
      job_id: payload?.jobId ?? "",
      platform: payload?.platform,
      project: payload?.project,
    });
    bc.close();
  } catch {
    // ignore
  }
}

/**
 * Enfoca la pestaña de inicio (opener) y cierra la de trabajo.
 * Nunca navega esta pestaña al inicio si existe opener (evita duplicar home).
 */
export function returnToHomeFromJobTab(payload?: EliaJobFinishedPayload): void {
  notifyHomeJobFinished(payload);
  if (window.opener && !window.opener.closed) {
    try {
      window.opener.focus();
    } catch {
      // ignore
    }
    try {
      window.close();
    } catch {
      // ignore
    }
    return;
  }
  const base = `${window.location.origin}${window.location.pathname.replace(/\?.*$/, "")}`;
  window.location.assign(base);
}

export async function pingAppSession(): Promise<boolean> {
  try {
    const res = await fetch("/api/app/ping", { method: "POST" });
    if (!res.ok) return false;
    const data = (await res.json()) as { ok?: boolean; session_id?: string };
    if (data.session_id) {
      sessionStorage.setItem("elia_session_id", data.session_id);
    }
    return data.ok === true;
  } catch {
    return false;
  }
}

/** Cierre de pestaña/ventana (no F5): apaga ELIA solo desde la pestaña de inicio titular. */
export function requestAppExitIfClosing(): void {
  if (isReloadNavigation()) return;
  if (checkAndConsumeSkipExit()) return;
  if (!isHomeTabOwner()) return;
  releasePrimaryTabClaim();
  const body = JSON.stringify({ reason: "ui_closed" });
  try {
    const blob = new Blob([body], { type: "application/json" });
    if (!navigator.sendBeacon("/api/app/exit", blob)) {
      void fetch("/api/app/exit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: true,
      });
    }
  } catch {
    try {
      void fetch("/api/app/exit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: true,
      });
    } catch {
      // ignore
    }
  }
}

/** Job tab sin pestaña de inicio viva: también solicita cierre global. */
export function requestAppExitIfClosingWhenOrphanJobTab(): void {
  if (isReloadNavigation()) return;
  if (window.opener && !window.opener.closed) return;
  requestAppExitIfClosing();
}
