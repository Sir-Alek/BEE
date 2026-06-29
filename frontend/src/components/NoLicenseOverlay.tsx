import React from "react";
import type { LicenseState } from "../app/licenseUtils";
import { licenseNeedsActivationBanner } from "../app/licenseUtils";

type Props = {
  c: Record<string, string>;
  license: LicenseState | null;
  onOpenLicenseSettings: () => void;
  children: React.ReactNode;
};

/** Capa clara de activación cuando la licencia no permite operar (Variante B — sin medias tintas). */
export function NoLicenseOverlay(props: Props) {
  const { c, license, onOpenLicenseSettings, children } = props;
  const activation = license && licenseNeedsActivationBanner(license);

  return (
    <div style={{ position: "relative" }}>
      <div style={{ opacity: 0.35, pointerEvents: "none", userSelect: "none" }} aria-hidden>
        {children}
      </div>
      <div
        role="alert"
        data-testid="elia-no-license-overlay"
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
          background: "rgba(15, 23, 42, 0.12)",
          borderRadius: 14,
        }}
      >
        <div
          style={{
            maxWidth: 420,
            padding: "20px 22px",
            borderRadius: 12,
            border: `1px solid ${c.errorBorder}`,
            background: c.surface,
            boxShadow: c.shadow,
            textAlign: "center",
          }}
        >
          <div style={{ fontWeight: 800, fontSize: 16, color: c.text, marginBottom: 8 }}>
            {activation ? "Activa tu licencia ELIA" : "Licencia no disponible"}
          </div>
          <div style={{ fontSize: 13, color: c.muted, lineHeight: 1.5, marginBottom: 16 }}>
            {license?.message ||
              "Introduce tu clave en Configuración → Licencia para usar automatización, API e inteligencia."}
          </div>
          <button
            type="button"
            data-testid="elia-no-license-open-settings"
            onClick={onOpenLicenseSettings}
            style={{
              padding: "10px 18px",
              borderRadius: 10,
              border: "none",
              background: c.primary,
              color: c.primaryFg,
              fontWeight: 700,
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            Ir a activación de licencia
          </button>
        </div>
      </div>
    </div>
  );
}
