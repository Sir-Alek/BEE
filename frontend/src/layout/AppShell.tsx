import React, { useState } from "react";
import type { AiCapabilitiesResponse } from "../api";
import { ELIA_LOGO_ICON_STYLE, ELIA_LOGO_LETTERS_STYLE } from "../app/constants";
import { formatJobMode } from "../app/utils";
import type { EliaConnectorProfile } from "../types";

function aiBadgeLabel(aiCaps: AiCapabilitiesResponse): string {
  const { resolution, preferences } = aiCaps;
  if (preferences.mode === "off") return "IA desactivada";
  if (preferences.mode === "on") return "IA forzada";
  if (resolution.degraded) return "IA degradada";
  if (resolution.use_ai) return "IA activa";
  return "Modo heurístico";
}

export function AppHeader(props: {
  c: Record<string, string>;
  isHomeSurface: boolean;
  jobState?: string;
  workspaceMode: string | null;
  connectorProfiles: EliaConnectorProfile[];
  reqConnectorProfileId: string;
  aiCaps: AiCapabilitiesResponse | null;
  onOpenSettings: () => void;
  onOpenAiSettings: () => void;
  handoff?: boolean;
}) {
  const { c, isHomeSurface, jobState, workspaceMode, aiCaps, onOpenSettings, onOpenAiSettings, handoff } = props;
  const [aiPopoverOpen, setAiPopoverOpen] = useState(false);
  const isHome = isHomeSurface;
  const statusLine = isHome
    ? "ELIA · Inicio · listo"
    : jobState
      ? `Estado: ${jobState}`
      : "Cargando trabajo…";
  const sub = !isHome && workspaceMode ? `${formatJobMode(workspaceMode)} · ` : "";
  const aiActive = aiCaps && aiCaps.preferences.mode !== "off" && aiCaps.resolution.use_ai;

  return (
    <header
      data-elia-chrome="1"
      className={`elia-chrome${handoff ? " elia-chrome--handoff" : ""}`}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, flex: "0 0 auto", minWidth: 0 }}>
        <img src="/logo-icon.png" alt="" aria-hidden style={ELIA_LOGO_ICON_STYLE} />
        <img src="/logo-letters.png" alt="ELIA" style={ELIA_LOGO_LETTERS_STYLE} />
      </div>

      <div
        className={`elia-chrome__status${jobState === "running" ? " elia-chrome__status--running elia-state-running__label" : ""}`}
        style={{ marginLeft: "auto" }}
      >
        {!isHome && sub ? (
          <div style={{ marginBottom: 4, fontSize: 11, fontFamily: "var(--elia-font-mono)" }}>{sub}ventana de trabajo</div>
        ) : null}
        <span>{statusLine}</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
        {aiCaps ? (
          <div style={{ position: "relative" }}>
            <button
              type="button"
              data-testid="elia-ai-status-badge"
              className={`elia-badge${aiActive ? " elia-badge--active" : ""}`}
              onClick={() => setAiPopoverOpen((v) => !v)}
              title={aiCaps.resolution.message}
            >
              <span aria-hidden style={{ fontSize: 7 }}>●</span>
              {aiBadgeLabel(aiCaps)}
            </button>
            {aiPopoverOpen ? (
              <div
                className="elia-panel"
                style={{
                  position: "absolute",
                  right: 0,
                  top: "calc(100% + 8px)",
                  zIndex: 100,
                  minWidth: 260,
                  maxWidth: 360,
                  padding: "10px 12px",
                  fontSize: 12,
                  lineHeight: 1.45,
                  color: c.text,
                }}
              >
                <div style={{ marginBottom: 6 }}>{aiCaps.resolution.message}</div>
                <div style={{ color: c.muted, fontSize: 11 }}>{aiCaps.brand_line}</div>
                <button
                  type="button"
                  className="elia-btn elia-btn--ghost elia-btn--sm"
                  style={{ marginTop: 8 }}
                  onClick={() => {
                    setAiPopoverOpen(false);
                    onOpenAiSettings();
                  }}
                >
                  Configuración → IA
                </button>
              </div>
            ) : null}
          </div>
        ) : null}

        <button
          type="button"
          data-testid="elia-settings-open"
          aria-label="Abrir configuración"
          title="Configuración"
          onClick={onOpenSettings}
          className="elia-btn elia-btn--ghost elia-btn--icon"
        >
          ⚙
        </button>
      </div>
    </header>
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
      className="elia-loading-row elia-loading-row--error"
      style={{ marginBottom: 16 }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10, width: "100%" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <b style={{ color: c.errorTitle }}>Error</b>
          <div style={{ color: c.errorBody, marginTop: 6, whiteSpace: "pre-wrap" }}>{message}</div>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Cerrar mensaje de error"
          title="Cerrar"
          className="elia-btn elia-btn--ghost elia-btn--sm"
          style={{ flexShrink: 0, border: "none", color: c.errorTitle }}
        >
          ✕
        </button>
      </div>
    </div>
  );
}
