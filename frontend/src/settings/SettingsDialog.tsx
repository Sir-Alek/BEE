import React from "react";
import {
  activateLicense,
  clearAiMemory,
  deleteAiMemoryEntry,
  exportAiMemory,
  getAiCapabilities,
  getAiMemoryEntries,
  getAiSetupDownloadStatus,
  getModulesStatus,
  importAiMemory,
  postAiSetupDownload,
  postAiSetupVerify,
  putAiPreferences,
  putEliaConnectors,
  testEliaConnector,
  type AiCapabilitiesResponse,
  type AiMemoryEntryRow,
  type AiMemoryStatusResponse,
  type AiMode,
  type AppAboutResponse,
} from "../api";
import { copyTextToClipboard, modalFieldStyle } from "../app/utils";
import {
  formatLicenseStatusLabel,
  type LicenseState,
} from "../app/licenseUtils";
import type { SettingsTabId } from "../app/settingsTabs";
import { emptyAzureDevOpsCreds, emptyGitCreds, emptyJiraCreds, emptyValueEdgeCreds, newConnectorProfile } from "../connectorDefaults";
import { parseLicenseDisplayBlocks } from "../licenseTextFormat";
import type { EliaConnectorProfile } from "../types";
import { BetaFeedbackLink } from "../components/BetaFeedbackLink";
// Versión comercial (≥1.0): descomentar y usar en Licencia en lugar de BetaFeedbackLink.
// import { SupportSettingsContact } from "../components/SupportSettingsContact";
import { useConnectorContext } from "../context/ConnectorContext";
import { useLicenseContext } from "../context/LicenseContext";
import { useSettingsUiContext } from "../context/SettingsUiContext";

export type SettingsDialogProps = {
  open: boolean;
  onClose: () => void;
};

export function SettingsDialog(props: SettingsDialogProps) {
  if (!props.open) return null;
  const { onClose } = props;
  const [aiDownloadBusy, setAiDownloadBusy] = React.useState(false);
  const [aiDownloadMsg, setAiDownloadMsg] = React.useState<string | null>(null);
  const [aiLearnOpen, setAiLearnOpen] = React.useState(false);
  const [aiMemoryEntries, setAiMemoryEntries] = React.useState<AiMemoryEntryRow[]>([]);
  const {
    c,
    dark,
    toggleTheme,
    visibleSettingsTabs,
    settingsTab,
    setSettingsTab,
    aiCaps,
    aiPrefsSaving,
    setAiPrefsSaving,
    setAiCaps,
    aiMemoryOpen,
    setAiMemoryOpen,
    aiMemoryStatus,
    aiMemoryTeamPassphrase,
    setAiMemoryTeamPassphrase,
    aiMemoryImportMode,
    setAiMemoryImportMode,
    aiMemoryImportFile,
    setAiMemoryImportFile,
    aiMemoryBusy,
    setAiMemoryBusy,
    aiMemoryMsg,
    setAiMemoryMsg,
    refreshAiMemoryStatus,
    setErrorText,
    setModules,
    aboutInfo,
    aboutChangelogOpen,
    setAboutChangelogOpen,
    reopenAiWizard,
  } = useSettingsUiContext();
  const {
    license,
    activationKey,
    setActivationKey,
    licenseActivateMsg,
    setLicenseActivateMsg,
    licenseFpVisible,
    setLicenseFpVisible,
    fpCopyAck,
    setFpCopyAck,
    setLicense,
    refreshLicense,
  } = useLicenseContext();
  const {
    connectorProfiles,
    setConnectorProfiles,
    settingsProfileId,
    setSettingsProfileId,
    settingsTestMsg,
    setSettingsTestMsg,
    settingsSaveMsg,
    setSettingsSaveMsg,
    persistConnectorProfiles,
    duplicateConnectorProfile,
    deleteConnectorProfile,
  } = useConnectorContext();

  const patchAiPreferences = (patch: Parameters<typeof putAiPreferences>[0]) => {
    setAiPrefsSaving(true);
    void (async () => {
      try {
        const next = await putAiPreferences(patch);
        setAiCaps(next);
      } catch (e: unknown) {
        setErrorText(String((e as Error)?.message ?? e));
      } finally {
        setAiPrefsSaving(false);
      }
    })();
  };

  React.useEffect(() => {
    if (!props.open || settingsTab !== "ai" || !aiLearnOpen) return;
    void getAiMemoryEntries()
      .then((r) => setAiMemoryEntries(r.entries))
      .catch(() => setAiMemoryEntries([]));
  }, [props.open, settingsTab, aiLearnOpen, aiMemoryStatus?.entries]);

  return (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Configuración"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 100000,
            background: "rgba(15, 23, 42, 0.55)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 16,
          }}
          onClick={() => onClose()}
        >
          <div
            data-testid="elia-settings-dialog"
            style={{
              width: "min(680px, 100%)",
              maxHeight: "min(92vh, 920px)",
              overflow: "auto",
              borderRadius: 16,
              border: `1px solid ${c.border}`,
              background: c.surface,
              boxShadow: c.shadow,
              padding: 22,
              color: c.text,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
              <div style={{ fontSize: 18, fontWeight: 800, flex: 1 }}>Configuración</div>
              <button
                type="button"
                onClick={() => onClose()}
                style={{
                  border: `1px solid ${c.btnGhostBorder}`,
                  background: c.btnGhostBg,
                  color: c.text,
                  borderRadius: 10,
                  padding: "6px 12px",
                  cursor: "pointer",
                }}
              >
                Cerrar
              </button>
            </div>

            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 6,
                marginBottom: 16,
                padding: 4,
                borderRadius: 12,
                border: `1px solid ${c.border}`,
                background: c.neutralBg,
              }}
            >
              {visibleSettingsTabs.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  data-testid={`elia-settings-tab-${t.id}`}
                  onClick={() => setSettingsTab(t.id)}
                  style={{
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: `1px solid ${settingsTab === t.id ? c.primary : c.btnGhostBorder}`,
                    background: settingsTab === t.id ? c.primary : c.btnGhostBg,
                    color: settingsTab === t.id ? c.primaryFg : c.text,
                    fontWeight: settingsTab === t.id ? 700 : 500,
                    fontSize: 13,
                    cursor: "pointer",
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {settingsTab === "general" && (
            <div
              style={{
                border: `1px solid ${c.border}`,
                borderRadius: 12,
                padding: 14,
                marginBottom: 14,
                background: c.neutralBg,
              }}
            >
              <div style={{ fontWeight: 800, marginBottom: 10 }}>Apariencia</div>
              <label
                htmlFor="elia-theme-toggle"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 12,
                  cursor: "pointer",
                  fontSize: 14,
                }}
              >
                <span>{dark ? "Modo oscuro activo" : "Modo claro activo"}</span>
                <input
                  id="elia-theme-toggle"
                  type="checkbox"
                  checked={dark}
                  onChange={() => toggleTheme()}
                  style={{ position: "absolute", opacity: 0, width: 1, height: 1 }}
                />
                <span
                  style={{
                    position: "relative",
                    width: 44,
                    height: 26,
                    borderRadius: 999,
                    background: dark ? c.primary : c.border,
                    flexShrink: 0,
                  }}
                  aria-hidden
                >
                  <span
                    style={{
                      position: "absolute",
                      top: 3,
                      left: dark ? 22 : 3,
                      width: 20,
                      height: 20,
                      borderRadius: "50%",
                      background: "#fff",
                      transition: "left 160ms ease",
                    }}
                  />
                </span>
              </label>
            </div>
            )}

            {settingsTab === "ai" && (
            <>
            <div
              style={{
                border: `1px solid ${c.border}`,
                borderRadius: 12,
                padding: 14,
                marginBottom: 14,
                background: c.neutralBg,
              }}
            >
              <div style={{ fontWeight: 800, marginBottom: 4 }}>IA (Local)</div>
              <div style={{ fontSize: 12, color: c.muted, marginBottom: 12 }}>
                {aiCaps?.brand_line ?? "Evolving Learning & Intelligent Automation"} — activa por defecto en modo automático.
              </div>
              {(["auto", "on", "off"] as AiMode[]).map((m) => (
                <label
                  key={m}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 10,
                    marginBottom: 10,
                    cursor: aiPrefsSaving ? "wait" : "pointer",
                    fontSize: 14,
                    opacity: aiPrefsSaving ? 0.7 : 1,
                  }}
                >
                  <input
                    type="radio"
                    name="elia-ai-mode"
                    checked={(aiCaps?.preferences.mode ?? "auto") === m}
                    disabled={aiPrefsSaving}
                    onChange={() => {
                      setAiPrefsSaving(true);
                      void (async () => {
                        try {
                          const next = await putAiPreferences({ mode: m });
                          setAiCaps(next);
                        } catch (e: unknown) {
                          setErrorText(String((e as Error)?.message ?? e));
                        } finally {
                          setAiPrefsSaving(false);
                        }
                      })();
                    }}
                    style={{ marginTop: 3 }}
                  />
                  <span>
                    <b>
                      {m === "auto"
                        ? "Automático (recomendado)"
                        : m === "on"
                          ? "Siempre activada"
                          : "Modo rápido (sin IA)"}
                    </b>
                    <span style={{ display: "block", fontSize: 12, color: c.muted, marginTop: 2 }}>
                      {m === "auto"
                        ? "Standard (>8 GB RAM, ≥5 GB libres) o Lite (≤8 GB, ≥4 GB libres). Sin margen → heurísticas."
                        : m === "on"
                          ? "Fuerza IA si los modelos están disponibles; ignora el umbral de RAM libre (puede ir muy lento o fallar)."
                          : "Conversiones heurísticas deterministas, sin revisión de IA."}
                    </span>
                  </span>
                </label>
              ))}
              <div
                style={{
                  marginTop: 12,
                  paddingTop: 12,
                  borderTop: `1px solid ${c.border}`,
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                }}
              >
                <div style={{ fontWeight: 700, fontSize: 13 }}>Aprendizaje y Gherkin</div>
                <label style={{ display: "flex", gap: 8, fontSize: 13, cursor: aiPrefsSaving ? "wait" : "pointer" }}>
                  <input
                    type="checkbox"
                    checked={aiCaps?.preferences.gherkin_keywords_english !== false}
                    disabled={aiPrefsSaving}
                    onChange={(e) =>
                      patchAiPreferences({ gherkin_keywords_english: e.target.checked })
                    }
                  />
                  <span>
                    Keywords Gherkin en inglés (Given/When/Then) — recomendado para Behave
                    <span style={{ display: "block", fontSize: 11, color: c.muted, marginTop: 2 }}>
                      El texto del paso puede seguir en español; solo afecta las palabras reservadas.
                    </span>
                  </span>
                </label>
                <label style={{ display: "flex", gap: 8, fontSize: 13, cursor: aiPrefsSaving ? "wait" : "pointer" }}>
                  <input
                    type="checkbox"
                    checked={aiCaps?.preferences.memory_auto_learn !== false}
                    disabled={aiPrefsSaving}
                    onChange={(e) => patchAiPreferences({ memory_auto_learn: e.target.checked })}
                  />
                  <span>Recordar correcciones al aceptar features (solo con IA activa)</span>
                </label>
                <label style={{ display: "flex", gap: 8, fontSize: 13, cursor: aiPrefsSaving ? "wait" : "pointer" }}>
                  <input
                    type="checkbox"
                    checked={aiCaps?.preferences.memory_learn_after_retry === true}
                    disabled={aiPrefsSaving}
                    onChange={(e) =>
                      patchAiPreferences({ memory_learn_after_retry: e.target.checked })
                    }
                  />
                  <span>
                    También aprender al aceptar tras un reintento (aunque no edites el texto)
                    <span style={{ display: "block", fontSize: 11, color: c.muted, marginTop: 2 }}>
                      Opcional; la IA usa como máximo{" "}
                      {aiMemoryStatus?.prompt_examples_limit ?? 3} ejemplos recientes por prompt (de hasta{" "}
                      {aiMemoryStatus?.max_entries ?? 80} guardados).
                    </span>
                  </span>
                </label>
              </div>
              {aiCaps && (
                <div style={{ fontSize: 12, color: c.muted, marginTop: 8, lineHeight: 1.4 }}>
                  <div>{aiCaps.resolution.message}</div>
                  {aiCaps.capability.profile && (
                    <div style={{ marginTop: 6 }}>
                      Perfil asignado: <b>{aiCaps.capability.profile}</b>
                      {aiCaps.capability.runtime_profile &&
                      aiCaps.capability.runtime_profile !== aiCaps.capability.profile
                        ? ` (runtime: ${aiCaps.capability.runtime_profile})`
                        : ""}
                    </div>
                  )}
                  {aiCaps.capability.ram_total_gb != null && (
                    <div style={{ marginTop: 6 }}>
                      RAM: {aiCaps.capability.ram_available_gb ?? "?"} GB libres /{" "}
                      {aiCaps.capability.ram_total_gb} GB total (mín. {aiCaps.capability.ram_min_free_gb}{" "}
                      libres, {aiCaps.capability.ram_min_total_gb} total).
                    </div>
                  )}
                  {aiCaps.capability.reasons.length > 0 && (
                    <ul style={{ margin: "8px 0 0 16px", padding: 0 }}>
                      {aiCaps.capability.reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
              {aiCaps?.setup && (
                <div
                  style={{
                    marginTop: 12,
                    paddingTop: 12,
                    borderTop: `1px solid ${c.border}`,
                  }}
                >
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Motor de IA local</div>
                  <div style={{ fontSize: 12, color: c.muted, marginBottom: 8 }}>
                    Perfil Standard (~10 GB en disco) o Lite (~2,5 GB). ELIA elige según la RAM de tu equipo.
                  </div>
                  <div style={{ fontSize: 12, marginBottom: 8 }}>
                    Lite {aiCaps.setup.lite_ready ? "✓" : "—"} · Standard{" "}
                    {aiCaps.setup.standard_ready ? "✓" : "—"}
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    <button
                      type="button"
                      disabled={aiDownloadBusy}
                      onClick={() => {
                        setAiDownloadBusy(true);
                        setAiDownloadMsg(null);
                        void (async () => {
                          try {
                            await postAiSetupDownload("auto");
                            setAiDownloadMsg("Descarga iniciada…");
                            for (let i = 0; i < 360; i++) {
                              await new Promise((r) => setTimeout(r, 2000));
                              const st = await getAiSetupDownloadStatus();
                              if (st.errors.length) {
                                setAiDownloadMsg(st.errors.join("; "));
                              } else if (st.done) {
                                setAiDownloadMsg(
                                  st.completed.length
                                    ? `Completado: ${st.completed.join(", ")}`
                                    : "Descarga finalizada.",
                                );
                                setAiCaps(await getAiCapabilities());
                                break;
                              } else if (st.current) {
                                setAiDownloadMsg(`Descargando ${st.current}…`);
                              }
                              if (!st.active && st.done) break;
                            }
                          } catch (e: unknown) {
                            setAiDownloadMsg(String((e as Error)?.message ?? e));
                          } finally {
                            setAiDownloadBusy(false);
                          }
                        })();
                      }}
                      style={{
                        padding: "6px 12px",
                        borderRadius: 8,
                        border: `1px solid ${c.border}`,
                        background: aiDownloadBusy ? c.buttonDisabledBg : c.primary,
                        color: "#fff",
                        cursor: aiDownloadBusy ? "wait" : "pointer",
                        fontSize: 12,
                      }}
                    >
                      {aiDownloadBusy ? "Descargando…" : "Descargar perfil recomendado"}
                    </button>
                    <button
                      type="button"
                      disabled={aiDownloadBusy}
                      onClick={() => {
                        void (async () => {
                          try {
                            const v = await postAiSetupVerify("auto");
                            setAiDownloadMsg(
                              v.ok ? "Verificación OK" : "Verificación fallida — revisa modelos",
                            );
                            setAiCaps(await getAiCapabilities());
                          } catch (e: unknown) {
                            setAiDownloadMsg(String((e as Error)?.message ?? e));
                          }
                        })();
                      }}
                      style={{
                        padding: "6px 12px",
                        borderRadius: 8,
                        border: `1px solid ${c.border}`,
                        background: c.neutralBg,
                        cursor: "pointer",
                        fontSize: 12,
                      }}
                    >
                      Verificar integridad
                    </button>
                    {(!aiCaps.setup.wizard_completed || !aiCaps.setup.profile_ready) && (
                      <button
                        type="button"
                        data-testid="elia-ai-reopen-wizard"
                        disabled={aiDownloadBusy}
                        onClick={reopenAiWizard}
                        style={{
                          padding: "6px 12px",
                          borderRadius: 8,
                          border: `1px solid ${c.border}`,
                          background: c.neutralBg,
                          cursor: aiDownloadBusy ? "wait" : "pointer",
                          fontSize: 12,
                        }}
                      >
                        Reabrir asistente de IA
                      </button>
                    )}
                  </div>
                  {aiDownloadMsg && (
                    <div style={{ fontSize: 12, marginTop: 8, color: c.text }}>{aiDownloadMsg}</div>
                  )}
                </div>
              )}
            </div>

            <div
              data-testid="elia-ai-learn-accordion"
              style={{
                border: `1px solid ${c.border}`,
                borderRadius: 12,
                marginBottom: 14,
                background: c.neutralBg,
                overflow: "hidden",
              }}
            >
              <button
                type="button"
                data-testid="elia-ai-learn-toggle"
                onClick={() => setAiLearnOpen((open) => !open)}
                aria-expanded={aiLearnOpen}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "12px 14px",
                  border: "none",
                  background: "transparent",
                  color: c.text,
                  cursor: "pointer",
                  textAlign: "left",
                  fontSize: 14,
                  fontWeight: 700,
                }}
              >
                <span style={{ fontSize: 11, color: c.muted, width: 14 }}>{aiLearnOpen ? "▾" : "▸"}</span>
                <span>Qué aprendió ELIA</span>
                <span style={{ marginLeft: "auto", fontSize: 12, fontWeight: 500, color: c.muted }}>
                  {aiMemoryStatus
                    ? `${aiMemoryStatus.entries} guardados · ${aiMemoryStatus.prompt_examples_limit} en prompts`
                    : "—"}
                </span>
              </button>
              {aiLearnOpen && (
                <div
                  style={{
                    padding: "0 14px 14px",
                    borderTop: `1px solid ${c.border}`,
                    display: "flex",
                    flexDirection: "column",
                    gap: 10,
                  }}
                >
                  <div style={{ fontSize: 12, color: c.muted, lineHeight: 1.45, paddingTop: 12 }}>
                    Correcciones locales usadas como ejemplos few-shot en Doc-to-BDD y grabaciones web.
                    El límite de almacenamiento ({aiMemoryStatus?.max_entries ?? 80}) conserva historial
                    y exportación; la mejora por inferencia depende sobre todo de los{" "}
                    {aiMemoryStatus?.prompt_examples_limit ?? 3} ejemplos más recientes inyectados en cada prompt.
                  </div>
                  {aiMemoryEntries.length === 0 ? (
                    <div style={{ fontSize: 12, color: c.muted }}>Sin ejemplos guardados aún.</div>
                  ) : (
                    <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
                      {aiMemoryEntries.map((entry) => (
                        <li
                          key={entry.script_fp}
                          style={{
                            border: `1px solid ${c.border}`,
                            borderRadius: 8,
                            padding: "8px 10px",
                            fontSize: 11,
                            lineHeight: 1.4,
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 4 }}>
                            <span style={{ color: c.muted }}>
                              {entry.source === "web_capture"
                                ? "Grabación web"
                                : entry.source === "doc_to_bdd"
                                  ? "Doc-to-BDD"
                                  : "General"}{" "}
                              · {new Date(entry.ts * 1000).toLocaleString()}
                            </span>
                            <button
                              type="button"
                              disabled={aiMemoryBusy}
                              onClick={() => {
                                setAiMemoryBusy(true);
                                void (async () => {
                                  try {
                                    await deleteAiMemoryEntry(entry.script_fp);
                                    await refreshAiMemoryStatus();
                                    const r = await getAiMemoryEntries();
                                    setAiMemoryEntries(r.entries);
                                  } catch (e) {
                                    setAiMemoryMsg(e instanceof Error ? e.message : "No se pudo eliminar.");
                                  } finally {
                                    setAiMemoryBusy(false);
                                  }
                                })();
                              }}
                              style={{
                                border: "none",
                                background: "transparent",
                                color: c.errorBody,
                                cursor: aiMemoryBusy ? "wait" : "pointer",
                                fontSize: 11,
                              }}
                            >
                              Eliminar
                            </button>
                          </div>
                          <div style={{ color: c.text }}>
                            <strong>Feature:</strong> {entry.feature_preview}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                  <button
                    type="button"
                    disabled={aiMemoryBusy || !aiMemoryStatus?.entries}
                    onClick={() => {
                      if (!window.confirm("¿Vaciar todos los ejemplos aprendidos en este equipo?")) return;
                      setAiMemoryBusy(true);
                      void (async () => {
                        try {
                          await clearAiMemory();
                          await refreshAiMemoryStatus();
                          setAiMemoryEntries([]);
                          setAiMemoryMsg("Memoria local vaciada.");
                        } catch (e) {
                          setAiMemoryMsg(e instanceof Error ? e.message : "No se pudo vaciar.");
                        } finally {
                          setAiMemoryBusy(false);
                        }
                      })();
                    }}
                    style={{
                      alignSelf: "flex-start",
                      padding: "8px 12px",
                      borderRadius: 8,
                      border: `1px solid ${c.border}`,
                      background: c.surface,
                      color: c.text,
                      cursor: aiMemoryBusy ? "wait" : "pointer",
                      fontSize: 12,
                    }}
                  >
                    Vaciar memoria local
                  </button>
                </div>
              )}
            </div>

            <div
              data-testid="elia-ai-memory-accordion"
              style={{
                border: `1px solid ${c.border}`,
                borderRadius: 12,
                marginBottom: 14,
                background: c.neutralBg,
                overflow: "hidden",
              }}
            >
              <button
                type="button"
                data-testid="elia-ai-memory-toggle"
                onClick={() => setAiMemoryOpen((open) => !open)}
                aria-expanded={aiMemoryOpen}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "12px 14px",
                  border: "none",
                  background: "transparent",
                  color: c.text,
                  cursor: "pointer",
                  textAlign: "left",
                  fontSize: 14,
                  fontWeight: 700,
                }}
              >
                <span style={{ fontSize: 11, color: c.muted, width: 14 }}>{aiMemoryOpen ? "▾" : "▸"}</span>
                <span>Compartir base de conocimiento</span>
                <span style={{ marginLeft: "auto", fontSize: 12, fontWeight: 500, color: c.muted }}>
                  {aiMemoryStatus
                    ? `${aiMemoryStatus.entries}/${aiMemoryStatus.max_entries} ejemplos`
                    : "— ejemplos"}
                </span>
              </button>
              {aiMemoryOpen && (
                <div
                  style={{
                    padding: "0 14px 14px",
                    borderTop: `1px solid ${c.border}`,
                    display: "flex",
                    flexDirection: "column",
                    gap: 12,
                  }}
                >
                  <div style={{ fontSize: 12, color: c.muted, lineHeight: 1.45, paddingTop: 12 }}>
                    Exporta o importa el historial de entrenamiento para unificar los criterios de la IA con tu
                    equipo de trabajo. La memoria local se guarda cifrada en este equipo; el archivo exportado usa
                    una frase de equipo compartida.
                  </div>
                  <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12, color: c.text }}>
                    Frase de equipo
                    <input
                      type="password"
                      data-testid="elia-ai-memory-passphrase"
                      value={aiMemoryTeamPassphrase}
                      onChange={(e) => setAiMemoryTeamPassphrase(e.target.value)}
                      placeholder="Misma frase al exportar e importar"
                      style={{
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: `1px solid ${c.inputBorder}`,
                        background: c.inputBg,
                        color: c.text,
                        fontSize: 14,
                      }}
                    />
                  </label>
                  <button
                    type="button"
                    data-testid="elia-ai-memory-export"
                    disabled={aiMemoryBusy || !aiMemoryTeamPassphrase.trim()}
                    onClick={() => {
                      setAiMemoryBusy(true);
                      setAiMemoryMsg(null);
                      void (async () => {
                        try {
                          const { blob, filename } = await exportAiMemory(aiMemoryTeamPassphrase.trim());
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement("a");
                          a.href = url;
                          a.download = filename;
                          a.click();
                          URL.revokeObjectURL(url);
                          setAiMemoryMsg("Memoria exportada correctamente.");
                        } catch (e) {
                          setAiMemoryMsg(e instanceof Error ? e.message : "No se pudo exportar.");
                        } finally {
                          setAiMemoryBusy(false);
                        }
                      })();
                    }}
                    style={{
                      alignSelf: "flex-start",
                      padding: "10px 14px",
                      borderRadius: 10,
                      border: "none",
                      background: aiMemoryBusy ? c.buttonDisabledBg : c.primary,
                      color: c.primaryFg,
                      cursor: aiMemoryBusy ? "wait" : "pointer",
                      fontSize: 13,
                    }}
                  >
                    Exportar memoria actual
                  </button>

                  <div style={{ fontSize: 13, fontWeight: 700, color: c.text, marginTop: 4 }}>
                    Importar base de conocimiento
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13, color: c.text }}>
                    <label style={{ display: "flex", gap: 8, alignItems: "flex-start", cursor: "pointer" }}>
                      <input
                        type="radio"
                        name="elia-ai-memory-import-mode"
                        checked={aiMemoryImportMode === "merge"}
                        onChange={() => setAiMemoryImportMode("merge")}
                        style={{ marginTop: 3 }}
                      />
                      <span>
                        <b>Fusionar (recomendado)</b>
                        <span style={{ display: "block", fontSize: 12, color: c.muted, marginTop: 2 }}>
                          Añade reglas sin borrar tu historial. En conflicto prevalece lo importado.
                        </span>
                      </span>
                    </label>
                    <label style={{ display: "flex", gap: 8, alignItems: "flex-start", cursor: "pointer" }}>
                      <input
                        type="radio"
                        name="elia-ai-memory-import-mode"
                        checked={aiMemoryImportMode === "replace"}
                        onChange={() => setAiMemoryImportMode("replace")}
                        style={{ marginTop: 3 }}
                      />
                      <span>
                        <b>Reemplazar por completo</b>
                        <span style={{ display: "block", fontSize: 12, color: c.muted, marginTop: 2 }}>
                          Borra toda la memoria local y la sustituye por el archivo cargado (irreversible).
                        </span>
                      </span>
                    </label>
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                    <input
                      type="file"
                      accept=".enc,.json,application/json"
                      data-testid="elia-ai-memory-import-file"
                      onChange={(e) => setAiMemoryImportFile(e.target.files?.[0] ?? null)}
                      style={{ fontSize: 12, color: c.text, maxWidth: "100%" }}
                    />
                    <button
                      type="button"
                      data-testid="elia-ai-memory-import"
                      disabled={aiMemoryBusy || !aiMemoryTeamPassphrase.trim() || !aiMemoryImportFile}
                      onClick={() => {
                        if (!aiMemoryImportFile) return;
                        setAiMemoryBusy(true);
                        setAiMemoryMsg(null);
                        void (async () => {
                          try {
                            const result = await importAiMemory({
                              teamPassphrase: aiMemoryTeamPassphrase.trim(),
                              mode: aiMemoryImportMode,
                              file: aiMemoryImportFile,
                            });
                            await refreshAiMemoryStatus();
                            setAiMemoryImportFile(null);
                            setAiMemoryMsg(
                              result.mode === "replace"
                                ? `Importación completa: ${result.total} ejemplo(s) en memoria.`
                                : `Fusión: ${result.added} añadido(s), ${result.updated} actualizado(s), total ${result.total}.`,
                            );
                          } catch (e) {
                            setAiMemoryMsg(e instanceof Error ? e.message : "No se pudo importar.");
                          } finally {
                            setAiMemoryBusy(false);
                          }
                        })();
                      }}
                      style={{
                        padding: "10px 14px",
                        borderRadius: 10,
                        border: "none",
                        background: aiMemoryBusy ? c.buttonDisabledBg : c.primary,
                        color: c.primaryFg,
                        cursor: aiMemoryBusy ? "wait" : "pointer",
                        fontSize: 13,
                      }}
                    >
                      Confirmar importación
                    </button>
                  </div>
                  {aiMemoryMsg && (
                    <div style={{ fontSize: 12, color: c.text, lineHeight: 1.45 }}>{aiMemoryMsg}</div>
                  )}
                </div>
              )}
            </div>
            </>
            )}

            {settingsTab === "license" && (
            <div
              style={{
                border: `1px solid ${c.border}`,
                borderRadius: 12,
                padding: 14,
                marginBottom: 14,
                background: c.neutralBg,
              }}
            >
              <div style={{ fontWeight: 800, marginBottom: 10 }}>Licencia</div>
              {license ? (
                <>
                  <div style={{ fontSize: 14, marginBottom: 12, color: c.text }}>
                    <span style={{ fontWeight: 600 }}>Estado actual: </span>
                    {formatLicenseStatusLabel(license)}
                  </div>
                  {!license.activated && license.reason === "not_activated" && (
                    <div
                      style={{
                        fontSize: 13,
                        color: c.text,
                        marginBottom: 12,
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: `1px solid ${c.licWarnBorder}`,
                        background: c.licWarnBg,
                      }}
                    >
                      <div style={{ marginBottom: 8 }}>
                        Para activar ELIA, envía este código a soporte.
                      </div>
                      <div
                        style={{
                          display: "flex",
                          flexWrap: "wrap",
                          gap: 8,
                          alignItems: "center",
                          wordBreak: "break-all",
                        }}
                      >
                        <span style={{ fontWeight: 600 }}>Huella de máquina:</span>
                        <code style={{ userSelect: "all", fontWeight: 700, fontSize: 13 }}>
                          {license.machine_fingerprint}
                        </code>
                        <button
                          type="button"
                          onClick={() => {
                            void (async () => {
                              const ok = await copyTextToClipboard(license.machine_fingerprint);
                              if (ok) {
                                setFpCopyAck(true);
                                window.setTimeout(() => setFpCopyAck(false), 2000);
                              } else {
                                setLicenseActivateMsg("No se pudo copiar. Selecciona el código manualmente.");
                              }
                            })();
                          }}
                          style={{
                            padding: "4px 10px",
                            borderRadius: 8,
                            border: `1px solid ${c.btnGhostBorder}`,
                            background: c.btnGhostBg,
                            color: c.text,
                            fontSize: 12,
                            fontWeight: 600,
                            cursor: "pointer",
                          }}
                        >
                          {fpCopyAck ? "Copiado" : "Copiar"}
                        </button>
                      </div>
                    </div>
                  )}
                  {license.reason === "license_expired" && (
                    <div
                      style={{
                        fontSize: 13,
                        color: c.text,
                        marginBottom: 12,
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: `1px solid ${c.licWarnBorder}`,
                        background: c.licWarnBg,
                      }}
                    >
                      <div style={{ marginBottom: 8 }}>
                        Tu licencia ha caducado. Copia tu huella y solicita extensión o una nueva clave por el
                        formulario de soporte.
                      </div>
                      <div
                        style={{
                          display: "flex",
                          flexWrap: "wrap",
                          gap: 8,
                          alignItems: "center",
                          wordBreak: "break-all",
                          marginBottom: 8,
                        }}
                      >
                        <span style={{ fontWeight: 600 }}>Huella de máquina:</span>
                        <code style={{ userSelect: "all", fontWeight: 700, fontSize: 13 }}>
                          {license.machine_fingerprint}
                        </code>
                        <button
                          type="button"
                          onClick={() => {
                            void (async () => {
                              const ok = await copyTextToClipboard(license.machine_fingerprint);
                              if (ok) {
                                setFpCopyAck(true);
                                window.setTimeout(() => setFpCopyAck(false), 2000);
                              } else {
                                setLicenseActivateMsg("No se pudo copiar. Selecciona el código manualmente.");
                              }
                            })();
                          }}
                          style={{
                            padding: "4px 10px",
                            borderRadius: 8,
                            border: `1px solid ${c.btnGhostBorder}`,
                            background: c.btnGhostBg,
                            color: c.text,
                            fontSize: 12,
                            fontWeight: 600,
                            cursor: "pointer",
                          }}
                        >
                          {fpCopyAck ? "Copiado" : "Copiar"}
                        </button>
                      </div>
                    </div>
                  )}
                  {license.activated && licenseFpVisible && (
                    <div
                      style={{
                        fontSize: 13,
                        color: c.text,
                        marginBottom: 12,
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: `1px solid ${c.border}`,
                        background: c.surface,
                      }}
                    >
                      <div style={{ marginBottom: 8 }}>
                        Huella de máquina actual (para ampliar módulos u obtener otra clave en soporte):
                      </div>
                      <div
                        style={{
                          display: "flex",
                          flexWrap: "wrap",
                          gap: 8,
                          alignItems: "center",
                          wordBreak: "break-all",
                        }}
                      >
                        <code style={{ userSelect: "all", fontWeight: 700, fontSize: 13 }}>
                          {license.machine_fingerprint}
                        </code>
                        <button
                          type="button"
                          onClick={() => {
                            void (async () => {
                              const ok = await copyTextToClipboard(license.machine_fingerprint);
                              if (ok) {
                                setFpCopyAck(true);
                                window.setTimeout(() => setFpCopyAck(false), 2000);
                              } else {
                                setLicenseActivateMsg("No se pudo copiar. Selecciona el código manualmente.");
                              }
                            })();
                          }}
                          style={{
                            padding: "4px 10px",
                            borderRadius: 8,
                            border: `1px solid ${c.btnGhostBorder}`,
                            background: c.btnGhostBg,
                            color: c.text,
                            fontSize: 12,
                            fontWeight: 600,
                            cursor: "pointer",
                          }}
                        >
                          {fpCopyAck ? "Copiado" : "Copiar"}
                        </button>
                      </div>
                    </div>
                  )}
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
                    <input
                      type="text"
                      data-testid="elia-license-key"
                      value={activationKey}
                      onChange={(e) => setActivationKey(e.target.value)}
                      placeholder="Introduce tu código de activación"
                      style={{
                        flex: "1 1 220px",
                        minWidth: 200,
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: `1px solid ${c.inputBorder}`,
                        background: c.inputBg,
                        color: c.text,
                        fontSize: 14,
                      }}
                    />
                    <button
                      type="button"
                      data-testid="elia-license-activate"
                      disabled={!activationKey.trim()}
                      onClick={() => {
                        setLicenseActivateMsg(null);
                        void (async () => {
                          try {
                            const r = await activateLicense(activationKey.trim());
                            if (r.ok) {
                              await refreshLicense();
                              setActivationKey("");
                              setLicenseFpVisible(false);
                              setFpCopyAck(false);
                              setLicenseActivateMsg("Licencia activada correctamente.");
                              const m = await getModulesStatus();
                              setModules(m);
                            } else {
                              setLicenseActivateMsg(r.message || "Clave no válida para esta máquina.");
                            }
                          } catch (e: unknown) {
                            setLicenseActivateMsg(String((e as Error)?.message ?? e));
                          }
                        })();
                      }}
                      style={{
                        padding: "10px 16px",
                        borderRadius: 10,
                        border: "none",
                        background: c.primary,
                        color: c.primaryFg,
                        fontWeight: 700,
                        fontSize: 14,
                        cursor: activationKey.trim() ? "pointer" : "not-allowed",
                        opacity: activationKey.trim() ? 1 : 0.55,
                      }}
                    >
                      Activar
                    </button>
                  </div>
                  {licenseActivateMsg && (
                    <div data-testid="elia-license-message" style={{ marginTop: 10, fontSize: 13, color: c.text }}>{licenseActivateMsg}</div>
                  )}
                  {license.activated && !licenseFpVisible && (
                    <button
                      type="button"
                      onClick={() => {
                        setLicenseActivateMsg(null);
                        void refreshLicense().then(() => setLicenseFpVisible(true));
                      }}
                      style={{
                        marginTop: 10,
                        padding: "6px 12px",
                        borderRadius: 8,
                        border: `1px solid ${c.btnGhostBorder}`,
                        background: c.btnGhostBg,
                        color: c.text,
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      Obtener huella de máquina
                    </button>
                  )}
                  <BetaFeedbackLink url={aboutInfo?.beta_feedback_url} c={c} variant="license" />
                  {/*
                  Versión comercial (≥1.0): quitar BetaFeedbackLink de arriba y usar:
                  <SupportSettingsContact
                    email={aboutInfo?.support_email ?? ""}
                    c={c}
                  />
                  */}
                </>
              ) : (
                <div style={{ fontSize: 13, color: c.muted }}>No se pudo consultar el estado de la licencia.</div>
              )}
            </div>
            )}

            {settingsTab === "connectors" && (
            <div
              style={{
                border: `1px solid ${c.border}`,
                borderRadius: 12,
                padding: 14,
                marginBottom: 14,
              }}
            >
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Conectores · ALM, Git y publicación BDD</div>
              <div style={{ color: c.muted, fontSize: 13, marginBottom: 12 }}>
                Perfiles para lectura (Jira/VE) y publicación multi-destino. Datos cifrados en disco (misma máquina).
                Solo red local (<code>127.0.0.1</code>).
              </div>

              <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", marginBottom: 12 }}>
                <label style={{ fontSize: 13, fontWeight: 600 }}>Perfil</label>
                <select
                  value={settingsProfileId}
                  onChange={(e) => setSettingsProfileId(e.target.value)}
                  style={{
                    flex: "1 1 240px",
                    minWidth: 200,
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: `1px solid ${c.inputBorder}`,
                    background: c.inputBg,
                    color: c.text,
                    fontSize: 14,
                  }}
                >
                  {connectorProfiles.length === 0 && <option value="">— Sin perfiles —</option>}
                  {connectorProfiles.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => {
                    const np = newConnectorProfile(connectorProfiles.length + 1);
                    setConnectorProfiles((l) => [...l, np]);
                    setSettingsProfileId(np.id);
                    setSettingsTestMsg(null);
                    setSettingsSaveMsg(null);
                  }}
                  style={{
                    padding: "10px 14px",
                    borderRadius: 10,
                    border: `1px solid ${c.primary}`,
                    background: c.primary,
                    color: c.primaryFg,
                    cursor: "pointer",
                    fontWeight: 700,
                  }}
                >
                  Añadir nuevo
                </button>
                {connectorProfiles.length > 0 && settingsProfileId && (
                  <>
                    <button
                      type="button"
                      onClick={duplicateConnectorProfile}
                      style={{
                        padding: "10px 14px",
                        borderRadius: 10,
                        border: `1px solid ${c.btnGhostBorder}`,
                        background: c.btnGhostBg,
                        color: c.text,
                        cursor: "pointer",
                        fontWeight: 600,
                      }}
                    >
                      Duplicar
                    </button>
                    <button
                      type="button"
                      onClick={deleteConnectorProfile}
                      style={{
                        padding: "10px 14px",
                        borderRadius: 10,
                        border: `1px solid ${c.licWarnBorder}`,
                        background: c.licWarnBg,
                        color: c.text,
                        cursor: "pointer",
                        fontWeight: 600,
                      }}
                    >
                      Eliminar
                    </button>
                  </>
                )}
              </div>

              {connectorProfiles.length === 0 && (
                <div style={{ fontSize: 13, color: c.muted, marginBottom: 8 }}>
                  Sin perfiles aún: pulsa «Añadir nuevo» para crear el primero.
                </div>
              )}

              {connectorProfiles.length > 0 && settingsProfileId && (
                <>
                  <div style={{ fontSize: 13, color: c.muted, marginBottom: 10 }}>
                    Edita el perfil seleccionado (Jira, Value Edge, Git, Azure DevOps). Usa «Guardar» al terminar.
                  </div>
                  <div style={{ marginBottom: 14 }}>
                    <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                      Nombre del perfil
                    </label>
                    <input
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.name ?? ""
                      }
                      onChange={(e) =>
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, name: e.target.value } : p,
                          ),
                        )
                      }
                      style={{
                        width: "100%",
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: `1px solid ${c.inputBorder}`,
                        background: c.inputBg,
                        color: c.text,
                      }}
                    />
                  </div>

                  <div style={{ fontWeight: 800, margin: "14px 0 8px" }}>Jira</div>
                  <div style={{ display: "grid", gap: 10 }}>
                    <input
                      placeholder="URL de instancia"
                      autoComplete="off"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.jira.url ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, jira: { ...p.jira, url: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Usuario / Email"
                      type="email"
                      autoComplete="off"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.jira.email ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, jira: { ...p.jira, email: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="API token"
                      type="password"
                      autoComplete="new-password"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.jira.api_token ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, jira: { ...p.jira, api_token: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <select
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.jira.mode ?? "vanilla"}
                      onChange={(e) => {
                        const v = e.target.value as "vanilla" | "xray";
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, jira: { ...p.jira, mode: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    >
                      <option value="vanilla">Modo Jira vanilla (descripción)</option>
                      <option value="xray">Modo Jira + Xray</option>
                    </select>
                    <input
                      placeholder="Project key (Xray)"
                      autoComplete="off"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.jira.project_key ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, jira: { ...p.jira, project_key: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Xray base URL (opcional)"
                      autoComplete="off"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.jira.xray_base_url ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, jira: { ...p.jira, xray_base_url: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Campo destino (description | acceptance)"
                      autoComplete="off"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.jira.target_field ?? "description"}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, jira: { ...p.jira, target_field: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Issue key por defecto"
                      autoComplete="off"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.jira.default_issue_key ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, jira: { ...p.jira, default_issue_key: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      const p = connectorProfiles.find((x) => x.id === settingsProfileId);
                      void (async () => {
                        setSettingsTestMsg(null);
                        try {
                          const r = await testEliaConnector({
                            kind: "jira",
                            jira: p?.jira ?? emptyJiraCreds(),
                            value_edge: p?.value_edge ?? emptyValueEdgeCreds(),
                          });
                          const data = r as { ok?: boolean; connection_ok?: boolean };
                          const okConn = data.connection_ok ?? data.ok ?? false;
                          setSettingsTestMsg(
                            okConn ? "Jira · conexión correcta." : "Jira · conexión rechazada o credenciales inválidas.",
                          );
                        } catch (err: unknown) {
                          setSettingsTestMsg(`Jira · ${String((err as Error)?.message ?? err)}`);
                        }
                      })();
                    }}
                    style={{
                      marginTop: 10,
                      padding: "8px 12px",
                      borderRadius: 10,
                      border: `1px solid ${c.btnGhostBorder}`,
                      background: c.btnGhostBg,
                      cursor: "pointer",
                    }}
                  >
                    Probar conexión · Jira
                  </button>

                  <div style={{ fontWeight: 800, margin: "14px 0 8px" }}>Value Edge</div>
                  <div style={{ display: "grid", gap: 10 }}>
                    <input
                      placeholder="URL de instancia"
                      autoComplete="off"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.value_edge.url ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId
                              ? { ...p, value_edge: { ...p.value_edge, url: v } }
                              : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Shared space ID"
                      autoComplete="off"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.value_edge.shared_space ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId
                              ? { ...p, value_edge: { ...p.value_edge, shared_space: v } }
                              : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Workspace ID"
                      autoComplete="off"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.value_edge.workspace ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId
                              ? { ...p, value_edge: { ...p.value_edge, workspace: v } }
                              : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder='Tech preview flag (ej. "true")'
                      autoComplete="off"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.value_edge
                          .tech_preview_flag ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId
                              ? { ...p, value_edge: { ...p.value_edge, tech_preview_flag: v } }
                              : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="URL de login (opcional)"
                      autoComplete="off"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.value_edge.login ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, value_edge: { ...p.value_edge, login: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Usuario"
                      autoComplete="off"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.value_edge.user ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, value_edge: { ...p.value_edge, user: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Contraseña"
                      type="password"
                      autoComplete="new-password"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.value_edge.password ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, value_edge: { ...p.value_edge, password: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="ID story/requerimiento por defecto (publicación BDD)"
                      autoComplete="off"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.value_edge.default_requirement_id ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId
                              ? { ...p, value_edge: { ...p.value_edge, default_requirement_id: v } }
                              : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      const p = connectorProfiles.find((x) => x.id === settingsProfileId);
                      void (async () => {
                        setSettingsTestMsg(null);
                        try {
                          const r = await testEliaConnector({
                            kind: "value_edge",
                            jira: p?.jira ?? emptyJiraCreds(),
                            value_edge: p?.value_edge ?? emptyValueEdgeCreds(),
                          });
                          const data = r as { ok?: boolean; connection_ok?: boolean };
                          const okConn = data.connection_ok ?? data.ok ?? false;
                          setSettingsTestMsg(
                            okConn ? "Value Edge · login correcto." : "Value Edge · login rechazado o credenciales inválidas.",
                          );
                        } catch (err: unknown) {
                          setSettingsTestMsg(`Value Edge · ${String((err as Error)?.message ?? err)}`);
                        }
                      })();
                    }}
                    style={{
                      marginTop: 10,
                      padding: "8px 12px",
                      borderRadius: 10,
                      border: `1px solid ${c.btnGhostBorder}`,
                      background: c.btnGhostBg,
                      cursor: "pointer",
                    }}
                  >
                    Probar conexión · Value Edge
                  </button>

                  <div style={{ fontWeight: 800, margin: "14px 0 8px" }}>Git (publicación .feature)</div>
                  <div style={{ display: "grid", gap: 10 }}>
                    <input
                      placeholder="URL repositorio (GitHub / GitLab / Azure Repos)"
                      autoComplete="off"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.git.repo_url ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) => (p.id === settingsProfileId ? { ...p, git: { ...p.git, repo_url: v } } : p)),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Token / PAT"
                      type="password"
                      autoComplete="new-password"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.git.token ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) => (p.id === settingsProfileId ? { ...p, git: { ...p.git, token: v } } : p)),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Rama (main)"
                      autoComplete="off"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.git.branch ?? "main"}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) => (p.id === settingsProfileId ? { ...p, git: { ...p.git, branch: v } } : p)),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Carpeta base (features/)"
                      autoComplete="off"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.git.base_path ?? "features/"}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) => (p.id === settingsProfileId ? { ...p, git: { ...p.git, base_path: v } } : p)),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      const p = connectorProfiles.find((x) => x.id === settingsProfileId);
                      void (async () => {
                        setSettingsTestMsg(null);
                        try {
                          const r = await testEliaConnector({
                            kind: "git",
                            jira: p?.jira ?? emptyJiraCreds(),
                            value_edge: p?.value_edge ?? emptyValueEdgeCreds(),
                            git: p?.git ?? emptyGitCreds(),
                          });
                          setSettingsTestMsg(r.ok ? `Git · ${r.message ?? "OK"}` : `Git · ${r.message ?? "falló"}`);
                        } catch (err: unknown) {
                          setSettingsTestMsg(`Git · ${String((err as Error)?.message ?? err)}`);
                        }
                      })();
                    }}
                    style={{
                      marginTop: 10,
                      padding: "8px 12px",
                      borderRadius: 10,
                      border: `1px solid ${c.btnGhostBorder}`,
                      background: c.btnGhostBg,
                      cursor: "pointer",
                    }}
                  >
                    Probar conexión · Git
                  </button>

                  <div style={{ fontWeight: 800, margin: "14px 0 8px" }}>Azure DevOps</div>
                  <div style={{ display: "grid", gap: 10 }}>
                    <input
                      placeholder="Organización"
                      autoComplete="off"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.azure_devops.org ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, azure_devops: { ...p.azure_devops, org: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Proyecto"
                      autoComplete="off"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.azure_devops.project ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, azure_devops: { ...p.azure_devops, project: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="PAT"
                      type="password"
                      autoComplete="new-password"
                      value={connectorProfiles.find((x) => x.id === settingsProfileId)?.azure_devops.pat ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId ? { ...p, azure_devops: { ...p.azure_devops, pat: v } } : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                    <input
                      placeholder="Work item ID por defecto"
                      autoComplete="off"
                      value={
                        connectorProfiles.find((x) => x.id === settingsProfileId)?.azure_devops.default_work_item_id ?? ""
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setConnectorProfiles((list) =>
                          list.map((p) =>
                            p.id === settingsProfileId
                              ? { ...p, azure_devops: { ...p.azure_devops, default_work_item_id: v } }
                              : p,
                          ),
                        );
                      }}
                      style={modalFieldStyle(c)}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      const p = connectorProfiles.find((x) => x.id === settingsProfileId);
                      void (async () => {
                        setSettingsTestMsg(null);
                        try {
                          const r = await testEliaConnector({
                            kind: "azure_devops",
                            jira: p?.jira ?? emptyJiraCreds(),
                            value_edge: p?.value_edge ?? emptyValueEdgeCreds(),
                            azure_devops: p?.azure_devops ?? emptyAzureDevOpsCreds(),
                          });
                          setSettingsTestMsg(
                            r.ok ? `Azure DevOps · ${r.message ?? "OK"}` : `Azure DevOps · ${r.message ?? "falló"}`,
                          );
                        } catch (err: unknown) {
                          setSettingsTestMsg(`Azure DevOps · ${String((err as Error)?.message ?? err)}`);
                        }
                      })();
                    }}
                    style={{
                      marginTop: 10,
                      padding: "8px 12px",
                      borderRadius: 10,
                      border: `1px solid ${c.btnGhostBorder}`,
                      background: c.btnGhostBg,
                      cursor: "pointer",
                    }}
                  >
                    Probar conexión · Azure DevOps
                  </button>
                </>
              )}

              {settingsTestMsg && (
                <div
                  style={{
                    marginTop: 12,
                    fontSize: 13,
                    color: c.text,
                    background: c.hintBg,
                    border: `1px solid ${c.hintBorder}`,
                    borderRadius: 10,
                    padding: 10,
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {settingsTestMsg}
                </div>
              )}
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, flexWrap: "wrap", marginTop: 14 }}>
                <button
                  type="button"
                  onClick={() => {
                    void (async () => {
                      setSettingsSaveMsg(null);
                      try {
                        await persistConnectorProfiles(connectorProfiles);
                        setSettingsSaveMsg("Guardado en el navegador y en el backend (si está disponible).");
                      } catch (e: unknown) {
                        setSettingsSaveMsg(`Error al guardar: ${String((e as Error)?.message ?? e)}`);
                      }
                    })();
                  }}
                  style={{
                    padding: "10px 16px",
                    borderRadius: 10,
                    border: "none",
                    background: c.primary,
                    color: c.primaryFg,
                    fontWeight: 800,
                    cursor: "pointer",
                  }}
                >
                  Guardar perfiles
                </button>
              </div>
              {settingsSaveMsg && (
                <div style={{ marginTop: 10, fontSize: 13, color: c.muted }}>{settingsSaveMsg}</div>
              )}
            </div>
            )}

            {settingsTab === "about" && (
            <div
              data-testid="elia-about-panel"
              style={{
                border: `1px solid ${c.border}`,
                borderRadius: 12,
                padding: 14,
                marginBottom: 14,
                background: c.neutralBg,
              }}
            >
              <div style={{ fontWeight: 800, marginBottom: 8 }}>Acerca de ELIA</div>
              {aboutInfo ? (
                <>
                  <div style={{ fontSize: 14, marginBottom: 6 }}>
                    <b>{aboutInfo.app_name}</b> — {aboutInfo.tagline}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      alignItems: "center",
                      gap: "8px 12px",
                      fontSize: 13,
                      color: c.muted,
                      marginBottom: 6,
                    }}
                  >
                    <span>
                      Versión: <span style={{ color: c.text }}>{aboutInfo.version_display}</span>
                    </span>
                    {aboutInfo.changelog.length > 0 && (
                      <button
                        type="button"
                        data-testid="elia-changelog-toggle"
                        aria-expanded={aboutChangelogOpen}
                        onClick={() => setAboutChangelogOpen((open) => !open)}
                        style={{
                          border: `1px solid ${c.border}`,
                          borderRadius: 999,
                          padding: "2px 10px",
                          fontSize: 12,
                          fontWeight: 600,
                          color: c.muted,
                          background: c.inputBg,
                          cursor: "pointer",
                        }}
                      >
                        {aboutChangelogOpen ? "▾ Ver novedades" : "▸ Ver novedades"}
                      </button>
                    )}
                  </div>
                  {aboutChangelogOpen && aboutInfo.changelog.length > 0 && (
                    <div
                      data-testid="elia-changelog-panel"
                      style={{
                        marginBottom: 12,
                        padding: "12px 14px",
                        borderRadius: 10,
                        border: `1px solid ${c.border}`,
                        background: c.inputBg,
                        maxHeight: "min(36vh, 320px)",
                        overflow: "auto",
                      }}
                    >
                      {aboutInfo.changelog.map((entry, entryIndex) => {
                        const isCurrent = entry.version === aboutInfo.version;
                        const isLast = entryIndex === aboutInfo.changelog.length - 1;
                        const sections: Array<{
                          key: "added" | "fixed" | "changed";
                          label: string;
                          items: string[];
                        }> = [];
                        if (entry.added.length > 0) {
                          sections.push({ key: "added", label: "Añadido", items: entry.added });
                        }
                        if (entry.fixed.length > 0) {
                          sections.push({ key: "fixed", label: "Corregido", items: entry.fixed });
                        }
                        if (entry.changed.length > 0) {
                          sections.push({ key: "changed", label: "Cambiado", items: entry.changed });
                        }

                        return (
                          <div
                            key={entry.version}
                            data-testid={`elia-changelog-entry-${entry.version}`}
                            style={{
                              marginBottom: isLast ? 0 : 16,
                              paddingBottom: isLast ? 0 : 16,
                              borderBottom: isLast ? "none" : `1px solid ${c.border}`,
                            }}
                          >
                            <div
                              style={{
                                display: "flex",
                                flexWrap: "wrap",
                                alignItems: "baseline",
                                gap: "6px 10px",
                                marginBottom: 8,
                              }}
                            >
                              <span style={{ fontWeight: 800, fontSize: 13, color: c.text }}>
                                {entry.version}
                                {isCurrent ? " (actual)" : ""}
                              </span>
                              {entry.date && (
                                <span style={{ fontSize: 11, color: c.muted }}>{entry.date}</span>
                              )}
                            </div>
                            {sections.map((section) => (
                              <div key={section.key} style={{ marginBottom: 10 }}>
                                <div
                                  style={{
                                    fontSize: 11,
                                    fontWeight: 700,
                                    color: c.muted,
                                    marginBottom: 4,
                                    letterSpacing: "0.02em",
                                  }}
                                >
                                  [{section.label}]
                                </div>
                                <ul
                                  style={{
                                    margin: 0,
                                    paddingLeft: 18,
                                    fontSize: 12,
                                    lineHeight: 1.55,
                                    color: c.text,
                                  }}
                                >
                                  {section.items.map((item, i) => (
                                    <li key={i} style={{ marginBottom: 4 }}>
                                      {item}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            ))}
                          </div>
                        );
                      })}
                    </div>
                  )}
                  <div style={{ fontSize: 14, marginBottom: 12 }}>
                    Desarrollador: {aboutInfo.developer}
                  </div>
                  {aboutInfo.contact_email ? (
                    <div style={{ fontSize: 14, marginBottom: 12 }}>
                      Contacto:{" "}
                      <a href={`mailto:${aboutInfo.contact_email}`} style={{ color: c.primary }}>
                        {aboutInfo.contact_email}
                      </a>
                    </div>
                  ) : null}
                  <BetaFeedbackLink url={aboutInfo.beta_feedback_url} c={c} variant="about" />
                  {/*
                  Versión comercial (≥1.0): quitar BetaFeedbackLink de arriba.
                  En Acerca de basta con la línea Contacto (contact_email) ya mostrada arriba.
                  */}
                  {aboutInfo.local_logs_hint ? (
                    <div style={{ fontSize: 12, color: c.muted, marginBottom: 12 }}>
                      {aboutInfo.local_logs_hint}
                    </div>
                  ) : null}
                  {aboutInfo.show_beta_disclaimer ? (
                    <div
                      style={{
                        padding: "14px 16px",
                        borderRadius: 10,
                        border: `1px solid ${dark ? "rgba(160,160,160,0.45)" : "#5a5a5a"}`,
                        background: dark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.04)",
                        marginBottom: 16,
                      }}
                    >
                      <div
                        style={{
                          fontWeight: 700,
                          fontSize: 13,
                          lineHeight: 1.45,
                          marginBottom: 10,
                          color: c.text,
                        }}
                      >
                        ⚠️ Aviso Importante: Fase Beta y Resguardo de Información
                      </div>
                      <div style={{ fontSize: 12, lineHeight: 1.65, color: c.text }}>
                        ELIA se encuentra actualmente en fase de desarrollo activo y pruebas Beta. Aunque el
                        software opera de forma estrictamente local en su equipo, al tratarse de una versión de
                        evaluación, le recomendamos encarecidamente mantener copias de seguridad y respaldos
                        actualizados de todos sus archivos de configuración, bases de datos y entornos de prueba
                        antes y durante el uso de la aplicación.
                      </div>
                      <div style={{ fontSize: 12, lineHeight: 1.65, color: c.text, marginTop: 10 }}>
                        El uso de esta herramienta está sujeto a los términos de la Licencia de Autor Restringida
                        (LAR) v1.1 que se detalla a continuación.
                      </div>
                    </div>
                  ) : null}
                  {/*
                  Versión comercial (≥1.0): show_beta_disclaimer=false — solo queda la licencia LAR.
                  */}
                  <div style={{ fontSize: 12, color: c.muted, marginBottom: 8 }}>Licencia de uso</div>
                  <div
                    style={{
                      padding: "14px 16px",
                      borderRadius: 10,
                      border: `1px solid ${c.border}`,
                      background: c.inputBg,
                      color: c.text,
                      maxHeight: "min(42vh, 360px)",
                      overflow: "auto",
                    }}
                  >
                    {aboutInfo.license_text ? (
                      parseLicenseDisplayBlocks(aboutInfo.license_text).map((block, i) => {
                        if (block.kind === "title") {
                          return (
                            <div
                              key={i}
                              style={{
                                fontWeight: 800,
                                fontSize: 13,
                                lineHeight: 1.45,
                                marginBottom: 10,
                                letterSpacing: "0.01em",
                              }}
                            >
                              {block.text}
                            </div>
                          );
                        }
                        if (block.kind === "heading") {
                          return (
                            <div
                              key={i}
                              style={{
                                fontWeight: 700,
                                fontSize: 12,
                                lineHeight: 1.45,
                                marginTop: i > 0 ? 14 : 0,
                                marginBottom: 6,
                              }}
                            >
                              {block.text}
                            </div>
                          );
                        }
                        if (block.kind === "list") {
                          return (
                            <ul
                              key={i}
                              style={{
                                margin: "0 0 12px",
                                paddingLeft: 20,
                                fontSize: 12,
                                lineHeight: 1.6,
                              }}
                            >
                              {block.items.map((item, j) => (
                                <li key={j} style={{ marginBottom: 8 }}>
                                  {item}
                                </li>
                              ))}
                            </ul>
                          );
                        }
                        return (
                          <p
                            key={i}
                            style={{
                              margin: "0 0 12px",
                              fontSize: 12,
                              lineHeight: 1.65,
                              textAlign: "justify",
                            }}
                          >
                            {block.text}
                          </p>
                        );
                      })
                    ) : (
                      <div style={{ fontSize: 12, color: c.muted }}>(Licence.txt no disponible)</div>
                    )}
                  </div>
                </>
              ) : (
                <div style={{ fontSize: 13, color: c.muted }}>Cargando información…</div>
              )}
            </div>
            )}
          </div>
        </div>

  );
}
