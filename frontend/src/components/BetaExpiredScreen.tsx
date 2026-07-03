import React from "react";
import { UPGRADE_CONTACT_EMAIL } from "../app/entitlements";
import { EliaLinkButton } from "./ui";

type Props = {
  c: Record<string, string>;
  message: string;
  reason?: string;
  upgradeEmail?: string;
};

export function BetaExpiredScreen(props: Props) {
  const { c, message, reason, upgradeEmail = UPGRADE_CONTACT_EMAIL } = props;
  const mailto = `mailto:${upgradeEmail}?subject=${encodeURIComponent("Suscripción ELIA")}`;

  return (
    <div
      data-testid="elia-beta-expired"
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: c.bg,
        padding: 24,
      }}
    >
      <div
        style={{
          maxWidth: 520,
          background: c.surface,
          border: `1px solid ${c.border}`,
          borderRadius: 16,
          padding: "32px 28px",
          boxShadow: c.shadow,
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 40, marginBottom: 12 }}>{reason === "clock_tamper" ? "⏱️" : "🙏"}</div>
        <h1 style={{ margin: "0 0 12px", fontSize: 22, color: c.text }}>
          {reason === "clock_tamper" ? "Reloj del sistema inválido" : "Beta finalizada"}
        </h1>
        <p style={{ margin: "0 0 20px", color: c.muted, lineHeight: 1.6, whiteSpace: "pre-line" }}>{message}</p>
        <EliaLinkButton href={mailto} variant="primary" size="sm">
          Adquirir suscripción
        </EliaLinkButton>
      </div>
    </div>
  );
}
