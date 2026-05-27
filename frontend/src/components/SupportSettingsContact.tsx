/**
 * Contacto de soporte en Configuración (Licencia).
 * Versión comercial (≥1.0): activar en SettingsDialog.tsx (sustituye BetaFeedbackLink variant="license").
 * Correo: core/_version.py → ELIA_SUPPORT_EMAIL, expuesto en /api/app/about → support_email.
 */
import React from "react";

type Props = {
  email: string;
  c: Record<string, string>;
};

export function SupportSettingsContact(props: Props) {
  const { email, c } = props;
  const trimmed = email.trim();
  if (!trimmed) return null;

  const subject = "ELIA — Consulta de licencia o módulos";
  const body =
    "Describe si necesitas ampliar módulos, renovar o solicitar una nueva clave de activación.\n" +
    "Incluye tu huella de máquina si aplica.\n\n";

  const href = `mailto:${trimmed}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

  return (
    <div
      data-testid="elia-support-contact-license"
      style={{ marginTop: 10, fontSize: 13, lineHeight: 1.5 }}
    >
      <div style={{ fontWeight: 600, marginBottom: 4 }}>Soporte y licencias:</div>
      <a href={href} style={{ color: c.primary, fontWeight: 600 }}>
        Contactar a soporte (ampliar módulos o solicitar clave) →
      </a>
    </div>
  );
}
