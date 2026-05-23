import React from "react";
import { PROMPT_ANSWER_BACK, sendPromptResponse, stopRecording } from "../api";
import { formatPromptType, goHomeInThisTab, tryFocusOpenerAndCloseThisTab } from "../app/utils";
import { JobEventTimeline } from "./JobEventTimeline";
import type { JobEvent } from "./jobEvents";
import { ActionsCheckboxList, GeneratedFilesResultView } from "./jobUiComponents";
import type { JobProgressState } from "./useJobProgress";
import type { ActivePrompt } from "../types";
import { promptAllowsBack } from "../types";

export type JobWorkspaceProps = {
  c: Record<string, string>;
  jobId: string | null;
  job: JobProgressState | null;
  jobEvents: JobEvent[];
  activePrompt: ActivePrompt | null;
  stoppingRecording: boolean;
  setStoppingRecording: (v: boolean) => void;
  setErrorText: (v: string | null) => void;
  textValue: string;
  setTextValue: (v: string) => void;
  bddPreviewText: string;
  setBddPreviewText: (v: string) => void;
};

export function JobWorkspace(props: JobWorkspaceProps) {
  const {
    c, jobId, job, jobEvents, activePrompt, stoppingRecording, setStoppingRecording,
    setErrorText, textValue, setTextValue, bddPreviewText, setBddPreviewText,
  } = props;

  return (
    <>
        {!job && jobId && <div style={{ color: c.muted }}>Cargando...</div>}

        {job && job.state === "running" && !activePrompt && (
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
            <div>
              {job.progress?.stage
                ? String(job.progress.stage)
                : "Procesando… (espera; esta pestaña no se cerrará sola)."}
            </div>
            {job.progress?.events_captured != null && (
              <div style={{ marginTop: 8, fontSize: 13 }}>
                Pantallas / eventos capturados: <b>{String(job.progress.events_captured)}</b>
                {job.progress?.elapsed_s != null ? ` · ${String(job.progress.elapsed_s)}s` : ""}
              </div>
            )}
            {Boolean(job.progress?.recording) && (
                <div style={{ marginTop: 12 }}>
                  <button
                    type="button"
                    disabled={stoppingRecording}
                    onClick={() => {
                      if (!jobId) return;
                      setStoppingRecording(true);
                      void stopRecording(jobId)
                        .catch((e: unknown) => {
                          setErrorText(String((e as Error)?.message ?? e));
                        })
                        .finally(() => setStoppingRecording(false));
                    }}
                    style={{
                      padding: "10px 16px",
                      borderRadius: 10,
                      background: c.primary,
                      color: c.primaryFg,
                      border: "none",
                      cursor: stoppingRecording ? "wait" : "pointer",
                      fontWeight: 600,
                    }}
                  >
                    {stoppingRecording ? "Finalizando…" : "Finalizar grabación"}
                  </button>
                </div>
              )}
            <JobEventTimeline
              events={jobEvents}
              c={c}
              recordingOnly={Boolean(job.progress?.recording)}
            />
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
            data-testid="elia-job-prompt"
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

            {activePrompt.type === "pick_conversion_mode" && activePrompt.options && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {(activePrompt.options as { value: string; label: string }[]).map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={async () => {
                      if (!jobId) return;
                      await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: opt.value });
                    }}
                    style={{
                      padding: "12px 14px",
                      borderRadius: 10,
                      background: c.btnGhostBg,
                      color: c.text,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: "pointer",
                      textAlign: "left",
                    }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}

            {(activePrompt.type === "pick_project" || activePrompt.type === "pick_script") && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  {(activePrompt.options as { value: string; label: string }[]).map((opt) => (
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
                {promptAllowsBack(activePrompt.payload) && (
                  <button
                    type="button"
                    onClick={async () => {
                      if (!jobId) return;
                      await sendPromptResponse({
                        jobId,
                        promptId: activePrompt.prompt_id,
                        answer: PROMPT_ANSWER_BACK,
                      });
                    }}
                    style={{
                      alignSelf: "flex-start",
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.btnGhostBg,
                      color: c.text,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: "pointer",
                    }}
                  >
                    Regresar
                  </button>
                )}
              </div>
            )}

            {activePrompt.type === "pick_scripts_multi" && activePrompt.actions && (
              <div>
                <div style={{ fontSize: 12, color: c.muted, marginBottom: 8 }}>
                  Marca al menos 2 grabaciones y pulsa Continuar.
                </div>
                <div style={{ border: `1px solid ${c.border}`, borderRadius: 12, padding: 12, maxHeight: 320, overflow: "auto" }}>
                  <ActionsCheckboxList
                    c={c}
                    promptId={activePrompt.prompt_id}
                    actions={activePrompt.actions}
                    minSelected={2}
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

            {activePrompt.type === "pick_actions" && activePrompt.actions && (
              <div>
                <div style={{ fontSize: 13, color: c.muted, marginBottom: 10 }}>
                  Marca las acciones a convertir
                </div>
                <div style={{ border: `1px solid ${c.border}`, borderRadius: 12, padding: 12, maxHeight: 320, overflow: "auto" }}>
                  <ActionsCheckboxList
                    c={c}
                    promptId={activePrompt.prompt_id}
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

            {activePrompt.type === "bdd_preview" && (() => {
              const ap = activePrompt as Extract<ActivePrompt, { type: "bdd_preview" }>;
              if (!ap.payload) return null;
              return (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ fontSize: 13, color: c.muted }}>
                  Intento {ap.payload.attempt} de {ap.payload.max_attempts}.{" "}
                  {ap.payload.can_manual
                    ? "Puedes editar el escenario a mano o usar la versión heurística."
                    : "Revisa el texto; puedes aceptarlo o pedir otra versión con IA."}
                </div>
                {ap.payload.script_excerpt?.trim() ? (
                  <div>
                    <div style={{ fontSize: 12, color: c.muted, marginBottom: 6 }}>Extracto del script (referencia)</div>
                    <textarea
                      readOnly
                      value={ap.payload.script_excerpt}
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
                    readOnly={!ap.payload.can_manual}
                    style={{
                      width: "100%",
                      minHeight: 220,
                      padding: 10,
                      borderRadius: 10,
                      border: `1px solid ${c.inputBorder}`,
                      fontFamily: "ui-monospace, monospace",
                      fontSize: 13,
                      background: ap.payload.can_manual ? c.inputBg : c.codeBg,
                      color: c.text,
                    }}
                  />
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                  <button
                    type="button"
                    onClick={async () => {
                      if (!jobId) return;
                      const orig = String(ap.payload?.feature_text ?? "");
                      const edited = bddPreviewText.trim() !== orig.trim();
                      await sendPromptResponse({
                        jobId,
                        promptId: ap.prompt_id,
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
                    {ap.payload.can_manual ? "Aceptar escenario" : "Aceptar"}
                  </button>
                  {!ap.payload.can_manual ? (
                    <button
                      type="button"
                      onClick={async () => {
                        if (!jobId) return;
                        await sendPromptResponse({
                          jobId,
                          promptId: ap.prompt_id,
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
                          promptId: ap.prompt_id,
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
                      await sendPromptResponse({ jobId, promptId: ap.prompt_id, answer: null });
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
              );
            })()}

            {activePrompt.type === "grouped_feature_review" && (() => {
              const ap = activePrompt as {
                prompt_id: string;
                payload?: {
                  feature_text?: string;
                  script_names?: string[];
                  background_count?: number;
                };
              };
              if (!ap.payload) return null;
              const names = ap.payload.script_names ?? [];
              const bg = ap.payload.background_count ?? 0;
              return (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div style={{ fontSize: 13, color: c.muted }}>
                    Grabaciones: {names.join(", ") || "—"}
                    {bg > 0 ? ` · Background: ${bg} paso(s)` : ""}
                  </div>
                  <textarea
                    value={bddPreviewText}
                    onChange={(e) => setBddPreviewText(e.target.value)}
                    style={{
                      width: "100%",
                      minHeight: 280,
                      padding: 10,
                      borderRadius: 10,
                      border: `1px solid ${c.inputBorder}`,
                      fontFamily: "ui-monospace, monospace",
                      fontSize: 13,
                      background: c.inputBg,
                      color: c.text,
                    }}
                  />
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                    <button
                      type="button"
                      onClick={async () => {
                        if (!jobId) return;
                        await sendPromptResponse({
                          jobId,
                          promptId: ap.prompt_id,
                          answer: { action: "accept", feature_text: bddPreviewText },
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
                      Aceptar y generar
                    </button>
                    <button
                      type="button"
                      onClick={async () => {
                        if (!jobId) return;
                        await sendPromptResponse({ jobId, promptId: ap.prompt_id, answer: null });
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
              );
            })()}

            {activePrompt.type === "message_ack" && (() => {
              const ap = activePrompt as Extract<ActivePrompt, { type: "message_ack" }>;
              const resultPayload = ap.payload ?? null;
              const hasFiles =
                Boolean(resultPayload?.generated_files?.length) ||
                Boolean(resultPayload?.output_dir || resultPayload?.project_dir);
              return (
              <div>
                {hasFiles ? (
                  <GeneratedFilesResultView
                    message={ap.message}
                    payload={resultPayload}
                    progress={job?.progress}
                    c={c}
                  />
                ) : (
                <div
                  style={{
                    background:
                      ap.severity === "error"
                        ? c.msgErrBg
                        : ap.severity === "warning"
                          ? c.msgWarnBg
                          : c.msgInfoBg,
                    border:
                      ap.severity === "error"
                        ? `1px solid ${c.msgErrBorder}`
                        : ap.severity === "warning"
                          ? `1px solid ${c.msgWarnBorder}`
                          : `1px solid ${c.msgInfoBorder}`,
                    color:
                      ap.severity === "error"
                        ? c.msgErrText
                        : ap.severity === "warning"
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
                  {ap.message}
                </div>
                )}
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
                      await sendPromptResponse({ jobId, promptId: ap.prompt_id, answer: true });
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
                      await sendPromptResponse({ jobId, promptId: ap.prompt_id, answer: true });
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
              );
            })()}

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
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
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
                  {promptAllowsBack(activePrompt.payload) && (
                    <button
                      type="button"
                      onClick={async () => {
                        if (!jobId) return;
                        await sendPromptResponse({
                          jobId,
                          promptId: activePrompt.prompt_id,
                          answer: PROMPT_ANSWER_BACK,
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
                      Regresar
                    </button>
                  )}
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

        {job?.state === "done" && (
          <div
            data-testid="elia-job-done"
            style={{
              background: c.successBg,
              border: `1px solid ${c.successBorder}`,
              padding: 16,
              borderRadius: 14,
            }}
          >
            <b style={{ color: c.successTitle }}>Conversión finalizada</b>
            <div style={{ marginTop: 10 }}>
              <GeneratedFilesResultView progress={job.progress} c={c} />
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

        {job?.state === "error" && (
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

        {job?.state === "cancelled" && (
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

    </>
  );
}
