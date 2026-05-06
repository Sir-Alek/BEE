import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  activateLicense,
  getAiStatus,
  getEliaConnectors,
  getJob,
  getLicenseStatus,
  putEliaConnectors,
  sendPromptResponse,
  startConvertJob,
  testEliaConnector,
} from "./api";
import type { ActivePrompt, EliaConnectorProfile } from "./types";
import { ELIA_CONNECTORS_LS_KEY, emptyJiraCreds, emptyValueEdgeCreds, newConnectorProfile } from "./connectorDefaults";
import { themeQuerySuffix, useEliaTheme } from "./eliaTheme";

type JobStatus = {
  job_id: string;
  state: string;
  active_prompt: ActivePrompt | null;
  error: null | { message: string; details?: string };
  progress: Record<string, any>;
};

function formatPromptType(t: string): string {
  if (t === "message_ack") return "Aviso";
  return t.replaceAll("_", " ");
}

function formatJobMode(mode: string | null): string {
  if (!mode) return "";
  if (mode === "puppeteer_recorder") return "Grabar interacciones";
  if (mode === "puppeteer_to_behave") return "Convertir a Behave";
  if (mode === "puppeteer_to_step_by_step") return "Convertir a step by step";
  if (mode === "elia_jira_smoke") return "ELIA · Conectar a Jira";
  if (mode === "elia_value_edge_smoke") return "ELIA · Extraer de ValueEdge";
  if (mode === "elia_gherkin_batch") return "ELIA · Procesamiento por lotes (Gherkin)";
  return mode;
}

function openJobUrlInNewTabPrepared(): Window | null {
  return window.open("about:blank", "_blank");
}

const ELIA_UI_BC = "elia-ui";

/** Visible in the UI: if this text does not appear, `frontend/dist` is stale — run `npm run build`. */
const ELIA_WEB_UI_BUILD = "elia-ui-20260505-c";

function goHomeInThisTab(): void {
  window.location.assign(`${window.location.origin}/`);
}

function modalFieldStyle(c: {
  inputBorder: string;
  inputBg: string;
  text: string;
}): React.CSSProperties {
  return {
    width: "100%",
    padding: "10px 12px",
    borderRadius: 10,
    border: `1px solid ${c.inputBorder}`,
    background: c.inputBg,
    color: c.text,
    fontSize: 14,
  };
}

function tryFocusOpenerAndCloseThisTab(): boolean {
  if (!window.opener || window.opener.closed) {
    return false;
  }
  try {
    window.opener.focus();
  } catch {
    // ignore
  }
  try {
    window.close();
    return true;
  } catch {
    return false;
  }
}

export default function App() {
  const { c, dark, toggle } = useEliaTheme();

  /** Pinned from first paint: home URL has no job_id; avoids any edge case mixing job UI into home. */
  const [isHomeSurface] = useState(() => !new URLSearchParams(window.location.search).get("job_id"));
  const [homeTab, setHomeTab] = useState<"ui" | "req">("ui");

  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [polling, setPolling] = useState<boolean>(false);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [textValue, setTextValue] = useState<string>("");
  const [urlValue, setUrlValue] = useState<string>("");
  const [initialChecked, setInitialChecked] = useState<boolean>(false);
  const [workspaceMode, setWorkspaceMode] = useState<string | null>(null);
  const [homeHint, setHomeHint] = useState<string | null>(null);
  /** Solo afecta a «Convertir a Behave»: llama.cpp + GGUF + metadatos de grabación. */
  const [useAi, setUseAi] = useState(false);
  const [aiStatusLine, setAiStatusLine] = useState<string | null>(null);
  const [license, setLicense] = useState<{
    can_run_jobs: boolean;
    message: string;
    demo_days_left: number | null;
    activated: boolean;
    machine_fingerprint: string;
  } | null>(null);
  const [activationKey, setActivationKey] = useState("");
  const [activationMsg, setActivationMsg] = useState<string | null>(null);
  const [bddPreviewText, setBddPreviewText] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [connectorProfiles, setConnectorProfiles] = useState<EliaConnectorProfile[]>([]);
  const [reqConnectorProfileId, setReqConnectorProfileId] = useState("");
  const [settingsProfileId, setSettingsProfileId] = useState("");
  const [settingsTestMsg, setSettingsTestMsg] = useState<string | null>(null);
  const [settingsSaveMsg, setSettingsSaveMsg] = useState<string | null>(null);

  const activePrompt = (job?.active_prompt ?? null) as ActivePrompt | null;

  const persistConnectorProfiles = useCallback(async (next: EliaConnectorProfile[]) => {
    const doc = { version: 1 as const, profiles: next };
    try {
      localStorage.setItem(ELIA_CONNECTORS_LS_KEY, JSON.stringify(doc));
    } catch {
      // ignore
    }
    try {
      await putEliaConnectors(doc);
    } catch {
      // guardar local aunque backend falle (p. ej. sin cryptography instalado)
    }
  }, []);

  useEffect(() => {
    if (!isHomeSurface) return;
    let alive = true;
    void (async () => {
      let localProfiles: EliaConnectorProfile[] = [];
      try {
        const raw = localStorage.getItem(ELIA_CONNECTORS_LS_KEY);
        if (raw) {
          const p = JSON.parse(raw) as { profiles?: EliaConnectorProfile[] };
          if (Array.isArray(p?.profiles)) localProfiles = p.profiles;
        }
      } catch {
        localProfiles = [];
      }
      try {
        const remote = await getEliaConnectors();
        if (!alive) return;
        const r = remote?.profiles ?? [];
        const use = r.length ? r : localProfiles;
        setConnectorProfiles(use);
        const firstId = use[0]?.id ?? "";
        setReqConnectorProfileId((prev) => (prev && use.some((x) => x.id === prev) ? prev : firstId));
        setSettingsProfileId((prev) => (prev && use.some((x) => x.id === prev) ? prev : firstId));
      } catch {
        if (!alive) return;
        setConnectorProfiles(localProfiles);
        const firstId = localProfiles[0]?.id ?? "";
        setReqConnectorProfileId((prev) =>
          prev && localProfiles.some((x) => x.id === prev) ? prev : firstId,
        );
        setSettingsProfileId((prev) =>
          prev && localProfiles.some((x) => x.id === prev) ? prev : firstId,
        );
      }
    })();
    return () => {
      alive = false;
    };
  }, [isHomeSurface]);

  useEffect(() => {
    if (!isHomeSurface) return;
    let alive = true;
    void (async () => {
      try {
        const s = await getAiStatus();
        if (!alive) return;
        const m = s.model;
        const hasModel = m?.exists && (m.size_bytes ?? 0) > 0;
        const hasLib = s.llama_cpp_python_available === true;
        if (hasModel && hasLib) {
          setAiStatusLine("IA local: modelo Gemma + llama-cpp-python listos.");
        } else if (hasModel && !hasLib) {
          setAiStatusLine(
            "Modelo Gemma presente; falta el paquete llama-cpp-python (pip install). Modo heurístico hasta entonces.",
          );
        } else {
          setAiStatusLine("Modelo Gemma no encontrado en resources/models/gemma/ — conversión en modo heurístico.");
        }
      } catch {
        if (alive) setAiStatusLine(null);
      }
    })();
    return () => {
      alive = false;
    };
  }, [isHomeSurface]);

  useEffect(() => {
    if (!isHomeSurface) return;
    let alive = true;
    void (async () => {
      try {
        const l = await getLicenseStatus();
        if (!alive) return;
        setLicense({
          can_run_jobs: l.can_run_jobs,
          message: l.message,
          demo_days_left: l.demo_days_left,
          activated: l.activated,
          machine_fingerprint: l.machine_fingerprint,
        });
      } catch {
        if (alive) setLicense(null);
      }
    })();
    return () => {
      alive = false;
    };
  }, [isHomeSurface]);

  // Close home tab = close whole app (backend). sendBeacon/fetch + main.py polling /api/app/should-exit.
  useEffect(() => {
    if (!isHomeSurface) return;
    const body = JSON.stringify({ reason: "home_closed" });
    const fireExit = () => {
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
    };
    window.addEventListener("beforeunload", fireExit);
    window.addEventListener("pagehide", fireExit);
    return () => {
      window.removeEventListener("beforeunload", fireExit);
      window.removeEventListener("pagehide", fireExit);
    };
  }, [isHomeSurface]);

  const startJob = (
    mode:
      | "puppeteer_recorder"
      | "puppeteer_to_behave"
      | "puppeteer_to_step_by_step"
      // ELIA
      | "elia_jira_smoke"
      | "elia_value_edge_smoke"
      | "elia_gherkin_batch",
  ) => {
    setErrorText(null);
    setHomeHint(null);
    if (license && !license.can_run_jobs) {
      setErrorText("Periodo de demostración finalizado. Introduce la clave de activación abajo.");
      return;
    }
    if (mode === "puppeteer_recorder" && !urlValue.trim()) {
      setErrorText("URL requerida para 'Grabar Interacciones'.");
      return;
    }

    const eliaNeedsProfile =
      mode === "elia_jira_smoke" ||
      mode === "elia_value_edge_smoke" ||
      mode === "elia_gherkin_batch";
    if (eliaNeedsProfile && connectorProfiles.length === 0) {
      setErrorText("Primero crea un perfil de conectores en Configuración (⚙).");
      return;
    }
    const selProf = connectorProfiles.find((x) => x.id === reqConnectorProfileId);
    if ((mode === "elia_jira_smoke" || mode === "elia_value_edge_smoke") && !selProf) {
      setErrorText("Selecciona un perfil de conectores en la pestaña «Inteligencia de Requerimientos».");
      return;
    }

    const newTab = openJobUrlInNewTabPrepared();
    if (!newTab) {
      setErrorText(
        "El navegador bloqueó la ventana emergente. Permite ventanas emergentes para 127.0.0.1 e inténtalo de nuevo. " +
          "Sin eso, el flujo podría abrirse en esta misma pestaña y reemplazar el inicio.",
      );
      return;
    }

    void (async () => {
      try {
        const eliaModes = new Set([
          "elia_jira_smoke",
          "elia_value_edge_smoke",
          "elia_gherkin_batch",
        ]);
        const prof = connectorProfiles.find((x) => x.id === reqConnectorProfileId);
        const res = await startConvertJob({
          mode,
          url: mode === "puppeteer_recorder" ? urlValue.trim() : undefined,
          use_ai: mode === "puppeteer_to_behave" ? useAi : false,
          ...(eliaModes.has(mode)
            ? {
                elia_use_inline_connectors: true,
                elia_jira: prof?.jira ?? emptyJiraCreds(),
                elia_value_edge: prof?.value_edge ?? emptyValueEdgeCreds(),
              }
            : {}),
        });
        const base = `${window.location.origin}${window.location.pathname}`;
        const jobUrl = `${base}?job_id=${encodeURIComponent(res.job_id)}&mode=${encodeURIComponent(mode)}${themeQuerySuffix()}`;
        try {
          newTab.location.replace(jobUrl);
        } catch {
          newTab.location.href = jobUrl;
        }
        setHomeHint(
          "El flujo se abrió en otra pestaña. Esta vista es el inicio: déjala abierta y usa la otra pestaña para los pasos y el resultado.",
        );
      } catch (e: any) {
        try {
          newTab.close();
        } catch {
          // ignore
        }
        setErrorText(String(e?.message ?? e));
      }
    })();
  };

  useEffect(() => {
    if (activePrompt?.type === "input_text") {
      setTextValue("");
    }
  }, [activePrompt?.prompt_id, activePrompt?.type]);

  useEffect(() => {
    const ap = activePrompt as { type?: string; payload?: { feature_text?: string } } | null;
    if (ap?.type === "bdd_preview" && ap.payload?.feature_text != null) {
      setBddPreviewText(String(ap.payload.feature_text));
    }
  }, [activePrompt?.prompt_id, activePrompt]);

  useEffect(() => {
    const sp = new URLSearchParams(window.location.search);
    const initialJobId = sp.get("job_id");
    const mode = sp.get("mode");
    if (mode) setWorkspaceMode(mode);

    if (initialJobId) {
      setJobId(initialJobId);
      setPolling(true);
      setInitialChecked(true);
      return;
    }

    setInitialChecked(true);
  }, []);

  useEffect(() => {
    if (!isHomeSurface) return;
    let bc: BroadcastChannel | null = null;
    try {
      bc = new BroadcastChannel(ELIA_UI_BC);
      bc.onmessage = (ev: MessageEvent) => {
        if (ev.data?.type === "elia_job_finished" || ev.data?.type === "bee_job_finished") {
          setHomeHint(null);
        }
      };
    } catch {
      // ignore
    }
    return () => {
      try {
        bc?.close();
      } catch {
        // ignore
      }
    };
  }, [isHomeSurface]);

  useEffect(() => {
    if (!homeHint) return;
    const t = window.setTimeout(() => setHomeHint(null), 5 * 60 * 1000);
    return () => window.clearTimeout(t);
  }, [homeHint]);

  useEffect(() => {
    if (isHomeSurface || !jobId || !job) return;
    const s = job.state;
    if (s !== "done" && s !== "error" && s !== "cancelled") return;
    try {
      const key = `elia_job_finished_broadcast:${jobId}`;
      if (sessionStorage.getItem(key)) return;
      sessionStorage.setItem(key, "1");
      const bc = new BroadcastChannel(ELIA_UI_BC);
      bc.postMessage({ type: "elia_job_finished", job_id: jobId });
      bc.close();
    } catch {
      // ignore
    }
  }, [isHomeSurface, jobId, job?.state]);

  useEffect(() => {
    if (!polling || !jobId) return;

    let alive = true;
    const tick = async () => {
      try {
        const j = await getJob(jobId);
        if (!alive) return;
        setJob({
          job_id: j.job_id,
          state: j.state,
          active_prompt: j.active_prompt,
          error: j.error,
          progress: j.progress ?? {},
        });
        if (j.state === "done" || j.state === "error" || j.state === "cancelled") {
          setPolling(false);
        }
      } catch (e: any) {
        if (!alive) return;
        setErrorText(String(e?.message ?? e));
        setPolling(false);
      }
    };

    tick();
    const interval = window.setInterval(tick, 450);
    return () => {
      alive = false;
      window.clearInterval(interval);
    };
  }, [polling, jobId]);

  const header = useMemo(() => {
    const isHome = isHomeSurface;
    const statusLine = isHome
      ? "Inicio · deja esta pestaña abierta para nuevas tareas"
      : job
        ? `Estado: ${job.state}`
        : "Cargando trabajo…";
    const sub = !isHome && workspaceMode ? `${formatJobMode(workspaceMode)} · ` : "";

    return (
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 12,
          padding: "16px 18px",
          borderBottom: `1px solid ${c.border}`,
          background: c.chromeBg,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12, flex: "0 1 auto", minWidth: 0 }}>
          <img
            src="/logo.png"
            alt="ELIA"
            style={{
              width: 42,
              height: 42,
              borderRadius: 12,
              objectFit: "contain",
              background: "transparent",
            }}
          />
          <div style={{ display: "flex", flexDirection: "column", minWidth: 140 }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: c.text }}>ELIA</div>
            <div style={{ fontSize: 12, color: c.chromeHint }}>
              {isHome ? "Local Web UI — inicio" : sub + "ventana de trabajo"}
            </div>
          </div>
        </div>
        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "flex-end",
            gap: 12,
            rowGap: 8,
            flex: "1 1 0",
            minWidth: 0,
          }}
        >
          <div
            style={{
              fontSize: 12,
              color: c.chromeHint,
              textAlign: "right",
              flex: "1 1 220px",
              minWidth: 160,
              maxWidth: "min(520px, 100%)",
            }}
          >
            {statusLine}
          </div>
          <button
            type="button"
            aria-label="Abrir configuración"
            title={`Configuración · build ${ELIA_WEB_UI_BUILD}`}
            onClick={() => {
              setSettingsOpen(true);
              setSettingsTestMsg(null);
              setSettingsSaveMsg(null);
              const fallback = reqConnectorProfileId || connectorProfiles[0]?.id || "";
              setSettingsProfileId((prev) =>
                prev && connectorProfiles.some((x) => x.id === prev) ? prev : fallback,
              );
            }}
            style={{
              marginLeft: "auto",
              flexShrink: 0,
              width: 42,
              height: 42,
              borderRadius: 10,
              fontSize: 22,
              lineHeight: 1,
              cursor: "pointer",
              border: `1px solid ${c.btnGhostBorder}`,
              background: c.btnGhostBg,
              color: c.text,
              boxShadow: c.shadow,
            }}
          >
            ⚙
          </button>
        </div>
      </div>
    );
  }, [job, workspaceMode, isHomeSurface, c, connectorProfiles, reqConnectorProfileId]);

  return (
    <div
      style={{
        fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial",
        background: c.pageBg,
        color: c.text,
        minHeight: "100vh",
      }}
    >
      {header}

      {settingsOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Configuración"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 100000,
            background: "rgba(15, 23, 42, 0.55)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 16,
          }}
          onClick={() => setSettingsOpen(false)}
        >
          <div
            style={{
              width: "min(680px, 100%)",
              maxHeight: "min(92vh, 920px)",
              overflow: "auto",
              borderRadius: 16,
              border: `1px solid ${c.border}`,
              background: c.surface,
              boxShadow: c.shadow,
              padding: 22,
              color: c.text,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
              <div style={{ fontSize: 18, fontWeight: 800, flex: 1 }}>Configuración</div>
              <button
                type="button"
                onClick={() => setSettingsOpen(false)}
                style={{
                  border: `1px solid ${c.btnGhostBorder}`,
                  background: c.btnGhostBg,
                  color: c.text,
                  borderRadius: 10,
                  padding: "6px 12px",
                  cursor: "pointer",
                }}
              >
                Cerrar
              </button>
            </div>

            <div
              style={{
                border: `1px solid ${c.border}`,
                borderRadius: 12,
                padding: 14,
                marginBottom: 14,
                background: c.neutralBg,
              }}
            >
              <div style={{ fontWeight: 800, marginBottom: 10 }}>Apariencia</div>
              <label
                htmlFor="elia-theme-toggle"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 12,
                  cursor: "pointer",
                  fontSize: 14,
                }}
              >
                <span>{dark ? "Modo oscuro activo" : "Modo claro activo"}</span>
                <input
                  id="elia-theme-toggle"
                  type="checkbox"
                  checked={dark}
                  onChange={() => toggle()}
                  style={{ position: "absolute", opacity: 0, width: 1, height: 1 }}
                />
                <span
                  style={{
                    position: "relative",
                    width: 44,
                    height: 26,
                    borderRadius: 999,
                    background: dark ? c.primary : c.border,
                    flexShrink: 0,
                  }}
                  aria-hidden
                >
                  <span
                    style={{
                      position: "absolute",
                      top: 3,
                      left: dark ? 22 : 3,
                      width: 20,
                      height: 20,
                      borderRadius: "50%",
                      background: "#fff",
                      transition: "left 160ms ease",
                    }}
                  />
                </span>
              </label>
            </div>

            <div
              style={{
                border: `1px solid ${c.border}`,
                borderRadius: 12,
                padding: 14,
                marginBottom: 14,
              }}
            >
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Conectores · Jira y Value Edge</div>
              <div style={{ color: c.muted, fontSize: 13, marginBottom: 12 }}>
                Los datos se guardan en el navegador y, si el backend tiene <code>cryptography</code>, también cifrados
                en disco (misma máquina). Usa solo en red local (<code>127.0.0.1</code>).
              </div>

              <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", marginBottom: 12 }}>
                <label style={{ fontSize: 13, fontWeight: 600 }}>Perfil</label>
                <select
                  value={settingsProfileId}
                  onChange={(e) => setSettingsProfileId(e.target.value)}
                  style={{
                    flex: "1 1 240px",
                    minWidth: 200,
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: `1px solid ${c.inputBorder}`,
                    background: c.inputBg,
                    color: c.text,
                    fontSize: 14,
                  }}
                >
                  {connectorProfiles.length === 0 && <option value="">— Sin perfiles —</option>}
                  {connectorProfiles.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => {
                    const np = newConnectorProfile(connectorProfiles.length + 1);
                    setConnectorProfiles((l) => [...l, np]);
                    setSettingsProfileId(np.id);
                    setSettingsTestMsg(null);
                    setSettingsSaveMsg(null);
                  }}
                  style={{
                    padding: "10px 14px",
                    borderRadius: 10,
                    border: `1px solid ${c.primary}`,
                    background: c.primary,
                    color: c.primaryFg,
                    cursor: "pointer",
                    fontWeight: 700,
                  }}
                >
                  Añadir nuevo
                </button>
              </div>

              {connectorProfiles.length === 0 && (
                <div style={{ fontSize: 13, color: c.muted, marginBottom: 8 }}>
                  Sin perfiles aún: pulsa «Añadir nuevo» para crear el primero.
                </div>
              )}

              {connectorProfiles.length > 0 && settingsProfileId && (
                <>
                  <div style={{ marginBottom: 14 }}>
                    <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                      Nombre del perfil
                    </label>
                    <input
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.name ?? ""
                      }
                      onChange={(e) =>
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, name: e.target.value } : p,
                          ),
                        )
                      }
                      style={{
                        width: "100%",
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: `1px solid ${c.inputBorder}`,
                        background: c.inputBg,
                        color: c.text,
                      }}
                    />
                  </div>

                  <div style={{ fontWeight: 800, margin: "14px 0 8px" }}>Jira</div>
                  <div style={{ display: "grid", gap: 10 }}>
                    <input
                      placeholder="URL de instancia"
                      autoComplete="off"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.jira.url ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, jira: { ...p.jira, url: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Usuario / Email"
                      type="email"
                      autoComplete="off"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.jira.email ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, jira: { ...p.jira, email: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="API token"
                      type="password"
                      autoComplete="new-password"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.jira.api_token ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, jira: { ...p.jira, api_token: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      const p = connectorProfiles.find((x) => x.id === settingsProfileId);
                      void (async () => {
                        setSettingsTestMsg(null);
                        try {
                          const r = await testEliaConnector({
                            kind: "jira",
                            jira: p?.jira ?? emptyJiraCreds(),
                            value_edge: p?.value_edge ?? emptyValueEdgeCreds(),
                          });
                          const data = r as { ok?: boolean; connection_ok?: boolean };
                          const okConn = data.connection_ok ?? data.ok ?? false;
                          setSettingsTestMsg(
                            okConn ? "Jira · conexión correcta." : "Jira · conexión rechazada o credenciales inválidas.",
                          );
                        } catch (err: unknown) {
                          setSettingsTestMsg(`Jira · ${String((err as Error)?.message ?? err)}`);
                        }
                      })();
                    }}
                    style={{
                      marginTop: 10,
                      padding: "8px 12px",
                      borderRadius: 10,
                      border: `1px solid ${c.btnGhostBorder}`,
                      background: c.btnGhostBg,
                      cursor: "pointer",
                    }}
                  >
                    Probar conexión · Jira
                  </button>

                  <div style={{ fontWeight: 800, margin: "14px 0 8px" }}>Value Edge</div>
                  <div style={{ display: "grid", gap: 10 }}>
                    <input
                      placeholder="URL de instancia"
                      autoComplete="off"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.value_edge.url ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId
                              ? { ...p, value_edge: { ...p.value_edge, url: v } }
                              : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Shared space ID"
                      autoComplete="off"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.value_edge.shared_space ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId
                              ? { ...p, value_edge: { ...p.value_edge, shared_space: v } }
                              : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Workspace ID"
                      autoComplete="off"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.value_edge.workspace ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId
                              ? { ...p, value_edge: { ...p.value_edge, workspace: v } }
                              : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder='Tech preview flag (ej. "true")'
                      autoComplete="off"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.value_edge
                          .tech_preview_flag ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId
                              ? { ...p, value_edge: { ...p.value_edge, tech_preview_flag: v } }
                              : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="URL de login (opcional)"
                      autoComplete="off"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.value_edge.login ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, value_edge: { ...p.value_edge, login: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Usuario"
                      autoComplete="off"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.value_edge.user ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, value_edge: { ...p.value_edge, user: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Contraseña"
                      type="password"
                      autoComplete="new-password"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.value_edge.password ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, value_edge: { ...p.value_edge, password: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      const p = connectorProfiles.find((x) => x.id === settingsProfileId);
                      void (async () => {
                        setSettingsTestMsg(null);
                        try {
                          const r = await testEliaConnector({
                            kind: "value_edge",
                            jira: p?.jira ?? emptyJiraCreds(),
                            value_edge: p?.value_edge ?? emptyValueEdgeCreds(),
                          });
                          const data = r as { ok?: boolean; connection_ok?: boolean };
                          const okConn = data.connection_ok ?? data.ok ?? false;
                          setSettingsTestMsg(
                            okConn ? "Value Edge · login correcto." : "Value Edge · login rechazado o credenciales inválidas.",
                          );
                        } catch (err: unknown) {
                          setSettingsTestMsg(`Value Edge · ${String((err as Error)?.message ?? err)}`);
                        }
                      })();
                    }}
                    style={{
                      marginTop: 10,
                      padding: "8px 12px",
                      borderRadius: 10,
                      border: `1px solid ${c.btnGhostBorder}`,
                      background: c.btnGhostBg,
                      cursor: "pointer",
                    }}
                  >
                    Probar conexión · Value Edge
                  </button>
                </>
              )}

              {settingsTestMsg && (
                <div
                  style={{
                    marginTop: 12,
                    fontSize: 13,
                    color: c.text,
                    background: c.hintBg,
                    border: `1px solid ${c.hintBorder}`,
                    borderRadius: 10,
                    padding: 10,
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {settingsTestMsg}
                </div>
              )}
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => {
                  void (async () => {
                    setSettingsSaveMsg(null);
                    try {
                      await persistConnectorProfiles(connectorProfiles);
                      setSettingsSaveMsg("Guardado en el navegador y en el backend (si está disponible).");
                    } catch (e: unknown) {
                      setSettingsSaveMsg(`Error al guardar: ${String((e as Error)?.message ?? e)}`);
                    }
                  })();
                }}
                style={{
                  padding: "10px 16px",
                  borderRadius: 10,
                  border: "none",
                  background: c.primary,
                  color: c.primaryFg,
                  fontWeight: 800,
                  cursor: "pointer",
                }}
              >
                Guardar
              </button>
            </div>
            {settingsSaveMsg && (
              <div style={{ marginTop: 10, fontSize: 13, color: c.muted }}>{settingsSaveMsg}</div>
            )}
          </div>
        </div>
      )}

      <div
        style={{
          position: "fixed",
          left: 10,
          bottom: 8,
          zIndex: 99998,
          fontSize: 11,
          fontFamily: "ui-monospace, monospace",
          color: c.muted,
          opacity: 0.85,
          pointerEvents: "none",
        }}
        aria-hidden
      >
        UI {ELIA_WEB_UI_BUILD}
      </div>

      <div style={{ maxWidth: 980, margin: "0 auto", padding: "20px" }}>
        {errorText && (
          <div
            style={{
              background: c.errorBg,
              border: `1px solid ${c.errorBorder}`,
              padding: 12,
              borderRadius: 10,
              marginBottom: 16,
            }}
          >
            <b style={{ color: c.errorTitle }}>Error</b>
            <div style={{ color: c.errorBody, marginTop: 6, whiteSpace: "pre-wrap" }}>{errorText}</div>
          </div>
        )}

        {isHomeSurface && initialChecked && (
          <div
            style={{
              background: c.surface,
              border: `1px solid ${c.border}`,
              borderRadius: 14,
              padding: 18,
              boxShadow: c.shadow,
            }}
          >
            <h2 style={{ margin: "0 0 10px 0", fontSize: 20, color: c.text }}>ELIA Web UI</h2>
            <div style={{ color: c.text, marginBottom: 14 }}>
              Pestaña principal: cada operación se abre en una <b>nueva pestaña</b> (avisos, prompts y resultado) sin cerrar
              esta vista. El tema se cambia con <b>Modo oscuro</b> / <b>Modo claro</b> en la barra superior.
            </div>

            <div
              style={{
                display: "flex",
                gap: 10,
                padding: 6,
                borderRadius: 12,
                border: `1px solid ${c.border}`,
                background: c.neutralBg,
                marginBottom: 14,
                flexWrap: "wrap",
              }}
            >
              <button
                type="button"
                onClick={() => setHomeTab("ui")}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  border: `1px solid ${homeTab === "ui" ? c.primary : c.btnGhostBorder}`,
                  background: homeTab === "ui" ? c.primary : c.btnGhostBg,
                  color: homeTab === "ui" ? c.primaryFg : c.text,
                  cursor: "pointer",
                  fontWeight: 700,
                }}
              >
                Automatización UI
              </button>
              <button
                type="button"
                onClick={() => setHomeTab("req")}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  border: `1px solid ${homeTab === "req" ? c.primary : c.btnGhostBorder}`,
                  background: homeTab === "req" ? c.primary : c.btnGhostBg,
                  color: homeTab === "req" ? c.primaryFg : c.text,
                  cursor: "pointer",
                  fontWeight: 700,
                }}
              >
                Inteligencia de Requerimientos
              </button>
            </div>

            {homeHint && (
              <div
                style={{
                  background: c.hintBg,
                  border: `1px solid ${c.hintBorder}`,
                  color: c.hintText,
                  padding: 12,
                  borderRadius: 10,
                  marginBottom: 14,
                  fontSize: 14,
                }}
              >
                {homeHint}
              </div>
            )}

            {license && (
              <div
                style={{
                  background: license.can_run_jobs ? c.licOkBg : c.licWarnBg,
                  border: `1px solid ${license.can_run_jobs ? c.licOkBorder : c.licWarnBorder}`,
                  color: c.text,
                  padding: 12,
                  borderRadius: 10,
                  marginBottom: 14,
                  fontSize: 14,
                }}
              >
                <div style={{ fontWeight: 700, marginBottom: 6 }}>Licencia</div>
                <div style={{ marginBottom: 8 }}>{license.message}</div>
                {!license.activated && (
                  <div style={{ fontSize: 12, color: c.muted, marginBottom: 8, wordBreak: "break-all" }}>
                    Huella (soporte): <code>{license.machine_fingerprint}</code>
                  </div>
                )}
                {!license.can_run_jobs && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
                    <input
                      type="password"
                      value={activationKey}
                      onChange={(e) => setActivationKey(e.target.value)}
                      placeholder="Clave de activación"
                      style={{
                        flex: "1 1 240px",
                        minWidth: 200,
                        padding: "8px 10px",
                        borderRadius: 8,
                        border: `1px solid ${c.inputBorder}`,
                        background: c.inputBg,
                        color: c.text,
                        fontSize: 14,
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => {
                        setActivationMsg(null);
                        void (async () => {
                          try {
                            const r = await activateLicense(activationKey);
                            if (r.ok) {
                              const l = await getLicenseStatus();
                              setLicense({
                                can_run_jobs: l.can_run_jobs,
                                message: l.message,
                                demo_days_left: l.demo_days_left,
                                activated: l.activated,
                                machine_fingerprint: l.machine_fingerprint,
                              });
                              setActivationKey("");
                              setActivationMsg("Activación correcta.");
                            } else {
                              setActivationMsg(r.message || "Clave no válida.");
                            }
                          } catch (e: any) {
                            setActivationMsg(String(e?.message ?? e));
                          }
                        })();
                      }}
                      style={{
                        padding: "8px 14px",
                        borderRadius: 8,
                        background: c.primary,
                        color: c.primaryFg,
                        border: "none",
                        cursor: "pointer",
                      }}
                    >
                      Activar
                    </button>
                  </div>
                )}
                {activationMsg && <div style={{ marginTop: 8, fontSize: 13 }}>{activationMsg}</div>}
              </div>
            )}

            {homeTab === "ui" && (
              <>
                <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 14, flexWrap: "wrap" }}>
                  <input
                    value={urlValue}
                    onChange={(e) => setUrlValue(e.target.value)}
                    placeholder="URL para grabar (solo para 'Grabar Interacciones')"
                    style={{
                      flex: "1 1 360px",
                      minWidth: 280,
                      padding: "10px 12px",
                      borderRadius: 10,
                      border: `1px solid ${c.inputBorder}`,
                      background: c.inputBg,
                      color: c.text,
                      outline: "none",
                      fontSize: 14,
                    }}
                  />
                </div>

                <label
                  style={{
                    display: "flex",
                    gap: 10,
                    alignItems: "flex-start",
                    marginBottom: 14,
                    cursor: "pointer",
                    fontSize: 14,
                    color: c.text,
                  }}
                >
                  <input
                    type="checkbox"
                    checked={useAi}
                    onChange={(e) => setUseAi(e.target.checked)}
                    style={{ marginTop: 3 }}
                  />
                  <span>
                    <b>Activar IA</b> (Gemma + llama.cpp) en «Convertir a Behave»: agrupación BDD y preferencia de localizadores si
                    hay archivo <code>_bee_meta.json</code> junto al .js grabado. Si no hay modelo o binario, se usa el modo
                    heurístico.
                    {aiStatusLine && (
                      <span style={{ display: "block", marginTop: 6, fontSize: 12, color: c.muted }}>{aiStatusLine}</span>
                    )}
                  </span>
                </label>

                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <button
                    disabled={license ? !license.can_run_jobs : false}
                    onClick={() => startJob("puppeteer_recorder")}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: license && !license.can_run_jobs ? c.buttonDisabledBg : c.primary,
                      color: c.primaryFg,
                      border: "none",
                      cursor: license && !license.can_run_jobs ? "not-allowed" : "pointer",
                    }}
                  >
                    Grabar Interacciones
                  </button>
                  <button
                    disabled={license ? !license.can_run_jobs : false}
                    onClick={() => startJob("puppeteer_to_behave")}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.btnGhostBg,
                      color: c.text,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: license && !license.can_run_jobs ? "not-allowed" : "pointer",
                      opacity: license && !license.can_run_jobs ? 0.5 : 1,
                    }}
                  >
                    Convertir a Behave
                  </button>
                  <button
                    disabled={license ? !license.can_run_jobs : false}
                    onClick={() => startJob("puppeteer_to_step_by_step")}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.btnGhostBg,
                      color: c.text,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: license && !license.can_run_jobs ? "not-allowed" : "pointer",
                      opacity: license && !license.can_run_jobs ? 0.5 : 1,
                    }}
                  >
                    Convertir a step by step
                  </button>
                </div>
              </>
            )}

            {homeTab === "req" && (
              <div
                style={{
                  background: c.neutralBg,
                  border: `1px solid ${c.border}`,
                  borderRadius: 14,
                  padding: 14,
                }}
              >
                <div style={{ fontWeight: 800, color: c.text, marginBottom: 6 }}>Inteligencia de Requerimientos</div>
                <div style={{ color: c.muted, fontSize: 13, marginBottom: 10 }}>
                  Selecciona un <b>perfil de conectores</b> (credenciales definidas en ⚙ Configuración). Cada trabajo usa
                  ese perfil sin leer <code>secrets.ini</code>.
                </div>
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 10,
                    alignItems: "center",
                    marginBottom: 12,
                  }}
                >
                  <label style={{ fontSize: 13, fontWeight: 600, color: c.text }}>Perfil activo</label>
                  <select
                    value={reqConnectorProfileId}
                    onChange={(e) => setReqConnectorProfileId(e.target.value)}
                    style={{
                      flex: "1 1 260px",
                      minWidth: 220,
                      padding: "10px 12px",
                      borderRadius: 10,
                      border: `1px solid ${c.inputBorder}`,
                      background: c.inputBg,
                      color: c.text,
                      fontSize: 14,
                    }}
                  >
                    {connectorProfiles.length === 0 ? (
                      <option value="">Sin perfiles — usa Configuración (⚙)</option>
                    ) : (
                      connectorProfiles.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))
                    )}
                  </select>
                </div>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <button
                    disabled={license ? !license.can_run_jobs : false}
                    onClick={() => startJob("elia_jira_smoke")}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.btnGhostBg,
                      color: c.text,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: license && !license.can_run_jobs ? "not-allowed" : "pointer",
                      opacity: license && !license.can_run_jobs ? 0.5 : 1,
                    }}
                  >
                    Conectar a Jira
                  </button>
                  <button
                    disabled={license ? !license.can_run_jobs : false}
                    onClick={() => startJob("elia_value_edge_smoke")}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.btnGhostBg,
                      color: c.text,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: license && !license.can_run_jobs ? "not-allowed" : "pointer",
                      opacity: license && !license.can_run_jobs ? 0.5 : 1,
                    }}
                  >
                    Extraer de ValueEdge
                  </button>
                  <button
                    disabled={license ? !license.can_run_jobs : false}
                    onClick={() => startJob("elia_gherkin_batch")}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.btnGhostBg,
                      color: c.text,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: license && !license.can_run_jobs ? "not-allowed" : "pointer",
                      opacity: license && !license.can_run_jobs ? 0.5 : 1,
                    }}
                  >
                    Procesar lote (.json → .feature)
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {!job && jobId && <div style={{ color: c.muted }}>Cargando...</div>}

        {!isHomeSurface && job && job.state === "running" && !activePrompt && (
          <div
            style={{
              background: c.processingBg,
              border: `1px solid ${c.processingBorder}`,
              color: c.processingText,
              padding: 12,
              borderRadius: 10,
              marginBottom: 16,
              fontSize: 14,
            }}
          >
            Procesando… (espera; esta pestaña no se cerrará sola).
          </div>
        )}

        {job && job.state === "running" && String(job.progress?.stage ?? "").includes("Ejecutando Puppeteer") && (
          <div
            style={{
              background: c.warnBg,
              border: `1px solid ${c.warnBorder}`,
              color: c.warnText,
              padding: 12,
              borderRadius: 10,
              marginBottom: 16,
              fontSize: 14,
            }}
          >
            Se está abriendo el <b>navegador de grabación</b>. En Windows intentamos pasarlo al primer plano; si sigues viendo
            solo ELIA, revisa la barra de tareas u otras ventanas de Chrome/Chromium.
          </div>
        )}

        {job?.error && (
          <div
            style={{
              background: c.errorBg,
              border: `1px solid ${c.errorBorder}`,
              padding: 12,
              borderRadius: 10,
              marginBottom: 16,
            }}
          >
            <b style={{ color: c.errorTitle }}>Job error</b>
            <div style={{ color: c.errorBody, marginTop: 6, whiteSpace: "pre-wrap" }}>
              {job.error.message}
              {job.error.details ? `\n${job.error.details}` : ""}
            </div>
          </div>
        )}

        {job?.state === "waiting_user" && activePrompt && (
          <div
            style={{
              background: c.surface,
              border: `1px solid ${c.border}`,
              borderRadius: 14,
              padding: 18,
              boxShadow: c.shadow,
            }}
          >
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
              <div style={{ fontSize: 13, color: c.muted }}>{formatPromptType(activePrompt.type)}</div>
              <div style={{ marginLeft: "auto", fontSize: 12, color: c.muted }}>job: {job.job_id.slice(0, 8)}...</div>
            </div>

            <h2 style={{ margin: "10px 0 6px", fontSize: 20, color: c.text }}>{activePrompt.title}</h2>
            {activePrompt.type !== "message_ack" && (
              <div style={{ color: c.text, marginBottom: 14 }}>{activePrompt.message}</div>
            )}

            {(activePrompt.type === "pick_project" || activePrompt.type === "pick_script") && (
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                {activePrompt.options.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={async () => {
                      if (!jobId) return;
                      await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: opt.value });
                    }}
                    style={{
                      padding: "10px 12px",
                      borderRadius: 10,
                      border: `1px solid ${c.btnGhostBorder}`,
                      background: c.btnGhostBg,
                      color: c.text,
                      cursor: "pointer",
                    }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}

            {activePrompt.type === "pick_actions" && activePrompt.actions && (
              <div>
                <div style={{ fontSize: 13, color: c.muted, marginBottom: 10 }}>
                  Marca las acciones a convertir
                </div>
                <div style={{ border: `1px solid ${c.border}`, borderRadius: 12, padding: 12, maxHeight: 320, overflow: "auto" }}>
                  <ActionsCheckboxList
                    c={c}
                    actions={activePrompt.actions}
                    onSubmit={async (selectedLines) => {
                      if (!jobId) return;
                      await sendPromptResponse({
                        jobId,
                        promptId: activePrompt.prompt_id,
                        answer: selectedLines,
                      });
                    }}
                  />
                </div>
              </div>
            )}

            {activePrompt.type === "yes_no" && (
              <div style={{ display: "flex", gap: 10 }}>
                <button
                  onClick={async () => {
                    if (!jobId) return;
                    await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: true });
                  }}
                  style={{
                    padding: "10px 14px",
                    borderRadius: 10,
                    background: c.primary,
                    color: c.primaryFg,
                    border: "none",
                    cursor: "pointer",
                  }}
                >
                  Sí
                </button>
                <button
                  onClick={async () => {
                    if (!jobId) return;
                    await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: false });
                  }}
                  style={{
                    padding: "10px 14px",
                    borderRadius: 10,
                    background: c.btnGhostBg,
                    color: c.text,
                    border: `1px solid ${c.btnGhostBorder}`,
                    cursor: "pointer",
                  }}
                >
                  No
                </button>
              </div>
            )}

            {activePrompt.type === "yes_no_cancel" && (
              <div style={{ display: "flex", gap: 10 }}>
                <button
                  onClick={async () => {
                    if (!jobId) return;
                    await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: true });
                  }}
                  style={{
                    padding: "10px 14px",
                    borderRadius: 10,
                    background: c.primary,
                    color: c.primaryFg,
                    border: "none",
                    cursor: "pointer",
                  }}
                >
                  Sí
                </button>
                <button
                  onClick={async () => {
                    if (!jobId) return;
                    await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: false });
                  }}
                  style={{
                    padding: "10px 14px",
                    borderRadius: 10,
                    background: c.btnGhostBg,
                    color: c.text,
                    border: `1px solid ${c.btnGhostBorder}`,
                    cursor: "pointer",
                  }}
                >
                  No
                </button>
                <button
                  onClick={async () => {
                    if (!jobId) return;
                    await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: null });
                  }}
                  style={{
                    padding: "10px 14px",
                    borderRadius: 10,
                    background: c.btnGhostBg,
                    color: c.muted,
                    border: `1px solid ${c.btnGhostBorder}`,
                    cursor: "pointer",
                  }}
                >
                  Cancelar
                </button>
              </div>
            )}

            {activePrompt.type === "bdd_preview" && activePrompt.payload && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ fontSize: 13, color: c.muted }}>
                  Intento {activePrompt.payload.attempt} de {activePrompt.payload.max_attempts}.{" "}
                  {activePrompt.payload.can_manual
                    ? "Puedes editar el escenario a mano o usar la versión heurística."
                    : "Revisa el texto; puedes aceptarlo o pedir otra versión con IA."}
                </div>
                {activePrompt.payload.script_excerpt?.trim() ? (
                  <div>
                    <div style={{ fontSize: 12, color: c.muted, marginBottom: 6 }}>Extracto del script (referencia)</div>
                    <textarea
                      readOnly
                      value={activePrompt.payload.script_excerpt}
                      style={{
                        width: "100%",
                        minHeight: 120,
                        padding: 10,
                        borderRadius: 10,
                        border: `1px solid ${c.border}`,
                        fontFamily: "ui-monospace, monospace",
                        fontSize: 12,
                        background: c.codeBg,
                        color: c.text,
                      }}
                    />
                  </div>
                ) : null}
                <div>
                  <div style={{ fontSize: 12, color: c.muted, marginBottom: 6 }}>Feature (.feature)</div>
                  <textarea
                    value={bddPreviewText}
                    onChange={(e) => setBddPreviewText(e.target.value)}
                    readOnly={!activePrompt.payload.can_manual}
                    style={{
                      width: "100%",
                      minHeight: 220,
                      padding: 10,
                      borderRadius: 10,
                      border: `1px solid ${c.inputBorder}`,
                      fontFamily: "ui-monospace, monospace",
                      fontSize: 13,
                      background: activePrompt.payload.can_manual ? c.inputBg : c.codeBg,
                      color: c.text,
                    }}
                  />
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                  <button
                    type="button"
                    onClick={async () => {
                      if (!jobId) return;
                      const orig = String(activePrompt.payload?.feature_text ?? "");
                      const edited = bddPreviewText.trim() !== orig.trim();
                      await sendPromptResponse({
                        jobId,
                        promptId: activePrompt.prompt_id,
                        answer: {
                          action: "accept",
                          feature_text: bddPreviewText,
                          edited,
                        },
                      });
                    }}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.primary,
                      color: c.primaryFg,
                      border: "none",
                      cursor: "pointer",
                    }}
                  >
                    {activePrompt.payload.can_manual ? "Aceptar escenario" : "Aceptar"}
                  </button>
                  {!activePrompt.payload.can_manual ? (
                    <button
                      type="button"
                      onClick={async () => {
                        if (!jobId) return;
                        await sendPromptResponse({
                          jobId,
                          promptId: activePrompt.prompt_id,
                          answer: { action: "reject" },
                        });
                      }}
                      style={{
                        padding: "10px 14px",
                        borderRadius: 10,
                        background: c.btnGhostBg,
                        color: c.text,
                        border: `1px solid ${c.btnGhostBorder}`,
                        cursor: "pointer",
                      }}
                    >
                      Rechazar (regenerar)
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={async () => {
                        if (!jobId) return;
                        await sendPromptResponse({
                          jobId,
                          promptId: activePrompt.prompt_id,
                          answer: { action: "use_heuristic" },
                        });
                      }}
                      style={{
                        padding: "10px 14px",
                        borderRadius: 10,
                        background: c.btnGhostBg,
                        color: c.text,
                        border: `1px solid ${c.btnGhostBorder}`,
                        cursor: "pointer",
                      }}
                    >
                      Usar generación heurística
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={async () => {
                      if (!jobId) return;
                      await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: null });
                    }}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.btnGhostBg,
                      color: c.muted,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: "pointer",
                    }}
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            )}

            {activePrompt.type === "message_ack" && (
              <div>
                <div
                  style={{
                    background:
                      activePrompt.severity === "error"
                        ? c.msgErrBg
                        : activePrompt.severity === "warning"
                          ? c.msgWarnBg
                          : c.msgInfoBg,
                    border:
                      activePrompt.severity === "error"
                        ? `1px solid ${c.msgErrBorder}`
                        : activePrompt.severity === "warning"
                          ? `1px solid ${c.msgWarnBorder}`
                          : `1px solid ${c.msgInfoBorder}`,
                    color:
                      activePrompt.severity === "error"
                        ? c.msgErrText
                        : activePrompt.severity === "warning"
                          ? c.msgWarnText
                          : c.msgInfoText,
                    padding: 12,
                    borderRadius: 10,
                    marginBottom: 14,
                    whiteSpace: "pre-wrap",
                    fontSize: 14,
                    maxHeight: "min(50vh, 360px)",
                    overflow: "auto",
                  }}
                >
                  {activePrompt.message}
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: 10,
                    flexWrap: "wrap",
                    marginTop: 4,
                    position: "sticky",
                    bottom: 0,
                    background: c.stickyBarBg,
                    paddingTop: 8,
                  }}
                >
                  <button
                    type="button"
                    onClick={async () => {
                      if (!jobId) return;
                      await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: true });
                    }}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.primary,
                      color: c.primaryFg,
                      border: "none",
                      cursor: "pointer",
                    }}
                  >
                    Aceptar
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      if (!jobId) return;
                      await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: true });
                    }}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.btnGhostBg,
                      color: c.text,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: "pointer",
                    }}
                  >
                    Cerrar
                  </button>
                </div>
              </div>
            )}

            {activePrompt.type === "input_text" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <input
                  value={textValue}
                  onChange={(e) => setTextValue(e.target.value)}
                  placeholder={activePrompt.message}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: `1px solid ${c.inputBorder}`,
                    background: c.inputBg,
                    color: c.text,
                    outline: "none",
                    fontSize: 14,
                  }}
                />
                <div style={{ display: "flex", gap: 10 }}>
                  <button
                    onClick={async () => {
                      if (!jobId) return;
                      const value = textValue.trim();
                      await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: value });
                    }}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.primary,
                      color: c.primaryFg,
                      border: "none",
                      cursor: "pointer",
                    }}
                  >
                    Guardar
                  </button>
                  <button
                    onClick={async () => {
                      if (!jobId) return;
                      await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: null });
                    }}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.btnGhostBg,
                      color: c.muted,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: "pointer",
                    }}
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {!isHomeSurface && job?.state === "done" && (
          <div
            style={{
              background: c.successBg,
              border: `1px solid ${c.successBorder}`,
              padding: 16,
              borderRadius: 14,
            }}
          >
            <b style={{ color: c.successTitle }}>Conversión finalizada</b>
            <div style={{ marginTop: 6, color: c.successBody, whiteSpace: "pre-wrap" }}>
              {job?.progress?.result_file ? `Archivo: ${job.progress.result_file}` : ""}
              {job?.progress?.video_path ? `\nVideo: ${job.progress.video_path}` : ""}
              {!job?.progress?.result_file && !job?.progress?.video_path ? "OK" : ""}
            </div>
            <div style={{ marginTop: 12, fontSize: 13, color: c.successHint }}>
              <b>Volver al inicio:</b> si abriste el flujo desde la pestaña de inicio, se cierra <b>esta</b> pestaña y se
              pone al frente la de inicio (no duplicas el inicio). Si abriste solo esta URL (p. ej. desde el escritorio),
              se abrirá otra vista de inicio en esta pestaña.
            </div>
            <div style={{ marginTop: 14, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
              <button
                type="button"
                title="Cierra esta pestaña de trabajo y enfoca la de inicio, si existe."
                onClick={() => {
                  if (!tryFocusOpenerAndCloseThisTab()) {
                    goHomeInThisTab();
                  }
                }}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: c.primary,
                  color: c.primaryFg,
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Volver al inicio
              </button>
            </div>
          </div>
        )}

        {!isHomeSurface && job?.state === "error" && (
          <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <button
              type="button"
              onClick={() => {
                if (!tryFocusOpenerAndCloseThisTab()) {
                  goHomeInThisTab();
                }
              }}
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                background: c.primary,
                color: c.primaryFg,
                border: "none",
                cursor: "pointer",
              }}
            >
              Volver al inicio
            </button>
          </div>
        )}

        {!isHomeSurface && job?.state === "cancelled" && (
          <div
            style={{
              background: c.neutralBg,
              border: `1px solid ${c.border}`,
              padding: 16,
              borderRadius: 14,
              marginTop: 8,
            }}
          >
            <b style={{ color: c.text }}>Operación cancelada</b>
            <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
              <button
                type="button"
                onClick={() => {
                  if (!tryFocusOpenerAndCloseThisTab()) {
                    goHomeInThisTab();
                  }
                }}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: c.primary,
                  color: c.primaryFg,
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Volver al inicio
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ActionsCheckboxList(props: {
  c: import("./eliaTheme").EliaPalette;
  actions: { type: string; description: string; original_line: string }[];
  onSubmit: (selectedLines: string[]) => void | Promise<void>;
}) {
  const { c } = props;
  const [selected, setSelected] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const next: Record<string, boolean> = {};
    for (const a of props.actions) next[a.original_line] = true;
    setSelected(next);
  }, [props.actions]);

  const selectedLines = useMemo(() => {
    return props.actions.filter((a) => selected[a.original_line]).map((a) => a.original_line);
  }, [props.actions, selected]);

  return (
    <div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {props.actions.map((a, idx) => (
          <label key={idx} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
            <input
              type="checkbox"
              checked={!!selected[a.original_line]}
              onChange={(e) => setSelected((prev) => ({ ...prev, [a.original_line]: e.target.checked }))}
              style={{ marginTop: 3 }}
            />
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: c.text }}>{a.type}</div>
              <div style={{ fontSize: 12, color: c.actionDesc }}>{a.description}</div>
            </div>
          </label>
        ))}
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 14, justifyContent: "flex-end" }}>
        <button
          onClick={() => setSelected((prev) => Object.fromEntries(Object.keys(prev).map((k) => [k, true])))}
          style={{
            padding: "8px 12px",
            borderRadius: 10,
            background: c.btnGhostBg,
            border: `1px solid ${c.btnGhostBorder}`,
            color: c.text,
            cursor: "pointer",
          }}
        >
          Incluir todas
        </button>
        <button
          onClick={() => setSelected((prev) => Object.fromEntries(Object.keys(prev).map((k) => [k, false])))}
          style={{
            padding: "8px 12px",
            borderRadius: 10,
            background: c.btnGhostBg,
            border: `1px solid ${c.btnGhostBorder}`,
            color: c.text,
            cursor: "pointer",
          }}
        >
          Excluir todas
        </button>
        <button
          onClick={async () => {
            await props.onSubmit(selectedLines);
          }}
          style={{
            padding: "8px 12px",
            borderRadius: 10,
            background: c.primary,
            color: c.primaryFg,
            border: "none",
            cursor: "pointer",
          }}
        >
          Continuar
        </button>
      </div>
    </div>
  );
}
