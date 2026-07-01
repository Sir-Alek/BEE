import React from "react";
import {
  getProjectAssetUrl,
  openProjectFile,
  openProjectFolder,
  type RunDiagnosticResponse,
} from "../api";
import { useAutoDismissHint } from "../hooks/useAutoDismissHint";

type Props = {
  c: Record<string, string>;
  platform: string;
  project: string;
  diagnostic: RunDiagnosticResponse;
};

export function RunDiagnosticPanel(props: Props) {
  const { c, platform, project, diagnostic } = props;
  const [folderHint, setFolderHint] = useAutoDismissHint();

  if (diagnostic.ok) return null;

  const failure = diagnostic.failures[0];
  const evidences = diagnostic.evidences ?? [];
  const reason =
    failure?.failure_reason || failure?.hook_error || failure?.step_error || null;
  const screenshot = failure?.primary_screenshot ?? failure?.screenshots?.[0];
  const screenshotUrl =
    screenshot?.path ? getProjectAssetUrl(platform, project, screenshot.path) : "";

  return (
    <div
      data-testid="elia-run-diagnostic"
      style={{
        marginTop: 12,
        padding: 12,
        borderRadius: 10,
        border: `1px solid ${c.errorBorder ?? "#c0392b"}`,
        background: c.errorBg ?? "rgba(192,57,43,0.06)",
      }}
    >
      <div style={{ fontWeight: 700, color: c.errorTitle ?? c.text, marginBottom: 8 }}>
        Diagnóstico de la ejecución
      </div>

      {failure ? (
        <div style={{ fontSize: 13, lineHeight: 1.5, color: c.text }}>
          <div>
            <strong>Escenario:</strong> {failure.scenario}
          </div>
          {failure.feature_file ? (
            <div>
              <strong>Feature:</strong> {failure.feature_file}
              {failure.feature_line ? `:${failure.feature_line}` : ""}
            </div>
          ) : null}
          {failure.failed_step ? (
            <div style={{ marginTop: 6 }}>
              <strong>Paso fallido:</strong> {failure.failed_step}
              {failure.exception_type ? (
                <span style={{ color: c.muted }}> ({failure.exception_type})</span>
              ) : null}
            </div>
          ) : null}
          {reason ? (
            <div style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>
              <strong>Motivo del fallo:</strong> {reason}
            </div>
          ) : (
            <div style={{ marginTop: 6, color: c.muted }}>
              No se pudo extraer un motivo concreto. Revisa la consola o el log del escenario.
            </div>
          )}
          {failure.hook_error && failure.hook_error !== reason ? (
            <div style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>
              <strong>Error de hook:</strong> {failure.hook_error}
            </div>
          ) : null}
          {failure.step_error && failure.step_error !== reason ? (
            <div style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>
              <strong>Error del paso:</strong> {failure.step_error}
            </div>
          ) : null}
          {failure.diagnostic_notes?.length ? (
            <div style={{ marginTop: 6, fontSize: 12, color: c.muted }}>
              <strong>Notas técnicas:</strong>{" "}
              {failure.diagnostic_notes[failure.diagnostic_notes.length - 1]}
            </div>
          ) : null}
          {failure.log_path ? (
            <div style={{ marginTop: 6 }}>
              <strong>Log del escenario:</strong>{" "}
              <code style={{ fontSize: 12 }}>{failure.log_path}</code>
              {!failure.log_exists ? (
                <span style={{ color: c.muted }}> (aún no generado)</span>
              ) : null}
            </div>
          ) : null}
          {screenshotUrl ? (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Captura del fallo</div>
              <a href={screenshotUrl} target="_blank" rel="noreferrer">
                <img
                  src={screenshotUrl}
                  alt={screenshot?.name ?? "Captura de fallo"}
                  style={{
                    maxWidth: "100%",
                    maxHeight: 180,
                    borderRadius: 8,
                    border: `1px solid ${c.border}`,
                  }}
                />
              </a>
            </div>
          ) : null}
        </div>
      ) : (
        <div style={{ fontSize: 13, color: c.muted }}>
          No se pudo identificar el escenario fallido. Revisa la consola y los logs del proyecto.
        </div>
      )}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
        {failure?.log_path && failure.log_exists ? (
          <button
            type="button"
            onClick={() => {
              void openProjectFile(platform, project, failure.log_path!).then((r) =>
                setFolderHint(
                  r.hint ?? "Si no ves la ventana del explorador, revísala en la barra de tareas.",
                ),
              );
            }}
            style={{
              padding: "6px 10px",
              borderRadius: 8,
              border: `1px solid ${c.primary}`,
              background: c.primary,
              color: c.primaryFg,
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            Abrir log del escenario
          </button>
        ) : (
          <button
            type="button"
            onClick={() => {
              void openProjectFolder(platform, project, "outputs/logs").then((r) =>
                setFolderHint(
                  r.hint ?? "Si no ves la ventana del explorador, revísala en la barra de tareas.",
                ),
              );
            }}
            style={{
              padding: "6px 10px",
              borderRadius: 8,
              border: `1px solid ${c.btnGhostBorder}`,
              background: c.btnGhostBg,
              color: c.text,
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            Abrir carpeta logs
          </button>
        )}
        {evidences.length > 0 ? (
          <button
            type="button"
            onClick={() => {
              void openProjectFolder(platform, project, "outputs/evidences").then((r) =>
                setFolderHint(
                  r.hint ?? "Si no ves la ventana del explorador, revísala en la barra de tareas.",
                ),
              );
            }}
            style={{
              padding: "6px 10px",
              borderRadius: 8,
              border: `1px solid ${c.btnGhostBorder}`,
              background: c.btnGhostBg,
              color: c.text,
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            Abrir evidencias
          </button>
        ) : null}
      </div>

      {folderHint ? (
        <div style={{ fontSize: 12, color: c.muted, marginTop: 8 }}>{folderHint}</div>
      ) : null}
    </div>
  );
}
