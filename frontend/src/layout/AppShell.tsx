import React from "react";
import { ELIA_LOGO_ICON_STYLE, ELIA_LOGO_LETTERS_STYLE } from "../app/constants";
import { formatJobMode } from "../app/utils";
import type { EliaConnectorProfile } from "../types";

export function AppHeader(props: {
  c: Record<string, string>;
  isHomeSurface: boolean;
  jobState?: string;
  workspaceMode: string | null;
  connectorProfiles: EliaConnectorProfile[];
  reqConnectorProfileId: string;
  onOpenSettings: () => void;
}) {
  const { c, isHomeSurface, jobState, workspaceMode, onOpenSettings } = props;
  const isHome = isHomeSurface;
  const statusLine = isHome
    ? "Inicio · deja esta pestaña abierta para nuevas tareas"
    : jobState
      ? `Estado: ${jobState}`
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
      <div style={{ display: "flex", alignItems: "center", flex: "0 0 auto" }}>
        <img src="/logo-icon.png" alt="" aria-hidden style={ELIA_LOGO_ICON_STYLE} />
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
        <img src="/logo-letters.png" alt="ELIA" style={ELIA_LOGO_LETTERS_STYLE} />
        <div
          style={{
            fontSize: 12,
            color: c.chromeHint,
            textAlign: "right",
            flex: "1 1 160px",
            minWidth: 120,
            maxWidth: "min(420px, 100%)",
          }}
        >
          {!isHome && sub ? (
            <div style={{ marginBottom: 4, fontSize: 11 }}>{sub}ventana de trabajo</div>
          ) : null}
          {statusLine}
        </div>
        <button
          type="button"
          data-testid="elia-settings-open"
          aria-label="Abrir configuración"
          title="Configuración"
          onClick={onOpenSettings}
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
}

export function ErrorAlert(props: {
  c: Record<string, string>;
  message: string;
  onDismiss: () => void;
}) {
  const { c, message, onDismiss } = props;
  return (
    <div
      role="alert"
      data-testid="elia-error-alert"
      style={{
        background: c.errorBg,
        border: `1px solid ${c.errorBorder}`,
        padding: 12,
        borderRadius: 10,
        marginBottom: 16,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <b style={{ color: c.errorTitle }}>Error</b>
          <div style={{ color: c.errorBody, marginTop: 6, whiteSpace: "pre-wrap" }}>{message}</div>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Cerrar mensaje de error"
          title="Cerrar"
          style={{
            flexShrink: 0,
            border: "none",
            background: "transparent",
            color: c.errorTitle,
            fontSize: 18,
            lineHeight: 1,
            cursor: "pointer",
            padding: "2px 6px",
            borderRadius: 6,
          }}
        >
          ✕
        </button>
      </div>
    </div>
  );
}
