import React from "react";
import {
  TIER_ARCHITECT,
  tierDisplayName,
  UPGRADE_CONTACT_EMAIL,
} from "../app/entitlements";
import { EliaButton, EliaLinkButton, EliaModalActions, EliaModalOverlay, EliaModalPanel } from "./ui";

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
    <EliaModalOverlay testId="elia-avd-architect-upsell" ariaLabel="Creación automática de AVD" onClose={onClose}>
      <EliaModalPanel onClick={(e) => e.stopPropagation()} style={{ maxWidth: 420, padding: "26px 28px" }}>
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
        <EliaModalActions>
          <EliaButton variant="ghost" size="sm" onClick={onClose}>
            Entendido
          </EliaButton>
          {onOpenEnvironmentSettings ? (
            <EliaButton
              variant="ghost"
              size="sm"
              data-testid="elia-avd-upsell-env-settings"
              onClick={() => {
                onOpenEnvironmentSettings();
                onClose();
              }}
            >
              Entorno local…
            </EliaButton>
          ) : null}
          <EliaButton
            variant="ghost"
            size="sm"
            data-testid="elia-avd-upsell-open-studio"
            onClick={() => {
              onOpenStudio();
              onClose();
            }}
          >
            Abrir Android Studio
          </EliaButton>
          <EliaLinkButton href={mailto} variant="primary" size="sm">
            Conocer Architect
          </EliaLinkButton>
        </EliaModalActions>
      </EliaModalPanel>
    </EliaModalOverlay>
  );
}
