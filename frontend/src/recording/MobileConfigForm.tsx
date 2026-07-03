import React, { useMemo, useRef, useState } from "react";
import type {
  MobileAppiumStatusResponse,
  MobileDeviceInfo,
  MobilePreflightResponse,
} from "../api";
import { openMobileAndroidStudio } from "../api";
import { avdOrchestrationAllowed } from "../app/entitlements";
import type { LicenseState } from "../app/licenseUtils";
import { AvdArchitectUpsellModal } from "../components/AvdArchitectUpsellModal";
import { AvdSetupWizardModal } from "../components/AvdSetupWizardModal";
import { AndroidStudioPathPanel } from "../components/AndroidStudioPathPanel";
import { FieldLabel, SegmentedTabs, EliaButton } from "../components/ui";
import { LoadingStatusRow } from "../components/LoadingStatusRow";
import type { EmulatorMessageTone } from "../hooks/useMobileRecording";
import {
  formatPreflightItemMessage,
  friendlyAvdsError,
  MANUAL_DEVICE_OPTION,
  mobilePreflightSummary,
  normalizeMobileWarnings,
  preflightSeverity,
} from "../mobileEnvUi";

export type MobileConfigFormProps = {
  c: Record<string, string>;
  license: LicenseState | null;
  mobilePreflight: MobilePreflightResponse | null;
  mobilePreflightLoading: boolean;
  mobileEnvOpen: boolean;
  onMobileEnvOpenChange: (open: boolean) => void;
  appiumStatus: MobileAppiumStatusResponse | null;
  appiumStarting: boolean;
  onStartAppium: () => void;
  onStopAppium: () => void;
  deviceMode: "physical" | "emulator";
  onDeviceModeChange: (mode: "physical" | "emulator") => void;
  deviceId: string;
  onDeviceIdChange: (value: string) => void;
  deviceManualMode: boolean;
  onDeviceManualModeChange: (value: boolean) => void;
  mobileDevices: MobileDeviceInfo[];
  mobileDevicesLoading: boolean;
  mobileDevicesError: string | null;
  onRefreshDevices: () => void;
  mobileAvds: string[];
  mobileAvdsLoading: boolean;
  mobileAvdsError: string | null;
  selectedAvd: string;
  onSelectedAvdChange: (value: string) => void;
  onRefreshAvds: () => void;
  onRefreshMobileEnv: (preferAvdName?: string) => void;
  onOpenEnvironmentSettings?: () => void;
  emulatorStarting: boolean;
  onStartEmulator: (avdOverride?: string) => void;
  emulatorMessage: string | null;
  emulatorMessageTone: EmulatorMessageTone;
  mobileFieldError: string | null;
  appSource: "installed" | "apk";
  onAppSourceChange: (value: "installed" | "apk") => void;
  appPackage: string;
  onAppPackageChange: (value: string) => void;
  appActivity: string;
  onAppActivityChange: (value: string) => void;
  detectingForegroundApp: boolean;
  onDetectForegroundApp: () => void;
  apkPath: string;
  onApkPathChange: (value: string) => void;
  onClearMobileFieldError: () => void;
};

const fieldInputStyle = (c: Record<string, string>): React.CSSProperties => ({
  padding: "10px 12px",
  borderRadius: 10,
  border: `1px solid ${c.inputBorder}`,
  background: c.inputBg,
  color: c.text,
  outline: "none",
  fontSize: 14,
});

export function MobileConfigForm(props: MobileConfigFormProps) {
  const {
    c,
    license,
    mobilePreflight,
    mobilePreflightLoading,
    mobileEnvOpen,
    onMobileEnvOpenChange,
    appiumStatus,
    appiumStarting,
    onStartAppium,
    onStopAppium,
    deviceMode,
    onDeviceModeChange,
    deviceId,
    onDeviceIdChange,
    deviceManualMode,
    onDeviceManualModeChange,
    mobileDevices,
    mobileDevicesLoading,
    mobileDevicesError,
    onRefreshDevices,
    mobileAvds,
    mobileAvdsLoading,
    mobileAvdsError,
    selectedAvd,
    onSelectedAvdChange,
    onRefreshAvds,
    onRefreshMobileEnv,
    onOpenEnvironmentSettings,
    emulatorStarting,
    onStartEmulator,
    emulatorMessage,
    emulatorMessageTone,
    mobileFieldError,
    appSource,
    onAppSourceChange,
    appPackage,
    onAppPackageChange,
    appActivity,
    onAppActivityChange,
    detectingForegroundApp,
    onDetectForegroundApp,
    apkPath,
    onApkPathChange,
    onClearMobileFieldError,
  } = props;

  const severity = preflightSeverity(mobilePreflight);
  const severityBorder =
    severity === "error" ? c.severityErrorBorder : severity === "warn" ? c.severityWarnBorder : c.inputBorder;
  const severityText =
    severity === "error" ? c.severityErrorText : severity === "warn" ? c.severityWarnText : c.text;

  const physicalDevices = useMemo(
    () => mobileDevices.filter((d) => d.kind === "physical"),
    [mobileDevices],
  );

  const onlineEmulators = useMemo(
    () => mobileDevices.filter((d) => d.kind === "emulator" && d.state === "device"),
    [mobileDevices],
  );
  const hasOnlineEmulator = onlineEmulators.length > 0;
  const primaryOnlineEmulator = onlineEmulators[0];

  const avdSelectRef = useRef<HTMLSelectElement>(null);
  const [avdWizardOpen, setAvdWizardOpen] = useState(false);
  const [avdUpsellOpen, setAvdUpsellOpen] = useState(false);
  const [studioHint, setStudioHint] = useState<string | null>(null);
  const [studioPathPanelOpen, setStudioPathPanelOpen] = useState(false);
  const [studioSdkOk, setStudioSdkOk] = useState(false);
  const canOrchestrateAvd = avdOrchestrationAllowed(license);
  const canPickAvd = !mobileAvdsLoading && mobileAvds.length > 0;
  const hasSelectedAvd = Boolean(selectedAvd.trim());
  const canLaunchNewAvd = canPickAvd && hasSelectedAvd && !emulatorStarting;
  const showAvdCatalogEmpty =
    !mobileAvdsLoading && mobileAvds.length === 0 && !mobileAvdsError && !hasOnlineEmulator;
  const showAvdCatalogEmptyButEmulatorRunning =
    !mobileAvdsLoading && mobileAvds.length === 0 && !mobileAvdsError && hasOnlineEmulator;

  const handleStartEmulatorClick = () => {
    if (hasOnlineEmulator && !canPickAvd) {
      return;
    }
    const fromSelect = avdSelectRef.current?.value?.trim() ?? "";
    onStartEmulator(fromSelect || selectedAvd.trim() || undefined);
  };

  const deviceSelectValue = deviceManualMode
    ? MANUAL_DEVICE_OPTION
    : physicalDevices.some((d) => d.id === deviceId)
      ? deviceId
      : "";

  const handleDeviceSelectChange = (value: string) => {
    if (value === MANUAL_DEVICE_OPTION) {
      onDeviceManualModeChange(true);
      return;
    }
    onDeviceManualModeChange(false);
    onDeviceIdChange(value);
  };

  const handleOpenStudio = () => {
    setStudioHint(null);
    setStudioPathPanelOpen(false);
    setStudioSdkOk(false);
    void (async () => {
      try {
        const res = await openMobileAndroidStudio();
        if (!res.ok) {
          setStudioHint(res.message);
          setStudioSdkOk(Boolean(res.sdk_ok));
          setStudioPathPanelOpen(true);
          return;
        }
        setStudioHint(res.message);
      } catch (e: unknown) {
        setStudioHint(String((e as Error)?.message ?? e));
        setStudioPathPanelOpen(true);
      }
    })();
  };

  const handleAvdAssistantClick = () => {
    if (canOrchestrateAvd) {
      setAvdWizardOpen(true);
      return;
    }
    setAvdUpsellOpen(true);
  };

  const handleRecheckAvdEnv = () => {
    onRefreshAvds();
    onRefreshMobileEnv();
    setStudioHint("Comprobando catálogo AVD y entorno…");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 14 }}>
      {mobilePreflightLoading && (
        <LoadingStatusRow
          c={c}
          text="Comprobando entorno Android…"
          testId="elia-mobile-preflight-loading"
          loading
        />
      )}

      {!mobilePreflightLoading && mobilePreflight && mobilePreflight.items.length > 0 && (
        <div
          data-testid="elia-mobile-preflight-checklist"
          style={{
            borderRadius: 10,
            border: `1px solid ${severityBorder}`,
            background: c.inputBg,
            overflow: "hidden",
          }}
        >
          <button
            type="button"
            data-testid="elia-mobile-env-toggle"
            onClick={() => onMobileEnvOpenChange(!mobileEnvOpen)}
            aria-expanded={mobileEnvOpen}
            style={{
              width: "100%",
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 12px",
              border: "none",
              background: "transparent",
              color: severityText,
              cursor: "pointer",
              textAlign: "left",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            <span style={{ fontSize: 11, color: c.muted, width: 14 }}>{mobileEnvOpen ? "▾" : "▸"}</span>
            <span>Diagnóstico de conexión</span>
            <span style={{ marginLeft: "auto", fontSize: 12, fontWeight: 500, color: c.muted }}>
              {(() => {
                const { ok, total } = mobilePreflightSummary(mobilePreflight.items);
                return `${ok}/${total} requisitos cumplidos`;
              })()}
            </span>
          </button>
          {mobileEnvOpen && (
            <div
              style={{
                fontSize: 11,
                color: c.muted,
                lineHeight: 1.5,
                padding: "0 12px 10px 34px",
                borderTop: `1px solid ${severityBorder}`,
              }}
            >
              {!mobilePreflight.ok && mobilePreflight.errors.length > 0 ? (
                <div data-testid="elia-mobile-preflight-errors" role="alert" style={{ marginBottom: 8 }}>
                  {mobilePreflight.errors.map((line, i) => (
                    <div key={i} style={{ color: c.severityErrorText }}>
                      {line}
                    </div>
                  ))}
                </div>
              ) : null}
              {normalizeMobileWarnings(mobilePreflight.warnings).length > 0 ? (
                <div data-testid="elia-mobile-preflight-warnings" style={{ marginBottom: 8 }}>
                  {normalizeMobileWarnings(mobilePreflight.warnings).map((line, i) => (
                    <div key={i} style={{ color: c.severityWarnText }}>
                      {line}
                    </div>
                  ))}
                </div>
              ) : null}
              {mobilePreflight.items.map((item) => (
                <div key={item.id}>
                  {item.ok ? "✓" : "✗"} {item.label}: {formatPreflightItemMessage(item)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {appiumStatus && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ fontSize: 12, color: c.muted, flex: "1 1 200px" }}>
            Appium {appiumStatus.url}:{" "}
            {appiumStatus.running
              ? "en ejecución"
              : appiumStatus.installed
                ? "detenido (instalado)"
                : "no instalado"}
            {appiumStatus.managed_by_elia ? " · iniciado por ELIA" : ""}
          </div>
          {!appiumStatus.running && appiumStatus.installed && (
            <EliaButton variant="primary" size="sm" data-testid="elia-mobile-start-appium" disabled={appiumStarting} onClick={onStartAppium}>
              {appiumStarting ? "Iniciando Appium…" : "Iniciar Appium"}
            </EliaButton>
          )}
          {appiumStatus.running && appiumStatus.managed_by_elia && (
            <EliaButton variant="ghost" size="sm" data-testid="elia-mobile-stop-appium" onClick={onStopAppium}>
              Detener Appium (ELIA)
            </EliaButton>
          )}
        </div>
      )}

      <FieldLabel
        c={c}
        tooltip="Dispositivo físico con USB/Wi‑Fi adb o emulador Android Studio (AVD). iOS no soportado."
      >
        Origen del dispositivo (Android)
      </FieldLabel>
      <SegmentedTabs
        c={c}
        value={deviceMode}
        onChange={onDeviceModeChange}
        options={[
          { id: "physical", label: "Dispositivo físico", testId: "elia-mobile-mode-physical" },
          { id: "emulator", label: "Emulador Android", testId: "elia-mobile-mode-emulator" },
        ]}
      />

      {deviceMode === "physical" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <FieldLabel
            c={c}
            tooltip="Conecta el móvil por USB o Wi‑Fi adb y activa la depuración USB en el dispositivo."
          >
            Dispositivo adb
          </FieldLabel>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <select
              data-testid="elia-mobile-device-select"
              value={deviceSelectValue}
              onChange={(e) => handleDeviceSelectChange(e.target.value)}
              style={{ ...fieldInputStyle(c), flex: "1 1 220px" }}
            >
              <option value="">— Selecciona dispositivo adb —</option>
              {physicalDevices.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.id}
                  {d.model ? ` · ${d.model}` : ""} ({d.state})
                </option>
              ))}
              <option value={MANUAL_DEVICE_OPTION}>✍️ Ingresar serial manualmente…</option>
            </select>
            <button
              type="button"
              data-testid="elia-mobile-refresh-devices"
              disabled={mobileDevicesLoading}
              onClick={onRefreshDevices}
              title="Actualizar lista adb"
              aria-label="Actualizar lista adb"
              style={{
                padding: "10px 12px",
                borderRadius: 10,
                border: `1px solid ${c.inputBorder}`,
                background: c.inputBg,
                color: c.text,
                cursor: mobileDevicesLoading ? "wait" : "pointer",
                fontSize: 13,
                minWidth: 44,
              }}
            >
              {mobileDevicesLoading ? "…" : "↻"}
            </button>
          </div>
          {mobileDevicesError && (
            <div style={{ fontSize: 11, color: c.errorTitle }}>{mobileDevicesError}</div>
          )}
          {deviceManualMode ? (
            <input
              data-testid="elia-mobile-device-manual"
              value={deviceId}
              onChange={(e) => onDeviceIdChange(e.target.value)}
              placeholder="Serial adb (adb devices)"
              style={fieldInputStyle(c)}
            />
          ) : null}
        </div>
      )}

      {deviceMode === "emulator" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {hasOnlineEmulator && primaryOnlineEmulator && (
            <LoadingStatusRow
              c={c}
              testId="elia-mobile-emulator-online"
              tone="success"
              text={`Emulador conectado en adb (${primaryOnlineEmulator.id}). Ya puedes grabar: selecciónalo abajo si no está activo. «Iniciar emulador» solo arranca un AVD nuevo desde el catálogo del SDK.`}
            />
          )}
          {showAvdCatalogEmptyButEmulatorRunning && (
            <LoadingStatusRow
              c={c}
              testId="elia-mobile-avd-catalog-empty-running"
              tone="neutral"
              text="El catálogo de AVDs del SDK está vacío (emulator -list-avds), pero hay un emulador en ejecución. No necesitas «Iniciar emulador» para esta sesión."
            />
          )}
          {showAvdCatalogEmpty && (
            <LoadingStatusRow
              c={c}
              testId="elia-mobile-no-avds"
              tone="neutral"
              text="No hay AVDs en el catálogo del SDK. Usa «Asistente AVD», abre Android Studio o pulsa «Comprobar de nuevo»."
            />
          )}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <EliaButton variant="ghost" size="sm" data-testid="elia-mobile-avd-assistant" onClick={handleAvdAssistantClick}>
              Asistente AVD
            </EliaButton>
            <EliaButton variant="ghost" size="sm" data-testid="elia-mobile-open-studio" onClick={handleOpenStudio}>
              Abrir Android Studio
            </EliaButton>
            <button
              type="button"
              data-testid="elia-mobile-recheck-avd"
              onClick={handleRecheckAvdEnv}
              style={{
                padding: "8px 12px",
                borderRadius: 10,
                border: `1px solid ${c.inputBorder}`,
                background: c.inputBg,
                color: c.text,
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              Comprobar de nuevo
            </button>
          </div>
          {studioHint && (
            <div style={{ fontSize: 11, color: c.muted, lineHeight: 1.45 }}>{studioHint}</div>
          )}
          {studioPathPanelOpen && (
            <AndroidStudioPathPanel
              c={c}
              open={studioPathPanelOpen}
              sdkOk={studioSdkOk}
              onOpenEnvironmentSettings={onOpenEnvironmentSettings}
              onClose={() => setStudioPathPanelOpen(false)}
              onOpened={(message) => {
                setStudioHint(message);
                setStudioPathPanelOpen(false);
              }}
            />
          )}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <select
              ref={avdSelectRef}
              data-testid="elia-mobile-avd-select"
              value={selectedAvd}
              onChange={(e) => onSelectedAvdChange(e.target.value)}
              disabled={mobileAvdsLoading || mobileAvds.length === 0}
              style={{ ...fieldInputStyle(c), flex: "1 1 220px" }}
              title={
                mobileAvds.length === 0
                  ? hasOnlineEmulator
                    ? "Catálogo AVD vacío; usa el emulador ya conectado en adb abajo"
                    : "Sin AVDs en el SDK"
                  : undefined
              }
            >
              <option value="">
                {mobileAvdsLoading
                  ? "Cargando AVDs…"
                  : mobileAvds.length === 0
                    ? hasOnlineEmulator
                      ? "— Sin AVDs en catálogo (emulador ya activo) —"
                      : "— Sin AVDs en el SDK —"
                    : "— Selecciona AVD —"}
              </option>
              {mobileAvds.map((avd) => (
                <option key={avd} value={avd}>
                  {avd}
                </option>
              ))}
            </select>
            <EliaButton
              variant="primary"
              size="sm"
              data-testid="elia-mobile-start-emulator"
              disabled={emulatorStarting || (hasOnlineEmulator && !canPickAvd) || !canLaunchNewAvd}
              onClick={handleStartEmulatorClick}
              title={
                hasOnlineEmulator && !canPickAvd
                  ? "Ya hay un emulador en adb; usa el selector de abajo"
                  : !canPickAvd
                    ? "Crea o importa un AVD en Android Studio y pulsa «AVDs»"
                    : !hasSelectedAvd
                      ? "Selecciona un AVD de la lista"
                      : undefined
              }
            >
              {emulatorStarting
                ? "Arrancando…"
                : hasOnlineEmulator && !canPickAvd
                  ? "Emulador activo"
                  : "Iniciar emulador"}
            </EliaButton>
            <button
              type="button"
              data-testid="elia-mobile-refresh-avds"
              disabled={mobileAvdsLoading}
              onClick={onRefreshAvds}
              style={{
                padding: "10px 12px",
                borderRadius: 10,
                border: `1px solid ${c.inputBorder}`,
                background: c.inputBg,
                color: c.text,
                cursor: mobileAvdsLoading ? "wait" : "pointer",
                fontSize: 13,
              }}
            >
              AVDs
            </button>
          </div>
          {friendlyAvdsError(mobileAvdsError) && (
            <div style={{ fontSize: 11, color: c.errorTitle }}>{friendlyAvdsError(mobileAvdsError)}</div>
          )}
          {!mobileAvdsLoading && mobileAvds.length > 0 && !hasSelectedAvd && !hasOnlineEmulator && (
            <LoadingStatusRow
              c={c}
              testId="elia-mobile-avd-hint"
              tone="neutral"
              text="Selecciona un AVD de la lista y pulsa «Iniciar emulador»."
            />
          )}
          {(emulatorMessage || emulatorStarting) && (
            <LoadingStatusRow
              c={c}
              text={emulatorMessage || "Iniciando emulador…"}
              testId="elia-mobile-emulator-status"
              loading={emulatorStarting || emulatorMessageTone === "loading"}
              tone={
                emulatorMessageTone === "error"
                  ? "error"
                  : emulatorMessageTone === "success"
                    ? "success"
                    : "neutral"
              }
            />
          )}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <select
              data-testid="elia-mobile-emulator-device-select"
              value={deviceId}
              onChange={(e) => onDeviceIdChange(e.target.value)}
              style={{ ...fieldInputStyle(c), flex: "1 1 220px" }}
            >
              <option value="">— Emulador en adb —</option>
              {mobileDevices
                .filter((d) => d.kind === "emulator")
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.id} ({d.state})
                  </option>
                ))}
            </select>
            <button
              type="button"
              disabled={mobileDevicesLoading}
              onClick={onRefreshDevices}
              title="Actualizar adb"
              aria-label="Actualizar adb"
              style={{
                padding: "10px 12px",
                borderRadius: 10,
                border: `1px solid ${c.inputBorder}`,
                background: c.inputBg,
                color: c.text,
                cursor: mobileDevicesLoading ? "wait" : "pointer",
                fontSize: 13,
              }}
            >
              ↻
            </button>
          </div>
        </div>
      )}

      <FieldLabel
        c={c}
        tooltip={
          <>
            ELIA puede iniciar Appium al grabar. Requiere Android SDK y adb en PATH. Variables opcionales: ELIA_APPIUM_PATH,
            ELIA_ANDROID_HOME.
          </>
        }
        style={{ marginTop: 4 }}
      >
        Aplicación a grabar
      </FieldLabel>
      <SegmentedTabs
        c={c}
        value={appSource}
        onChange={onAppSourceChange}
        options={[
          { id: "installed", label: "App instalada", testId: "elia-mobile-app-installed" },
          { id: "apk", label: "Instalar APK", testId: "elia-mobile-app-apk" },
        ]}
      />

      {mobileFieldError && (
        <div
          data-testid="elia-mobile-form-error"
          role="alert"
          style={{
            fontSize: 12,
            color: c.text,
            background: c.licWarnBg,
            border: `1px solid ${c.licWarnBorder}`,
            borderRadius: 10,
            padding: "10px 12px",
            lineHeight: 1.45,
          }}
        >
          {mobileFieldError}
        </div>
      )}

      {appSource === "installed" ? (
        <>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <input
              data-testid="elia-mobile-app-package"
              value={appPackage}
              onChange={(e) => {
                onAppPackageChange(e.target.value);
                onClearMobileFieldError();
              }}
              placeholder="Paquete (ej: com.empresa.miapp)"
              style={{ ...fieldInputStyle(c), flex: "1 1 220px" }}
            />
            <EliaButton
              variant="ghost"
              size="sm"
              data-testid="elia-mobile-detect-app"
              disabled={detectingForegroundApp || !deviceId.trim() || deviceId === MANUAL_DEVICE_OPTION}
              onClick={onDetectForegroundApp}
            >
              {detectingForegroundApp ? "Detectando…" : "Detectar app abierta"}
            </EliaButton>
          </div>
          <FieldLabel
            c={c}
            tooltip={
              <>
                Si dejas el paquete vacío, ELIA intentará detectar la app en primer plano al pulsar Grabar. También puedes
                usar «Detectar app abierta» con la app visible (no el launcher). Si la actividad está vacía, ELIA usa adb
                shell cmd package resolve-activity.
              </>
            }
          >
            Actividad principal (opcional)
          </FieldLabel>
          <input
            value={appActivity}
            onChange={(e) => onAppActivityChange(e.target.value)}
            placeholder="ej: .MainActivity"
            style={fieldInputStyle(c)}
          />
        </>
      ) : (
        <>
          <FieldLabel c={c} tooltip="Ruta absoluta del APK en este PC. ELIA lo instalará en el dispositivo al grabar.">
            Ruta del APK
          </FieldLabel>
          <input
            data-testid="elia-mobile-apk-path"
            value={apkPath}
            onChange={(e) => onApkPathChange(e.target.value)}
            placeholder="C:\apps\miapp.apk"
            style={fieldInputStyle(c)}
          />
        </>
      )}

      {avdUpsellOpen && (
        <AvdArchitectUpsellModal
          c={c}
          onClose={() => setAvdUpsellOpen(false)}
          onOpenStudio={handleOpenStudio}
          onOpenEnvironmentSettings={onOpenEnvironmentSettings}
        />
      )}
      {avdWizardOpen && (
        <AvdSetupWizardModal
          c={c}
          open={avdWizardOpen}
          onClose={() => setAvdWizardOpen(false)}
          onOpenEnvironmentSettings={onOpenEnvironmentSettings}
          onRefresh={(preferAvdName) => {
            onRefreshAvds();
            onRefreshMobileEnv(preferAvdName);
          }}
        />
      )}
    </div>
  );
}
