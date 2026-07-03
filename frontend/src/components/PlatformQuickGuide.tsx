import React from "react";
import { dismissPlatformQuickGuide, type QuickGuidePlatform } from "../app/platformGuidePrefs";
import {
  fetchPlatformQuickGuideCached,
  peekPlatformQuickGuide,
} from "../app/guidesCache";
import { usePlatformGuidePrefs } from "../hooks/usePlatformGuidePrefs";
import { MarkdownGuideModal } from "./MarkdownGuideModal";
import { EliaButton } from "./ui";

type Props = {
  c: Record<string, string>;
  platform: QuickGuidePlatform;
  /** Enlace compacto siempre visible junto al formulario de grabación. */
  showLink?: boolean;
  /** Tarjeta contextual en runner cuando no hay proyectos. */
  showRunnerHint?: boolean;
  hasProjects?: boolean;
};

const DEFAULT_TITLES: Record<QuickGuidePlatform, string> = {
  mobile: "Guía rápida — Móvil",
  legacy: "Guía rápida — Legacy",
  api_load: "Guía rápida — Suites y carga",
};

export function PlatformQuickGuide(props: Props) {
  const { c, platform, showLink = true, showRunnerHint = false, hasProjects = false } = props;
  const { guidesEnabled, isCardDismissed } = usePlatformGuidePrefs();
  const dismissed = isCardDismissed(platform);
  const [modalOpen, setModalOpen] = React.useState(false);
  const cached = peekPlatformQuickGuide(platform);
  const [title, setTitle] = React.useState(cached?.title ?? DEFAULT_TITLES[platform]);
  const [content, setContent] = React.useState(cached?.content ?? "");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const hit = peekPlatformQuickGuide(platform);
    if (hit) {
      setTitle(hit.title);
      setContent(hit.content);
    }
  }, [platform]);

  const openGuide = () => {
    setModalOpen(true);
    const hit = peekPlatformQuickGuide(platform);
    if (hit) {
      setTitle(hit.title);
      setContent(hit.content);
      setLoading(false);
      setError(null);
      return;
    }
    if (content.trim()) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    void fetchPlatformQuickGuideCached(platform)
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

  const steps =
    platform === "mobile"
      ? [
          "Revisa el checklist de entorno Android.",
          "Configura dispositivo y app, luego graba el flujo.",
          "Convierte la grabación: se crea el proyecto en behave/mobile/.",
          "Ejecuta el .feature desde la consola de abajo.",
        ]
      : platform === "legacy"
        ? [
            "Indica el título exacto de la ventana (y opcionalmente el .exe).",
            "Graba la interacción con la aplicación de escritorio.",
            "Convierte: el proyecto queda en behave/legacy/.",
            "Ejecuta Behave con la app accesible.",
          ]
        : [
            "Guarda escenarios en la pestaña Cliente API.",
            "Importa CSV/XLSX si necesitas datos parametrizados.",
            "Selecciona escenarios y ejecuta una suite funcional.",
            "Configura Locust (perfil, usuarios, CSV opcional).",
          ];

  const isApiLoad = platform === "api_load";
  const showExpandedHint = showRunnerHint && !dismissed && (isApiLoad || !hasProjects);

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
          <EliaButton
            variant="ghost"
            size="sm"
            data-testid={`elia-${platform}-quick-guide-link`}
            onClick={openGuide}
            style={{ color: c.primary, fontWeight: 700 }}
          >
            Guía rápida
          </EliaButton>
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
          <div style={{ fontWeight: 700, marginBottom: 6 }}>
            Primeros pasos en{" "}
            {platform === "mobile" ? "móvil" : platform === "legacy" ? "legacy" : "Suites y carga"}
          </div>
          <ol style={{ margin: "0 0 10px 18px", padding: 0 }}>
            {steps.map((step) => (
              <li key={step} style={{ marginBottom: 4 }}>
                {step}
              </li>
            ))}
          </ol>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <EliaButton variant="ghost" size="sm" onClick={openGuide} style={{ color: c.primary, fontWeight: 700 }}>
              Ver guía completa
            </EliaButton>
            <EliaButton
              variant="ghost"
              size="sm"
              data-testid={`elia-${platform}-quick-guide-dismiss`}
              onClick={handleDismiss}
              style={{ border: "none", color: c.muted, fontWeight: 600 }}
            >
              No volver a mostrar
            </EliaButton>
          </div>
        </div>
      ) : null}

      {showRunnerHint && dismissed && (isApiLoad || !hasProjects) ? (
        <div
          data-testid={isApiLoad ? "elia-api-load-quick-start-hint" : "elia-no-behave-projects-hint"}
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
          {isApiLoad ? (
            <>
              ¿Primera vez en suites o carga?{" "}
              <EliaButton
                variant="ghost"
                size="sm"
                onClick={openGuide}
                style={{ padding: 0, border: "none", background: "transparent", color: c.primary, fontWeight: 700, fontSize: 13 }}
              >
                Guía rápida
              </EliaButton>
            </>
          ) : (
            <>
              Aún no hay proyectos en esta plataforma. En {platform === "mobile" ? "móvil" : "legacy"} se crean al{" "}
              <b>convertir una grabación</b>.{" "}
              <EliaButton
                variant="ghost"
                size="sm"
                onClick={openGuide}
                style={{ padding: 0, border: "none", background: "transparent", color: c.primary, fontWeight: 700, fontSize: 13 }}
              >
                Guía rápida
              </EliaButton>
            </>
          )}
        </div>
      ) : null}

      {modalOpen ? (
        <MarkdownGuideModal
          c={c}
          title={title}
          subtitle={
            platform === "mobile"
              ? "Grabación Android → conversión Behave → ejecución"
              : platform === "legacy"
                ? "Grabación Windows → conversión Behave → ejecución"
                : "Escenarios → suite funcional → prueba de carga Locust"
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
