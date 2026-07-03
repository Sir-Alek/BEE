import React from "react";
import type { AiCapabilitiesResponse } from "../api";
import { postAiSetupWizardComplete } from "../api";
import {
  downloadStatusMessage,
  pollAiDownload,
  refreshAiCapabilitiesAfterSetup,
  startProfileDownload,
  verifyProfileInstall,
} from "../hooks/aiModelSetup";
import { EliaButton, EliaModalOverlay, EliaModalPanel } from "./ui";

type Props = {
  c: Record<string, string>;
  open: boolean;
  setup: NonNullable<AiCapabilitiesResponse["setup"]>;
  onClose: () => void;
  onUpdated: (caps: AiCapabilitiesResponse) => void;
};

function profileLabel(profile: string): string {
  if (profile === "lite") return "ELIA Lite";
  if (profile === "standard") return "ELIA Standard";
  return "IA local no disponible";
}

export function AiSetupWizardModal(props: Props) {
  const { c, open, setup, onClose, onUpdated } = props;
  const [step, setStep] = React.useState<"intro" | "working" | "done">("intro");
  const [busy, setBusy] = React.useState(false);
  const [msg, setMsg] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!open) return;
    setStep(setup.profile_ready ? "done" : setup.assigned_profile === "off" ? "intro" : "intro");
    setMsg(null);
    setBusy(false);
  }, [open, setup.profile_ready, setup.assigned_profile]);

  if (!open) return null;

  const assigned = setup.assigned_profile;
  const isOff = assigned === "off";
  const downloadGb = setup.download_size_hint_gb ?? (assigned === "lite" ? 2.5 : 10);

  const finishWizard = async () => {
    await postAiSetupWizardComplete();
    onUpdated(await refreshAiCapabilitiesAfterSetup());
    onClose();
  };

  const runDownload = () => {
    setBusy(true);
    setStep("working");
    setMsg("Iniciando descarga…");
    void (async () => {
      try {
        const profile = assigned === "lite" || assigned === "standard" ? assigned : "auto";
        await startProfileDownload(profile);
        const st = await pollAiDownload((s) => setMsg(downloadStatusMessage(s) || "Descargando…"));
        if (st.errors.length) {
          setMsg(st.errors.join("; "));
          setStep("intro");
          return;
        }
        const verified = await verifyProfileInstall(profile);
        if (!verified.ok) {
          setMsg("Descarga terminada pero la verificación falló. Revisa los archivos o reintenta.");
          setStep("intro");
          return;
        }
        setStep("done");
        setMsg("Modelos listos. ELIA activará IA cuando haya RAM libre suficiente.");
        onUpdated(await refreshAiCapabilitiesAfterSetup());
      } catch (e: unknown) {
        setMsg(String((e as Error)?.message ?? e));
        setStep("intro");
      } finally {
        setBusy(false);
      }
    })();
  };

  const runVerifyManual = () => {
    setBusy(true);
    setMsg(null);
    void (async () => {
      try {
        const profile = assigned === "lite" || assigned === "standard" ? assigned : "auto";
        const v = await verifyProfileInstall(profile);
        if (v.ok) {
          setStep("done");
          setMsg("Modelos detectados correctamente.");
          onUpdated(await refreshAiCapabilitiesAfterSetup());
        } else {
          setMsg("No se encontraron modelos válidos. Descarga desde aquí o copia los archivos manualmente.");
        }
      } catch (e: unknown) {
        setMsg(String((e as Error)?.message ?? e));
      } finally {
        setBusy(false);
      }
    })();
  };

  return (
    <EliaModalOverlay testId="elia-ai-setup-wizard" ariaLabel="Configuración de IA local" onClose={() => {}} zIndex={1200}>
      <EliaModalPanel onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520, padding: "24px 28px" }}>
        <div style={{ fontWeight: 800, fontSize: 18, color: c.text, marginBottom: 6 }}>
          Configuración de IA local
        </div>
        <div style={{ fontSize: 13, color: c.muted, marginBottom: 16, lineHeight: 1.5 }}>
          Bienvenido a ELIA. Configura el motor de IA local para Doc-to-BDD, locators y asistencia
          en pruebas. Sin modelos instalados, ELIA usa heurísticas deterministas.
        </div>

        <div
          style={{
            background: c.neutralBg,
            border: `1px solid ${c.border}`,
            borderRadius: 12,
            padding: 14,
            marginBottom: 16,
            fontSize: 13,
            lineHeight: 1.55,
          }}
        >
          <div>
            <b>Equipo:</b> {setup.ram_available_gb ?? "?"} GB libres / {setup.ram_total_gb ?? "?"} GB total
          </div>
          {!isOff && (
            <div style={{ marginTop: 6 }}>
              <b>Perfil recomendado:</b> {profileLabel(assigned)}
            </div>
          )}
          {!isOff && (
            <div style={{ marginTop: 6, color: setup.ram_free_ok ? c.text : "#b45309" }}>
              RAM libre mínima: {setup.ram_min_free_gb} GB
              {setup.ram_free_ok ? " (OK)" : " — cierra apps pesadas antes de usar IA"}
            </div>
          )}
          {isOff && (
            <div style={{ marginTop: 8, color: c.muted }}>
              Tu equipo tiene menos de 8 GB RAM. La IA local no está disponible; ELIA seguirá con
              heurísticas.
            </div>
          )}
          {!isOff && step === "intro" && (
            <div style={{ marginTop: 8, color: c.muted }}>
              Descarga estimada: ~{downloadGb} GB en disco
              {assigned === "standard" ? " (dos componentes; uno activo en memoria a la vez)" : ""}.
            </div>
          )}
          {step === "done" && (
            <div style={{ marginTop: 8, color: "#15803d", fontWeight: 600 }}>
              Perfil listo para inferencia local.
            </div>
          )}
        </div>

        {msg && (
          <div style={{ fontSize: 13, marginBottom: 14, color: c.text, lineHeight: 1.45 }}>{msg}</div>
        )}

        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, justifyContent: "flex-end" }}>
          {isOff ? (
            <EliaButton variant="primary" size="sm" disabled={busy} onClick={() => void finishWizard()}>
              Entendido, continuar
            </EliaButton>
          ) : step === "done" ? (
            <EliaButton variant="primary" size="sm" disabled={busy} onClick={() => void finishWizard()}>
              Empezar a usar ELIA
            </EliaButton>
          ) : (
            <>
              <EliaButton variant="ghost" size="sm" disabled={busy} onClick={onClose}>
                Configurar más tarde
              </EliaButton>
              {!busy && step === "intro" && (
                <EliaButton variant="ghost" size="sm" onClick={runVerifyManual}>
                  Ya los instalé
                </EliaButton>
              )}
              <EliaButton variant="primary" size="sm" disabled={busy} onClick={runDownload}>
                {busy ? "Descargando…" : "Descargar ahora"}
              </EliaButton>
            </>
          )}
        </div>

        {!isOff && (
          <div style={{ marginTop: 14, fontSize: 11, color: c.muted, lineHeight: 1.4 }}>
            Carpeta: {setup.models_root}
            {" · "}
            Puedes reanudar desde Configuración → Inteligencia.
          </div>
        )}
      </EliaModalPanel>
    </EliaModalOverlay>
  );
}
