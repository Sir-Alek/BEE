import React, { useEffect, useMemo, useState } from "react";
import { getJob, sendPromptResponse, startConvertJob } from "./api";
import type { ActivePrompt } from "./types";

type JobStatus = {
  job_id: string;
  state: string;
  active_prompt: ActivePrompt | null;
  error: null | { message: string; details?: string };
};

function formatPromptType(t: string): string {
  return t.replaceAll("_", " ");
}

export default function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [polling, setPolling] = useState<boolean>(false);
  const [errorText, setErrorText] = useState<string | null>(null);

  const activePrompt = (job?.active_prompt ?? null) as ActivePrompt | null;

  useEffect(() => {
    // Demo: start job automatically for quick integration smoke tests.
    (async () => {
      try {
        setErrorText(null);
        const res = await startConvertJob("demo");
        setJobId(res.job_id);
        setPolling(true);
      } catch (e: any) {
        setErrorText(String(e?.message ?? e));
      }
    })();
  }, []);

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
        <div style={{ width: 42, height: 42, borderRadius: 12, background: "#0ea5e9" }} />
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 16, fontWeight: 700 }}>BEE</div>
          <div style={{ fontSize: 12, color: "#6b7280" }}>Local Web UI</div>
        </div>
        <div style={{ marginLeft: "auto", fontSize: 12, color: "#6b7280" }}>
          {job ? `Estado: ${job.state}` : "Estado: ..."}
        </div>
      </div>
    );
  }, [job]);

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

        {!job && <div>Cargando...</div>}

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
            <div style={{ color: "#374151", marginBottom: 14 }}>{activePrompt.message}</div>

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
          </div>
        )}

        {job?.state === "done" && (
          <div
            style={{
              background: "#ecfdf5",
              border: "1px solid #bbf7d0",
              padding: 16,
              borderRadius: 14,
            }}
          >
            <b style={{ color: "#166534" }}>Conversión finalizada</b>
            <div style={{ marginTop: 6, color: "#065f46" }}>
              Ya puedes integrar descarga de artifacts cuando tengamos el wiring de archivos.
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

