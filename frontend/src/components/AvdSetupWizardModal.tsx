import React from "react";
import type { MobileAvdWizardCapabilitiesResponse } from "../api";
import {
  getMobileAvdWizardCapabilities,
  getMobileAvdWizardStatus,
  openMobileAndroidStudio,
  startMobileAvdWizard,
} from "../api";
import { LoadingStatusRow } from "./LoadingStatusRow";
import { AndroidStudioPathPanel } from "./AndroidStudioPathPanel";

type Props = {
  c: Record<string, string>;
  open: boolean;
  onClose: () => void;
  onRefresh: (preferAvdName?: string) => void;
  onOpenEnvironmentSettings?: () => void;
};

function pollJob(
  onUpdate: (msg: string) => void,
  signal: { cancelled: boolean },
): Promise<{ ok: boolean; avdName?: string | null; error?: string }> {
  return new Promise((resolve) => {
    const tick = async () => {
      if (signal.cancelled) return;
      try {
        const { status } = await getMobileAvdWizardStatus();
        onUpdate(status.message || status.phase || "Procesando…");
        if (status.done) {
          resolve({ ok: status.ok, avdName: status.avd_name, error: status.error ?? undefined });
          return;
        }
      } catch {
        resolve({ ok: false, error: "No se pudo consultar el progreso." });
        return;
      }
      window.setTimeout(() => void tick(), 1200);
    };
    void tick();
  });
}

export function AvdSetupWizardModal(props: Props) {
  const { c, open, onClose, onRefresh, onOpenEnvironmentSettings } = props;
  const [caps, setCaps] = React.useState<MobileAvdWizardCapabilitiesResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [templateId, setTemplateId] = React.useState("standard");
  const [step, setStep] = React.useState<"intro" | "working" | "done">("intro");
  const [msg, setMsg] = React.useState<string | null>(null);
  const [studioMsg, setStudioMsg] = React.useState<string | null>(null);
  const [studioPanelOpen, setStudioPanelOpen] = React.useState(false);
  const [studioSdkOk, setStudioSdkOk] = React.useState(false);
  const pollRef = React.useRef({ cancelled: false });

  React.useEffect(() => {
    if (!open) return;
    pollRef.current.cancelled = false;
    setStep("intro");
    setMsg(null);
    setStudioMsg(null);
    setLoading(true);
    void (async () => {
      try {
        const data = await getMobileAvdWizardCapabilities();
        setCaps(data);
        if (data.templates.length > 0) {
          setTemplateId(data.templates[0].id);
        }
        if (data.job?.active) {
          setStep("working");
          const result = await pollJob(setMsg, pollRef.current);
          if (result.ok) {
            setStep("done");
            setMsg(result.avdName ? `AVD «${result.avdName}» listo.` : "AVD creado.");
            onRefresh(result.avdName ?? undefined);
          } else {
            setMsg(result.error || "No se pudo completar el asistente.");
            setStep("intro");
          }
        }
      } catch (e: unknown) {
        setMsg(String((e as Error)?.message ?? e));
      } finally {
        setLoading(false);
      }
    })();
    return () => {
      pollRef.current.cancelled = true;
    };
  }, [open, onRefresh]);

  if (!open) return null;

  const templates = caps?.templates ?? [];
  const selected = templates.find((t) => t.id === templateId) ?? templates[0];

  const handleOpenStudio = () => {
    setStudioMsg(null);
    setStudioPanelOpen(false);
    setStudioSdkOk(false);
    void (async () => {
      try {
        const res = await openMobileAndroidStudio();
        if (!res.ok) {
          setStudioMsg(res.message);
          setStudioSdkOk(Boolean(res.sdk_ok));
          setStudioPanelOpen(true);
          return;
        }
        setStudioMsg(res.message + (res.hint ? ` ${res.hint}` : ""));
      } catch (e: unknown) {
        setStudioMsg(String((e as Error)?.message ?? e));
        setStudioPanelOpen(true);
      }
    })();
  };
  const handleRecheck = () => {
    onRefresh();
    setStudioMsg("Catálogo actualizado. Si creaste un AVD en Studio, debería aparecer en la lista.");
    void (async () => {
      try {
        setCaps(await getMobileAvdWizardCapabilities());
      } catch {
        /* ignore */
      }
    })();
  };

  const runWizard = () => {
    if (!caps?.orchestration_allowed) return;
    if (!caps.cmdline_tools_ok) {
      setMsg("Instala Android SDK Command-line Tools desde Android Studio.");
      return;
    }
    if (caps.disk_ok === false) {
      setMsg("Espacio en disco insuficiente (se recomiendan al menos 8 GB libres).");
      return;
    }
    setStep("working");
    setMsg("Iniciando asistente…");
    void (async () => {
      try {
        await startMobileAvdWizard(templateId);
        const result = await pollJob(setMsg, pollRef.current);
        if (result.ok) {
          setStep("done");
          setMsg(result.avdName ? `AVD «${result.avdName}» creado correctamente.` : "AVD creado.");
          onRefresh(result.avdName ?? undefined);
        } else {
          setMsg(result.error || "El asistente AVD no pudo completarse.");
          setStep("intro");
        }
      } catch (e: unknown) {
        setMsg(String((e as Error)?.message ?? e));
        setStep("intro");
      }
    })();
  };

  return (
    <div
      data-testid="elia-avd-setup-wizard"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1200,
        padding: 16,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: c.surface,
          border: `1px solid ${c.border}`,
          borderRadius: 16,
          padding: "24px 28px",
          maxWidth: 540,
          width: "100%",
          maxHeight: "90vh",
          overflow: "auto",
          boxShadow: "0 12px 40px rgba(0,0,0,0.28)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ fontWeight: 800, fontSize: 18, color: c.text, marginBottom: 6 }}>
          Asistente AVD
        </div>
        <div style={{ fontSize: 13, color: c.muted, marginBottom: 16, lineHeight: 1.5 }}>
          Crea un dispositivo virtual local para grabación móvil. Architect puede automatizar
          licencias, descarga e instalación; en cualquier plan puedes usar Android Studio.
        </div>

        {loading && (
          <LoadingStatusRow c={c} text="Comprobando entorno…" loading testId="elia-avd-wizard-loading" />
        )}

        {!loading && caps && step === "intro" && (
          <>
            <div
              style={{
                display: "grid",
                gap: 8,
                marginBottom: 14,
                fontSize: 12,
                color: c.muted,
              }}
            >
              <div>
                SDK: {caps.sdk_path ? "detectado" : "no detectado"} · Command-line tools:{" "}
                {caps.cmdline_tools_ok ? "OK" : "faltan"}
              </div>
              <div>
                Studio: {caps.studio_available ? "detectado" : "no detectado"}
                {caps.studio_configured_by ? ` (${caps.studio_configured_by})` : ""}
              </div>
              <div>
                Catálogo AVD: {caps.avd_count} · Emulador online:{" "}
                {caps.has_online_emulator ? "sí" : "no"}
                {caps.disk_free_gb != null ? ` · Disco libre: ~${caps.disk_free_gb} GB` : ""}
              </div>
            </div>

            {caps.studio_missing_sdk_ok && (
              <LoadingStatusRow
                c={c}
                tone="neutral"
                testId="elia-avd-studio-missing-sdk-ok"
                text="El SDK Android está listo, pero falta Android Studio. Configúralo en Entorno local o indica studio64.exe abajo."
              />
            )}

            {!caps.sdk_path && caps.suggested_sdk_path && (
              <div style={{ fontSize: 12, color: c.muted, marginBottom: 12, lineHeight: 1.5 }}>
                SDK sugerido: {caps.suggested_sdk_path}
                {onOpenEnvironmentSettings ? (
                  <>
                    {" "}
                    ·{" "}
                    <button
                      type="button"
                      onClick={onOpenEnvironmentSettings}
                      style={{
                        border: "none",
                        background: "transparent",
                        color: c.primary,
                        cursor: "pointer",
                        padding: 0,
                        fontSize: 12,
                        textDecoration: "underline",
                      }}
                    >
                      Configurar en Entorno local
                    </button>
                  </>
                ) : null}
              </div>
            )}

            {templates.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
                {templates.map((tpl) => (
                  <label
                    key={tpl.id}
                    style={{
                      display: "flex",
                      gap: 10,
                      alignItems: "flex-start",
                      padding: 12,
                      borderRadius: 12,
                      border: `1px solid ${templateId === tpl.id ? c.primary : c.border}`,
                      background: templateId === tpl.id ? c.neutralBg : c.inputBg,
                      cursor: "pointer",
                    }}
                  >
                    <input
                      type="radio"
                      name="avd-template"
                      checked={templateId === tpl.id}
                      onChange={() => setTemplateId(tpl.id)}
                      style={{ marginTop: 3 }}
                    />
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 14, color: c.text }}>{tpl.label}</div>
                      <div style={{ fontSize: 12, color: c.muted, lineHeight: 1.45 }}>
                        {tpl.description} · ~{tpl.estimated_gb} GB
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            )}

            <div
              style={{
                borderTop: `1px solid ${c.border}`,
                paddingTop: 14,
                marginBottom: 14,
              }}
            >
              <div style={{ fontWeight: 700, fontSize: 13, color: c.text, marginBottom: 8 }}>
                Configuración manual (todos los planes)
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button
                  type="button"
                  data-testid="elia-avd-open-studio"
                  onClick={handleOpenStudio}
                  style={{
                    padding: "8px 14px",
                    borderRadius: 8,
                    border: `1px solid ${c.inputBorder}`,
                    background: c.inputBg,
                    color: c.text,
                    cursor: "pointer",
                    fontSize: 13,
                  }}
                >
                  Abrir Android Studio
                </button>
                <button
                  type="button"
                  data-testid="elia-avd-recheck"
                  onClick={handleRecheck}
                  style={{
                    padding: "8px 14px",
                    borderRadius: 8,
                    border: `1px solid ${c.inputBorder}`,
                    background: c.inputBg,
                    color: c.text,
                    cursor: "pointer",
                    fontSize: 13,
                  }}
                >
                  Comprobar de nuevo
                </button>
                {onOpenEnvironmentSettings ? (
                  <button
                    type="button"
                    data-testid="elia-avd-env-settings"
                    onClick={onOpenEnvironmentSettings}
                    style={{
                      padding: "8px 14px",
                      borderRadius: 8,
                      border: `1px solid ${c.inputBorder}`,
                      background: c.inputBg,
                      color: c.text,
                      cursor: "pointer",
                      fontSize: 13,
                    }}
                  >
                    Entorno local…
                  </button>
                ) : null}
              </div>
              {studioMsg && (
                <div style={{ fontSize: 12, color: c.muted, marginTop: 8, lineHeight: 1.5 }}>
                  {studioMsg}
                </div>
              )}
              {studioPanelOpen && (
                <div style={{ marginTop: 10 }}>
                  <AndroidStudioPathPanel
                    c={c}
                    open={studioPanelOpen}
                    sdkOk={studioSdkOk}
                    onOpenEnvironmentSettings={onOpenEnvironmentSettings}
                    onClose={() => setStudioPanelOpen(false)}
                    onOpened={(message) => {
                      setStudioMsg(message);
                      setStudioPanelOpen(false);
                    }}
                  />
                </div>
              )}
            </div>

            {msg && (
              <div style={{ fontSize: 12, color: c.errorTitle, marginBottom: 12 }}>{msg}</div>
            )}
          </>
        )}

        {step === "working" && (
          <LoadingStatusRow
            c={c}
            text={msg || "Creando AVD…"}
            loading
            testId="elia-avd-wizard-working"
          />
        )}

        {step === "done" && (
          <LoadingStatusRow
            c={c}
            text={msg || "AVD listo."}
            tone="success"
            testId="elia-avd-wizard-done"
          />
        )}

        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 16 }}>
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
            {step === "done" ? "Cerrar" : "Cancelar"}
          </button>
          {step === "intro" && caps?.orchestration_allowed && (
            <button
              type="button"
              data-testid="elia-avd-wizard-run"
              onClick={runWizard}
              disabled={!selected}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                background: c.primary,
                color: c.primaryFg,
                border: "none",
                cursor: selected ? "pointer" : "not-allowed",
              }}
            >
              Crear AVD automáticamente
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
