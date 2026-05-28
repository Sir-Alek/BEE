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

function aiBadgeColor(c: Record<string, string>, aiCaps: AiCapabilitiesResponse): { bg: string; fg: string; border: string } {
  const { resolution, preferences } = aiCaps;
  if (preferences.mode === "off" || !resolution.use_ai) {
    return { bg: c.neutralBg, fg: c.muted, border: c.border };
  }
  if (resolution.degraded || preferences.mode === "on") {
    return { bg: c.warnBg, fg: c.warnText, border: c.severityWarnBorder };
  }
  return { bg: c.hintBg, fg: c.hintText, border: c.hintBorder };
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
}) {
  const { c, isHomeSurface, jobState, workspaceMode, aiCaps, onOpenSettings, onOpenAiSettings } = props;
  const [aiPopoverOpen, setAiPopoverOpen] = useState(false);
  const isHome = isHomeSurface;
  const statusLine = isHome
    ? "Inicio · deja esta pestaña abierta para nuevas tareas"
    : jobState
      ? `Estado: ${jobState}`
      : "Cargando trabajo…";
  const sub = !isHome && workspaceMode ? `${formatJobMode(workspaceMode)} · ` : "";
  const badgeColors = aiCaps ? aiBadgeColor(c, aiCaps) : null;

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
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-end",
            gap: 6,
            flexShrink: 0,
            marginLeft: "auto",
          }}
        >
          <button
            type="button"
            data-testid="elia-settings-open"
            aria-label="Abrir configuración"
            title="Configuración"
            onClick={onOpenSettings}
            style={{
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
          {aiCaps && badgeColors ? (
            <div style={{ position: "relative" }}>
              <button
                type="button"
                data-testid="elia-ai-status-badge"
                onClick={() => setAiPopoverOpen((v) => !v)}
                title={aiCaps.resolution.message}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 5,
                  padding: "3px 8px",
                  borderRadius: 999,
                  border: `1px solid ${badgeColors.border}`,
                  background: badgeColors.bg,
                  color: badgeColors.fg,
                  fontSize: 10,
                  fontWeight: 600,
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  maxWidth: 140,
                }}
              >
                <span aria-hidden style={{ fontSize: 7 }}>●</span>
                {aiBadgeLabel(aiCaps)}
              </button>
              {aiPopoverOpen ? (
                <div
                  style={{
                    position: "absolute",
                    right: 0,
                    top: "calc(100% + 8px)",
                    zIndex: 100,
                    minWidth: 260,
                    maxWidth: 360,
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: `1px solid ${c.border}`,
                    background: c.surface,
                    boxShadow: c.shadow,
                    fontSize: 12,
                    lineHeight: 1.45,
                    color: c.text,
                  }}
                >
                  <div style={{ marginBottom: 6 }}>{aiCaps.resolution.message}</div>
                  <div style={{ color: c.muted, fontSize: 11 }}>{aiCaps.brand_line}</div>
                  <button
                    type="button"
                    onClick={() => {
                      setAiPopoverOpen(false);
                      onOpenAiSettings();
                    }}
                    style={{
                      marginTop: 8,
                      padding: "4px 8px",
                      borderRadius: 6,
                      border: `1px solid ${c.btnGhostBorder}`,
                      background: c.btnGhostBg,
                      color: c.text,
                      fontSize: 11,
                      cursor: "pointer",
                    }}
                  >
                    Configuración → IA
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
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
