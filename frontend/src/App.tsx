import React, { useEffect, useMemo, useState } from "react";
import { getJob, sendPromptResponse, startConvertJob } from "./api";
import type { ActivePrompt } from "./types";

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
  return mode;
}

/**
 * Open job flow in a NEW tab without ever navigating the current (home) tab.
 *
 * Important: `window.open(url)` must NOT run after `await` — Chrome treats that as
 * a non-user gesture and may reuse the current tab. We open `about:blank` synchronously
 * on click, then assign the job URL after the API returns.
 */
function openJobUrlInNewTabPrepared(): Window | null {
  return window.open("about:blank", "_blank");
}

const BEE_UI_BC = "bee-ui";

function goHomeInThisTab(): void {
  window.location.assign(`${window.location.origin}/`);
}

/** Si la pestaña de trabajo fue abierta desde inicio (hay opener), enfoca inicio y cierra esta pestaña — evita duplicar inicio. */
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
  /** Pinned from first paint: home URL has no job_id; avoids any edge case mixing job UI into home. */
  const [isHomeSurface] = useState(() => !new URLSearchParams(window.location.search).get("job_id"));

  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [polling, setPolling] = useState<boolean>(false);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [textValue, setTextValue] = useState<string>("");
  const [urlValue, setUrlValue] = useState<string>("");
  const [initialChecked, setInitialChecked] = useState<boolean>(false);
  /** Label parsed from ?mode= on job workspace tabs */
  const [workspaceMode, setWorkspaceMode] = useState<string | null>(null);
  const [homeHint, setHomeHint] = useState<string | null>(null);

  const activePrompt = (job?.active_prompt ?? null) as ActivePrompt | null;

  const startJob = (mode: "puppeteer_recorder" | "puppeteer_to_behave" | "puppeteer_to_step_by_step") => {
    setErrorText(null);
    setHomeHint(null);
    if (mode === "puppeteer_recorder" && !urlValue.trim()) {
      setErrorText("URL requerida para 'Grabar Interacciones'.");
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
        const res = await startConvertJob({
          mode,
          url: mode === "puppeteer_recorder" ? urlValue.trim() : undefined,
        });
        const base = `${window.location.origin}${window.location.pathname}`;
        const jobUrl = `${base}?job_id=${encodeURIComponent(res.job_id)}&mode=${encodeURIComponent(mode)}`;
        try {
          newTab.location.replace(jobUrl);
        } catch {
          newTab.location.href = jobUrl;
        }
        // Mantener window.opener para que "Volver al inicio" pueda enfocar inicio y cerrar esta pestaña sin duplicar.
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
    // Reset text input when prompt changes.
    if (activePrompt?.type === "input_text") {
      setTextValue("");
    }
  }, [activePrompt?.prompt_id, activePrompt?.type]);

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

  /** Inicio: quitar el aviso azul cuando el flujo termina en la otra pestaña (BroadcastChannel) o tras un tiempo. */
  useEffect(() => {
    if (!isHomeSurface) return;
    let bc: BroadcastChannel | null = null;
    try {
      bc = new BroadcastChannel(BEE_UI_BC);
      bc.onmessage = (ev: MessageEvent) => {
        if (ev.data?.type === "bee_job_finished") {
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

  /** Pestaña de trabajo: avisar a inicio una sola vez cuando el job llega a estado terminal. */
  useEffect(() => {
    if (isHomeSurface || !jobId || !job) return;
    const s = job.state;
    if (s !== "done" && s !== "error" && s !== "cancelled") return;
    try {
      const key = `bee_job_finished_broadcast:${jobId}`;
      if (sessionStorage.getItem(key)) return;
      sessionStorage.setItem(key, "1");
      const bc = new BroadcastChannel(BEE_UI_BC);
      bc.postMessage({ type: "bee_job_finished", job_id: jobId });
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
    const sub =
      !isHome && workspaceMode ? `${formatJobMode(workspaceMode)} · ` : "";

    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "16px 18px",
          borderBottom: "1px solid #e5e7eb",
          background: "#ffffff",
        }}
      >
        <img
          src="/logo.png"
          alt="BEE"
          style={{
            width: 42,
            height: 42,
            borderRadius: 12,
            objectFit: "contain",
            background: "transparent",
          }}
        />
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 16, fontWeight: 700 }}>BEE</div>
          <div style={{ fontSize: 12, color: "#6b7280" }}>
            {isHome ? "Local Web UI — inicio" : sub + "ventana de trabajo"}
          </div>
        </div>
        <div style={{ marginLeft: "auto", fontSize: 12, color: "#6b7280", textAlign: "right" }}>{statusLine}</div>
      </div>
    );
  }, [job, jobId, workspaceMode, isHomeSurface]);

  return (
    <div style={{ fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial", background: "#f9fafb", minHeight: "100vh" }}>
      {header}

      <div style={{ maxWidth: 980, margin: "0 auto", padding: "20px" }}>
        {errorText && (
          <div style={{ background: "#fef2f2", border: "1px solid #fecaca", padding: 12, borderRadius: 10, marginBottom: 16 }}>
            <b style={{ color: "#b91c1c" }}>Error</b>
            <div style={{ color: "#991b1b", marginTop: 6, whiteSpace: "pre-wrap" }}>{errorText}</div>
          </div>
        )}

        {isHomeSurface && initialChecked && (
          <div
            style={{
              background: "#ffffff",
              border: "1px solid #e5e7eb",
              borderRadius: 14,
              padding: 18,
              boxShadow: "0 1px 2px rgba(0,0,0,0.03)",
            }}
          >
            <h2 style={{ margin: "4px 0 10px", fontSize: 20 }}>BEE Web UI</h2>
            <div style={{ color: "#374151", marginBottom: 14 }}>
              Pestaña principal: cada operación se abre en una <b>nueva pestaña</b> (avisos, prompts y resultado) sin cerrar
              esta vista.
            </div>

            {homeHint && (
              <div
                style={{
                  background: "#eff6ff",
                  border: "1px solid #bfdbfe",
                  color: "#1e3a8a",
                  padding: 12,
                  borderRadius: 10,
                  marginBottom: 14,
                  fontSize: 14,
                }}
              >
                {homeHint}
              </div>
            )}

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
                  border: "1px solid #d1d5db",
                  outline: "none",
                  fontSize: 14,
                }}
              />
            </div>

            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button
                onClick={() => startJob("puppeteer_recorder")}
                style={{ padding: "10px 14px", borderRadius: 10, background: "#0ea5e9", color: "white", border: "none", cursor: "pointer" }}
              >
                Grabar Interacciones
              </button>
              <button
                onClick={() => startJob("puppeteer_to_behave")}
                style={{ padding: "10px 14px", borderRadius: 10, background: "#fff", color: "#111827", border: "1px solid #d1d5db", cursor: "pointer" }}
              >
                Convertir a Behave
              </button>
              <button
                onClick={() => startJob("puppeteer_to_step_by_step")}
                style={{ padding: "10px 14px", borderRadius: 10, background: "#fff", color: "#111827", border: "1px solid #d1d5db", cursor: "pointer" }}
              >
                Convertir a step by step
              </button>
            </div>
          </div>
        )}

        {!job && jobId && <div>Cargando...</div>}

        {!isHomeSurface && job && job.state === "running" && !activePrompt && (
          <div
            style={{
              background: "#f3f4f6",
              border: "1px solid #e5e7eb",
              color: "#374151",
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
              background: "#fffbeb",
              border: "1px solid #fde68a",
              color: "#92400e",
              padding: 12,
              borderRadius: 10,
              marginBottom: 16,
              fontSize: 14,
            }}
          >
            Se está abriendo el <b>navegador de grabación</b>. En Windows intentamos pasarlo al primer plano; si sigues viendo
            solo BEE, revisa la barra de tareas u otras ventanas de Chrome/Chromium.
          </div>
        )}

        {job?.error && (
          <div style={{ background: "#fef2f2", border: "1px solid #fecaca", padding: 12, borderRadius: 10, marginBottom: 16 }}>
            <b style={{ color: "#b91c1c" }}>Job error</b>
            <div style={{ color: "#991b1b", marginTop: 6, whiteSpace: "pre-wrap" }}>
              {job.error.message}
              {job.error.details ? `\n${job.error.details}` : ""}
            </div>
          </div>
        )}

        {job?.state === "waiting_user" && activePrompt && (
          <div
            style={{
              background: "#ffffff",
              border: "1px solid #e5e7eb",
              borderRadius: 14,
              padding: 18,
              boxShadow: "0 1px 2px rgba(0,0,0,0.03)",
            }}
          >
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
              <div style={{ fontSize: 13, color: "#6b7280" }}>{formatPromptType(activePrompt.type)}</div>
              <div style={{ marginLeft: "auto", fontSize: 12, color: "#6b7280" }}>job: {job.job_id.slice(0, 8)}...</div>
            </div>

            <h2 style={{ margin: "10px 0 6px", fontSize: 20 }}>{activePrompt.title}</h2>
            {activePrompt.type !== "message_ack" && (
              <div style={{ color: "#374151", marginBottom: 14 }}>{activePrompt.message}</div>
            )}

            {/* pick_project + pick_script */}
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
                      border: "1px solid #d1d5db",
                      background: "#fff",
                      cursor: "pointer",
                    }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}

            {/* pick_actions */}
            {activePrompt.type === "pick_actions" && activePrompt.actions && (
              <div>
                <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 10 }}>
                  Marca las acciones a convertir
                </div>
                <div style={{ border: "1px solid #e5e7eb", borderRadius: 12, padding: 12, maxHeight: 320, overflow: "auto" }}>
                  <ActionsCheckboxList
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
                  style={{ padding: "10px 14px", borderRadius: 10, background: "#0ea5e9", color: "white", border: "none", cursor: "pointer" }}
                >
                  Sí
                </button>
                <button
                  onClick={async () => {
                    if (!jobId) return;
                    await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: false });
                  }}
                  style={{ padding: "10px 14px", borderRadius: 10, background: "#fff", color: "#111827", border: "1px solid #d1d5db", cursor: "pointer" }}
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
                  style={{ padding: "10px 14px", borderRadius: 10, background: "#0ea5e9", color: "white", border: "none", cursor: "pointer" }}
                >
                  Sí
                </button>
                <button
                  onClick={async () => {
                    if (!jobId) return;
                    await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: false });
                  }}
                  style={{ padding: "10px 14px", borderRadius: 10, background: "#fff", color: "#111827", border: "1px solid #d1d5db", cursor: "pointer" }}
                >
                  No
                </button>
                <button
                  onClick={async () => {
                    if (!jobId) return;
                    await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: null });
                  }}
                  style={{ padding: "10px 14px", borderRadius: 10, background: "#fff", color: "#6b7280", border: "1px solid #d1d5db", cursor: "pointer" }}
                >
                  Cancelar
                </button>
              </div>
            )}

            {activePrompt.type === "message_ack" && (
              <div>
                <div
                  style={{
                    background:
                      activePrompt.severity === "error"
                        ? "#fef2f2"
                        : activePrompt.severity === "warning"
                          ? "#fffbeb"
                          : "#eff6ff",
                    border:
                      activePrompt.severity === "error"
                        ? "1px solid #fecaca"
                        : activePrompt.severity === "warning"
                          ? "1px solid #fde68a"
                          : "1px solid #bfdbfe",
                    color: activePrompt.severity === "error" ? "#991b1b" : activePrompt.severity === "warning" ? "#92400e" : "#1e3a8a",
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
                    background: "#ffffff",
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
                      background: "#0ea5e9",
                      color: "white",
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
                      background: "#fff",
                      color: "#111827",
                      border: "1px solid #d1d5db",
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
                    border: "1px solid #d1d5db",
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
                      background: "#0ea5e9",
                      color: "white",
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
                      background: "#fff",
                      color: "#6b7280",
                      border: "1px solid #d1d5db",
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
              background: "#ecfdf5",
              border: "1px solid #bbf7d0",
              padding: 16,
              borderRadius: 14,
            }}
          >
            <b style={{ color: "#166534" }}>Conversión finalizada</b>
            <div style={{ marginTop: 6, color: "#065f46", whiteSpace: "pre-wrap" }}>
              {job?.progress?.result_file ? `Archivo: ${job.progress.result_file}` : ""}
              {job?.progress?.video_path ? `\nVideo: ${job.progress.video_path}` : ""}
              {!job?.progress?.result_file && !job?.progress?.video_path ? "OK" : ""}
            </div>
            <div style={{ marginTop: 12, fontSize: 13, color: "#047857" }}>
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
                  background: "#0ea5e9",
                  color: "white",
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
                background: "#0ea5e9",
                color: "white",
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
              background: "#f9fafb",
              border: "1px solid #e5e7eb",
              padding: 16,
              borderRadius: 14,
              marginTop: 8,
            }}
          >
            <b style={{ color: "#374151" }}>Operación cancelada</b>
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
                  background: "#0ea5e9",
                  color: "white",
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
  actions: { type: string; description: string; original_line: string }[];
  onSubmit: (selectedLines: string[]) => void | Promise<void>;
}) {
  const [selected, setSelected] = useState<Record<string, boolean>>({});

  useEffect(() => {
    // Reset when actions change
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
              <div style={{ fontSize: 13, fontWeight: 600 }}>{a.type}</div>
              <div style={{ fontSize: 12, color: "#4b5563" }}>{a.description}</div>
            </div>
          </label>
        ))}
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 14, justifyContent: "flex-end" }}>
        <button
          onClick={() => setSelected((prev) => Object.fromEntries(Object.keys(prev).map((k) => [k, true])))}
          style={{ padding: "8px 12px", borderRadius: 10, background: "#fff", border: "1px solid #d1d5db", cursor: "pointer" }}
        >
          Incluir todas
        </button>
        <button
          onClick={() => setSelected((prev) => Object.fromEntries(Object.keys(prev).map((k) => [k, false])))}
          style={{ padding: "8px 12px", borderRadius: 10, background: "#fff", border: "1px solid #d1d5db", cursor: "pointer" }}
        >
          Excluir todas
        </button>
        <button
          onClick={async () => {
            await props.onSubmit(selectedLines);
          }}
          style={{ padding: "8px 12px", borderRadius: 10, background: "#0ea5e9", color: "white", border: "none", cursor: "pointer" }}
        >
          Continuar
        </button>
      </div>
    </div>
  );
}

