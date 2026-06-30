import React from "react";
import type { RecorderPreflightResponse } from "../api";
import { LoadingStatusRow } from "../components/LoadingStatusRow";
import { FieldLabel } from "../components/ui";

export function WebConfigForm(props: {
  c: Record<string, string>;
  urlValue: string;
  onUrlChange: (value: string) => void;
  recorderPreflight: RecorderPreflightResponse | null;
  recorderPreflightLoading: boolean;
}) {
  const { c, urlValue, onUrlChange, recorderPreflight, recorderPreflightLoading } = props;

  return (
    <div style={{ marginBottom: 14 }}>
      <FieldLabel
        c={c}
        tooltip={
          <>
            Requisito: Google Chrome instalado (Edge no válido). Opcional: variable ELIA_CHROME_PATH si Chrome está en
            ruta no estándar.
          </>
        }
      >
        URL de grabación
      </FieldLabel>
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <input
          data-testid="elia-web-url"
          value={urlValue}
          onChange={(e) => onUrlChange(e.target.value)}
          placeholder="https://miapp.com"
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
      {recorderPreflightLoading && (
        <LoadingStatusRow
          c={c}
          text="Comprobando Chrome…"
          loading
          testId="elia-web-chrome-preflight-loading"
        />
      )}
      {!recorderPreflightLoading && recorderPreflight && !recorderPreflight.ok && (
        <div
          role="alert"
          style={{
            marginTop: 10,
            padding: "10px 12px",
            borderRadius: 10,
            fontSize: 13,
            background: c.licWarnBg,
            border: `1px solid ${c.licWarnBorder}`,
            color: c.text,
          }}
        >
          {recorderPreflight.errors.map((line, i) => (
            <div key={i} style={{ marginTop: i ? 6 : 0 }}>
              {line}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
