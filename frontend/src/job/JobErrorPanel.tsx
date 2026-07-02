import React, { useState } from "react";
import { downloadJobErrorReport, openEliaLogsFolder } from "../api";
import { returnToHomeFromJobTab } from "../app/homeNavigation";
import { FOLDER_OPEN_HINT } from "../app/folderOpenHint";
import { useAutoDismissHint } from "../hooks/useAutoDismissHint";
import { BetaFeedbackLink } from "../components/BetaFeedbackLink";
import { InlineActionHint } from "../components/InlineActionHint";
// Versión comercial (≥1.0): descomentar y usar en lugar de BetaFeedbackLink (ver bloque JSX abajo).
// import { SupportContactLink } from "../components/SupportContactLink";

type Props = {
  c: Record<string, string>;
  jobId: string;
  errorMessage: string;
  betaFeedbackUrl?: string | null;
  /** Versión comercial: pasar aboutInfo?.support_email desde App.tsx → JobWorkspace */
  // supportEmail?: string | null;
  onDownloadError?: (message: string | null) => void;
};

export function JobErrorPanel(props: Props) {
  const { c, jobId, errorMessage, betaFeedbackUrl, onDownloadError } = props;
  const [downloading, setDownloading] = useState(false);
  const [logsFolderHint, setLogsFolderHint] = useAutoDismissHint();

  const handleDownload = () => {
    setDownloading(true);
    onDownloadError?.(null);
    void downloadJobErrorReport(jobId)
      .catch((e: unknown) => {
        onDownloadError?.(String((e as Error)?.message ?? e));
      })
      .finally(() => setDownloading(false));
  };

  return (
    <>
      <div
        style={{
          background: c.errorBg,
          border: `1px solid ${c.errorBorder}`,
          padding: 12,
          borderRadius: 10,
          marginBottom: 16,
        }}
      >
        <b style={{ color: c.errorTitle }}>Error en el trabajo</b>
        <div style={{ color: c.errorBody, marginTop: 6, whiteSpace: "pre-wrap" }}>{errorMessage}</div>
        <div style={{ marginTop: 12, fontSize: 13, color: c.muted, lineHeight: 1.5 }}>
          Revisa el archivo de reporte antes de compartirlo fuera de tu organización. No incluye credenciales ni
          telemetría en la nube. El registro global <code>elia_execution.log</code> (Documents/ELIA/logs/) incluye
          hitos recientes de ejecución y se adjunta parcialmente al reporte descargable.
        </div>
        <div style={{ marginTop: 12 }}>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <button
            type="button"
            disabled={downloading}
            onClick={handleDownload}
            style={{
              padding: "10px 14px",
              borderRadius: 10,
              background: c.primary,
              color: c.primaryFg,
              border: "none",
              cursor: downloading ? "wait" : "pointer",
              fontWeight: 600,
            }}
          >
            {downloading ? "Generando…" : "Descargar reporte de error"}
          </button>
          <button
            type="button"
            onClick={() => {
              void openEliaLogsFolder()
                .then((r) => {
                  setLogsFolderHint(r.hint ?? FOLDER_OPEN_HINT);
                })
                .catch((e: unknown) =>
                  onDownloadError?.(String((e as Error)?.message ?? e)),
                );
            }}
            style={{
              padding: "10px 14px",
              borderRadius: 10,
              border: `1px solid ${c.btnGhostBorder}`,
              background: c.btnGhostBg,
              color: c.text,
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Abrir carpeta de logs
          </button>
          {betaFeedbackUrl ? (
            <BetaFeedbackLink url={betaFeedbackUrl} c={c} variant="job" />
          ) : null}
          </div>
          <InlineActionHint c={c} message={logsFolderHint} testId="elia-job-open-logs-folder-hint" />
          {/* Versión comercial (≥1.0): quitar BetaFeedbackLink de arriba y descomentar:
          {supportEmail ? (
            <SupportContactLink email={supportEmail} jobId={jobId} c={c} />
          ) : null}
          También: import SupportContactLink, prop supportEmail, y App.tsx → supportEmail={aboutInfo?.support_email}
          */}
        </div>
      </div>
      <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        <button
          type="button"
          onClick={() => returnToHomeFromJobTab({ jobId })}
          style={{
            padding: "10px 14px",
            borderRadius: 10,
            background: c.btnGhostBg,
            color: c.text,
            border: `1px solid ${c.btnGhostBorder}`,
            cursor: "pointer",
          }}
        >
          Volver al inicio
        </button>
      </div>
    </>
  );
}

export function JobErrorActions(props: { c: Record<string, string> }) {
  const { c } = props;
  return (
    <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
      <button
        type="button"
        onClick={() => returnToHomeFromJobTab()}
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
  );
}
