import React from "react";
import {
  TIER_ARCHITECT,
  tierDisplayName,
  UPGRADE_CONTACT_EMAIL,
} from "../app/entitlements";

type Props = {
  c: Record<string, string>;
  onClose: () => void;
  onOpenStudio: () => void;
  onOpenEnvironmentSettings?: () => void;
};

export function AvdArchitectUpsellModal(props: Props) {
  const { c, onClose, onOpenStudio, onOpenEnvironmentSettings } = props;
  const mailto = `mailto:${UPGRADE_CONTACT_EMAIL}?subject=${encodeURIComponent(
    "Upgrade ELIA — Architect (orquestación AVD)",
  )}`;

  return (
    <div
      data-testid="elia-avd-architect-upsell"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.42)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1100,
        padding: 16,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: c.surface,
          border: `1px solid ${c.border}`,
          borderRadius: 18,
          padding: "26px 28px",
          maxWidth: 420,
          width: "100%",
          boxShadow: "0 16px 48px rgba(0,0,0,0.28)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background: c.neutralBg,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 22,
            marginBottom: 14,
          }}
        >
          📱
        </div>
        <div style={{ fontWeight: 800, fontSize: 17, color: c.text, marginBottom: 10 }}>
          Creación automática de AVD
        </div>
        <p
          style={{
            margin: 0,
            fontSize: 14,
            color: c.muted,
            lineHeight: 1.6,
            marginBottom: 18,
          }}
        >
          La creación y orquestación automática de dispositivos virtuales locales es una
          característica exclusiva de{" "}
          <strong style={{ color: c.text }}>{tierDisplayName(TIER_ARCHITECT)}</strong>. Para
          usarla, configure su emulador manualmente o actualice su suscripción.
        </p>
        <div
          style={{
            fontSize: 12,
            color: c.muted,
            background: c.neutralBg,
            border: `1px solid ${c.border}`,
            borderRadius: 10,
            padding: "10px 12px",
            marginBottom: 18,
            lineHeight: 1.5,
          }}
        >
          Con Architect, ELIA descarga la system image, acepta licencias y crea el AVD en un
          solo clic. Mientras tanto, puedes abrir Android Studio y usar Device Manager.
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: "8px 14px",
              borderRadius: 8,
              background: c.btnGhostBg,
              color: c.text,
              border: `1px solid ${c.btnGhostBorder}`,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            Entendido
          </button>
          {onOpenEnvironmentSettings ? (
            <button
              type="button"
              data-testid="elia-avd-upsell-env-settings"
              onClick={() => {
                onOpenEnvironmentSettings();
                onClose();
              }}
              style={{
                padding: "8px 14px",
                borderRadius: 8,
                background: c.inputBg,
                color: c.text,
                border: `1px solid ${c.inputBorder}`,
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              Entorno local…
            </button>
          ) : null}
          <button
            type="button"
            data-testid="elia-avd-upsell-open-studio"
            onClick={() => {
              onOpenStudio();
              onClose();
            }}
            style={{
              padding: "8px 14px",
              borderRadius: 8,
              background: c.inputBg,
              color: c.text,
              border: `1px solid ${c.inputBorder}`,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            Abrir Android Studio
          </button>
          <a
            href={mailto}
            style={{
              padding: "8px 14px",
              borderRadius: 8,
              background: c.primary,
              color: c.primaryFg,
              border: "none",
              cursor: "pointer",
              fontSize: 13,
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
            }}
          >
            Conocer Architect
          </a>
        </div>
      </div>
    </div>
  );
}
