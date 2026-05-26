import React from "react";

export const BETA_FEEDBACK_LINK_LABEL = "Ayúdanos a mejorar llenando el formulario de la Beta";

type Props = {
  url: string | null | undefined;
  c: Record<string, string>;
  variant: "about" | "license" | "job";
};

export function BetaFeedbackLink(props: Props) {
  const { url, c, variant } = props;
  const href = (url ?? "").trim();
  if (!href) return null;

  if (variant === "about") {
    return (
      <div
        data-testid="elia-beta-feedback-about"
        style={{
          marginBottom: 12,
          padding: "12px 14px",
          borderRadius: 10,
          border: `1px solid ${c.border}`,
          background: c.inputBg,
          fontSize: 13,
          lineHeight: 1.5,
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: 6 }}>¿Feedback o Errores?</div>
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: c.primary, fontWeight: 600 }}
        >
          {BETA_FEEDBACK_LINK_LABEL} →
        </a>
        <div style={{ marginTop: 8, fontSize: 12, color: c.muted }}>
          Si un trabajo falla, descarga el reporte desde la pantalla del error antes de enviar el formulario. Sin
          telemetría automática en la nube.
        </div>
      </div>
    );
  }

  if (variant === "license") {
    return (
      <div data-testid="elia-beta-feedback-license" style={{ marginTop: 10, fontSize: 13, lineHeight: 1.5 }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>Reporte de bugs y retroalimentación:</div>
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: c.primary, fontWeight: 600 }}
        >
          Compartir feedback en el Formulario de la Beta →
        </a>
      </div>
    );
  }

  return (
    <a
      data-testid="elia-beta-feedback-job"
      href={href}
      target="_blank"
      rel="noopener noreferrer"
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
      Enviar feedback beta →
    </a>
  );
}
