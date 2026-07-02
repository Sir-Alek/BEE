import React, { useEffect, useState } from "react";
import { stopMobileAppium, getRecordings, getScenarios, uploadDocs } from "../api";
import { encodeRecordingLink, encodeScenarioLink } from "../app/linkUtils";
import {
  canExecuteHomeActions,
  getFeatureAccess,
  isNoLicense,
  shouldShowTierUpsell,
} from "../app/entitlementPhase";
import {
  formatLicenseExpiryDate,
  licenseNeedsActivationBanner,
  licenseNeedsExpiryBanner,
  licenseNeedsSoftExpiryBanner,
  licenseSoftExpiryDismissKey,
  type LicenseState,
} from "../app/licenseUtils";
import { OutlinedButton, SecondaryToolbar } from "../components/ui";
import { EntitlementBanner } from "../components/EntitlementBanner";
import { NoLicenseOverlay } from "../components/NoLicenseOverlay";
import { ProjectManageToolbar } from "../components/ProjectManageToolbar";
import { ProjectTemplateModal } from "../components/ProjectTemplateModal";
import { PlatformQuickGuide } from "../components/PlatformQuickGuide";
import { TierBadge, UpsellModal } from "../components/UpsellModal";
import { LegacyConfigForm } from "../recording/LegacyConfigForm";
import { MobileConfigForm } from "../recording/MobileConfigForm";
import { WebConfigForm } from "../recording/WebConfigForm";
import { ApiSurface } from "./ApiSurface";
import { RunWorkspacePanel, usePlatformProjects } from "./RunWorkspacePanel";
import { BehaveProjectSelect } from "./BehaveProjectSelect";
import { useConnectorContext } from "../context/ConnectorContext";
import { useHomeUiContext } from "../context/HomeUiContext";
import { useRecordingContext } from "../context/RecordingContext";

export function HomeSurface() {
  const {
    c, dark, initialChecked, homeTab, setHomeTab, homeHint, license, licenseLoading,
    setSettingsOpen, setSettingsTab, setLicenseActivateMsg, canRunJobs, modules, modulesLoading,
    entitlementPhase, entitlementFeatures, entitlementBanner, showTierUpsell,
    offlineBannerDismissed, setOfflineBannerDismissed,
    showLockModal, setShowLockModal, showHomeError, autoLinkToScenario, setAutoLinkToScenario,
    autoLinkScenarioRef, setAutoLinkScenarioRef, availableScenarios, startJob, loadedDocs,
    setLoadedDocs, docDragOver, setDocDragOver, docUploadError, setDocUploadError, linkRecordings,
    setLinkRecordings, linkMapping, setLinkMapping, recordingMapping, setRecordingMapping,
    availableRecordings, setAvailableScenarios, setAvailableRecordings, setHomeHint,
    homeDataRefresh, pendingRunProject, clearPendingRunProject,
    refreshHomeData, selectRunProject, selectApiProject,
  } = useHomeUiContext();
  const {
    connectorProfiles, reqConnectorProfileId, setReqConnectorProfileId,
  } = useConnectorContext();
  const {
    platform, setPlatform, urlValue, setUrlValue, recorderPreflight, recorderPreflightLoading,
    mobilePreflight, mobilePreflightLoading, mobileEnvOpen, setMobileEnvOpen, appiumStatus,
    appiumStarting, handleStartAppium, refreshAppiumStatus, refreshMobilePreflight,
    deviceMode, setDeviceMode, deviceId, setDeviceId, mobileDevices, mobileDevicesLoading,
    mobileDevicesError, refreshMobileDevices, mobileAvds, mobileAvdsLoading, mobileAvdsError,
    selectedAvd, setSelectedAvd, refreshMobileAvds, emulatorStarting, handleStartEmulator,
    emulatorMessage, emulatorMessageTone, mobileFieldError, appPackage, setAppPackage, appActivity, setAppActivity,
    appSource, setAppSource, deviceManualMode, setDeviceManualMode,
    detectingForegroundApp, detectForegroundApp, apkPath, setApkPath, setMobileFieldError,
    windowName, setWindowName, exePath, setExePath,
  } = useRecordingContext();

  const [runProject, setRunProject] = useState("");
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const runProjects = usePlatformProjects(platform, homeDataRefresh);
  const features = entitlementFeatures;
  const actionsEnabled = canExecuteHomeActions(entitlementPhase, canRunJobs);

  const openLicenseSettings = () => {
    setSettingsTab("license");
    setSettingsOpen(true);
  };

  const openEnvironmentSettings = () => {
    setSettingsTab("environment");
    setSettingsOpen(true);
  };

  const docAccess = getFeatureAccess(entitlementPhase, "doc_to_bdd", features, license);
  const mobileAccess = getFeatureAccess(entitlementPhase, "mobile_recording", features, license);
  const legacyAccess = getFeatureAccess(entitlementPhase, "legacy_recording", features, license);

  const showDocLock = shouldShowTierUpsell(entitlementPhase, docAccess, showTierUpsell);
  const showMobileLock = shouldShowTierUpsell(entitlementPhase, mobileAccess, showTierUpsell);
  const showLegacyLock = shouldShowTierUpsell(entitlementPhase, legacyAccess, showTierUpsell);

  const [softExpiryDismissed, setSoftExpiryDismissed] = useState(() => {
    if (!license?.expires_at) return false;
    try {
      return localStorage.getItem(licenseSoftExpiryDismissKey(license.expires_at)) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    if (!license?.expires_at) return;
    try {
      setSoftExpiryDismissed(localStorage.getItem(licenseSoftExpiryDismissKey(license.expires_at)) === "1");
    } catch {
      setSoftExpiryDismissed(false);
    }
  }, [license?.expires_at]);

  useEffect(() => {
    setRunProject("");
  }, [platform]);

  useEffect(() => {
    if (!pendingRunProject) return;
    if (pendingRunProject.platform !== platform) return;
    if (runProjects.includes(pendingRunProject.project)) {
      setRunProject(pendingRunProject.project);
      clearPendingRunProject();
    }
  }, [pendingRunProject, platform, runProjects, clearPendingRunProject]);

  if (!initialChecked) return null;

  return (
          <div
            data-testid="elia-home"
            style={{
              background: c.surface,
              border: `1px solid ${c.border}`,
              borderRadius: 14,
              padding: 18,
              boxShadow: c.shadow,
            }}
          >
            <h2 style={{ margin: "0 0 10px 0", fontSize: 20, color: c.text }}>ELIA Web UI</h2>
            <div style={{ color: c.text, marginBottom: 14 }}>
              Pestaña principal: cada operación se abre en una <b>nueva pestaña</b> (avisos, prompts y resultado) sin cerrar
              esta vista.
            </div>

            <div
              style={{
                display: "flex",
                gap: 10,
                padding: 6,
                borderRadius: 12,
                border: `1px solid ${c.border}`,
                background: c.neutralBg,
                marginBottom: 14,
                flexWrap: "wrap",
              }}
            >
              <button
                type="button"
                data-testid="elia-home-tab-ui"
                onClick={() => setHomeTab("ui")}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  border: `1px solid ${homeTab === "ui" ? c.primary : c.btnGhostBorder}`,
                  background: homeTab === "ui" ? c.primary : c.btnGhostBg,
                  color: homeTab === "ui" ? c.primaryFg : c.text,
                  cursor: "pointer",
                  fontWeight: 700,
                }}
              >
                Automatización UI
              </button>
              <button
                type="button"
                data-testid="elia-home-tab-api"
                onClick={() => setHomeTab("api")}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  border: `1px solid ${homeTab === "api" ? c.primary : c.btnGhostBorder}`,
                  background: homeTab === "api" ? c.primary : c.btnGhostBg,
                  color: homeTab === "api" ? c.primaryFg : c.text,
                  cursor: "pointer",
                  fontWeight: 700,
                }}
              >
                Pruebas API
              </button>
              <button
                type="button"
                data-testid="elia-home-tab-req"
                onClick={() => {
                  if (docAccess === "denied" && showDocLock) {
                    setShowLockModal("doc_to_bdd");
                    return;
                  }
                  if (docAccess !== "granted") return;
                  setHomeTab("req");
                }}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  border: `1px solid ${homeTab === "req" ? c.primary : c.btnGhostBorder}`,
                  background: homeTab === "req" ? c.primary : c.btnGhostBg,
                  color: homeTab === "req" ? c.primaryFg : c.text,
                  cursor: "pointer",
                  fontWeight: 700,
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                {showDocLock ? <span style={{ fontSize: 12 }}>🔒</span> : null}
                Inteligencia de Requerimientos
                {showDocLock ? <TierBadge c={c} label="Tester" /> : null}
              </button>
            </div>

            {homeHint && (
              <div
                data-testid="elia-home-hint"
                style={{
                  background: c.hintBg,
                  border: `1px solid ${c.hintBorder}`,
                  color: c.hintText,
                  padding: 12,
                  borderRadius: 10,
                  marginBottom: 14,
                  fontSize: 14,
                }}
              >
                {homeHint}
              </div>
            )}

            <EntitlementBanner
              c={c}
              banner={entitlementBanner}
              offlineDismissed={offlineBannerDismissed}
              onDismissOffline={() => setOfflineBannerDismissed(true)}
            />

            {license && licenseNeedsActivationBanner(license) && (
              <div
                role="alert"
                data-testid="elia-license-banner"
                style={{
                  background: c.licWarnBg,
                  border: `1px solid ${c.licWarnBorder}`,
                  color: c.text,
                  padding: "10px 14px",
                  borderRadius: 10,
                  marginBottom: 14,
                  fontSize: 14,
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 8,
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <span>
                  ELIA requiere una clave de activación. Configuración → Licencia (huella de máquina necesaria).
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setLicenseActivateMsg(null);
                    setSettingsTab("license");
                    setSettingsOpen(true);
                  }}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 8,
                    border: `1px solid ${c.btnGhostBorder}`,
                    background: c.btnGhostBg,
                    color: c.text,
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                  }}
                >
                  Configuración →
                </button>
              </div>
            )}

            {license && licenseNeedsExpiryBanner(license) && license.expires_at != null && (
              <div
                role="alert"
                style={{
                  background: c.hintBg,
                  border: `1px solid ${c.hintBorder}`,
                  color: c.text,
                  padding: "10px 14px",
                  borderRadius: 10,
                  marginBottom: 14,
                  fontSize: 14,
                }}
              >
                Tu licencia expira el {formatLicenseExpiryDate(license.expires_at)} (
                {Math.max(0, Math.ceil((license.expires_at * 1000 - Date.now()) / 86400000))} día(s) restantes).
              </div>
            )}

            {license &&
              licenseNeedsSoftExpiryBanner(license) &&
              license.expires_at != null &&
              !softExpiryDismissed && (
                <div
                  role="alert"
                  data-testid="elia-license-soft-expiry-banner"
                  style={{
                    background: c.neutralBg,
                    border: `1px solid ${c.border}`,
                    color: c.text,
                    padding: "10px 14px",
                    borderRadius: 10,
                    marginBottom: 14,
                    fontSize: 14,
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 8,
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <span>
                    Tu licencia caduca el {formatLicenseExpiryDate(license.expires_at)} (
                    {Math.max(0, Math.ceil((license.expires_at * 1000 - Date.now()) / 86400000))} día(s)). Renueva a
                    tiempo para evitar interrupciones.
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      try {
                        localStorage.setItem(licenseSoftExpiryDismissKey(license.expires_at!), "1");
                      } catch {
                        /* ignore */
                      }
                      setSoftExpiryDismissed(true);
                    }}
                    style={{
                      padding: "6px 12px",
                      borderRadius: 8,
                      border: `1px solid ${c.btnGhostBorder}`,
                      background: c.btnGhostBg,
                      color: c.text,
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                    }}
                  >
                    Entendido
                  </button>
                </div>
              )}


            {isNoLicense(entitlementPhase) ? (
              <NoLicenseOverlay c={c} license={license} onOpenLicenseSettings={openLicenseSettings}>
                <div data-testid="elia-no-license-placeholder" style={{ minHeight: 320 }} />
              </NoLicenseOverlay>
            ) : null}

            {!isNoLicense(entitlementPhase) && homeTab === "ui" && (
              <>
                {/* Lock Modal */}
                {showLockModal && (
                  <UpsellModal
                    c={c}
                    requiredTier={
                      showLockModal === "mobile"
                        ? "mobile"
                        : showLockModal === "legacy"
                          ? "legacy"
                          : showLockModal === "doc_to_bdd"
                            ? "doc_to_bdd"
                            : "mobile"
                    }
                    onClose={() => setShowLockModal(null)}
                  />
                )}

                <div>

                {/* Segmented Control — selector de plataforma */}
                <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
                  {(["web", "mobile", "legacy"] as const).map((p) => {
                    const labels = { web: "Web", mobile: "Móvil", legacy: "Legacy" };
                    const access =
                      p === "mobile" ? mobileAccess : p === "legacy" ? legacyAccess : ("granted" as const);
                    const locked =
                      p === "mobile" ? showMobileLock : p === "legacy" ? showLegacyLock : false;
                    const pending = access === "pending";
                    const badge = p === "mobile" ? "Tester" : p === "legacy" ? "Architect" : null;
                    const active = platform === p;
                    return (
                      <button
                        key={p}
                        data-testid={`elia-platform-${p}`}
                        onClick={() => {
                          if (locked) { setShowLockModal(p); return; }
                          if (access === "denied" || access === "pending") return;
                          setPlatform(p);
                        }}
                        style={{
                          padding: "7px 18px",
                          borderRadius: 8,
                          border: active ? `2px solid ${c.primary}` : `1px solid ${c.btnGhostBorder}`,
                          background: active ? c.primary : c.btnGhostBg,
                          color: active ? c.primaryFg : locked || pending ? c.muted : c.text,
                          fontWeight: active ? 700 : 400,
                          cursor: "pointer",
                          opacity: locked ? 0.6 : pending ? 0.5 : 1,
                          fontSize: 14,
                          display: "flex", alignItems: "center", gap: 5,
                        }}
                      >
                        {locked && <span style={{ fontSize: 12 }}>🔒</span>}
                        {pending && !locked && <span style={{ fontSize: 10, opacity: 0.7 }}>…</span>}
                        {labels[p]}
                        {locked && badge ? <TierBadge c={c} label={badge} /> : null}
                      </button>
                    );
                  })}
                </div>

                {/* Dynamic form by platform */}
                {platform === "web" && (
                  <WebConfigForm
                    c={c}
                    urlValue={urlValue}
                    onUrlChange={setUrlValue}
                    recorderPreflight={recorderPreflight}
                    recorderPreflightLoading={recorderPreflightLoading}
                  />
                )}
                {platform === "mobile" && (
                  <>
                  <MobileConfigForm
                    c={c}
                    license={license}
                    mobilePreflight={mobilePreflight}
                    mobilePreflightLoading={mobilePreflightLoading}
                    mobileEnvOpen={mobileEnvOpen}
                    onMobileEnvOpenChange={setMobileEnvOpen}
                    appiumStatus={appiumStatus}
                    appiumStarting={appiumStarting}
                    onStartAppium={() => void handleStartAppium()}
                    onStopAppium={() => {
                      void (async () => {
                        try {
                          await stopMobileAppium();
                          await refreshAppiumStatus();
                          await refreshMobilePreflight();
                        } catch (e) {
                          showHomeError(
                            e instanceof Error ? e.message : "No se pudo detener Appium.",
                            { mobileInline: true },
                          );
                        }
                      })();
                    }}
                    deviceMode={deviceMode}
                    onDeviceModeChange={setDeviceMode}
                    deviceId={deviceId}
                    onDeviceIdChange={setDeviceId}
                    mobileDevices={mobileDevices}
                    mobileDevicesLoading={mobileDevicesLoading}
                    mobileDevicesError={mobileDevicesError}
                    onRefreshDevices={() => void refreshMobileDevices()}
                    mobileAvds={mobileAvds}
                    mobileAvdsLoading={mobileAvdsLoading}
                    mobileAvdsError={mobileAvdsError}
                    selectedAvd={selectedAvd}
                    onSelectedAvdChange={setSelectedAvd}
                    onRefreshAvds={() => void refreshMobileAvds()}
                    onRefreshMobileEnv={(preferAvdName) => {
                      void refreshMobileAvds(preferAvdName);
                      void refreshMobilePreflight();
                      void refreshMobileDevices();
                    }}
                    onOpenEnvironmentSettings={openEnvironmentSettings}
                    emulatorStarting={emulatorStarting}
                    onStartEmulator={(avd) => void handleStartEmulator(avd)}
                    emulatorMessage={emulatorMessage}
                    emulatorMessageTone={emulatorMessageTone}
                    mobileFieldError={mobileFieldError}
                    appPackage={appPackage}
                    onAppPackageChange={setAppPackage}
                    appActivity={appActivity}
                    onAppActivityChange={setAppActivity}
                    detectingForegroundApp={detectingForegroundApp}
                    onDetectForegroundApp={() => void detectForegroundApp()}
                    apkPath={apkPath}
                    onApkPathChange={setApkPath}
                    appSource={appSource}
                    onAppSourceChange={setAppSource}
                    deviceManualMode={deviceManualMode}
                    onDeviceManualModeChange={setDeviceManualMode}
                    onClearMobileFieldError={() => setMobileFieldError(null)}
                  />
                  <PlatformQuickGuide
                    c={c}
                    platform="mobile"
                    hasProjects={runProjects.length > 0}
                  />
                  </>
                )}
                {platform === "legacy" && (
                  <>
                  <LegacyConfigForm
                    c={c}
                    windowName={windowName}
                    exePath={exePath}
                    onWindowNameChange={setWindowName}
                    onExePathChange={setExePath}
                  />
                  <PlatformQuickGuide
                    c={c}
                    platform="legacy"
                    hasProjects={runProjects.length > 0}
                  />
                  </>
                )}

                {(platform === "web" || platform === "mobile" || platform === "legacy") && (
                  <div style={{ marginBottom: 12 }}>
                    <label
                      style={{
                        display: "flex",
                        gap: 10,
                        alignItems: "flex-start",
                        cursor: "pointer",
                        fontSize: 13,
                        color: c.text,
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={autoLinkToScenario}
                        disabled={!actionsEnabled}
                        onChange={async (e) => {
                          if (!actionsEnabled) return;
                          const checked = e.target.checked;
                          setAutoLinkToScenario(checked);
                          if (checked) {
                            try {
                              const data = await getScenarios();
                              setAvailableScenarios(data.scenarios);
                            } catch {
                              setAvailableScenarios([]);
                            }
                          } else {
                            setAutoLinkScenarioRef("");
                          }
                        }}
                        style={{ marginTop: 2 }}
                      />
                      <span>
                        <b>Vincular conversión a escenario BDD existente</b>
                        <span style={{ display: "block", fontSize: 12, color: c.muted, marginTop: 2 }}>
                          Fusiona los pasos generados en un Scenario ya presente en el proyecto
                        </span>
                      </span>
                    </label>
                    {autoLinkToScenario && (
                      <select
                        value={autoLinkScenarioRef}
                        disabled={!actionsEnabled}
                        onChange={(e) => setAutoLinkScenarioRef(e.target.value)}
                        style={{
                          marginTop: 8,
                          width: "100%",
                          padding: "8px 12px",
                          borderRadius: 10,
                          border: `1px solid ${c.inputBorder}`,
                          background: c.inputBg,
                          color: c.text,
                          fontSize: 13,
                        }}
                      >
                        <option value="">Selecciona escenario…</option>
                        {availableScenarios.map((s, i) => (
                          <option key={i} value={encodeScenarioLink(s)}>
                            {s.scenario_name} ({s.feature_file.split(/[\\/]/).pop()})
                          </option>
                        ))}
                      </select>
                    )}
                    {autoLinkToScenario && availableScenarios.length === 0 && (
                      <div style={{ fontSize: 12, color: c.muted, marginTop: 6 }}>
                        No hay escenarios .feature en el proyecto. Genera o importa features primero.
                      </div>
                    )}
                  </div>
                )}

                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <button
                    data-testid="elia-btn-record"
                    disabled={
                      !actionsEnabled ||
                      (platform === "web" &&
                        (recorderPreflightLoading || (recorderPreflight != null && !recorderPreflight.ok))) ||
                      (platform === "mobile" &&
                        (mobilePreflightLoading || (mobilePreflight != null && !mobilePreflight.ok)))
                    }
                    onClick={() => {
                      if (platform === "web") void startJob("puppeteer_recorder");
                      else if (platform === "mobile") void startJob("mobile_recorder");
                      else void startJob("legacy_recorder");
                    }}
                    style={{
                      padding: "10px 14px", borderRadius: 10,
                      background:
                        !actionsEnabled
                          ? c.buttonDisabledBg
                          : platform === "web" && recorderPreflight && !recorderPreflight.ok
                            ? c.buttonDisabledBg
                            : platform === "mobile" && mobilePreflight && !mobilePreflight.ok
                              ? c.buttonDisabledBg
                              : c.primary,
                      color: c.primaryFg, border: "none",
                      cursor:
                        !actionsEnabled ||
                        (platform === "web" && recorderPreflight && !recorderPreflight.ok) ||
                        (platform === "mobile" && mobilePreflight && !mobilePreflight.ok)
                          ? "not-allowed"
                          : "pointer",
                    }}
                  >
                    Grabar Interacciones
                  </button>
                  <button
                    disabled={
                      !actionsEnabled ||
                      (platform === "mobile" && !features.mobile_recording) ||
                      (platform === "legacy" && !features.legacy_recording)
                    }
                    onClick={() => {
                      if (platform === "web") void startJob("puppeteer_to_behave");
                      else if (platform === "mobile") void startJob("mobile_to_behave");
                      else void startJob("legacy_to_behave");
                    }}
                    style={{
                      padding: "10px 14px", borderRadius: 10,
                      background: c.btnGhostBg, color: c.text,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: !actionsEnabled ? "not-allowed" : "pointer",
                      opacity: !actionsEnabled ? 0.5 : 1,
                    }}
                  >
                    Convertir a Behave
                  </button>
                  {platform === "web" && (
                  <button
                    disabled={!actionsEnabled}
                    onClick={() => void startJob("puppeteer_to_step_by_step")}
                    style={{
                      padding: "10px 14px", borderRadius: 10,
                      background: c.btnGhostBg, color: c.text,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: !actionsEnabled ? "not-allowed" : "pointer",
                      opacity: !actionsEnabled ? 0.5 : 1,
                    }}
                  >
                    Convertir a step by step
                  </button>
                  )}
                </div>

                <div
                  style={{
                    marginTop: 14,
                    paddingTop: 14,
                    borderTop: `1px solid ${c.border}`,
                  }}
                >
                  <div style={{ fontSize: 13, color: c.muted, marginBottom: 8 }}>
                    Ejecutar Behave, editar .feature / steps y generar PDF (proyecto en behave/{platform}/).
                  </div>
                  {runProjects.length === 0 && platform === "web" && (
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
                      Aún no tienes proyectos en esta plataforma. Crea uno desde plantilla para ejecutar tu
                      primera prueba en minutos.
                    </div>
                  )}
                  {(platform === "mobile" || platform === "legacy") && (
                    <PlatformQuickGuide
                      c={c}
                      platform={platform}
                      showLink={false}
                      showRunnerHint
                      hasProjects={runProjects.length > 0}
                    />
                  )}
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10, alignItems: "center" }}>
                    <BehaveProjectSelect
                      c={c}
                      platform={platform}
                      value={runProject}
                      onChange={setRunProject}
                      projects={runProjects}
                    />
                    {platform === "web" && (
                    <button
                      type="button"
                      data-testid="elia-new-from-template-btn"
                      disabled={!actionsEnabled}
                      onClick={() => setTemplateModalOpen(true)}
                      style={{
                        padding: "8px 12px",
                        borderRadius: 8,
                        border: `1px solid ${c.primary}`,
                        background: "transparent",
                        color: c.primary,
                        fontWeight: 700,
                        fontSize: 13,
                        cursor: !actionsEnabled ? "not-allowed" : "pointer",
                        opacity: !actionsEnabled ? 0.5 : 1,
                      }}
                    >
                      Nueva plantilla…
                    </button>
                    )}
                  </div>
                  {runProject ? (
                    <ProjectManageToolbar
                      c={c}
                      platform={platform}
                      project={runProject}
                      disabled={!actionsEnabled}
                      onProjectRenamed={(newName) => {
                        refreshHomeData();
                        setRunProject(newName);
                        selectRunProject(platform, newName);
                      }}
                      onProjectDeleted={() => {
                        refreshHomeData();
                        setRunProject("");
                      }}
                      onError={showHomeError}
                    />
                  ) : null}
                  <RunWorkspacePanel
                    key={`${platform}-${runProject}-${homeDataRefresh}`}
                    c={c}
                    platform={platform}
                    project={runProject}
                    canRunJobs={actionsEnabled}
                    onShowError={showHomeError}
                    showLocust={false}
                  />
                </div>
                </div>
              </>
            )}

            {!isNoLicense(entitlementPhase) && homeTab === "req" && (
              <div
                style={{
                  background: c.neutralBg,
                  border: `1px solid ${c.border}`,
                  borderRadius: 14,
                  padding: 14,
                  opacity: docAccess === "pending" ? 0.55 : 1,
                  pointerEvents: docAccess === "pending" ? "none" : "auto",
                }}
              >
                <div style={{ fontWeight: 800, color: c.text, marginBottom: 6 }}>Inteligencia de Requerimientos</div>

                {/* Carga de documentos locales */}
                <div style={{ fontWeight: 600, color: c.text, fontSize: 13, marginBottom: 8 }}>
                  Carga de Documentos (Word / Excel → BDD)
                </div>

                {/* Área Drag & Drop */}
                <div
                  onDragOver={(e) => { e.preventDefault(); setDocDragOver(true); }}
                  onDragLeave={() => setDocDragOver(false)}
                  onDrop={async (e) => {
                    e.preventDefault();
                    setDocDragOver(false);
                    setDocUploadError(null);
                    const files = Array.from(e.dataTransfer.files).filter((f) =>
                      [".docx", ".xlsx", ".json"].some((ext) => f.name.toLowerCase().endsWith(ext))
                    );
                    if (!files.length) { setDocUploadError("Solo se aceptan archivos .docx, .xlsx y .json"); return; }
                    try {
                      const result = await uploadDocs(files);
                      setLoadedDocs((prev) => {
                        const existing = new Set(prev.map((d) => d.path));
                        return [...prev, ...result.files.filter((f) => !existing.has(f.path))];
                      });
                    } catch (err: any) {
                      setDocUploadError(String(err?.message ?? err));
                    }
                  }}
                  onClick={() => {
                    const input = document.createElement("input");
                    input.type = "file";
                    input.accept = ".docx,.xlsx,.json";
                    input.multiple = true;
                    input.onchange = async () => {
                      const files = Array.from(input.files ?? []);
                      if (!files.length) return;
                      setDocUploadError(null);
                      try {
                        const result = await uploadDocs(files);
                        setLoadedDocs((prev) => {
                          const existing = new Set(prev.map((d) => d.path));
                          return [...prev, ...result.files.filter((f) => !existing.has(f.path))];
                        });
                      } catch (err: any) {
                        setDocUploadError(String(err?.message ?? err));
                      }
                    };
                    input.click();
                  }}
                  style={{
                    border: `2px dashed ${docDragOver ? c.primary : c.inputBorder}`,
                    borderRadius: 12,
                    padding: "18px 14px",
                    textAlign: "center",
                    cursor: "pointer",
                    background: docDragOver ? (dark ? "rgba(99,102,241,0.08)" : "rgba(99,102,241,0.04)") : c.inputBg,
                    color: c.muted,
                    fontSize: 13,
                    marginBottom: 8,
                    transition: "border-color 0.15s, background 0.15s",
                  }}
                >
                  Arrastra tus archivos aquí o haz clic para buscar
                  <span style={{ display: "block", fontSize: 11, marginTop: 4 }}>(.docx, .xlsx, .json)</span>
                </div>

                {docUploadError && (
                  <div style={{ fontSize: 12, color: "#e53e3e", marginBottom: 8 }}>{docUploadError}</div>
                )}

                {/* Lista de documentos cargados */}
                {loadedDocs.length > 0 && (
                  <div style={{ marginBottom: 10 }}>
                    {loadedDocs.map((doc, i) => (
                      <div
                        key={doc.path}
                        style={{
                          display: "flex", alignItems: "center", gap: 8,
                          padding: "5px 8px", borderRadius: 8,
                          background: c.surface, border: `1px solid ${c.border}`,
                          marginBottom: 4, fontSize: 13,
                        }}
                      >
                        <span style={{ fontSize: 16 }}>
                          {doc.ext === ".docx" ? "📄" : doc.ext === ".xlsx" ? "📊" : "📋"}
                        </span>
                        <span style={{ flex: 1, color: c.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {doc.name}
                        </span>
                        <button
                          onClick={() => setLoadedDocs((prev) => prev.filter((_, j) => j !== i))}
                          style={{
                            background: "none", border: "none", color: c.muted,
                            cursor: "pointer", fontSize: 14, padding: "0 4px",
                          }}
                          title="Quitar"
                        >✕</button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Toggle: vincular grabaciones */}
                <label
                  style={{
                    display: "flex", gap: 10, alignItems: "flex-start",
                    marginBottom: 10, cursor: "pointer", fontSize: 13, color: c.text,
                  }}
                >
                  <input
                    type="checkbox"
                    checked={linkRecordings}
                    disabled={!actionsEnabled}
                    onChange={async (e) => {
                      if (!actionsEnabled) return;
                      const checked = e.target.checked;
                      setLinkRecordings(checked);
                      if (checked) {
                        try {
                          const [scData, recData] = await Promise.all([
                            getScenarios(),
                            getRecordings(),
                          ]);
                          setAvailableScenarios(scData.scenarios);
                          setAvailableRecordings(recData.recordings);
                        } catch {
                          setAvailableScenarios([]);
                          setAvailableRecordings([]);
                        }
                      } else {
                        setRecordingMapping({});
                      }
                    }}
                    style={{ marginTop: 2 }}
                  />
                  <span>
                    <b>Vincular features generados con grabaciones existentes</b>
                    <span style={{ display: "block", fontSize: 12, color: c.muted, marginTop: 2 }}>
                      Asocia el output BDD con una grabación ya realizada en el proyecto
                    </span>
                  </span>
                </label>

                {/* Panel de vinculación */}
                {linkRecordings && availableScenarios.length > 0 && (
                  <div
                    style={{
                    background: c.surface, border: `1px solid ${c.border}`,
                    borderRadius: 10, padding: 12, marginBottom: 10,
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 600, color: c.text, marginBottom: 8 }}>
                      Por documento: escenario destino y grabación (.json / .js)
                    </div>
                    {loadedDocs.map((doc) => (
                      <div key={doc.path} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
                        <span style={{ fontSize: 12, color: c.muted, minWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {doc.name}
                        </span>
                        <span style={{ color: c.muted, fontSize: 12 }}>→</span>
                        <select
                          value={linkMapping[doc.path] ?? ""}
                          onChange={(e) => setLinkMapping((prev) => ({ ...prev, [doc.path]: e.target.value }))}
                          style={{
                            flex: 1, padding: "5px 8px", borderRadius: 8,
                            border: `1px solid ${c.inputBorder}`, background: c.inputBg,
                            color: c.text, fontSize: 12,
                          }}
                        >
                          <option value="">Sin vincular</option>
                          {availableScenarios.map((s, i) => (
                            <option key={i} value={encodeScenarioLink(s)}>
                              {s.scenario_name} ({s.feature_file.split(/[\\/]/).pop()})
                            </option>
                          ))}
                        </select>
                        <select
                          value={recordingMapping[doc.path] ?? ""}
                          onChange={(e) =>
                            setRecordingMapping((prev) => ({ ...prev, [doc.path]: e.target.value }))
                          }
                          style={{
                            flex: 1, padding: "5px 8px", borderRadius: 8, marginTop: 6,
                            border: `1px solid ${c.inputBorder}`, background: c.inputBg,
                            color: c.text, fontSize: 12,
                          }}
                        >
                          <option value="">Grabación — opcional</option>
                          {availableRecordings.map((r, i) => (
                            <option key={i} value={encodeRecordingLink(r)}>
                              {r.label} · {r.project}
                            </option>
                          ))}
                        </select>
                      </div>
                    ))}
                  </div>
                )}
                {linkRecordings && availableScenarios.length === 0 && (
                  <div style={{ fontSize: 12, color: c.muted, marginBottom: 10 }}>
                    No se encontraron escenarios en el proyecto. Convierte grabaciones primero.
                  </div>
                )}

                {/* Botón de acción principal */}
                <div style={{ marginTop: 4 }}>
                  <button
                    data-testid="elia-btn-doc-bdd"
                    disabled={!actionsEnabled}
                    onClick={() => void startJob("doc_to_bdd")}
                    style={{
                      padding: "10px 20px", borderRadius: 10,
                      background: !actionsEnabled ? c.buttonDisabledBg : c.primary,
                      color: c.primaryFg, border: "none", fontWeight: 600, fontSize: 14,
                      cursor: !actionsEnabled ? "not-allowed" : "pointer",
                    }}
                  >
                    Procesar y Convertir a BDD
                  </button>
                </div>

                <SecondaryToolbar c={c} title="Integraciones y utilidades">
                  <label style={{ fontSize: 13, fontWeight: 600, color: c.text, marginRight: 4 }}>Perfil</label>
                  <select
                    value={reqConnectorProfileId}
                    onChange={(e) => setReqConnectorProfileId(e.target.value)}
                    style={{
                      flex: "1 1 180px", minWidth: 160, padding: "7px 10px",
                      borderRadius: 8, border: `1px solid ${c.inputBorder}`,
                      background: c.inputBg, color: c.text, fontSize: 13,
                    }}
                  >
                    {connectorProfiles.length === 0 ? (
                      <option value="">Sin perfiles — Configuración (⚙)</option>
                    ) : (
                      connectorProfiles.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))
                    )}
                  </select>
                  <OutlinedButton
                    c={c}
                    disabled={!actionsEnabled}
                    onClick={() => void startJob("elia_jira_smoke")}
                    testId="elia-btn-jira-smoke"
                  >
                    Conectar a Jira
                  </OutlinedButton>
                  <OutlinedButton
                    c={c}
                    disabled={!actionsEnabled}
                    onClick={() => void startJob("elia_value_edge_smoke")}
                    testId="elia-btn-ve-smoke"
                  >
                    Extraer de ValueEdge
                  </OutlinedButton>
                  <OutlinedButton
                    c={c}
                    disabled={!actionsEnabled}
                    onClick={() => void startJob("elia_gherkin_batch")}
                    testId="elia-btn-gherkin-batch"
                  >
                    Lote .json → .feature
                  </OutlinedButton>
                </SecondaryToolbar>
              </div>
            )}
            {!isNoLicense(entitlementPhase) && homeTab === "api" && (
              <ApiSurface
                c={c}
                modules={modules}
                modulesLoading={modulesLoading}
                canRunJobs={canRunJobs}
                entitlementPhase={entitlementPhase}
                entitlementFeatures={entitlementFeatures}
                showTierUpsell={showTierUpsell}
                license={license}
                onShowError={showHomeError}
                setHomeHint={setHomeHint}
              />
            )}

            <ProjectTemplateModal
              c={c}
              open={templateModalOpen}
              onClose={() => setTemplateModalOpen(false)}
              contextPlatform="web"
              onCreated={(result) => {
                refreshHomeData();
                const apiProj = result.projects.find((p) => p.platform === "api");
                if (apiProj) {
                  selectApiProject(apiProj.project);
                  setHomeHint(`Proyecto API «${apiProj.project}» creado. Abre la pestaña Pruebas API.`);
                }
                const forPlatform = result.projects.find((p) => p.platform === platform) ?? result.projects[0];
                if (forPlatform) {
                  selectRunProject(forPlatform.platform, forPlatform.project);
                  if (forPlatform.platform === platform) {
                    setRunProject(forPlatform.project);
                  }
                }
              }}
            />
          </div>

  );
}
