import React from "react";
import { goHomeInThisTab, tryFocusOpenerAndCloseThisTab } from "../app/utils";
import { GeneratedFilesResultView } from "./jobUiComponents";
import type { JobProgressState } from "./useJobProgress";

type Props = {
  c: Record<string, string>;
  job: JobProgressState;
};

export function JobDonePanel(props: Props) {
  const { c, job } = props;
  return (
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
  );
}

export function JobCancelledPanel(props: { c: Record<string, string> }) {
  const { c } = props;
  return (
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
  );
}
