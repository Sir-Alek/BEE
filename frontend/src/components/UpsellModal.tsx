import React from "react";
import {
  TIER_ARCHITECT,
  TIER_TESTER,
  tierAudience,
  tierDisplayName,
  upsellBenefits,
  UPGRADE_CONTACT_EMAIL,
} from "../app/entitlements";
import { EliaButton, EliaLinkButton, EliaModalActions, EliaModalOverlay, EliaModalPanel } from "./ui";

type Props = {
  c: Record<string, string>;
  requiredTier:
    | typeof TIER_TESTER
    | typeof TIER_ARCHITECT
    | "mobile"
    | "legacy"
    | "doc_to_bdd"
    | "api_postman"
    | "api_locust"
    | "publishers_enterprise"
    | "team_memory";
  onClose: () => void;
};

function resolveTier(requiredTier: Props["requiredTier"]): typeof TIER_TESTER | typeof TIER_ARCHITECT {
  if (
    requiredTier === TIER_TESTER ||
    requiredTier === "mobile" ||
    requiredTier === "doc_to_bdd" ||
    requiredTier === "api_postman"
  ) {
    return TIER_TESTER;
  }
  return TIER_ARCHITECT;
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
    [TIER_TESTER]: "Plan ELIA Tester",
    [TIER_ARCHITECT]: "Plan ELIA Architect",
  };
  return map[requiredTier] ?? "Función premium";
}

export function UpsellModal(props: Props) {
  const { c, requiredTier, onClose } = props;
  const tier = resolveTier(requiredTier);
  const benefits = upsellBenefits(tier);
  const audience = tierAudience(tier);
  const mailto = `mailto:${UPGRADE_CONTACT_EMAIL}?subject=${encodeURIComponent(`Upgrade ELIA — ${tierDisplayName(tier)}`)}`;

  return (
    <EliaModalOverlay onClose={onClose} zIndex={1000}>
      <EliaModalPanel testId="elia-upsell-modal" onClick={(e) => e.stopPropagation()}>
        <div style={{ fontSize: 28, marginBottom: 8 }}>🚀</div>
        <div className="elia-modal-header__title" style={{ marginBottom: 8 }}>
          Sube de nivel tu automatización
        </div>
        <div className="elia-modal-body-text" style={{ marginBottom: 16 }}>
          <b>{featureTitle(requiredTier)}</b> es exclusivo del <b>{tierDisplayName(tier)}</b>.
        </div>
        {audience ? (
          <div style={{ fontSize: 12, color: c.muted, marginBottom: 12, lineHeight: 1.5 }}>{audience}</div>
        ) : null}
        {benefits.length > 0 ? (
          <div style={{ fontSize: 13, color: c.text, marginBottom: 18 }}>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Beneficios de {tierDisplayName(tier)}:</div>
            <ul style={{ margin: 0, paddingLeft: 18, lineHeight: 1.6 }}>
              {benefits.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <EliaModalActions>
          <EliaButton variant="ghost" size="sm" onClick={onClose}>
            Cancelar
          </EliaButton>
          <EliaLinkButton href={mailto} variant="primary" size="sm">
            Contactar para Upgrade
          </EliaLinkButton>
        </EliaModalActions>
      </EliaModalPanel>
    </EliaModalOverlay>
  );
}

export function TierBadge(props: { label: string; c: Record<string, string> }) {
  const { label } = props;
  return <span className="elia-badge">{label}</span>;
}
