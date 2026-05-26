import React, { useState } from "react";
import { downloadJobErrorReport } from "../api";
import { goHomeInThisTab, tryFocusOpenerAndCloseThisTab } from "../app/utils";
import { BetaFeedbackLink } from "../components/BetaFeedbackLink";

type Props = {
  c: Record<string, string>;
  jobId: string;
  errorMessage: string;
  betaFeedbackUrl?: string | null;
  onDownloadError?: (message: string | null) => void;
};

export function JobErrorPanel(props: Props) {
  const { c, jobId, errorMessage, betaFeedbackUrl, onDownloadError } = props;
  const [downloading, setDownloading] = useState(false);

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
          telemetría en la nube.
        </div>
        <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
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
          {betaFeedbackUrl ? (
            <BetaFeedbackLink url={betaFeedbackUrl} c={c} variant="job" />
          ) : null}
        </div>
      </div>
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
  );
}
