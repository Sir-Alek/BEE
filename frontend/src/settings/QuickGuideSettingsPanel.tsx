import React from "react";
import {
  areQuickGuidesEnabled,
  resetAllQuickGuideDismissCards,
  setQuickGuidesEnabled,
} from "../app/platformGuidePrefs";

type Props = {
  c: Record<string, string>;
};

export function QuickGuideSettingsPanel(props: Props) {
  const { c } = props;
  const [enabled, setEnabled] = React.useState(() => areQuickGuidesEnabled());
  const [resetMsg, setResetMsg] = React.useState<string | null>(null);

  const handleToggle = () => {
    const next = !enabled;
    setEnabled(next);
    setQuickGuidesEnabled(next);
    setResetMsg(null);
  };

  const handleResetCards = () => {
    resetAllQuickGuideDismissCards();
    setResetMsg("Tarjetas de primeros pasos restablecidas en móvil y legacy.");
    window.setTimeout(() => setResetMsg(null), 3000);
  };

  return (
    <div
      style={{
        border: `1px solid ${c.border}`,
        borderRadius: 12,
        padding: 14,
        marginBottom: 14,
        background: c.neutralBg,
      }}
      data-testid="elia-settings-quick-guides"
    >
      <div style={{ fontWeight: 800, marginBottom: 6 }}>Guías rápidas (móvil y legacy)</div>
      <div style={{ fontSize: 12, color: c.muted, marginBottom: 12, lineHeight: 1.45 }}>
        Tarjetas de «Primeros pasos», enlaces «Guía rápida» y modal de ayuda en grabación y runner. No afecta
        plantillas web/API ni otras ayudas del producto.
      </div>
      <label
        htmlFor="elia-quick-guides-toggle"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          cursor: "pointer",
          fontSize: 14,
          marginBottom: 12,
        }}
      >
        <span>Mostrar guías rápidas de inicio</span>
        <input
          id="elia-quick-guides-toggle"
          type="checkbox"
          checked={enabled}
          onChange={handleToggle}
          data-testid="elia-quick-guides-enabled"
          style={{ position: "absolute", opacity: 0, width: 1, height: 1 }}
        />
        <span
          style={{
            position: "relative",
            width: 44,
            height: 26,
            borderRadius: 999,
            background: enabled ? c.primary : c.border,
            flexShrink: 0,
          }}
          aria-hidden
        >
          <span
            style={{
              position: "absolute",
              top: 3,
              left: enabled ? 22 : 3,
              width: 20,
              height: 20,
              borderRadius: "50%",
              background: "#fff",
              transition: "left 160ms ease",
            }}
          />
        </span>
      </label>
      <button
        type="button"
        onClick={handleResetCards}
        disabled={!enabled}
        data-testid="elia-quick-guides-reset-cards"
        style={{
          padding: "8px 12px",
          borderRadius: 8,
          border: `1px solid ${c.btnGhostBorder}`,
          background: c.btnGhostBg,
          color: enabled ? c.text : c.muted,
          fontSize: 13,
          fontWeight: 600,
          cursor: enabled ? "pointer" : "not-allowed",
          opacity: enabled ? 1 : 0.6,
        }}
      >
        Restablecer tarjetas ocultas
      </button>
      <div style={{ fontSize: 11, color: c.muted, marginTop: 8, lineHeight: 1.4 }}>
        «No volver a mostrar» solo oculta la tarjeta expandida; el enlace «Guía rápida» seguía visible. Usa
        restablecer para volver a ver las tarjetas sin reactivar todo desde cero.
      </div>
      {resetMsg ? (
        <div
          role="status"
          style={{ fontSize: 12, color: c.hintText, marginTop: 8 }}
          data-testid="elia-quick-guides-reset-msg"
        >
          {resetMsg}
        </div>
      ) : null}
    </div>
  );
}
