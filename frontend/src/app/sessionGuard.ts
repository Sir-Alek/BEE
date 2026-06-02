import { ELIA_UI_BC } from "./constants";
import { isReloadNavigation } from "./navigationUtils";

export type SessionReconcileResult = "ok" | "offline" | "stale";

const SKIP_EXIT_KEY = "elia_skip_exit_on_pagehide";
const HOME_OWNER_KEY = "elia_home_owner_tab";
const HOME_OWNER_TS_KEY = "elia_home_owner_ts";
const STARTUP_GRACE_MS = 12_000;
const HOME_OWNER_STALE_MS = 12_000;
const CANONICAL_UI_PORT = "8765";

const TAB_ID =
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `tab-${Date.now()}-${Math.random().toString(16).slice(2)}`;

const PAGE_STARTED_AT = Date.now();

export function readUrlSessionId(): string | null {
  try {
    return new URLSearchParams(window.location.search).get("elia_sid");
  } catch {
    return null;
  }
}

export function isEliaJobTab(): boolean {
  try {
    return !!new URLSearchParams(window.location.search).get("job_id");
  } catch {
    return false;
  }
}

/** Pestaña de flujo (job o abierta con window.open desde inicio). */
export function isEliaWorkflowTab(): boolean {
  if (isEliaJobTab()) return true;
  try {
    return !!(window.opener && !window.opener.closed);
  } catch {
    return !!window.opener;
  }
}

export function isEliaHomeTab(): boolean {
  return !isEliaWorkflowTab();
}

export function shouldSkipExitOnPageHide(): boolean {
  return checkAndConsumeSkipExit();
}

export function checkAndConsumeSkipExit(): boolean {
  try {
    if (sessionStorage.getItem(SKIP_EXIT_KEY) === "1") {
      sessionStorage.removeItem(SKIP_EXIT_KEY);
      return true;
    }
  } catch {
    // ignore
  }
  return false;
}

export function isHomeTabOwner(): boolean {
  if (!isEliaHomeTab()) return false;
  try {
    return sessionStorage.getItem(HOME_OWNER_KEY) === TAB_ID;
  } catch {
    return true;
  }
}

export function releasePrimaryTabClaim(): void {
  try {
    if (sessionStorage.getItem(HOME_OWNER_KEY) === TAB_ID) {
      sessionStorage.removeItem(HOME_OWNER_KEY);
      sessionStorage.removeItem(HOME_OWNER_TS_KEY);
    }
  } catch {
    // ignore
  }
}

function markClosingWithoutServerExit(): void {
  try {
    sessionStorage.setItem(SKIP_EXIT_KEY, "1");
  } catch {
    // ignore
  }
}

function syncSessionInUrl(liveSid: string): void {
  const next = new URL(window.location.href);
  next.searchParams.set("elia_sid", liveSid);
  window.history.replaceState(null, "", next.toString());
}

function isLegacyRandomPort(): boolean {
  const port = window.location.port;
  return !!port && port !== CANONICAL_UI_PORT;
}

/** Cierra pestaña obsoleta/duplicada sin apagar ELIA. */
export function closeWithoutStoppingServer(): void {
  if (isReloadNavigation()) return;
  markClosingWithoutServerExit();
  try {
    window.close();
  } catch {
    // ignore
  }
  window.setTimeout(() => {
    try {
      window.close();
    } catch {
      // ignore
    }
  }, 250);
}

/** @deprecated */
export function attemptCloseStaleTab(): void {
  closeWithoutStoppingServer();
}

/**
 * Solo una pestaña de inicio activa: las demás se cierran solas (sin /api/app/exit).
 */
export function maintainSingleHomeTab(): boolean {
  if (!isEliaHomeTab()) return true;
  try {
    const owner = sessionStorage.getItem(HOME_OWNER_KEY);
    const ts = Number(sessionStorage.getItem(HOME_OWNER_TS_KEY) || 0);
    const ownerStale = !ts || Date.now() - ts > HOME_OWNER_STALE_MS;
    if (!owner || owner === TAB_ID || ownerStale) {
      sessionStorage.setItem(HOME_OWNER_KEY, TAB_ID);
      sessionStorage.setItem(HOME_OWNER_TS_KEY, String(Date.now()));
      return true;
    }
    return false;
  } catch {
    return true;
  }
}

export function touchHomeTabOwner(): void {
  if (!isEliaHomeTab() || !isHomeTabOwner()) return;
  try {
    sessionStorage.setItem(HOME_OWNER_TS_KEY, String(Date.now()));
  } catch {
    // ignore
  }
}

/** @deprecated */
export function touchPrimaryTabHeartbeat(): void {
  touchHomeTabOwner();
}

/** @deprecated */
export function isThisPrimaryEliaTab(): boolean {
  return isHomeTabOwner();
}

export async function reconcileEliaSession(): Promise<SessionReconcileResult> {
  const urlSid = readUrlSessionId();
  try {
    const res = await fetch("/api/app/ping", { method: "POST" });
    if (!res.ok) return "offline";
    const data = (await res.json()) as { ok?: boolean; session_id?: string };
    if (data.ok !== true) return "offline";
    const liveSid = typeof data.session_id === "string" ? data.session_id : "";
    if (liveSid) {
      sessionStorage.setItem("elia_session_id", liveSid);
    }
    if (urlSid && liveSid && urlSid !== liveSid) {
      if (isEliaWorkflowTab()) {
        syncSessionInUrl(liveSid);
        return "ok";
      }
      return "stale";
    }
    if (!urlSid && liveSid && isEliaHomeTab()) {
      syncSessionInUrl(liveSid);
    }
    return "ok";
  } catch {
    return "offline";
  }
}

/** Tras ping: cerrar obsoletas/duplicadas; nunca apagar servidor desde aquí. */
export function applySessionGuard(result: SessionReconcileResult): boolean {
  if (result === "stale") {
    closeWithoutStoppingServer();
    return false;
  }
  if (result === "ok") {
    if (isEliaHomeTab() && !maintainSingleHomeTab()) {
      closeWithoutStoppingServer();
      return false;
    }
    touchHomeTabOwner();
    return true;
  }
  if (isEliaWorkflowTab()) return true;
  if (Date.now() - PAGE_STARTED_AT < STARTUP_GRACE_MS) return true;
  if (isLegacyRandomPort() || isEliaHomeTab()) {
    closeWithoutStoppingServer();
    return false;
  }
  return true;
}

/** @deprecated */
export function manageEliaTabLifecycle(result: SessionReconcileResult): boolean {
  return applySessionGuard(result);
}

/** Notifica a otras pestañas home que hay una sesión nueva (cierran si su sid difiere). */
export function broadcastNewEliaSession(sessionId: string): void {
  if (!sessionId) return;
  try {
    const bc = new BroadcastChannel(ELIA_UI_BC);
    bc.postMessage({ type: "elia_new_session", session_id: sessionId });
    bc.close();
  } catch {
    // ignore
  }
}

export function listenForNewEliaSession(onStale: () => void): () => void {
  try {
    const bc = new BroadcastChannel(ELIA_UI_BC);
    bc.onmessage = (ev: MessageEvent) => {
      if (ev.data?.type !== "elia_new_session") return;
      if (!isEliaHomeTab()) return;
      const liveSid = typeof ev.data.session_id === "string" ? ev.data.session_id : "";
      const urlSid = readUrlSessionId();
      if (liveSid && urlSid && liveSid !== urlSid) onStale();
    };
    return () => {
      try {
        bc.close();
      } catch {
        // ignore
      }
    };
  } catch {
    return () => {};
  }
}
