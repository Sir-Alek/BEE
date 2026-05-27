/**
 * Enlace mailto a soporte en pantalla de error del job.
 * Versión comercial (≥1.0): activar en JobErrorPanel.tsx (sustituye BetaFeedbackLink).
 * Correo: core/_version.py → ELIA_SUPPORT_EMAIL, expuesto en /api/app/about → support_email.
 */
import React from "react";

type Props = {
  email: string;
  jobId?: string;
  c: Record<string, string>;
};

export function SupportContactLink(props: Props) {
  const { email, jobId, c } = props;
  const trimmed = email.trim();
  if (!trimmed) return null;

  const subject = jobId
    ? `ELIA — Reporte de error (job ${jobId.slice(0, 8)})`
    : "ELIA — Reporte de error";
  const body =
    "Describe el problema y adjunta el reporte de error descargado desde ELIA.\n\n" +
    (jobId ? `Job ID: ${jobId}\n` : "");

  const href = `mailto:${trimmed}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

  return (
    <a
      data-testid="elia-support-contact-job"
      href={href}
      style={{
        display: "inline-block",
        padding: "10px 14px",
        borderRadius: 10,
        background: c.btnGhostBg,
        color: c.text,
        border: `1px solid ${c.btnGhostBorder}`,
        fontWeight: 600,
        fontSize: 13,
        textDecoration: "none",
      }}
    >
      Reportar o contactar a soporte →
    </a>
  );
}
