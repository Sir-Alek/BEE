import React from "react";
import type {
  MobileAppiumStatusResponse,
  MobileDeviceInfo,
  MobilePreflightResponse,
} from "../api";
import {
  formatPreflightItemMessage,
  friendlyAvdsError,
  mobilePreflightSummary,
  normalizeMobileWarnings,
} from "../mobileEnvUi";

export type MobileConfigFormProps = {
  c: Record<string, string>;
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
  emulatorStarting: boolean;
  onStartEmulator: () => void;
  emulatorMessage: string | null;
  mobileFieldError: string | null;
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

export function MobileConfigForm(props: MobileConfigFormProps) {
  const {
    c,
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
    emulatorStarting,
    onStartEmulator,
    emulatorMessage,
    mobileFieldError,
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

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 14 }}>
      {mobilePreflightLoading && (
        <div style={{ fontSize: 12, color: c.muted }}>Comprobando entorno Android…</div>
      )}
      {!mobilePreflightLoading && mobilePreflight && !mobilePreflight.ok && (
        <div
          data-testid="elia-mobile-preflight-errors"
          role="alert"
          style={{
            fontSize: 13,
            color: c.text,
            background: c.licWarnBg,
            border: `1px solid ${c.licWarnBorder}`,
            borderRadius: 10,
            padding: "10px 12px",
            lineHeight: 1.45,
          }}
        >
          {mobilePreflight.errors.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
      )}
      {!mobilePreflightLoading &&
        mobilePreflight?.ok &&
        normalizeMobileWarnings(mobilePreflight.warnings).length > 0 && (
          <div
            data-testid="elia-mobile-preflight-warnings"
            style={{
              fontSize: 12,
              color: c.text,
              background: c.warnBg,
              border: `1px solid ${c.warnBorder}`,
              borderRadius: 10,
              padding: "10px 12px",
              lineHeight: 1.45,
            }}
          >
            {normalizeMobileWarnings(mobilePreflight.warnings).map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </div>
        )}
      {!mobilePreflightLoading && mobilePreflight && mobilePreflight.items.length > 0 && (
        <div
          data-testid="elia-mobile-preflight-checklist"
          style={{
            borderRadius: 10,
            border: `1px solid ${c.inputBorder}`,
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
              color: c.text,
              cursor: "pointer",
              textAlign: "left",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            <span style={{ fontSize: 11, color: c.muted, width: 14 }}>
              {mobileEnvOpen ? "▾" : "▸"}
            </span>
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
                borderTop: `1px solid ${c.inputBorder}`,
              }}
            >
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
            <button
              type="button"
              data-testid="elia-mobile-start-appium"
              disabled={appiumStarting}
              onClick={onStartAppium}
              style={{
                padding: "8px 12px",
                borderRadius: 10,
                border: "none",
                background: appiumStarting ? c.buttonDisabledBg : c.primary,
                color: c.primaryFg,
                cursor: appiumStarting ? "wait" : "pointer",
                fontSize: 13,
              }}
            >
              {appiumStarting ? "Iniciando Appium…" : "Iniciar Appium"}
            </button>
          )}
          {appiumStatus.running && appiumStatus.managed_by_elia && (
            <button
              type="button"
              data-testid="elia-mobile-stop-appium"
              onClick={onStopAppium}
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
              Detener Appium (ELIA)
            </button>
          )}
        </div>
      )}

      <div style={{ fontSize: 12, fontWeight: 600, color: c.text }}>Origen del dispositivo (Android)</div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button
          type="button"
          data-testid="elia-mobile-mode-physical"
          onClick={() => onDeviceModeChange("physical")}
          style={{
            padding: "8px 12px",
            borderRadius: 10,
            border: `1px solid ${deviceMode === "physical" ? c.primary : c.inputBorder}`,
            background: deviceMode === "physical" ? c.primary : c.inputBg,
            color: deviceMode === "physical" ? c.primaryFg : c.text,
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          Dispositivo físico
        </button>
        <button
          type="button"
          data-testid="elia-mobile-mode-emulator"
          onClick={() => onDeviceModeChange("emulator")}
          style={{
            padding: "8px 12px",
            borderRadius: 10,
            border: `1px solid ${deviceMode === "emulator" ? c.primary : c.inputBorder}`,
            background: deviceMode === "emulator" ? c.primary : c.inputBg,
            color: deviceMode === "emulator" ? c.primaryFg : c.text,
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          Emulador Android
        </button>
      </div>

      {deviceMode === "physical" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <select
              data-testid="elia-mobile-device-select"
              value={deviceId}
              onChange={(e) => onDeviceIdChange(e.target.value)}
              style={{
                flex: "1 1 220px",
                padding: "10px 12px",
                borderRadius: 10,
                border: `1px solid ${c.inputBorder}`,
                background: c.inputBg,
                color: c.text,
                fontSize: 14,
              }}
            >
              <option value="">— Selecciona dispositivo adb —</option>
              {mobileDevices
                .filter((d) => d.kind === "physical")
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.id}
                    {d.model ? ` · ${d.model}` : ""} ({d.state})
                  </option>
                ))}
            </select>
            <button
              type="button"
              data-testid="elia-mobile-refresh-devices"
              disabled={mobileDevicesLoading}
              onClick={onRefreshDevices}
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
              {mobileDevicesLoading ? "…" : "Actualizar"}
            </button>
          </div>
          {mobileDevicesError && (
            <div style={{ fontSize: 11, color: c.errorTitle }}>{mobileDevicesError}</div>
          )}
          <input
            value={deviceId}
            onChange={(e) => onDeviceIdChange(e.target.value)}
            placeholder="O escribe el serial manualmente (adb devices)"
            style={{
              padding: "10px 12px",
              borderRadius: 10,
              border: `1px solid ${c.inputBorder}`,
              background: c.inputBg,
              color: c.text,
              outline: "none",
              fontSize: 14,
            }}
          />
          <div style={{ fontSize: 11, color: c.muted, lineHeight: 1.45 }}>
            Conecta el móvil por USB o Wi‑Fi adb. Activa depuración USB en el dispositivo.
          </div>
        </div>
      )}

      {deviceMode === "emulator" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <select
              data-testid="elia-mobile-avd-select"
              value={selectedAvd}
              onChange={(e) => onSelectedAvdChange(e.target.value)}
              disabled={mobileAvdsLoading || mobileAvds.length === 0}
              style={{
                flex: "1 1 220px",
                padding: "10px 12px",
                borderRadius: 10,
                border: `1px solid ${c.inputBorder}`,
                background: c.inputBg,
                color: c.text,
                fontSize: 14,
              }}
            >
              <option value="">
                {mobileAvdsLoading ? "Cargando AVDs…" : "— Selecciona AVD —"}
              </option>
              {mobileAvds.map((avd) => (
                <option key={avd} value={avd}>
                  {avd}
                </option>
              ))}
            </select>
            <button
              type="button"
              data-testid="elia-mobile-start-emulator"
              disabled={emulatorStarting || !selectedAvd.trim()}
              onClick={onStartEmulator}
              style={{
                padding: "10px 12px",
                borderRadius: 10,
                border: "none",
                background: emulatorStarting ? c.buttonDisabledBg : c.primary,
                color: c.primaryFg,
                cursor: emulatorStarting ? "wait" : "pointer",
                fontSize: 13,
              }}
            >
              {emulatorStarting ? "Arrancando…" : "Iniciar emulador"}
            </button>
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
          {emulatorMessage && (
            <div style={{ fontSize: 11, color: c.muted, lineHeight: 1.45 }}>{emulatorMessage}</div>
          )}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <select
              data-testid="elia-mobile-emulator-device-select"
              value={deviceId}
              onChange={(e) => onDeviceIdChange(e.target.value)}
              style={{
                flex: "1 1 220px",
                padding: "10px 12px",
                borderRadius: 10,
                border: `1px solid ${c.inputBorder}`,
                background: c.inputBg,
                color: c.text,
                fontSize: 14,
              }}
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
              adb
            </button>
          </div>
          <div style={{ fontSize: 11, color: c.muted, lineHeight: 1.45 }}>
            Requiere Android SDK + imagen AVD creada en Android Studio. iOS no soportado.
          </div>
        </div>
      )}

      <div style={{ fontSize: 12, fontWeight: 600, color: c.text, marginTop: 4 }}>
        App ya instalada en el móvil
      </div>
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
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <input
          data-testid="elia-mobile-app-package"
          value={appPackage}
          onChange={(e) => {
            onAppPackageChange(e.target.value);
            onClearMobileFieldError();
          }}
          placeholder="Paquete Android (ej: com.empresa.miapp) — opcional si detectas la app abierta"
          style={{
            flex: "1 1 220px",
            padding: "10px 12px",
            borderRadius: 10,
            border: `1px solid ${c.inputBorder}`,
            background: c.inputBg,
            color: c.text,
            outline: "none",
            fontSize: 14,
          }}
        />
        <button
          type="button"
          data-testid="elia-mobile-detect-app"
          disabled={detectingForegroundApp || !deviceId.trim()}
          onClick={onDetectForegroundApp}
          style={{
            padding: "10px 12px",
            borderRadius: 10,
            border: `1px solid ${c.inputBorder}`,
            background: c.inputBg,
            color: c.text,
            cursor: detectingForegroundApp || !deviceId.trim() ? "wait" : "pointer",
            fontSize: 13,
          }}
        >
          {detectingForegroundApp ? "Detectando…" : "Detectar app abierta"}
        </button>
      </div>
      <input
        value={appActivity}
        onChange={(e) => onAppActivityChange(e.target.value)}
        placeholder="Actividad principal — opcional (ej: .MainActivity)"
        style={{
          padding: "10px 12px",
          borderRadius: 10,
          border: `1px solid ${c.inputBorder}`,
          background: c.inputBg,
          color: c.text,
          outline: "none",
          fontSize: 14,
        }}
      />
      <div style={{ fontSize: 11, color: c.muted, lineHeight: 1.45 }}>
        Si dejas el paquete vacío, ELIA intentará detectar la app en primer plano al pulsar Grabar.
        También puedes usar «Detectar app abierta» con la app visible en el móvil (no la pantalla de inicio).
        Si dejas la actividad vacía, ELIA intenta detectarla con{" "}
        <code style={{ fontSize: 11 }}>adb shell cmd package resolve-activity</code>.
      </div>
      <div style={{ fontSize: 12, fontWeight: 600, color: c.text, marginTop: 4 }}>
        O instalar desde APK en este PC
      </div>
      <input
        value={apkPath}
        onChange={(e) => onApkPathChange(e.target.value)}
        placeholder="Ruta del APK en Windows (opcional, ej: C:\apps\miapp.apk)"
        style={{
          padding: "10px 12px",
          borderRadius: 10,
          border: `1px solid ${c.inputBorder}`,
          background: c.inputBg,
          color: c.text,
          outline: "none",
          fontSize: 14,
        }}
      />
      <div style={{ fontSize: 12, color: c.muted }}>
        ELIA puede iniciar Appium automáticamente al grabar si está instalado. Requiere Android SDK y{" "}
        <code style={{ fontSize: 11 }}>adb</code> en el PATH. Variables opcionales:{" "}
        <code style={{ fontSize: 11 }}>ELIA_APPIUM_PATH</code>,{" "}
        <code style={{ fontSize: 11 }}>ELIA_ANDROID_HOME</code>.
      </div>
    </div>
  );
}
