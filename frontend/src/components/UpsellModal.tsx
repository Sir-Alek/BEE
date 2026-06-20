import React from "react";
import {
  TIER_ENTERPRISE,
  TIER_PROFESSIONAL,
  tierDisplayName,
  upsellBenefits,
  UPGRADE_CONTACT_EMAIL,
} from "../app/entitlements";

type Props = {
  c: Record<string, string>;
  requiredTier: typeof TIER_PROFESSIONAL | typeof TIER_ENTERPRISE | "mobile" | "legacy" | "doc_to_bdd" | "api_postman" | "api_locust" | "publishers_enterprise" | "team_memory";
  onClose: () => void;
};

function resolveTier(requiredTier: Props["requiredTier"]): typeof TIER_PROFESSIONAL | typeof TIER_ENTERPRISE {
  if (requiredTier === TIER_PROFESSIONAL || requiredTier === "mobile" || requiredTier === "doc_to_bdd" || requiredTier === "api_postman") {
    return TIER_PROFESSIONAL;
  }
  return TIER_ENTERPRISE;
}

function featureTitle(requiredTier: Props["requiredTier"]): string {
  const map: Record<Props["requiredTier"], string> = {
    mobile: "Automatización Móvil (Appium)",
    legacy: "Automatización Legacy (escritorio)",
    doc_to_bdd: "Inteligencia de Requerimientos (Doc-to-BDD)",
    api_postman: "Pruebas API avanzadas (cliente y suites)",
    api_locust: "Pruebas de carga (motor Locust)",
    publishers_enterprise: "Publishers ALM Enterprise",
    team_memory: "Team Memory Crypto",
    [TIER_PROFESSIONAL]: "Plan Professional",
    [TIER_ENTERPRISE]: "Plan Enterprise",
  };
  return map[requiredTier] ?? "Función premium";
}

export function UpsellModal(props: Props) {
  const { c, requiredTier, onClose } = props;
  const tier = resolveTier(requiredTier);
  const benefits = upsellBenefits(tier);
  const mailto = `mailto:${UPGRADE_CONTACT_EMAIL}?subject=${encodeURIComponent(`Upgrade ELIA — ${tierDisplayName(tier)}`)}`;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        data-testid="elia-upsell-modal"
        aria-label="elia-lock-modal"
        style={{
          background: c.surface,
          border: `1px solid ${c.border}`,
          borderRadius: 16,
          padding: "28px 32px",
          maxWidth: 440,
          textAlign: "left",
          boxShadow: "0 8px 32px rgba(0,0,0,0.25)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ fontSize: 28, marginBottom: 8 }}>🚀</div>
        <div style={{ fontWeight: 800, fontSize: 17, color: c.text, marginBottom: 8 }}>
          Sube de nivel tu automatización
        </div>
        <div style={{ fontSize: 14, color: c.muted, marginBottom: 16, lineHeight: 1.5 }}>
          <b>{featureTitle(requiredTier)}</b> es exclusivo del{" "}
          <b>Plan {tierDisplayName(tier)}</b>.
        </div>
        {benefits.length > 0 ? (
          <div style={{ fontSize: 13, color: c.text, marginBottom: 18 }}>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Beneficios del Plan {tierDisplayName(tier)}:</div>
            <ul style={{ margin: 0, paddingLeft: 18, lineHeight: 1.6 }}>
              {benefits.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              background: c.btnGhostBg,
              color: c.text,
              border: `1px solid ${c.btnGhostBorder}`,
              cursor: "pointer",
            }}
          >
            Cancelar
          </button>
          <a
            href={mailto}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              background: c.primary,
              color: c.primaryFg,
              border: "none",
              cursor: "pointer",
              textDecoration: "none",
              fontWeight: 600,
              fontSize: 14,
            }}
          >
            Contactar para Upgrade
          </a>
        </div>
      </div>
    </div>
  );
}

export function TierBadge(props: { label: string; c: Record<string, string> }) {
  const { label, c } = props;
  return (
    <span
      style={{
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: 0.4,
        textTransform: "uppercase",
        padding: "2px 6px",
        borderRadius: 4,
        background: c.hintBg,
        color: c.muted,
        border: `1px solid ${c.hintBorder}`,
      }}
    >
      {label}
    </span>
  );
}
