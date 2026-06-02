import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getAiCapabilities,
  getAiMemoryStatus,
  getAppAbout,
  getModulesStatus,
  getRecorderPreflight,
  startConvertJob,
  type AiCapabilitiesResponse,
  type AiMemoryStatusResponse,
  type AppAboutResponse,
  type RecorderPreflightResponse,
} from "./api";
import type { ActivePrompt, LoadedDoc, ModulesStatus, RecordingRef, ScenarioRef } from "./types";
import { themeQuerySuffix, useEliaTheme } from "./eliaTheme";
import { useJobProgress } from "./job/useJobProgress";
import type { RecordingConfig } from "./recording/types";
import { buildConvertJobBody, validateRecordingStart } from "./recording/validateRecordingConfig";
import { ELIA_UI_BC, HOME_ERROR_DISMISS_MS } from "./app/constants";
import {
  inferBehaveProjectFromProgress,
  requestAppExitIfClosing,
} from "./app/homeNavigation";
import {
  applySessionGuard,
  broadcastNewEliaSession,
  closeWithoutStoppingServer,
  listenForNewEliaSession,
  reconcileEliaSession,
  shouldSkipExitOnPageHide,
} from "./app/sessionGuard";
import { settingsTabsForLicense, type SettingsTabId } from "./app/settingsTabs";
import { openJobUrlInNewTabPrepared } from "./app/utils";
import { ConnectorProvider } from "./context/ConnectorContext";
import { HomeUiProvider } from "./context/HomeUiContext";
import { LicenseProvider } from "./context/LicenseContext";
import { RecordingProvider } from "./context/RecordingContext";
import { SettingsUiProvider } from "./context/SettingsUiContext";
import { useConnectors } from "./hooks/useConnectors";
import { useLicense } from "./hooks/useLicense";
import { useMobileRecording } from "./hooks/useMobileRecording";
import { HomeSurface } from "./home/HomeSurface";
import { AppHeader, ErrorAlert } from "./layout/AppShell";
import { BetaExpiredScreen } from "./components/BetaExpiredScreen";
import { JobWorkspace } from "./job/JobWorkspace";
import { SettingsDialog } from "./settings/SettingsDialog";

export default function App() {
  const { c, dark, toggle } = useEliaTheme();

  const [isHomeSurface] = useState(() => !new URLSearchParams(window.location.search).get("job_id"));
  const [homeTab, setHomeTab] = useState<"ui" | "req" | "api">("ui");
  const [jobId, setJobId] = useState<string | null>(null);
  const [polling, setPolling] = useState<boolean>(false);
  const { job, events: jobEvents, errorText: jobPollError } = useJobProgress(jobId, polling);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [serverOnline, setServerOnline] = useState(true);
  const [textValue, setTextValue] = useState<string>("");
  const [urlValue, setUrlValue] = useState<string>("");
  const [initialChecked, setInitialChecked] = useState<boolean>(false);
  const [workspaceMode, setWorkspaceMode] = useState<string | null>(null);
  const [stoppingRecording, setStoppingRecording] = useState(false);
  const [homeHint, setHomeHint] = useState<string | null>(null);
  const [homeDataRefresh, setHomeDataRefresh] = useState(0);
  const [pendingRunProject, setPendingRunProject] = useState<{
    platform: string;
    project: string;
  } | null>(null);
  const flowTabRef = useRef<Window | null>(null);
  const [aiCaps, setAiCaps] = useState<AiCapabilitiesResponse | null>(null);
  const [aiPrefsSaving, setAiPrefsSaving] = useState(false);
  const [aiMemoryOpen, setAiMemoryOpen] = useState(false);
  const [aiMemoryStatus, setAiMemoryStatus] = useState<AiMemoryStatusResponse | null>(null);
  const [aiMemoryTeamPassphrase, setAiMemoryTeamPassphrase] = useState("");
  const [aiMemoryImportMode, setAiMemoryImportMode] = useState<"merge" | "replace">("merge");
  const [aiMemoryImportFile, setAiMemoryImportFile] = useState<File | null>(null);
  const [aiMemoryBusy, setAiMemoryBusy] = useState(false);
  const [aiMemoryMsg, setAiMemoryMsg] = useState<string | null>(null);
  const [bddPreviewText, setBddPreviewText] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState<SettingsTabId>("general");
  const [aboutInfo, setAboutInfo] = useState<AppAboutResponse | null>(null);
  const [aboutChangelogOpen, setAboutChangelogOpen] = useState(false);
  const [modules, setModules] = useState<ModulesStatus | null>(null);
  const [showLockModal, setShowLockModal] = useState<string | null>(null);
  const [platform, setPlatform] = useState<"web" | "mobile" | "legacy">("web");
  const [recorderPreflight, setRecorderPreflight] = useState<RecorderPreflightResponse | null>(null);
  const [recorderPreflightLoading, setRecorderPreflightLoading] = useState(false);
  const [windowName, setWindowName] = useState("");
  const [exePath, setExePath] = useState("");
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

  const licenseState = useLicense({ isHomeSurface, settingsOpen, settingsTab, setSettingsTab });
  const {
    license, setLicense, activationKey, setActivationKey, licenseActivateMsg, setLicenseActivateMsg,
    fpCopyAck, setFpCopyAck, licenseFpVisible, setLicenseFpVisible, canRunJobs, refreshLicense,
  } = licenseState;

  const connectorState = useConnectors({ isHomeSurface });
  const {
    connectorProfiles, setConnectorProfiles, reqConnectorProfileId, setReqConnectorProfileId,
    settingsProfileId, setSettingsProfileId, settingsTestMsg, setSettingsTestMsg,
    settingsSaveMsg, setSettingsSaveMsg, persistConnectorProfiles, duplicateConnectorProfile,
    deleteConnectorProfile, syncSettingsProfileId,
  } = connectorState;

  const setMobileFieldErrorRef = useRef<(v: string | null) => void>(() => {});

  const scrollToUserMessage = useCallback((testId: string) => {
    requestAnimationFrame(() => {
      document.querySelector(`[data-testid="${testId}"]`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }, []);

  const showHomeError = useCallback(
    (message: string, opts?: { mobileInline?: boolean }) => {
      setErrorText(message);
      if (opts?.mobileInline) {
        setMobileFieldErrorRef.current(message);
        scrollToUserMessage("elia-mobile-form-error");
      } else {
        scrollToUserMessage("elia-error-alert");
      }
    },
    [scrollToUserMessage],
  );

  const mobileState = useMobileRecording({
    isHomeSurface,
    homeTab,
    platform,
    canRunJobs,
    onShowError: showHomeError,
    onSetHomeHint: setHomeHint,
  });
  setMobileFieldErrorRef.current = mobileState.setMobileFieldError;

  const {
    apkPath, setApkPath, deviceId, setDeviceId, deviceMode, setDeviceMode,
    mobileDevices, mobileDevicesLoading, mobileDevicesError, refreshMobileDevices,
    mobileAvds, mobileAvdsLoading, mobileAvdsError, selectedAvd, setSelectedAvd,
    refreshMobileAvds, mobilePreflight, mobilePreflightLoading, mobileEnvOpen, setMobileEnvOpen,
    emulatorStarting, handleStartEmulator, emulatorMessage, mobileFieldError, setMobileFieldError,
    detectingForegroundApp, detectForegroundApp, appiumStatus, appiumStarting, handleStartAppium,
    refreshAppiumStatus, refreshMobilePreflight, appPackage, setAppPackage, appActivity, setAppActivity,
    appSource, setAppSource, deviceManualMode, setDeviceManualMode,
  } = mobileState;

  const visibleSettingsTabs = settingsTabsForLicense(canRunJobs);
  const activePrompt = (job?.active_prompt ?? null) as ActivePrompt | null;

  const recordingConfig = useMemo((): RecordingConfig => {
    if (platform === "mobile") {
      return { platform: "mobile", deviceId, deviceMode, appSource, apkPath, appPackage, appActivity };
    }
    if (platform === "legacy") {
      return { platform: "legacy", windowName, exePath };
    }
    return { platform: "web", url: urlValue };
  }, [platform, urlValue, deviceId, deviceMode, appSource, apkPath, appPackage, appActivity, windowName, exePath]);

  const refreshAiCapabilities = useCallback(async () => {
    try {
      setAiCaps(await getAiCapabilities());
    } catch {
      setAiCaps(null);
    }
  }, []);

  const refreshAiMemoryStatus = useCallback(async () => {
    try {
      setAiMemoryStatus(await getAiMemoryStatus());
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
    }
  }, [settingsOpen]);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const info = await getAppAbout();
        if (alive) setAboutInfo(info);
      } catch {
        if (alive) setAboutInfo(null);
      }
    })();
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!settingsOpen) return;
    let alive = true;
    void (async () => {
      try {
        const info = await getAppAbout();
        if (alive) setAboutInfo(info);
      } catch {
        if (alive) setAboutInfo(null);
      }
    })();
    return () => { alive = false; };
  }, [settingsOpen]);

  useEffect(() => {
    if (canRunJobs) return;
    setAutoLinkToScenario(false);
    setAutoLinkScenarioRef("");
    setLinkRecordings(false);
    setLinkMapping({});
    setRecordingMapping({});
    setLoadedDocs([]);
  }, [canRunJobs]);

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
    return () => { alive = false; };
  }, [isHomeSurface, homeTab, platform, canRunJobs]);

  const startJob = useCallback(async (
    mode:
      | "puppeteer_recorder"
      | "puppeteer_to_behave"
      | "puppeteer_to_step_by_step"
      | "mobile_recorder"
      | "legacy_recorder"
      | "mobile_to_behave"
      | "legacy_to_behave"
      | "doc_to_bdd"
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
      if (recordingConfig.appSource === "installed" && !mobilePkg) {
        const detected = await detectForegroundApp();
        if (detected?.package) {
          mobilePkg = detected.package;
          mobileAct = detected.activity || mobileAct;
        }
      }
      if (recordingConfig.appSource === "installed" && !mobilePkg) return;
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
        flowTabRef.current = newTab;
        setHomeHint(
          "El flujo se abrió en otra pestaña. Esta vista es el inicio: déjala abierta y usa la otra pestaña para los pasos y el resultado.",
        );
      } catch (e: unknown) {
        try {
          newTab.close();
        } catch {
          // ignore
        }
        setErrorText(String((e as Error)?.message ?? e));
      }
    })();
  }, [
    license,
    showHomeError,
    recordingConfig,
    recorderPreflight,
    mobilePreflight,
    loadedDocs,
    connectorProfiles,
    reqConnectorProfileId,
    urlValue,
    detectForegroundApp,
    linkMapping,
    recordingMapping,
    linkRecordings,
    autoLinkToScenario,
    autoLinkScenarioRef,
  ]);

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
    let alive = true;
    let sessionAnnounced = false;
    const tick = async () => {
      if (!alive) return;
      const result = await reconcileEliaSession();
      if (!alive) return;
      const keep = applySessionGuard(result);
      if (!alive || !keep) return;
      setServerOnline(result === "ok");
      if (result === "ok" && isHomeSurface && !sessionAnnounced) {
        const sid = sessionStorage.getItem("elia_session_id");
        if (sid) {
          broadcastNewEliaSession(sid);
          sessionAnnounced = true;
        }
      }
    };
    void tick();
    const id = window.setInterval(() => {
      void tick();
    }, 4000);
    const stopListen = listenForNewEliaSession(() => {
      if (!alive) return;
      closeWithoutStoppingServer();
    });
    return () => {
      alive = false;
      window.clearInterval(id);
      stopListen();
    };
  }, []);

  useEffect(() => {
    if (!isHomeSurface) return;
    const onHide = () => {
      if (shouldSkipExitOnPageHide()) return;
      requestAppExitIfClosing();
    };
    window.addEventListener("pagehide", onHide);
    return () => window.removeEventListener("pagehide", onHide);
  }, [isHomeSurface]);

  useEffect(() => {
    if (!isHomeSurface) return;
    let bc: BroadcastChannel | null = null;
    try {
      bc = new BroadcastChannel(ELIA_UI_BC);
      bc.onmessage = (ev: MessageEvent) => {
        if (ev.data?.type === "elia_job_finished" || ev.data?.type === "elia_job_tab_closed") {
          flowTabRef.current = null;
          setHomeHint(null);
          setHomeDataRefresh((n) => n + 1);
          if (ev.data?.type === "elia_job_finished") {
            const platform = typeof ev.data.platform === "string" ? ev.data.platform : "";
            const project = typeof ev.data.project === "string" ? ev.data.project : "";
            if (platform && project) {
              setPendingRunProject({ platform, project });
            }
          }
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
    const poll = window.setInterval(() => {
      if (flowTabRef.current?.closed) {
        flowTabRef.current = null;
        setHomeHint(null);
      }
    }, 400);
    return () => window.clearInterval(poll);
  }, [homeHint]);

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
      const inferred = inferBehaveProjectFromProgress(job.progress);
      const bc = new BroadcastChannel(ELIA_UI_BC);
      bc.postMessage({
        type: "elia_job_finished",
        job_id: jobId,
        platform: inferred.platform,
        project: inferred.project,
      });
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
    syncSettingsProfileId();
  };

  const openAiSettings = () => {
    setSettingsOpen(true);
    setSettingsTab("ai");
    setSettingsTestMsg(null);
    setSettingsSaveMsg(null);
  };

  const licenseCtx = useMemo(
    () => ({
      license, setLicense, activationKey, setActivationKey, licenseActivateMsg, setLicenseActivateMsg,
      fpCopyAck, setFpCopyAck, licenseFpVisible, setLicenseFpVisible, canRunJobs, refreshLicense,
    }),
    [
      license, activationKey, licenseActivateMsg, fpCopyAck, licenseFpVisible,
      canRunJobs, refreshLicense, setLicense, setActivationKey, setLicenseActivateMsg,
      setFpCopyAck, setLicenseFpVisible,
    ],
  );

  const connectorCtx = useMemo(
    () => ({
      connectorProfiles, setConnectorProfiles, reqConnectorProfileId, setReqConnectorProfileId,
      settingsProfileId, setSettingsProfileId, settingsTestMsg, setSettingsTestMsg,
      settingsSaveMsg, setSettingsSaveMsg, persistConnectorProfiles, duplicateConnectorProfile,
      deleteConnectorProfile,
    }),
    [
      connectorProfiles, reqConnectorProfileId, settingsProfileId, settingsTestMsg, settingsSaveMsg,
      persistConnectorProfiles, duplicateConnectorProfile, deleteConnectorProfile,
      setConnectorProfiles, setReqConnectorProfileId, setSettingsProfileId,
      setSettingsTestMsg, setSettingsSaveMsg,
    ],
  );

  const recordingCtx = useMemo(
    () => ({
      platform, setPlatform, urlValue, setUrlValue, windowName, setWindowName, exePath, setExePath,
      recorderPreflight, recorderPreflightLoading, mobilePreflight, mobilePreflightLoading,
      mobileEnvOpen, setMobileEnvOpen, appiumStatus, appiumStarting, handleStartAppium,
      refreshAppiumStatus, refreshMobilePreflight, deviceMode, setDeviceMode, deviceId, setDeviceId,
      mobileDevices, mobileDevicesLoading, mobileDevicesError, refreshMobileDevices,
      mobileAvds, mobileAvdsLoading, mobileAvdsError, selectedAvd, setSelectedAvd, refreshMobileAvds,
      emulatorStarting, handleStartEmulator, emulatorMessage, mobileFieldError, setMobileFieldError,
      appPackage, setAppPackage, appActivity, setAppActivity, apkPath, setApkPath,
      appSource, setAppSource, deviceManualMode, setDeviceManualMode,
      detectingForegroundApp, detectForegroundApp,
    }),
    [
      platform, urlValue, windowName, exePath, recorderPreflight, recorderPreflightLoading,
      mobilePreflight, mobilePreflightLoading, mobileEnvOpen, appiumStatus, appiumStarting,
      handleStartAppium, refreshAppiumStatus, refreshMobilePreflight, deviceMode, deviceId,
      mobileDevices, mobileDevicesLoading, mobileDevicesError, refreshMobileDevices,
      mobileAvds, mobileAvdsLoading, mobileAvdsError, selectedAvd, refreshMobileAvds,
      emulatorStarting, handleStartEmulator, emulatorMessage, mobileFieldError, appPackage,
      appActivity, apkPath, appSource, deviceManualMode, detectingForegroundApp, detectForegroundApp, setMobileFieldError,
    ],
  );

  const settingsUiCtx = useMemo(
    () => ({
      c, dark, toggleTheme: toggle, visibleSettingsTabs, settingsTab, setSettingsTab,
      aiCaps, aiPrefsSaving, setAiPrefsSaving, setAiCaps, aiMemoryOpen, setAiMemoryOpen,
      aiMemoryStatus, aiMemoryTeamPassphrase, setAiMemoryTeamPassphrase, aiMemoryImportMode,
      setAiMemoryImportMode, aiMemoryImportFile, setAiMemoryImportFile, aiMemoryBusy, setAiMemoryBusy,
      aiMemoryMsg, setAiMemoryMsg, refreshAiMemoryStatus, setErrorText, setModules,
      aboutInfo, aboutChangelogOpen, setAboutChangelogOpen,
    }),
    [
      c, dark, toggle, visibleSettingsTabs, settingsTab, aiCaps, aiPrefsSaving, aiMemoryOpen,
      aiMemoryStatus, aiMemoryTeamPassphrase, aiMemoryImportMode, aiMemoryImportFile, aiMemoryBusy,
      aiMemoryMsg, refreshAiMemoryStatus, aboutInfo, aboutChangelogOpen,
    ],
  );

  const homeUiCtx = useMemo(
    () => ({
      c, dark, initialChecked, homeTab, setHomeTab, homeHint, setHomeHint, aiCaps, license,
      setSettingsOpen, setSettingsTab, setLicenseActivateMsg, canRunJobs, modules,
      showLockModal, setShowLockModal, showHomeError, autoLinkToScenario, setAutoLinkToScenario,
      autoLinkScenarioRef, setAutoLinkScenarioRef, availableScenarios, startJob, loadedDocs,
      setLoadedDocs, docDragOver, setDocDragOver, docUploadError, setDocUploadError, linkRecordings,
      setLinkRecordings, linkMapping, setLinkMapping, recordingMapping, setRecordingMapping,
      availableRecordings, setAvailableScenarios, setAvailableRecordings,
      homeDataRefresh, pendingRunProject, clearPendingRunProject: () => setPendingRunProject(null),
    }),
    [
      c, dark, initialChecked, homeTab, homeHint, aiCaps, license, canRunJobs, modules,
      showLockModal, showHomeError, autoLinkToScenario, autoLinkScenarioRef, availableScenarios,
      loadedDocs, docDragOver, docUploadError, linkRecordings, linkMapping, recordingMapping,
      availableRecordings, startJob, homeDataRefresh, pendingRunProject,
    ],
  );

  const betaBlocked =
    license?.reason === "beta_expired" || license?.reason === "clock_tamper";

  return (
    <LicenseProvider value={licenseCtx}>
      <ConnectorProvider value={connectorCtx}>
        <RecordingProvider value={recordingCtx}>
          <SettingsUiProvider value={settingsUiCtx}>
            <HomeUiProvider value={homeUiCtx}>
              {betaBlocked ? (
                <BetaExpiredScreen
                  c={c}
                  message={license?.message ?? ""}
                  reason={license?.reason}
                  upgradeEmail={license?.upgrade_email}
                />
              ) : (
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
                  aiCaps={aiCaps}
                  onOpenSettings={openSettings}
                  onOpenAiSettings={openAiSettings}
                />

                <SettingsDialog open={settingsOpen} onClose={() => setSettingsOpen(false)} />

                <div style={{ maxWidth: 980, margin: "0 auto", padding: "20px" }}>
                  {!serverOnline && isHomeSurface ? (
                    <div
                      role="alert"
                      style={{
                        marginBottom: 12,
                        padding: "12px 14px",
                        borderRadius: 10,
                        border: `1px solid ${c.errorBorder}`,
                        background: c.errorBg,
                        color: c.errorBody,
                        fontSize: 14,
                        lineHeight: 1.45,
                      }}
                    >
                      <strong>Servidor ELIA desconectado.</strong> Cerrando esta pestaña obsoleta (puerto{" "}
                      <code>{window.location.port || "?"}</code>)… Si no se cierra sola, ciérrala manualmente.
                    </div>
                  ) : null}
                  {errorText && (
                    <ErrorAlert c={c} message={errorText} onDismiss={() => setErrorText(null)} />
                  )}

                  {isHomeSurface && <HomeSurface />}

                  {!isHomeSurface && (
                    // Versión comercial (≥1.0): añadir supportEmail={aboutInfo?.support_email} en JobWorkspace.
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
                      betaFeedbackUrl={aboutInfo?.beta_feedback_url}
                      jobLoadError={jobPollError}
                    />
                  )}
                </div>
              </div>
              )}
            </HomeUiProvider>
          </SettingsUiProvider>
        </RecordingProvider>
      </ConnectorProvider>
    </LicenseProvider>
  );
}
