import React from "react";
import { dismissPlatformQuickGuide, type QuickGuidePlatform } from "../app/platformGuidePrefs";
import { usePlatformGuidePrefs } from "../hooks/usePlatformGuidePrefs";
import { getPlatformQuickGuide } from "../api";
import { MarkdownGuideModal } from "./MarkdownGuideModal";

type Props = {
  c: Record<string, string>;
  platform: QuickGuidePlatform;
  /** Enlace compacto siempre visible junto al formulario de grabación. */
  showLink?: boolean;
  /** Tarjeta contextual en runner cuando no hay proyectos. */
  showRunnerHint?: boolean;
  hasProjects?: boolean;
};

export function PlatformQuickGuide(props: Props) {
  const { c, platform, showLink = true, showRunnerHint = false, hasProjects = false } = props;
  const { guidesEnabled, isCardDismissed } = usePlatformGuidePrefs();
  const dismissed = isCardDismissed(platform);
  const [modalOpen, setModalOpen] = React.useState(false);
  const [title, setTitle] = React.useState("");
  const [content, setContent] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const openGuide = () => {
    setModalOpen(true);
    if (content.trim()) return;
    setLoading(true);
    setError(null);
    void getPlatformQuickGuide(platform)
      .then((r) => {
        setTitle(r.title);
        setContent(r.content);
      })
      .catch((e: unknown) => setError(String((e as Error)?.message ?? e)))
      .finally(() => setLoading(false));
  };

  const handleDismiss = () => {
    dismissPlatformQuickGuide(platform);
  };

  if (!guidesEnabled) return null;

  const linkBtnStyle: React.CSSProperties = {
    padding: "6px 10px",
    borderRadius: 8,
    border: `1px solid ${c.border}`,
    background: "transparent",
    color: c.primary,
    fontWeight: 700,
    fontSize: 12,
    cursor: "pointer",
  };

  const steps =
    platform === "mobile"
      ? [
          "Revisa el checklist de entorno Android.",
          "Configura dispositivo y app, luego graba el flujo.",
          "Convierte la grabación: se crea el proyecto en behave/mobile/.",
          "Ejecuta el .feature desde la consola de abajo.",
        ]
      : [
          "Indica el título exacto de la ventana (y opcionalmente el .exe).",
          "Graba la interacción con la aplicación de escritorio.",
          "Convierte: el proyecto queda en behave/legacy/.",
          "Ejecuta Behave con la app accesible.",
        ];

  const showExpandedHint = showRunnerHint && !hasProjects && !dismissed;

  return (
    <>
      {showLink ? (
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            marginBottom: 10,
          }}
        >
          <button
            type="button"
            data-testid={`elia-${platform}-quick-guide-link`}
            onClick={openGuide}
            style={linkBtnStyle}
          >
            Guía rápida
          </button>
        </div>
      ) : null}

      {showExpandedHint ? (
        <div
          data-testid={`elia-${platform}-quick-start-hint`}
          style={{
            marginBottom: 10,
            padding: "10px 12px",
            borderRadius: 10,
            background: c.hintBg,
            border: `1px solid ${c.hintBorder}`,
            fontSize: 13,
            color: c.hintText,
            lineHeight: 1.45,
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Primeros pasos en {platform === "mobile" ? "móvil" : "legacy"}</div>
          <ol style={{ margin: "0 0 10px 18px", padding: 0 }}>
            {steps.map((step) => (
              <li key={step} style={{ marginBottom: 4 }}>
                {step}
              </li>
            ))}
          </ol>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <button type="button" onClick={openGuide} style={linkBtnStyle}>
              Ver guía completa
            </button>
            <button
              type="button"
              data-testid={`elia-${platform}-quick-guide-dismiss`}
              onClick={handleDismiss}
              style={{
                ...linkBtnStyle,
                border: "none",
                color: c.muted,
                fontWeight: 600,
              }}
            >
              No volver a mostrar
            </button>
          </div>
        </div>
      ) : null}

      {showRunnerHint && !hasProjects && dismissed ? (
        <div
          data-testid="elia-no-behave-projects-hint"
          style={{
            marginBottom: 10,
            padding: "10px 12px",
            borderRadius: 10,
            background: c.hintBg,
            border: `1px solid ${c.hintBorder}`,
            fontSize: 13,
            color: c.hintText,
            lineHeight: 1.45,
          }}
        >
          Aún no hay proyectos en esta plataforma. En {platform === "mobile" ? "móvil" : "legacy"} se crean al{" "}
          <b>convertir una grabación</b>.{" "}
          <button
            type="button"
            onClick={openGuide}
            style={{
              border: "none",
              background: "transparent",
              color: c.primary,
              fontWeight: 700,
              cursor: "pointer",
              padding: 0,
              fontSize: 13,
            }}
          >
            Guía rápida
          </button>
        </div>
      ) : null}

      {modalOpen ? (
        <MarkdownGuideModal
          c={c}
          title={title || (platform === "mobile" ? "Guía rápida — Móvil" : "Guía rápida — Legacy")}
          subtitle={
            platform === "mobile"
              ? "Grabación Android → conversión Behave → ejecución"
              : "Grabación Windows → conversión Behave → ejecución"
          }
          content={content}
          loading={loading}
          error={error}
          onClose={() => setModalOpen(false)}
          testId={`elia-${platform}-quick-guide-modal`}
        />
      ) : null}
    </>
  );
}
