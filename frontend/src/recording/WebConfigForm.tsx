import React from "react";
import type { RecorderPreflightResponse } from "../api";

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
      <div style={{ fontSize: 12, color: c.muted, marginBottom: 8 }}>
        Requisito: <b>Google Chrome</b> instalado en este equipo (Microsoft Edge no es válido para
        grabar). Opcional: variable <code>ELIA_CHROME_PATH</code> si Chrome está en una ruta no estándar.
      </div>
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <input
          data-testid="elia-web-url"
          value={urlValue}
          onChange={(e) => onUrlChange(e.target.value)}
          placeholder="URL para grabar (ej: https://miapp.com)"
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
        <div style={{ fontSize: 12, color: c.muted, marginTop: 8 }}>Comprobando Chrome…</div>
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
      {!recorderPreflightLoading && recorderPreflight?.ok && recorderPreflight.warnings.length > 0 && (
        <div
          style={{
            marginTop: 10,
            padding: "10px 12px",
            borderRadius: 10,
            fontSize: 13,
            background: c.hintBg,
            border: `1px solid ${c.hintBorder}`,
            color: c.hintText,
          }}
        >
          {recorderPreflight.warnings.join(" ")}
        </div>
      )}
      {!recorderPreflightLoading && recorderPreflight?.ok && recorderPreflight.source === "install" && (
        <div style={{ fontSize: 12, color: c.muted, marginTop: 8 }}>Chrome detectado.</div>
      )}
    </div>
  );
}
