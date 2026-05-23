import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  getAiCapabilities,
  getAiMemoryStatus,
  getAppAbout,
  putAiPreferences,
  type AiMemoryStatusResponse,
  type AppAboutResponse,
  getEliaConnectors,
  getLicenseStatus,
  getMobileAvds,
  getMobileAppiumStatus,
  getMobileDevices,
  getMobileForegroundApp,
  getMobilePreflight,
  getModulesStatus,
  getRecorderPreflight,
  getScenarios,
  getRecordings,
  type MobileAppiumStatusResponse,
  type MobileDeviceInfo,
  type MobilePreflightResponse,
  type RecorderPreflightResponse,
  type AiCapabilitiesResponse,
  putEliaConnectors,
  startConvertJob,
  startMobileAppium,
  startMobileEmulator,
  stopMobileAppium,
  uploadDocs,
} from "./api";
import { shouldAutoOpenMobileEnv } from "./mobileEnvUi";
import type {
  ActivePrompt,
  EliaConnectorProfile,
  LoadedDoc,
  ModulesStatus,
  RecordingRef,
  ScenarioRef,
} from "./types";
import { ELIA_CONNECTORS_LS_KEY, newConnectorProfile } from "./connectorDefaults";
import { themeQuerySuffix, useEliaTheme } from "./eliaTheme";
import { useJobProgress } from "./job/useJobProgress";
import type { RecordingConfig } from "./recording/types";
import { buildConvertJobBody, validateRecordingStart } from "./recording/validateRecordingConfig";
import { ELIA_UI_BC, HOME_ERROR_DISMISS_MS } from "./app/constants";
import { encodeRecordingLink, encodeScenarioLink } from "./app/linkUtils";
import { licenseFromApi, type LicenseState } from "./app/licenseUtils";
import { settingsTabsForLicense, SETTINGS_TABS_WITHOUT_LICENSE, type SettingsTabId } from "./app/settingsTabs";
import { openJobUrlInNewTabPrepared } from "./app/utils";
import { HomeSurface } from "./home/HomeSurface";
import { AppHeader, ErrorAlert } from "./layout/AppShell";
import { JobWorkspace } from "./job/JobWorkspace";
import { SettingsDialog } from "./settings/SettingsDialog";

export default function App() {
  const { c, dark, toggle } = useEliaTheme();

  /** Pinned from first paint: home URL has no job_id; avoids any edge case mixing job UI into home. */
  const [isHomeSurface] = useState(() => !new URLSearchParams(window.location.search).get("job_id"));
  const [homeTab, setHomeTab] = useState<"ui" | "req">("ui");

  const [jobId, setJobId] = useState<string | null>(null);
  const [polling, setPolling] = useState<boolean>(false);
  const {
    job,
    events: jobEvents,
    errorText: jobPollError,
  } = useJobProgress(jobId, polling);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [textValue, setTextValue] = useState<string>("");
  const [urlValue, setUrlValue] = useState<string>("");
  const [initialChecked, setInitialChecked] = useState<boolean>(false);
  const [workspaceMode, setWorkspaceMode] = useState<string | null>(null);
  const [stoppingRecording, setStoppingRecording] = useState(false);
  const [homeHint, setHomeHint] = useState<string | null>(null);
  /** Solo afecta a «Convertir a Behave»: llama.cpp + GGUF + metadatos de grabación. */
  const [aiCaps, setAiCaps] = useState<AiCapabilitiesResponse | null>(null);
  const [aiPrefsSaving, setAiPrefsSaving] = useState(false);
  const [aiMemoryOpen, setAiMemoryOpen] = useState(false);
  const [aiMemoryStatus, setAiMemoryStatus] = useState<AiMemoryStatusResponse | null>(null);
  const [aiMemoryTeamPassphrase, setAiMemoryTeamPassphrase] = useState("");
  const [aiMemoryImportMode, setAiMemoryImportMode] = useState<"merge" | "replace">("merge");
  const [aiMemoryImportFile, setAiMemoryImportFile] = useState<File | null>(null);
  const [aiMemoryBusy, setAiMemoryBusy] = useState(false);
  const [aiMemoryMsg, setAiMemoryMsg] = useState<string | null>(null);
  const [license, setLicense] = useState<LicenseState | null>(null);
  const [activationKey, setActivationKey] = useState("");
  const [licenseActivateMsg, setLicenseActivateMsg] = useState<string | null>(null);
  const [fpCopyAck, setFpCopyAck] = useState(false);
  /** Huella en pestaña Licencia: solo visible tras pulsar «Obtener huella»; se oculta al cerrar Configuración. */
  const [licenseFpVisible, setLicenseFpVisible] = useState(false);
  const [bddPreviewText, setBddPreviewText] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState<SettingsTabId>("general");
  const [aboutInfo, setAboutInfo] = useState<AppAboutResponse | null>(null);
  const [aboutChangelogOpen, setAboutChangelogOpen] = useState(false);
  const [connectorProfiles, setConnectorProfiles] = useState<EliaConnectorProfile[]>([]);
  const [reqConnectorProfileId, setReqConnectorProfileId] = useState("");
  const [settingsProfileId, setSettingsProfileId] = useState("");
  const [settingsTestMsg, setSettingsTestMsg] = useState<string | null>(null);
  const [settingsSaveMsg, setSettingsSaveMsg] = useState<string | null>(null);

  // Building Blocks — módulos por licencia
  const [modules, setModules] = useState<ModulesStatus | null>(null);
  const [showLockModal, setShowLockModal] = useState<string | null>(null);
  const canRunJobs = license?.can_run_jobs ?? false;
  const visibleSettingsTabs = settingsTabsForLicense(canRunJobs);

  // UI Automation — selector de plataforma
  const [platform, setPlatform] = useState<"web" | "mobile" | "legacy">("web");
  const [recorderPreflight, setRecorderPreflight] = useState<RecorderPreflightResponse | null>(null);
  const [recorderPreflightLoading, setRecorderPreflightLoading] = useState(false);
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
  const [windowName, setWindowName] = useState("");
  const [exePath, setExePath] = useState("");

  const recordingConfig = useMemo((): RecordingConfig => {
    if (platform === "mobile") {
      return {
        platform: "mobile",
        deviceId,
        deviceMode,
        apkPath,
        appPackage,
        appActivity,
      };
    }
    if (platform === "legacy") {
      return { platform: "legacy", windowName, exePath };
    }
    return { platform: "web", url: urlValue };
  }, [
    platform,
    urlValue,
    deviceId,
    deviceMode,
    apkPath,
    appPackage,
    appActivity,
    windowName,
    exePath,
  ]);

  // Req Intelligence — ingesta de documentos
  const [loadedDocs, setLoadedDocs] = useState<LoadedDoc[]>([]);
  const [docDragOver, setDocDragOver] = useState(false);
  const [docUploadError, setDocUploadError] = useState<string | null>(null);
  const [linkRecordings, setLinkRecordings] = useState(false);
  const [availableScenarios, setAvailableScenarios] = useState<ScenarioRef[]>([]);
  const [linkMapping, setLinkMapping] = useState<Record<string, string>>({});
  const [recordingMapping, setRecordingMapping] = useState<Record<string, string>>({});
  const [availableRecordings, setAvailableRecordings] = useState<RecordingRef[]>([]);
  const [autoLinkToScenario, setAutoLinkToScenario] = useState(false);
  const [autoLinkScenarioRef, setAutoLinkScenarioRef] = useState("");

  const activePrompt = (job?.active_prompt ?? null) as ActivePrompt | null;

  const persistConnectorProfiles = useCallback(async (next: EliaConnectorProfile[]) => {
    const doc = { version: 1 as const, profiles: next };
    try {
      localStorage.setItem(ELIA_CONNECTORS_LS_KEY, JSON.stringify(doc));
    } catch {
      // ignore
    }
    try {
      await putEliaConnectors(doc);
    } catch {
      // guardar local aunque backend falle (p. ej. sin cryptography instalado)
    }
  }, []);

  useEffect(() => {
    if (!isHomeSurface) return;
    let alive = true;
    void (async () => {
      let localProfiles: EliaConnectorProfile[] = [];
      try {
        const raw = localStorage.getItem(ELIA_CONNECTORS_LS_KEY);
        if (raw) {
          const p = JSON.parse(raw) as { profiles?: EliaConnectorProfile[] };
          if (Array.isArray(p?.profiles)) localProfiles = p.profiles;
        }
      } catch {
        localProfiles = [];
      }
      try {
        const remote = await getEliaConnectors();
        if (!alive) return;
        const r = remote?.profiles ?? [];
        const use = r.length ? r : localProfiles;
        setConnectorProfiles(use);
        const firstId = use[0]?.id ?? "";
        setReqConnectorProfileId((prev) => (prev && use.some((x) => x.id === prev) ? prev : firstId));
        setSettingsProfileId((prev) => (prev && use.some((x) => x.id === prev) ? prev : firstId));
      } catch {
        if (!alive) return;
        setConnectorProfiles(localProfiles);
        const firstId = localProfiles[0]?.id ?? "";
        setReqConnectorProfileId((prev) =>
          prev && localProfiles.some((x) => x.id === prev) ? prev : firstId,
        );
        setSettingsProfileId((prev) =>
          prev && localProfiles.some((x) => x.id === prev) ? prev : firstId,
        );
      }
    })();
    return () => {
      alive = false;
    };
  }, [isHomeSurface]);

  const refreshAiCapabilities = useCallback(async () => {
    try {
      const caps = await getAiCapabilities();
      setAiCaps(caps);
    } catch {
      setAiCaps(null);
    }
  }, []);

  const refreshAiMemoryStatus = useCallback(async () => {
    try {
      const st = await getAiMemoryStatus();
      setAiMemoryStatus(st);
    } catch {
      setAiMemoryStatus(null);
    }
  }, []);

  useEffect(() => {
    if (!isHomeSurface) return;
    void refreshAiCapabilities();
  }, [isHomeSurface, refreshAiCapabilities]);

  useEffect(() => {
    if (settingsOpen && isHomeSurface) void refreshAiCapabilities();
  }, [settingsOpen, isHomeSurface, refreshAiCapabilities]);

  useEffect(() => {
    if (!settingsOpen || settingsTab !== "ai" || !isHomeSurface) return;
    void refreshAiMemoryStatus();
  }, [settingsOpen, settingsTab, isHomeSurface, refreshAiMemoryStatus]);

  useEffect(() => {
    if (!settingsOpen) {
      setAboutChangelogOpen(false);
      return;
    }
    let alive = true;
    void (async () => {
      try {
        const info = await getAppAbout();
        if (alive) setAboutInfo(info);
      } catch {
        if (alive) setAboutInfo(null);
      }
    })();
    return () => {
      alive = false;
    };
  }, [settingsOpen]);

  const deleteConnectorProfile = useCallback(() => {
    const p = connectorProfiles.find((x) => x.id === settingsProfileId);
    if (!p) return;
    if (!window.confirm(`¿Eliminar el perfil «${p.name}»? Esta acción no se puede deshacer.`)) return;
    const next = connectorProfiles.filter((x) => x.id !== settingsProfileId);
    setConnectorProfiles(next);
    setSettingsProfileId(next[0]?.id ?? "");
    setSettingsTestMsg(null);
    setSettingsSaveMsg(null);
    void persistConnectorProfiles(next);
  }, [connectorProfiles, settingsProfileId, persistConnectorProfiles]);

  const duplicateConnectorProfile = useCallback(() => {
    const p = connectorProfiles.find((x) => x.id === settingsProfileId);
    if (!p) return;
    const np = newConnectorProfile(connectorProfiles.length + 1);
    const copy = {
      ...np,
      name: `${p.name} (copia)`,
      jira: { ...p.jira },
      value_edge: { ...p.value_edge },
    };
    const next = [...connectorProfiles, copy];
    setConnectorProfiles(next);
    setSettingsProfileId(copy.id);
    setSettingsTestMsg(null);
    setSettingsSaveMsg(null);
  }, [connectorProfiles, settingsProfileId]);

  const refreshLicense = useCallback(async () => {
    try {
      const l = await getLicenseStatus();
      setLicense(licenseFromApi(l));
    } catch {
      setLicense(null);
    }
  }, []);

  useEffect(() => {
    if (!isHomeSurface) return;
    void refreshLicense();
  }, [isHomeSurface, refreshLicense]);

  useEffect(() => {
    if (!settingsOpen || !isHomeSurface) return;
    void refreshLicense();
  }, [settingsOpen, isHomeSurface, refreshLicense]);

  useEffect(() => {
    if (!settingsOpen) {
      setLicenseFpVisible(false);
      setFpCopyAck(false);
    }
  }, [settingsOpen]);

  useEffect(() => {
    if (canRunJobs) return;
    if (!SETTINGS_TABS_WITHOUT_LICENSE.includes(settingsTab)) {
      setSettingsTab("license");
    }
  }, [canRunJobs, settingsTab]);

  useEffect(() => {
    if (canRunJobs) return;
    setAutoLinkToScenario(false);
    setAutoLinkScenarioRef("");
    setLinkRecordings(false);
    setLinkMapping({});
    setRecordingMapping({});
    setLoadedDocs([]);
  }, [canRunJobs]);

  // Cargar estado de módulos (Building Blocks)
  useEffect(() => {
    if (!isHomeSurface) return;
    let alive = true;
    void (async () => {
      try {
        const m = await getModulesStatus();
        if (alive) setModules(m);
      } catch {
        if (alive) setModules(null);
      }
    })();
    return () => { alive = false; };
  }, [isHomeSurface, canRunJobs]);

  useEffect(() => {
    if (!isHomeSurface || homeTab !== "ui" || platform !== "web" || !canRunJobs) return;
    let alive = true;
    setRecorderPreflightLoading(true);
    void (async () => {
      try {
        const pf = await getRecorderPreflight();
        if (alive) setRecorderPreflight(pf);
      } catch {
        if (alive) {
          setRecorderPreflight({
            ok: false,
            chrome_path: null,
            source: null,
            warnings: [],
            errors: ["No se pudo comprobar Chrome. Reinicie ELIA e inténtelo de nuevo."],
            chrome_required: true,
            chromium_fallback_enabled: false,
            platform: "unknown",
          });
        }
      } finally {
        if (alive) setRecorderPreflightLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [isHomeSurface, homeTab, platform, canRunJobs]);

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
      // ignore; handled on tab load
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

  // Close home tab = close whole app (backend). sendBeacon/fetch + main.py polling /api/app/should-exit.
  useEffect(() => {
    if (!isHomeSurface) return;
    const body = JSON.stringify({ reason: "home_closed" });
    const fireExit = () => {
      try {
        const blob = new Blob([body], { type: "application/json" });
        if (!navigator.sendBeacon("/api/app/exit", blob)) {
          void fetch("/api/app/exit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body,
            keepalive: true,
          });
        }
      } catch {
        try {
          void fetch("/api/app/exit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body,
            keepalive: true,
          });
        } catch {
          // ignore
        }
      }
    };
    window.addEventListener("beforeunload", fireExit);
    window.addEventListener("pagehide", fireExit);
    return () => {
      window.removeEventListener("beforeunload", fireExit);
      window.removeEventListener("pagehide", fireExit);
    };
  }, [isHomeSurface]);

  const scrollToUserMessage = useCallback((testId: string) => {
    requestAnimationFrame(() => {
      document.querySelector(`[data-testid="${testId}"]`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }, []);

  const showHomeError = useCallback(
    (message: string, opts?: { mobileInline?: boolean }) => {
      setErrorText(message);
      if (opts?.mobileInline) {
        setMobileFieldError(message);
        scrollToUserMessage("elia-mobile-form-error");
      } else {
        scrollToUserMessage("elia-error-alert");
      }
    },
    [scrollToUserMessage],
  );

  const detectForegroundApp = useCallback(async (): Promise<{ package: string; activity: string } | null> => {
    if (!deviceId.trim()) {
      showHomeError("Selecciona un dispositivo adb antes de detectar la app.", { mobileInline: true });
      return null;
    }
    setDetectingForegroundApp(true);
    setMobileFieldError(null);
    try {
      const fg = await getMobileForegroundApp(deviceId.trim());
      if (fg.ok && fg.package) {
        setAppPackage(fg.package);
        if (fg.activity) setAppActivity(fg.activity);
        setHomeHint(`App detectada en el móvil: ${fg.package}`);
        return { package: fg.package, activity: fg.activity ?? "" };
      }
      showHomeError(
        fg.error ||
          "No se detectó ninguna app en primer plano. Abre la app en el móvil (no el launcher) e inténtalo de nuevo.",
        { mobileInline: true },
      );
      return null;
    } catch (e) {
      showHomeError(
        e instanceof Error ? e.message : "No se pudo detectar la app en primer plano.",
        { mobileInline: true },
      );
      return null;
    } finally {
      setDetectingForegroundApp(false);
    }
  }, [deviceId, showHomeError]);

  const handleStartAppium = useCallback(async () => {
    setAppiumStarting(true);
    setMobileFieldError(null);
    try {
      const res = await startMobileAppium(60);
      await refreshAppiumStatus();
      await refreshMobilePreflight();
      if (res.ok && res.running) {
        setHomeHint(res.message || "Appium listo.");
      } else {
        showHomeError(res.message || "No se pudo iniciar Appium.", { mobileInline: true });
      }
    } catch (e) {
      showHomeError(e instanceof Error ? e.message : "Error al iniciar Appium.", { mobileInline: true });
    } finally {
      setAppiumStarting(false);
    }
  }, [refreshAppiumStatus, refreshMobilePreflight, showHomeError]);

  const startJob = async (
    mode:
      | "puppeteer_recorder"
      | "puppeteer_to_behave"
      | "puppeteer_to_step_by_step"
      | "mobile_recorder"
      | "legacy_recorder"
      | "mobile_to_behave"
      | "legacy_to_behave"
      | "doc_to_bdd"
      // ELIA
      | "elia_jira_smoke"
      | "elia_value_edge_smoke"
      | "elia_gherkin_batch",
  ) => {
    setErrorText(null);
    setHomeHint(null);
    setMobileFieldError(null);
    if (license && !license.can_run_jobs) {
      showHomeError("Licencia requerida. Activa ELIA en Configuración (⚙) → Licencia.");
      return;
    }

    const validation = validateRecordingStart({
      mode,
      config: recordingConfig,
      recorderPreflightOk: recorderPreflight?.ok ?? null,
      mobilePreflightOk: mobilePreflight?.ok ?? null,
      loadedDocsCount: loadedDocs.length,
      connectorProfiles,
      reqConnectorProfileId,
    });
    if (!validation.ok) {
      showHomeError(validation.message, { mobileInline: validation.mobileInline });
      return;
    }

    let mobilePkg = recordingConfig.platform === "mobile" ? recordingConfig.appPackage.trim() : "";
    let mobileAct = recordingConfig.platform === "mobile" ? recordingConfig.appActivity.trim() : "";

    if (mode === "mobile_recorder" && recordingConfig.platform === "mobile") {
      if (!recordingConfig.apkPath.trim() && !mobilePkg) {
        const detected = await detectForegroundApp();
        if (detected?.package) {
          mobilePkg = detected.package;
          mobileAct = detected.activity || mobileAct;
        }
      }
      if (!recordingConfig.apkPath.trim() && !mobilePkg) {
        return;
      }
    }

    const newTab = openJobUrlInNewTabPrepared();
    if (!newTab) {
      showHomeError(
        "El navegador bloqueó la ventana emergente. Permite ventanas emergentes para 127.0.0.1 e inténtalo de nuevo. " +
          "Sin eso, el flujo podría abrirse en esta misma pestaña y reemplazar el inicio.",
      );
      return;
    }

    void (async () => {
      try {
        const prof = connectorProfiles.find((x) => x.id === reqConnectorProfileId);

        const res = await startConvertJob(
          buildConvertJobBody({
            mode,
            config: recordingConfig,
            urlValue,
            mobilePackageOverride:
              mode === "mobile_recorder" ? { package: mobilePkg, activity: mobileAct } : undefined,
            docExtras:
              mode === "doc_to_bdd" ||
              mode === "puppeteer_to_behave" ||
              mode === "mobile_to_behave" ||
              mode === "legacy_to_behave"
                ? {
                    loadedDocs,
                    linkMapping,
                    recordingMapping,
                    linkRecordings,
                    autoLinkToScenario,
                    autoLinkScenarioRef,
                  }
                : undefined,
            connectorProfile: prof,
          }),
        );
        const base = `${window.location.origin}${window.location.pathname}`;
        const jobUrl = `${base}?job_id=${encodeURIComponent(res.job_id)}&mode=${encodeURIComponent(mode)}${themeQuerySuffix()}`;
        try {
          newTab.location.replace(jobUrl);
        } catch {
          newTab.location.href = jobUrl;
        }
        setHomeHint(
          "El flujo se abrió en otra pestaña. Esta vista es el inicio: déjala abierta y usa la otra pestaña para los pasos y el resultado.",
        );
      } catch (e: any) {
        try {
          newTab.close();
        } catch {
          // ignore
        }
        setErrorText(String(e?.message ?? e));
      }
    })();
  };

  useEffect(() => {
    if (activePrompt?.type === "input_text") {
      const ap = activePrompt as { payload?: { suggested?: string } };
      setTextValue(ap.payload?.suggested ?? "");
    }
  }, [activePrompt?.prompt_id, activePrompt?.type]);

  useEffect(() => {
    const ap = activePrompt as { type?: string; payload?: { feature_text?: string } } | null;
    if (
      (ap?.type === "bdd_preview" || ap?.type === "grouped_feature_review") &&
      ap.payload?.feature_text != null
    ) {
      setBddPreviewText(String(ap.payload.feature_text));
    }
  }, [activePrompt?.prompt_id, activePrompt?.type]);

  useEffect(() => {
    const sp = new URLSearchParams(window.location.search);
    const initialJobId = sp.get("job_id");
    const mode = sp.get("mode");
    if (mode) setWorkspaceMode(mode);

    if (initialJobId) {
      setJobId(initialJobId);
      setPolling(true);
      setInitialChecked(true);
      return;
    }

    setInitialChecked(true);
  }, []);

  useEffect(() => {
    if (!isHomeSurface) return;
    let bc: BroadcastChannel | null = null;
    try {
      bc = new BroadcastChannel(ELIA_UI_BC);
      bc.onmessage = (ev: MessageEvent) => {
        if (ev.data?.type === "elia_job_finished") {
          setHomeHint(null);
        }
      };
    } catch {
      // ignore
    }
    return () => {
      try {
        bc?.close();
      } catch {
        // ignore
      }
    };
  }, [isHomeSurface]);

  useEffect(() => {
    if (!homeHint) return;
    const t = window.setTimeout(() => setHomeHint(null), 5 * 60 * 1000);
    return () => window.clearTimeout(t);
  }, [homeHint]);

  useEffect(() => {
    if (!errorText) return;
    const t = window.setTimeout(() => setErrorText(null), HOME_ERROR_DISMISS_MS);
    return () => window.clearTimeout(t);
  }, [errorText]);

  useEffect(() => {
    setErrorText(null);
  }, [homeTab]);

  useEffect(() => {
    if (isHomeSurface || !jobId || !job) return;
    const s = job.state;
    if (s !== "done" && s !== "error" && s !== "cancelled") return;
    try {
      const key = `elia_job_finished_broadcast:${jobId}`;
      if (sessionStorage.getItem(key)) return;
      sessionStorage.setItem(key, "1");
      const bc = new BroadcastChannel(ELIA_UI_BC);
      bc.postMessage({ type: "elia_job_finished", job_id: jobId });
      bc.close();
    } catch {
      // ignore
    }
  }, [isHomeSurface, jobId, job?.state]);

  useEffect(() => {
    if (!jobPollError) return;
    setErrorText(jobPollError);
    setPolling(false);
  }, [jobPollError]);

  useEffect(() => {
    if (!job) return;
    if (job.state === "done" || job.state === "error" || job.state === "cancelled") {
      setPolling(false);
    }
  }, [job?.state]);


  const openSettings = () => {
    setSettingsOpen(true);
    setSettingsTab("general");
    setSettingsTestMsg(null);
    setSettingsSaveMsg(null);
    const fallback = reqConnectorProfileId || connectorProfiles[0]?.id || "";
    setSettingsProfileId((prev) =>
      prev && connectorProfiles.some((x) => x.id === prev) ? prev : fallback,
    );
  };

  return (
    <div
      style={{
        fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial",
        background: c.pageBg,
        color: c.text,
        minHeight: "100vh",
      }}
    >
      <AppHeader
        c={c}
        isHomeSurface={isHomeSurface}
        jobState={job?.state}
        workspaceMode={workspaceMode}
        connectorProfiles={connectorProfiles}
        reqConnectorProfileId={reqConnectorProfileId}
        onOpenSettings={openSettings}
      />

      <SettingsDialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        c={c}
        dark={dark}
        toggleTheme={toggle}
        visibleSettingsTabs={visibleSettingsTabs}
        settingsTab={settingsTab}
        setSettingsTab={setSettingsTab}
        aiCaps={aiCaps}
        aiPrefsSaving={aiPrefsSaving}
        setAiPrefsSaving={setAiPrefsSaving}
        setAiCaps={setAiCaps}
        aiMemoryOpen={aiMemoryOpen}
        setAiMemoryOpen={setAiMemoryOpen}
        aiMemoryStatus={aiMemoryStatus}
        aiMemoryTeamPassphrase={aiMemoryTeamPassphrase}
        setAiMemoryTeamPassphrase={setAiMemoryTeamPassphrase}
        aiMemoryImportMode={aiMemoryImportMode}
        setAiMemoryImportMode={setAiMemoryImportMode}
        aiMemoryImportFile={aiMemoryImportFile}
        setAiMemoryImportFile={setAiMemoryImportFile}
        aiMemoryBusy={aiMemoryBusy}
        setAiMemoryBusy={setAiMemoryBusy}
        aiMemoryMsg={aiMemoryMsg}
        setAiMemoryMsg={setAiMemoryMsg}
        refreshAiMemoryStatus={refreshAiMemoryStatus}
        setErrorText={setErrorText}
        refreshLicense={refreshLicense}
        setModules={setModules}
        license={license}
        activationKey={activationKey}
        setActivationKey={setActivationKey}
        licenseActivateMsg={licenseActivateMsg}
        setLicenseActivateMsg={setLicenseActivateMsg}
        licenseFpVisible={licenseFpVisible}
        setLicenseFpVisible={setLicenseFpVisible}
        fpCopyAck={fpCopyAck}
        setFpCopyAck={setFpCopyAck}
        setLicense={setLicense}
        connectorProfiles={connectorProfiles}
        setConnectorProfiles={setConnectorProfiles}
        settingsProfileId={settingsProfileId}
        setSettingsProfileId={setSettingsProfileId}
        settingsTestMsg={settingsTestMsg}
        setSettingsTestMsg={setSettingsTestMsg}
        settingsSaveMsg={settingsSaveMsg}
        setSettingsSaveMsg={setSettingsSaveMsg}
        persistConnectorProfiles={persistConnectorProfiles}
        duplicateConnectorProfile={duplicateConnectorProfile}
        deleteConnectorProfile={deleteConnectorProfile}
        aboutInfo={aboutInfo}
        aboutChangelogOpen={aboutChangelogOpen}
        setAboutChangelogOpen={setAboutChangelogOpen}
      />

      <div style={{ maxWidth: 980, margin: "0 auto", padding: "20px" }}>
        {errorText && <ErrorAlert c={c} message={errorText} onDismiss={() => setErrorText(null)} />}

        {isHomeSurface && (
          <HomeSurface
            c={c}
            dark={dark}
            initialChecked={initialChecked}
            homeTab={homeTab}
            setHomeTab={setHomeTab}
            homeHint={homeHint}
            aiCaps={aiCaps}
            license={license}
            setSettingsOpen={setSettingsOpen}
            setSettingsTab={setSettingsTab}
            setLicenseActivateMsg={setLicenseActivateMsg}
            canRunJobs={canRunJobs}
            modules={modules}
            showLockModal={showLockModal}
            setShowLockModal={setShowLockModal}
            platform={platform}
            setPlatform={setPlatform}
            urlValue={urlValue}
            setUrlValue={setUrlValue}
            recorderPreflight={recorderPreflight}
            recorderPreflightLoading={recorderPreflightLoading}
            mobilePreflight={mobilePreflight}
            mobilePreflightLoading={mobilePreflightLoading}
            mobileEnvOpen={mobileEnvOpen}
            setMobileEnvOpen={setMobileEnvOpen}
            appiumStatus={appiumStatus}
            appiumStarting={appiumStarting}
            handleStartAppium={handleStartAppium}
            refreshAppiumStatus={refreshAppiumStatus}
            refreshMobilePreflight={refreshMobilePreflight}
            showHomeError={showHomeError}
            deviceMode={deviceMode}
            setDeviceMode={setDeviceMode}
            deviceId={deviceId}
            setDeviceId={setDeviceId}
            mobileDevices={mobileDevices}
            mobileDevicesLoading={mobileDevicesLoading}
            mobileDevicesError={mobileDevicesError}
            refreshMobileDevices={refreshMobileDevices}
            mobileAvds={mobileAvds}
            mobileAvdsLoading={mobileAvdsLoading}
            mobileAvdsError={mobileAvdsError}
            selectedAvd={selectedAvd}
            setSelectedAvd={setSelectedAvd}
            refreshMobileAvds={refreshMobileAvds}
            emulatorStarting={emulatorStarting}
            handleStartEmulator={handleStartEmulator}
            emulatorMessage={emulatorMessage}
            mobileFieldError={mobileFieldError}
            appPackage={appPackage}
            setAppPackage={setAppPackage}
            appActivity={appActivity}
            setAppActivity={setAppActivity}
            detectingForegroundApp={detectingForegroundApp}
            detectForegroundApp={detectForegroundApp}
            apkPath={apkPath}
            setApkPath={setApkPath}
            setMobileFieldError={setMobileFieldError}
            windowName={windowName}
            setWindowName={setWindowName}
            exePath={exePath}
            setExePath={setExePath}
            autoLinkToScenario={autoLinkToScenario}
            setAutoLinkToScenario={setAutoLinkToScenario}
            autoLinkScenarioRef={autoLinkScenarioRef}
            setAutoLinkScenarioRef={setAutoLinkScenarioRef}
            availableScenarios={availableScenarios}
            startJob={startJob}
            loadedDocs={loadedDocs}
            setLoadedDocs={setLoadedDocs}
            docDragOver={docDragOver}
            setDocDragOver={setDocDragOver}
            docUploadError={docUploadError}
            setDocUploadError={setDocUploadError}
            linkRecordings={linkRecordings}
            setLinkRecordings={setLinkRecordings}
            linkMapping={linkMapping}
            setLinkMapping={setLinkMapping}
            recordingMapping={recordingMapping}
            setRecordingMapping={setRecordingMapping}
            availableRecordings={availableRecordings}
            setAvailableScenarios={setAvailableScenarios}
            setAvailableRecordings={setAvailableRecordings}
            reqConnectorProfileId={reqConnectorProfileId}
            setReqConnectorProfileId={setReqConnectorProfileId}
            connectorProfiles={connectorProfiles}
          />
        )}

        {!isHomeSurface && (
          <JobWorkspace
            c={c}
            jobId={jobId}
            job={job}
            jobEvents={jobEvents}
            activePrompt={activePrompt}
            stoppingRecording={stoppingRecording}
            setStoppingRecording={setStoppingRecording}
            setErrorText={setErrorText}
            textValue={textValue}
            setTextValue={setTextValue}
            bddPreviewText={bddPreviewText}
            setBddPreviewText={setBddPreviewText}
          />
        )}
      </div>
    </div>
  );
}
