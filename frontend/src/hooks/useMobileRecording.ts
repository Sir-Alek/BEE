import { useCallback, useEffect, useState } from "react";
import {
  getMobileAvds,
  getMobileAppiumStatus,
  getMobileDevices,
  getMobileForegroundApp,
  getMobilePreflight,
  startMobileAppium,
  startMobileEmulator,
  type MobileAppiumStatusResponse,
  type MobileDeviceInfo,
  type MobilePreflightResponse,
} from "../api";
import { shouldAutoOpenMobileEnv } from "../mobileEnvUi";

export type ShowHomeErrorFn = (message: string, opts?: { mobileInline?: boolean }) => void;

export type UseMobileRecordingOptions = {
  isHomeSurface: boolean;
  homeTab: "ui" | "req";
  platform: "web" | "mobile" | "legacy";
  canRunJobs: boolean;
  onShowError: ShowHomeErrorFn;
  onSetHomeHint: (hint: string | null) => void;
};

export function useMobileRecording(options: UseMobileRecordingOptions) {
  const { isHomeSurface, homeTab, platform, canRunJobs, onShowError, onSetHomeHint } = options;

  const [apkPath, setApkPath] = useState("");
  const [deviceId, setDeviceId] = useState("");
  const [deviceMode, setDeviceMode] = useState<"physical" | "emulator">("physical");
  const [mobileDevices, setMobileDevices] = useState<MobileDeviceInfo[]>([]);
  const [mobileDevicesLoading, setMobileDevicesLoading] = useState(false);
  const [mobileDevicesError, setMobileDevicesError] = useState<string | null>(null);
  const [mobileAvds, setMobileAvds] = useState<string[]>([]);
  const [mobileAvdsLoading, setMobileAvdsLoading] = useState(false);
  const [mobileAvdsError, setMobileAvdsError] = useState<string | null>(null);
  const [selectedAvd, setSelectedAvd] = useState("");
  const [mobilePreflight, setMobilePreflight] = useState<MobilePreflightResponse | null>(null);
  const [mobilePreflightLoading, setMobilePreflightLoading] = useState(false);
  const [mobileEnvOpen, setMobileEnvOpen] = useState(false);
  const [emulatorStarting, setEmulatorStarting] = useState(false);
  const [emulatorMessage, setEmulatorMessage] = useState<string | null>(null);
  const [mobileFieldError, setMobileFieldError] = useState<string | null>(null);
  const [detectingForegroundApp, setDetectingForegroundApp] = useState(false);
  const [appiumStatus, setAppiumStatus] = useState<MobileAppiumStatusResponse | null>(null);
  const [appiumStarting, setAppiumStarting] = useState(false);
  const [appPackage, setAppPackage] = useState("");
  const [appActivity, setAppActivity] = useState("");

  const refreshMobileDevices = useCallback(async () => {
    setMobileDevicesLoading(true);
    setMobileDevicesError(null);
    try {
      const res = await getMobileDevices();
      const devices = res.devices ?? [];
      setMobileDevices(devices);
      if (res.error) setMobileDevicesError(res.error);
      const online = devices.filter((d) => d.state === "device");
      setDeviceId((prev) => {
        const filtered =
          deviceMode === "physical"
            ? online.filter((d) => d.kind === "physical")
            : online.filter((d) => d.kind === "emulator");
        if (filtered.length === 1) return filtered[0].id;
        if (prev && filtered.some((d) => d.id === prev)) return prev;
        return filtered[0]?.id ?? prev;
      });
    } catch {
      setMobileDevices([]);
      setMobileDevicesError("No se pudo obtener la lista de dispositivos adb.");
    } finally {
      setMobileDevicesLoading(false);
    }
  }, [deviceMode]);

  const refreshMobileAvds = useCallback(async () => {
    setMobileAvdsLoading(true);
    setMobileAvdsError(null);
    try {
      const res = await getMobileAvds();
      const avds = res.avds ?? [];
      setMobileAvds(avds);
      if (res.error) setMobileAvdsError(res.error);
      setSelectedAvd((prev) => (prev && avds.includes(prev) ? prev : avds[0] ?? ""));
    } catch {
      setMobileAvds([]);
      setMobileAvdsError("No se pudo listar AVDs del SDK.");
    } finally {
      setMobileAvdsLoading(false);
    }
  }, []);

  const refreshMobilePreflight = useCallback(async () => {
    try {
      const pf = await getMobilePreflight();
      setMobilePreflight(pf);
    } catch {
      // handled on tab load
    }
  }, []);

  const refreshAppiumStatus = useCallback(async () => {
    try {
      const st = await getMobileAppiumStatus();
      setAppiumStatus(st);
    } catch {
      setAppiumStatus(null);
    }
  }, []);

  useEffect(() => {
    if (!isHomeSurface || homeTab !== "ui" || platform !== "mobile" || !canRunJobs) return;
    let alive = true;
    setMobilePreflightLoading(true);
    void (async () => {
      try {
        const pf = await getMobilePreflight();
        if (alive) setMobilePreflight(pf);
      } catch {
        if (alive) {
          setMobilePreflight({
            ok: false,
            platform: "unknown",
            items: [],
            warnings: [],
            errors: ["No se pudo comprobar el entorno móvil. Reinicie ELIA e inténtelo de nuevo."],
            env: {},
            android_only: true,
          });
        }
      } finally {
        if (alive) setMobilePreflightLoading(false);
      }
    })();
    void refreshMobileDevices();
    void refreshMobileAvds();
    void refreshAppiumStatus();
    return () => {
      alive = false;
    };
  }, [isHomeSurface, homeTab, platform, canRunJobs, refreshMobileDevices, refreshMobileAvds, refreshAppiumStatus]);

  useEffect(() => {
    if (shouldAutoOpenMobileEnv(mobilePreflight)) {
      setMobileEnvOpen(true);
    }
  }, [mobilePreflight]);

  useEffect(() => {
    if (platform !== "mobile") return;
    void refreshMobileDevices();
  }, [deviceMode, platform, refreshMobileDevices]);

  const handleStartEmulator = useCallback(async () => {
    if (!selectedAvd.trim()) {
      setEmulatorMessage("Selecciona un AVD.");
      return;
    }
    setEmulatorStarting(true);
    setEmulatorMessage("Iniciando emulador…");
    try {
      const res = await startMobileEmulator({ avd: selectedAvd.trim(), wait_boot: true });
      if (res.device_id) setDeviceId(res.device_id);
      setEmulatorMessage(res.message || (res.ok ? "Emulador listo." : "No se pudo iniciar el emulador."));
      await refreshMobileDevices();
    } catch (e) {
      setEmulatorMessage(e instanceof Error ? e.message : "Error al iniciar el emulador.");
    } finally {
      setEmulatorStarting(false);
    }
  }, [refreshMobileDevices, selectedAvd]);

  const detectForegroundApp = useCallback(async (): Promise<{ package: string; activity: string } | null> => {
    if (!deviceId.trim()) {
      onShowError("Selecciona un dispositivo adb antes de detectar la app.", { mobileInline: true });
      return null;
    }
    setDetectingForegroundApp(true);
    setMobileFieldError(null);
    try {
      const fg = await getMobileForegroundApp(deviceId.trim());
      if (fg.ok && fg.package) {
        setAppPackage(fg.package);
        if (fg.activity) setAppActivity(fg.activity);
        onSetHomeHint(`App detectada en el móvil: ${fg.package}`);
        return { package: fg.package, activity: fg.activity ?? "" };
      }
      onShowError(
        fg.error ||
          "No se detectó ninguna app en primer plano. Abre la app en el móvil (no el launcher) e inténtalo de nuevo.",
        { mobileInline: true },
      );
      return null;
    } catch (e) {
      onShowError(
        e instanceof Error ? e.message : "No se pudo detectar la app en primer plano.",
        { mobileInline: true },
      );
      return null;
    } finally {
      setDetectingForegroundApp(false);
    }
  }, [deviceId, onShowError, onSetHomeHint]);

  const handleStartAppium = useCallback(async () => {
    setAppiumStarting(true);
    setMobileFieldError(null);
    try {
      const res = await startMobileAppium(60);
      await refreshAppiumStatus();
      await refreshMobilePreflight();
      if (res.ok && res.running) {
        onSetHomeHint(res.message || "Appium listo.");
      } else {
        onShowError(res.message || "No se pudo iniciar Appium.", { mobileInline: true });
      }
    } catch (e) {
      onShowError(e instanceof Error ? e.message : "Error al iniciar Appium.", { mobileInline: true });
    } finally {
      setAppiumStarting(false);
    }
  }, [refreshAppiumStatus, refreshMobilePreflight, onShowError, onSetHomeHint]);

  return {
    apkPath,
    setApkPath,
    deviceId,
    setDeviceId,
    deviceMode,
    setDeviceMode,
    mobileDevices,
    mobileDevicesLoading,
    mobileDevicesError,
    refreshMobileDevices,
    mobileAvds,
    mobileAvdsLoading,
    mobileAvdsError,
    selectedAvd,
    setSelectedAvd,
    refreshMobileAvds,
    mobilePreflight,
    mobilePreflightLoading,
    mobileEnvOpen,
    setMobileEnvOpen,
    emulatorStarting,
    handleStartEmulator,
    emulatorMessage,
    mobileFieldError,
    setMobileFieldError,
    detectingForegroundApp,
    detectForegroundApp,
    appiumStatus,
    appiumStarting,
    handleStartAppium,
    refreshAppiumStatus,
    refreshMobilePreflight,
    appPackage,
    setAppPackage,
    appActivity,
    setAppActivity,
  };
}
