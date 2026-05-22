import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  activateLicense,
  getAiCapabilities,
  exportAiMemory,
  getAiMemoryStatus,
  importAiMemory,
  type AiMemoryStatusResponse,
  getAppAbout,
  putAiPreferences,
  type AppAboutResponse,
  getEliaConnectors,
  getJob,
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
  type LicenseStatusResponse,
  type MobileAppiumStatusResponse,
  type MobileDeviceInfo,
  type MobilePreflightResponse,
  type RecorderPreflightResponse,
  type AiCapabilitiesResponse,
  type AiMode,
  putEliaConnectors,
  PROMPT_ANSWER_BACK,
  sendPromptResponse,
  startConvertJob,
  startMobileAppium,
  startMobileEmulator,
  stopMobileAppium,
  stopRecording,
  testEliaConnector,
  uploadDocs,
} from "./api";
import {
  formatPreflightItemMessage,
  friendlyAvdsError,
  mobilePreflightSummary,
  normalizeMobileWarnings,
  shouldAutoOpenMobileEnv,
} from "./mobileEnvUi";
import type {
  ActivePrompt,
  ConversionResultPayload,
  EliaConnectorProfile,
  GeneratedFileEntry,
  LoadedDoc,
  ModulesStatus,
  RecordingRef,
  ScenarioRef,
} from "./types";
import { promptAllowsBack } from "./types";
import { ELIA_CONNECTORS_LS_KEY, emptyJiraCreds, emptyValueEdgeCreds, newConnectorProfile } from "./connectorDefaults";
import { themeQuerySuffix, useEliaTheme } from "./eliaTheme";
import { parseLicenseDisplayBlocks } from "./licenseTextFormat";

type JobStatus = {
  job_id: string;
  state: string;
  active_prompt: ActivePrompt | null;
  error: null | { message: string; details?: string };
  progress: Record<string, any>;
};

function formatPromptType(t: string): string {
  if (t === "message_ack") return "Aviso";
  return t.replaceAll("_", " ");
}

function formatJobMode(mode: string | null): string {
  if (!mode) return "";
  if (mode === "puppeteer_recorder") return "Grabar interacciones";
  if (mode === "puppeteer_to_behave") return "Convertir a Behave";
  if (mode === "puppeteer_to_step_by_step") return "Convertir a step by step";
  if (mode === "elia_jira_smoke") return "ELIA · Conectar a Jira";
  if (mode === "elia_value_edge_smoke") return "ELIA · Extraer de ValueEdge";
  if (mode === "elia_gherkin_batch") return "ELIA · Procesamiento por lotes (Gherkin)";
  if (mode === "mobile_recorder") return "Grabar interacciones (Móvil)";
  if (mode === "legacy_recorder") return "Grabar interacciones (Legacy)";
  if (mode === "mobile_to_behave") return "Convertir a Behave (Móvil)";
  if (mode === "legacy_to_behave") return "Convertir a Behave (Legacy)";
  if (mode === "doc_to_bdd") return "ELIA · Procesar y Convertir a BDD";
  return mode;
}

function normalizeGeneratedFiles(
  payload?: ConversionResultPayload | null,
  progress?: Record<string, any>,
): { dir?: string; files: GeneratedFileEntry[] } {
  const dir =
    payload?.output_dir ||
    payload?.project_dir ||
    progress?.output_dir ||
    progress?.project_dir;
  let files: GeneratedFileEntry[] =
    payload?.generated_files ||
    progress?.generated_files ||
    [];
  if (!files.length && progress?.result_file) {
    files = [{ path: String(progress.result_file), label: "grabación" }];
  }
  if (!files.length && progress?.video_path) {
    files = [{ path: String(progress.video_path), label: "video" }];
  }
  return { dir: dir ? String(dir) : undefined, files };
}

function GeneratedFilesResultView(props: {
  message?: string;
  payload?: ConversionResultPayload | null;
  progress?: Record<string, any>;
  c: Record<string, string>;
}) {
  const { message, payload, progress, c } = props;
  const { dir, files } = normalizeGeneratedFiles(payload, progress);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {message ? (
        <div style={{ whiteSpace: "pre-wrap", fontSize: 14 }}>{message}</div>
      ) : null}
      {dir ? (
        <div style={{ fontSize: 13 }}>
          <div style={{ color: c.muted, marginBottom: 4 }}>Carpeta de salida</div>
          <code
            style={{
              display: "block",
              padding: "8px 10px",
              borderRadius: 8,
              background: c.codeBg,
              border: `1px solid ${c.border}`,
              fontSize: 12,
              wordBreak: "break-all",
            }}
          >
            {dir}
          </code>
        </div>
      ) : null}
      {files.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ fontSize: 13, color: c.muted }}>Archivos generados</div>
          {files.map((f) => (
            <div
              key={f.path}
              style={{
                border: `1px solid ${c.border}`,
                borderRadius: 10,
                padding: 10,
                background: c.surface,
              }}
            >
              <div style={{ fontWeight: 600, fontSize: 13, color: c.text }}>
                {f.label || f.path.split(/[/\\]/).pop()}
              </div>
              <code
                style={{
                  display: "block",
                  marginTop: 4,
                  fontSize: 11,
                  color: c.muted,
                  wordBreak: "break-all",
                }}
              >
                {f.path}
              </code>
              {f.preview ? (
                <textarea
                  readOnly
                  value={f.preview}
                  style={{
                    width: "100%",
                    minHeight: 120,
                    marginTop: 8,
                    padding: 8,
                    borderRadius: 8,
                    border: `1px solid ${c.border}`,
                    fontFamily: "ui-monospace, monospace",
                    fontSize: 12,
                    background: c.codeBg,
                    color: c.text,
                    resize: "vertical",
                  }}
                />
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function openJobUrlInNewTabPrepared(): Window | null {
  return window.open("about:blank", "_blank");
}

/** feature_file + scenario_name para API link_scenario (mismo separador que backend). */
function encodeScenarioLink(s: ScenarioRef): string {
  return `${s.feature_file}\x1f${s.scenario_name}`;
}

function encodeRecordingLink(r: RecordingRef): string {
  return `${r.project}\x1e${r.file_name}`;
}

const ELIA_UI_BC = "elia-ui";

type SettingsTabId = "general" | "ai" | "license" | "connectors" | "about";

const SETTINGS_TABS: { id: SettingsTabId; label: string }[] = [
  { id: "general", label: "General" },
  { id: "ai", label: "Inteligencia" },
  { id: "connectors", label: "Conectores" },
  { id: "license", label: "Licencia" },
  { id: "about", label: "Acerca de" },
];

const SETTINGS_TABS_WITHOUT_LICENSE: SettingsTabId[] = ["general", "license", "about"];

function settingsTabsForLicense(canRunJobs: boolean) {
  if (canRunJobs) return SETTINGS_TABS;
  return SETTINGS_TABS.filter((t) => SETTINGS_TABS_WITHOUT_LICENSE.includes(t.id));
}

const ELIA_LOGO_ICON_STYLE: React.CSSProperties = {
  height: 52,
  width: "auto",
  maxWidth: 100,
  objectFit: "contain",
  flexShrink: 0,
  transform: "scale(1.6)",       
  transformOrigin: "left center",
};
const ELIA_LOGO_LETTERS_STYLE: React.CSSProperties = {
  height: 64,
  width: "auto",
  maxWidth: 100,
  objectFit: "contain",
  flexShrink: 0,
  transform: "scale(2.5)",       
  transformOrigin: "left center",
};

/** Avisos de validación en la pantalla principal: se ocultan solos o con ✕ */
const HOME_ERROR_DISMISS_MS = 8_000;

type LicenseState = {
  can_run_jobs: boolean;
  message: string;
  activated: boolean;
  machine_fingerprint: string;
  reason?: string;
  expires_at?: number | null;
  duration_code?: string | null;
};

function licenseFromApi(l: LicenseStatusResponse): LicenseState {
  return {
    can_run_jobs: l.can_run_jobs,
    message: l.message,
    activated: l.activated,
    machine_fingerprint: l.machine_fingerprint,
    reason: l.reason,
    expires_at: l.expires_at ?? null,
    duration_code: l.duration_code ?? null,
  };
}

function formatLicenseExpiryDate(expiresAtSec: number): string {
  return new Date(expiresAtSec * 1000).toLocaleDateString("es-MX", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/** Texto breve para la tarjeta Licencia en Configuración. */
function formatLicenseStatusLabel(license: LicenseState): string {
  if (license.reason === "skip") {
    return "Desarrollo (licencia omitida).";
  }
  if (license.reason === "killed") {
    return "Inactiva — instalación deshabilitada.";
  }
  if (!license.can_run_jobs) {
    if (license.reason === "not_activated") {
      return "Sin activar — introduce la clave de licencia.";
    }
    if (license.reason === "license_expired") {
      return "Inactiva — licencia caducada.";
    }
    return license.message;
  }
  if (license.activated) {
    if (license.expires_at == null) {
      return "Licencia permanente.";
    }
    const days = Math.max(0, (license.expires_at * 1000 - Date.now()) / 86400000);
    return `Licencia temporal: expira el ${formatLicenseExpiryDate(license.expires_at)} (≈ ${Math.ceil(days)} día(s)).`;
  }
  return license.message;
}

/** Aviso de activación (solo sin licencia activada). */
function licenseNeedsActivationBanner(license: LicenseState): boolean {
  return license.reason === "not_activated";
}

/** Aviso de caducidad próxima (licencia temporal activa). */
function licenseNeedsExpiryBanner(license: LicenseState): boolean {
  if (!license.activated || license.expires_at == null) {
    return false;
  }
  const daysLeft = (license.expires_at * 1000 - Date.now()) / 86400000;
  return daysLeft <= 7;
}

async function copyTextToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      /* fallback */
    }
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

function goHomeInThisTab(): void {
  window.location.assign(`${window.location.origin}/`);
}

function modalFieldStyle(c: {
  inputBorder: string;
  inputBg: string;
  text: string;
}): React.CSSProperties {
  return {
    width: "100%",
    padding: "10px 12px",
    borderRadius: 10,
    border: `1px solid ${c.inputBorder}`,
    background: c.inputBg,
    color: c.text,
    fontSize: 14,
  };
}

function tryFocusOpenerAndCloseThisTab(): boolean {
  if (!window.opener || window.opener.closed) {
    return false;
  }
  try {
    window.opener.focus();
  } catch {
    // ignore
  }
  try {
    window.close();
    return true;
  } catch {
    return false;
  }
}

export default function App() {
  const { c, dark, toggle } = useEliaTheme();

  /** Pinned from first paint: home URL has no job_id; avoids any edge case mixing job UI into home. */
  const [isHomeSurface] = useState(() => !new URLSearchParams(window.location.search).get("job_id"));
  const [homeTab, setHomeTab] = useState<"ui" | "req">("ui");

  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [polling, setPolling] = useState<boolean>(false);
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
    if (mode === "puppeteer_recorder" && !urlValue.trim()) {
      showHomeError("URL requerida para 'Grabar Interacciones'.");
      return;
    }
    if (mode === "puppeteer_recorder" && recorderPreflight && !recorderPreflight.ok) {
      showHomeError(
        recorderPreflight.errors.length
          ? recorderPreflight.errors.join(" ")
          : "Google Chrome es obligatorio para grabar. Instálelo o defina ELIA_CHROME_PATH.",
      );
      return;
    }

    let mobilePkg = appPackage.trim();
    let mobileAct = appActivity.trim();

    if (mode === "mobile_recorder") {
      if (!deviceId.trim()) {
        showHomeError(
          deviceMode === "emulator"
            ? "Inicia un emulador o selecciona uno visible en adb devices."
            : "Conecta un dispositivo Android o selecciónalo en la lista adb.",
          { mobileInline: true },
        );
        return;
      }
      if (mobilePreflight && !mobilePreflight.ok) {
        showHomeError(
          mobilePreflight.errors.length
            ? mobilePreflight.errors.join(" ")
            : "Revisa el entorno móvil (adb, Appium, dispositivo) antes de grabar.",
          { mobileInline: true },
        );
        return;
      }
      if (!apkPath.trim() && !mobilePkg) {
        const detected = await detectForegroundApp();
        if (detected?.package) {
          mobilePkg = detected.package;
          mobileAct = detected.activity || mobileAct;
        }
      }
      if (!apkPath.trim() && !mobilePkg) {
        return;
      }
    }
    if (mode === "legacy_recorder" && !windowName.trim() && !exePath.trim()) {
      showHomeError("Introduce el nombre de ventana o la ruta del ejecutable para la grabación legacy.");
      return;
    }
    if (mode === "doc_to_bdd" && loadedDocs.length === 0) {
      showHomeError("Carga al menos un documento (.docx o .xlsx) antes de convertir.");
      return;
    }

    const eliaNeedsProfile =
      mode === "elia_jira_smoke" ||
      mode === "elia_value_edge_smoke" ||
      mode === "elia_gherkin_batch";
    if (eliaNeedsProfile && connectorProfiles.length === 0) {
      showHomeError("Primero crea un perfil de conectores en Configuración (⚙).");
      return;
    }
    const selProf = connectorProfiles.find((x) => x.id === reqConnectorProfileId);
    if ((mode === "elia_jira_smoke" || mode === "elia_value_edge_smoke") && !selProf) {
      showHomeError("Selecciona un perfil de conectores en la pestaña «Inteligencia de Requerimientos».");
      return;
    }

    const newTab = openJobUrlInNewTabPrepared();
    if (!newTab) {
      showHomeError(
        "El navegador bloqueó la ventana emergente. Permite ventanas emergentes para 127.0.0.1 e inténtalo de nuevo. " +
          "Sin eso, el flujo podría abrirse en esta misma pestaña y reemplazar el inicio.",
      );
      return;
    }

    const pkgForJob = mobilePkg;
    const actForJob = mobileAct;

    void (async () => {
      try {
        const eliaModes = new Set([
          "elia_jira_smoke",
          "elia_value_edge_smoke",
          "elia_gherkin_batch",
        ]);
        const prof = connectorProfiles.find((x) => x.id === reqConnectorProfileId);

        const linkScenarioByDoc =
          mode === "doc_to_bdd"
            ? Object.fromEntries(Object.entries(linkMapping).filter(([, v]) => v))
            : undefined;
        let linkedScenario: string | undefined;
        if (mode === "doc_to_bdd") {
          linkedScenario = Object.values(linkScenarioByDoc ?? {})[0];
        } else if (
          (mode === "puppeteer_to_behave" ||
            mode === "mobile_to_behave" ||
            mode === "legacy_to_behave") &&
          autoLinkToScenario &&
          autoLinkScenarioRef
        ) {
          linkedScenario = autoLinkScenarioRef;
        }
        const linkRecordingByDoc =
          mode === "doc_to_bdd" && linkRecordings
            ? Object.fromEntries(
                Object.entries(recordingMapping).filter(([, v]) => v),
              )
            : undefined;

        const res = await startConvertJob({
          mode,
          url: mode === "puppeteer_recorder" ? urlValue.trim() : undefined,
          ...(eliaModes.has(mode)
            ? {
                elia_use_inline_connectors: true,
                elia_jira: prof?.jira ?? emptyJiraCreds(),
                elia_value_edge: prof?.value_edge ?? emptyValueEdgeCreds(),
              }
            : {}),
          ...(mode === "mobile_recorder"
            ? {
                platform: "mobile",
                apk_path: apkPath.trim(),
                device_id: deviceId.trim(),
                app_package: pkgForJob,
                app_activity: actForJob,
              }
            : {}),
          ...(mode === "legacy_recorder" ? { platform: "legacy", window_name: windowName.trim(), exe_path: exePath.trim() } : {}),
          ...(mode === "doc_to_bdd" ? {
            doc_files: loadedDocs.map((d) => d.path),
            ...(linkScenarioByDoc && Object.keys(linkScenarioByDoc).length
              ? { link_scenario_by_doc: linkScenarioByDoc }
              : {}),
            ...(linkRecordingByDoc && Object.keys(linkRecordingByDoc).length
              ? { link_recording_by_doc: linkRecordingByDoc }
              : {}),
          } : {}),
          ...(linkedScenario != null ? { link_scenario: linkedScenario } : {}),
        });
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
    if (!polling || !jobId) return;

    let alive = true;
    const tick = async () => {
      try {
        const j = await getJob(jobId);
        if (!alive) return;
        setJob({
          job_id: j.job_id,
          state: j.state,
          active_prompt: j.active_prompt,
          error: j.error,
          progress: j.progress ?? {},
        });
        if (j.state === "done" || j.state === "error" || j.state === "cancelled") {
          setPolling(false);
        }
      } catch (e: any) {
        if (!alive) return;
        setErrorText(String(e?.message ?? e));
        setPolling(false);
      }
    };

    tick();
    const interval = window.setInterval(tick, 450);
    return () => {
      alive = false;
      window.clearInterval(interval);
    };
  }, [polling, jobId]);

  const header = useMemo(() => {
    const isHome = isHomeSurface;
    const statusLine = isHome
      ? "Inicio · deja esta pestaña abierta para nuevas tareas"
      : job
        ? `Estado: ${job.state}`
        : "Cargando trabajo…";
    const sub = !isHome && workspaceMode ? `${formatJobMode(workspaceMode)} · ` : "";

    return (
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 12,
          padding: "16px 18px",
          borderBottom: `1px solid ${c.border}`,
          background: c.chromeBg,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", flex: "0 0 auto" }}>
          <img src="/logo-icon.png" alt="" aria-hidden style={ELIA_LOGO_ICON_STYLE} />
        </div>
        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "flex-end",
            gap: 12,
            rowGap: 8,
            flex: "1 1 0",
            minWidth: 0,
          }}
        >
          <img src="/logo-letters.png" alt="ELIA" style={ELIA_LOGO_LETTERS_STYLE} />
          <div
            style={{
              fontSize: 12,
              color: c.chromeHint,
              textAlign: "right",
              flex: "1 1 160px",
              minWidth: 120,
              maxWidth: "min(420px, 100%)",
            }}
          >
            {!isHome && sub ? (
              <div style={{ marginBottom: 4, fontSize: 11 }}>{sub}ventana de trabajo</div>
            ) : null}
            {statusLine}
          </div>
          <button
            type="button"
            data-testid="elia-settings-open"
            aria-label="Abrir configuración"
            title="Configuración"
            onClick={() => {
              setSettingsOpen(true);
              setSettingsTab("general");
              setSettingsTestMsg(null);
              setSettingsSaveMsg(null);
              const fallback = reqConnectorProfileId || connectorProfiles[0]?.id || "";
              setSettingsProfileId((prev) =>
                prev && connectorProfiles.some((x) => x.id === prev) ? prev : fallback,
              );
            }}
            style={{
              marginLeft: "auto",
              flexShrink: 0,
              width: 42,
              height: 42,
              borderRadius: 10,
              fontSize: 22,
              lineHeight: 1,
              cursor: "pointer",
              border: `1px solid ${c.btnGhostBorder}`,
              background: c.btnGhostBg,
              color: c.text,
              boxShadow: c.shadow,
            }}
          >
            ⚙
          </button>
        </div>
      </div>
    );
  }, [job, workspaceMode, isHomeSurface, c, connectorProfiles, reqConnectorProfileId]);

  return (
    <div
      style={{
        fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial",
        background: c.pageBg,
        color: c.text,
        minHeight: "100vh",
      }}
    >
      {header}

      {settingsOpen && (
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
          onClick={() => setSettingsOpen(false)}
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
                onClick={() => setSettingsOpen(false)}
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
                  onChange={() => toggle()}
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
                          const next = await putAiPreferences(m);
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
                        ? "Usa IA si hay modelo de IA disponible, llama-cpp y RAM (≥8 GB total, ≥4 GB libres)."
                        : m === "on"
                          ? "Fuerza IA si el modelo está disponible; ignora el umbral de RAM libre (puede ir muy lento o fallar)."
                          : "Conversiones heurísticas deterministas, sin revisión de IA."}
                    </span>
                  </span>
                </label>
              ))}
              {aiCaps && (
                <div style={{ fontSize: 12, color: c.muted, marginTop: 8, lineHeight: 1.4 }}>
                  <div>{aiCaps.resolution.message}</div>
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
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Conectores · Jira y Value Edge</div>
              <div style={{ color: c.muted, fontSize: 13, marginBottom: 12 }}>
                Los datos se guardan en el navegador y, también cifrados
                en disco (misma máquina). Usa solo en red local (<code>127.0.0.1</code>).
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
                    Edita el perfil seleccionado (nombre, Jira y Value Edge). Usa «Guardar» al terminar.
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
                        }> = [
                          { key: "added", label: "Añadido", items: entry.added },
                          { key: "fixed", label: "Corregido", items: entry.fixed },
                          { key: "changed", label: "Cambiado", items: entry.changed },
                        ].filter((section) => section.items.length > 0);

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
      )}

      <div style={{ maxWidth: 980, margin: "0 auto", padding: "20px" }}>
        {errorText && (
          <div
            role="alert"
            data-testid="elia-error-alert"
            style={{
              background: c.errorBg,
              border: `1px solid ${c.errorBorder}`,
              padding: 12,
              borderRadius: 10,
              marginBottom: 16,
            }}
          >
            <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <b style={{ color: c.errorTitle }}>Error</b>
                <div style={{ color: c.errorBody, marginTop: 6, whiteSpace: "pre-wrap" }}>{errorText}</div>
              </div>
              <button
                type="button"
                onClick={() => setErrorText(null)}
                aria-label="Cerrar mensaje de error"
                title="Cerrar"
                style={{
                  flexShrink: 0,
                  border: "none",
                  background: "transparent",
                  color: c.errorTitle,
                  fontSize: 18,
                  lineHeight: 1,
                  cursor: "pointer",
                  padding: "2px 6px",
                  borderRadius: 6,
                }}
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {isHomeSurface && initialChecked && (
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
                data-testid="elia-home-tab-req"
                onClick={() => setHomeTab("req")}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  border: `1px solid ${homeTab === "req" ? c.primary : c.btnGhostBorder}`,
                  background: homeTab === "req" ? c.primary : c.btnGhostBg,
                  color: homeTab === "req" ? c.primaryFg : c.text,
                  cursor: "pointer",
                  fontWeight: 700,
                }}
              >
                Inteligencia de Requerimientos
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

            {aiCaps?.resolution.degraded && aiCaps.preferences.mode === "auto" && (
              <div
                role="status"
                style={{
                  background: c.hintBg,
                  border: `1px solid ${c.hintBorder}`,
                  color: c.hintText,
                  padding: "10px 14px",
                  borderRadius: 10,
                  marginBottom: 14,
                  fontSize: 14,
                }}
              >
                {aiCaps.resolution.message}
              </div>
            )}

            {aiCaps && !aiCaps.resolution.degraded && aiCaps.resolution.use_ai && (
              <div
                style={{
                  fontSize: 13,
                  color: c.muted,
                  marginBottom: 14,
                  padding: "8px 12px",
                  borderRadius: 10,
                  border: `1px solid ${c.border}`,
                  background: c.neutralBg,
                }}
              >
                {aiCaps.resolution.message} · {aiCaps.brand_line}
              </div>
            )}

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

            {homeTab === "ui" && (
              <>
                {/* Lock Modal */}
                {showLockModal && (
                  <div
                    style={{
                      position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)",
                      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
                    }}
                    onClick={() => setShowLockModal(null)}
                  >
                    <div
                      data-testid="elia-lock-modal"
                      style={{
                        background: c.surface,
                        border: `1px solid ${c.border}`,
                        borderRadius: 16,
                        padding: "28px 32px",
                        maxWidth: 380,
                        textAlign: "center",
                        boxShadow: "0 8px 32px rgba(0,0,0,0.25)",
                      }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div style={{ fontSize: 32, marginBottom: 12 }}>🔒</div>
                      <div style={{ fontWeight: 700, fontSize: 16, color: c.text, marginBottom: 8 }}>
                        Módulo no habilitado
                      </div>
                      <div style={{ fontSize: 14, color: c.muted, marginBottom: 20 }}>
                        La grabación <b>{showLockModal === "mobile" ? "Móvil" : "Legacy"}</b> requiere una licencia adicional.
                        Contacta a soporte para activar este módulo.
                      </div>
                      <button
                        onClick={() => setShowLockModal(null)}
                        style={{
                          padding: "8px 20px", borderRadius: 8,
                          background: c.primary, color: c.primaryFg, border: "none", cursor: "pointer",
                        }}
                      >
                        Entendido
                      </button>
                    </div>
                  </div>
                )}

                <div
                  style={{
                    opacity: canRunJobs ? 1 : 0.55,
                    pointerEvents: canRunJobs ? "auto" : "none",
                  }}
                >

                {/* Segmented Control — selector de plataforma */}
                <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
                  {(["web", "mobile", "legacy"] as const).map((p) => {
                    const labels = { web: "Web", mobile: "Móvil", legacy: "Legacy" };
                    const locked = (p === "mobile" && !modules?.mobile_recording) || (p === "legacy" && !modules?.legacy_recording);
                    const active = platform === p;
                    return (
                      <button
                        key={p}
                        data-testid={`elia-platform-${p}`}
                        onClick={() => {
                          if (locked) { setShowLockModal(p); return; }
                          setPlatform(p);
                        }}
                        style={{
                          padding: "7px 18px",
                          borderRadius: 8,
                          border: active ? `2px solid ${c.primary}` : `1px solid ${c.btnGhostBorder}`,
                          background: active ? c.primary : c.btnGhostBg,
                          color: active ? c.primaryFg : locked ? c.muted : c.text,
                          fontWeight: active ? 700 : 400,
                          cursor: "pointer",
                          opacity: locked ? 0.6 : 1,
                          fontSize: 14,
                          display: "flex", alignItems: "center", gap: 5,
                        }}
                      >
                        {locked && <span style={{ fontSize: 12 }}>🔒</span>}
                        {labels[p]}
                      </button>
                    );
                  })}
                </div>

                {/* Dynamic form by platform */}
                {platform === "web" && (
                  <div style={{ marginBottom: 14 }}>
                    <div style={{ fontSize: 12, color: c.muted, marginBottom: 8 }}>
                      Requisito: <b>Google Chrome</b> instalado en este equipo (Microsoft Edge no es válido para
                      grabar). Opcional: variable <code>ELIA_CHROME_PATH</code> si Chrome está en una ruta no estándar.
                    </div>
                    <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                      <input
                        data-testid="elia-web-url"
                        value={urlValue}
                        onChange={(e) => setUrlValue(e.target.value)}
                        placeholder="URL para grabar (ej: https://miapp.com)"
                        style={{
                          flex: "1 1 360px", minWidth: 280, padding: "10px 12px",
                          borderRadius: 10, border: `1px solid ${c.inputBorder}`,
                          background: c.inputBg, color: c.text, outline: "none", fontSize: 14,
                        }}
                      />
                    </div>
                    {recorderPreflightLoading && (
                      <div style={{ fontSize: 12, color: c.muted, marginTop: 8 }}>Comprobando Chrome…</div>
                    )}
                    {!recorderPreflightLoading && recorderPreflight && !recorderPreflight.ok && (
                      <div
                        role="alert"
                        style={{
                          marginTop: 10,
                          padding: "10px 12px",
                          borderRadius: 10,
                          fontSize: 13,
                          background: c.licWarnBg,
                          border: `1px solid ${c.licWarnBorder}`,
                          color: c.text,
                        }}
                      >
                        {recorderPreflight.errors.map((line, i) => (
                          <div key={i} style={{ marginTop: i ? 6 : 0 }}>
                            {line}
                          </div>
                        ))}
                      </div>
                    )}
                    {!recorderPreflightLoading && recorderPreflight?.ok && recorderPreflight.warnings.length > 0 && (
                      <div
                        style={{
                          marginTop: 10,
                          padding: "10px 12px",
                          borderRadius: 10,
                          fontSize: 13,
                          background: c.hintBg,
                          border: `1px solid ${c.hintBorder}`,
                          color: c.hintText,
                        }}
                      >
                        {recorderPreflight.warnings.join(" ")}
                      </div>
                    )}
                    {!recorderPreflightLoading && recorderPreflight?.ok && recorderPreflight.source === "install" && (
                      <div style={{ fontSize: 12, color: c.muted, marginTop: 8 }}>Chrome detectado.</div>
                    )}
                  </div>
                )}
                {platform === "mobile" && (
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
                          onClick={() => setMobileEnvOpen((open) => !open)}
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
                            onClick={() => void handleStartAppium()}
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
                            onClick={() => {
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
                        onClick={() => setDeviceMode("physical")}
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
                        onClick={() => setDeviceMode("emulator")}
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
                            onChange={(e) => setDeviceId(e.target.value)}
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
                            onClick={() => void refreshMobileDevices()}
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
                          onChange={(e) => setDeviceId(e.target.value)}
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
                            onChange={(e) => setSelectedAvd(e.target.value)}
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
                            onClick={() => void handleStartEmulator()}
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
                            onClick={() => void refreshMobileAvds()}
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
                            onChange={(e) => setDeviceId(e.target.value)}
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
                            onClick={() => void refreshMobileDevices()}
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
                          setAppPackage(e.target.value);
                          if (mobileFieldError) setMobileFieldError(null);
                        }}
                        placeholder="Paquete Android (ej: com.empresa.miapp) — opcional si detectas la app abierta"
                        style={{
                          flex: "1 1 220px",
                          padding: "10px 12px", borderRadius: 10,
                          border: `1px solid ${c.inputBorder}`, background: c.inputBg,
                          color: c.text, outline: "none", fontSize: 14,
                        }}
                      />
                      <button
                        type="button"
                        data-testid="elia-mobile-detect-app"
                        disabled={detectingForegroundApp || !deviceId.trim()}
                        onClick={() => void detectForegroundApp()}
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
                      onChange={(e) => setAppActivity(e.target.value)}
                      placeholder="Actividad principal — opcional (ej: .MainActivity)"
                      style={{
                        padding: "10px 12px", borderRadius: 10,
                        border: `1px solid ${c.inputBorder}`, background: c.inputBg,
                        color: c.text, outline: "none", fontSize: 14,
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
                      onChange={(e) => setApkPath(e.target.value)}
                      placeholder="Ruta del APK en Windows (opcional, ej: C:\apps\miapp.apk)"
                      style={{
                        padding: "10px 12px", borderRadius: 10,
                        border: `1px solid ${c.inputBorder}`, background: c.inputBg,
                        color: c.text, outline: "none", fontSize: 14,
                      }}
                    />
                    <div style={{ fontSize: 12, color: c.muted }}>
                      ELIA puede iniciar Appium automáticamente al grabar si está instalado. Requiere Android SDK y{" "}
                      <code style={{ fontSize: 11 }}>adb</code> en el PATH. Variables opcionales:{" "}
                      <code style={{ fontSize: 11 }}>ELIA_APPIUM_PATH</code>,{" "}
                      <code style={{ fontSize: 11 }}>ELIA_ANDROID_HOME</code>.
                    </div>
                  </div>
                )}
                {platform === "legacy" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 14 }}>
                    <input
                      value={windowName}
                      onChange={(e) => setWindowName(e.target.value)}
                      placeholder="Nombre de la ventana (título exacto, ej: Mi Aplicación)"
                      style={{
                        padding: "10px 12px", borderRadius: 10,
                        border: `1px solid ${c.inputBorder}`, background: c.inputBg,
                        color: c.text, outline: "none", fontSize: 14,
                      }}
                    />
                    <input
                      value={exePath}
                      onChange={(e) => setExePath(e.target.value)}
                      placeholder="Ruta del ejecutable .exe (opcional si ya está abierto)"
                      style={{
                        padding: "10px 12px", borderRadius: 10,
                        border: `1px solid ${c.inputBorder}`, background: c.inputBg,
                        color: c.text, outline: "none", fontSize: 14,
                      }}
                    />
                    <div style={{ fontSize: 12, color: c.muted }}>
                      Grabación de interacciones en aplicaciones de escritorio Windows.
                    </div>
                  </div>
                )}

                {aiCaps && (
                  <div style={{ fontSize: 13, color: c.muted, marginBottom: 14, lineHeight: 1.45 }}>
                    <b>Inteligencia local:</b> {aiCaps.resolution.message}
                    {aiCaps.resolution.use_ai
                      ? " Las conversiones a Behave usan revisión asistida por IA."
                      : " Las conversiones usarán modo heurístico (rápido)."}
                  </div>
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
                        disabled={!canRunJobs}
                        onChange={async (e) => {
                          if (!canRunJobs) return;
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
                        disabled={!canRunJobs}
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
                      (license ? !license.can_run_jobs : false) ||
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
                        license && !license.can_run_jobs
                          ? c.buttonDisabledBg
                          : platform === "web" && recorderPreflight && !recorderPreflight.ok
                            ? c.buttonDisabledBg
                            : platform === "mobile" && mobilePreflight && !mobilePreflight.ok
                              ? c.buttonDisabledBg
                              : c.primary,
                      color: c.primaryFg, border: "none",
                      cursor:
                        (license && !license.can_run_jobs) ||
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
                      (license ? !license.can_run_jobs : false) ||
                      (platform === "mobile" && !modules?.mobile_recording) ||
                      (platform === "legacy" && !modules?.legacy_recording)
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
                      cursor: license && !license.can_run_jobs ? "not-allowed" : "pointer",
                      opacity: license && !license.can_run_jobs ? 0.5 : 1,
                    }}
                  >
                    Convertir a Behave
                  </button>
                  {platform === "web" && (
                  <button
                    disabled={license ? !license.can_run_jobs : false}
                    onClick={() => void startJob("puppeteer_to_step_by_step")}
                    style={{
                      padding: "10px 14px", borderRadius: 10,
                      background: c.btnGhostBg, color: c.text,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: license && !license.can_run_jobs ? "not-allowed" : "pointer",
                      opacity: license && !license.can_run_jobs ? 0.5 : 1,
                    }}
                  >
                    Convertir a step by step
                  </button>
                  )}
                </div>
                </div>
              </>
            )}

            {homeTab === "req" && (
              <div
                style={{
                  background: c.neutralBg,
                  border: `1px solid ${c.border}`,
                  borderRadius: 14,
                  padding: 14,
                  opacity: canRunJobs ? 1 : 0.55,
                  pointerEvents: canRunJobs ? "auto" : "none",
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
                    disabled={!canRunJobs}
                    onChange={async (e) => {
                      if (!canRunJobs) return;
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

                {aiCaps && (
                  <div style={{ fontSize: 13, color: c.muted, marginBottom: 12, lineHeight: 1.45 }}>
                    <b>Inteligencia local:</b> {aiCaps.resolution.message}
                  </div>
                )}

                {/* Botón de acción principal */}
                <div style={{ marginTop: 4 }}>
                  <button
                    data-testid="elia-btn-doc-bdd"
                    disabled={license ? !license.can_run_jobs : false}
                    onClick={() => void startJob("doc_to_bdd")}
                    style={{
                      padding: "10px 20px", borderRadius: 10,
                      background: license && !license.can_run_jobs ? c.buttonDisabledBg : c.primary,
                      color: c.primaryFg, border: "none", fontWeight: 600, fontSize: 14,
                      cursor: license && !license.can_run_jobs ? "not-allowed" : "pointer",
                    }}
                  >
                    Procesar y Convertir a BDD
                  </button>
                </div>

                {/* Separador */}
                <div style={{ borderTop: `1px solid ${c.border}`, margin: "16px 0 12px" }} />

                {/* Integraciones externas */}
                <div style={{ color: c.muted, fontSize: 13, marginBottom: 10 }}>
                  Conecta con sistemas externos o carga documentos locales para convertir a BDD.
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", marginBottom: 10 }}>
                  <label style={{ fontSize: 13, fontWeight: 600, color: c.text }}>Perfil activo</label>
                  <select
                    value={reqConnectorProfileId}
                    onChange={(e) => setReqConnectorProfileId(e.target.value)}
                    style={{
                      flex: "1 1 200px", minWidth: 180, padding: "8px 12px",
                      borderRadius: 10, border: `1px solid ${c.inputBorder}`,
                      background: c.inputBg, color: c.text, fontSize: 14,
                    }}
                  >
                    {connectorProfiles.length === 0 ? (
                      <option value="">Sin perfiles — usa Configuración (⚙)</option>
                    ) : (
                      connectorProfiles.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))
                    )}
                  </select>
                  <button
                    disabled={license ? !license.can_run_jobs : false}
                    onClick={() => void startJob("elia_jira_smoke")}
                    style={{
                      padding: "8px 12px", borderRadius: 10, background: c.btnGhostBg,
                      color: c.text, border: `1px solid ${c.btnGhostBorder}`, fontSize: 13,
                      cursor: license && !license.can_run_jobs ? "not-allowed" : "pointer",
                      opacity: license && !license.can_run_jobs ? 0.5 : 1,
                    }}
                  >Conectar a Jira</button>
                  <button
                    disabled={license ? !license.can_run_jobs : false}
                    onClick={() => void startJob("elia_value_edge_smoke")}
                    style={{
                      padding: "8px 12px", borderRadius: 10, background: c.btnGhostBg,
                      color: c.text, border: `1px solid ${c.btnGhostBorder}`, fontSize: 13,
                      cursor: license && !license.can_run_jobs ? "not-allowed" : "pointer",
                      opacity: license && !license.can_run_jobs ? 0.5 : 1,
                    }}
                  >Extraer de ValueEdge</button>
                  <button
                    disabled={license ? !license.can_run_jobs : false}
                    onClick={() => void startJob("elia_gherkin_batch")}
                    style={{
                      padding: "8px 12px", borderRadius: 10, background: c.btnGhostBg,
                      color: c.text, border: `1px solid ${c.btnGhostBorder}`, fontSize: 13,
                      cursor: license && !license.can_run_jobs ? "not-allowed" : "pointer",
                      opacity: license && !license.can_run_jobs ? 0.5 : 1,
                    }}
                  >Lote .json → .feature</button>
                </div>
              </div>
            )}
          </div>
        )}

        {!job && jobId && <div style={{ color: c.muted }}>Cargando...</div>}

        {!isHomeSurface && job && job.state === "running" && !activePrompt && (
          <div
            style={{
              background: c.processingBg,
              border: `1px solid ${c.processingBorder}`,
              color: c.processingText,
              padding: 12,
              borderRadius: 10,
              marginBottom: 16,
              fontSize: 14,
            }}
          >
            <div>
              {job.progress?.stage
                ? String(job.progress.stage)
                : "Procesando… (espera; esta pestaña no se cerrará sola)."}
            </div>
            {job.progress?.events_captured != null && (
              <div style={{ marginTop: 8, fontSize: 13 }}>
                Pantallas / eventos capturados: <b>{job.progress.events_captured}</b>
                {job.progress?.elapsed_s != null ? ` · ${job.progress.elapsed_s}s` : ""}
              </div>
            )}
            {job.progress?.recording && (
                <div style={{ marginTop: 12 }}>
                  <button
                    type="button"
                    disabled={stoppingRecording}
                    onClick={() => {
                      if (!jobId) return;
                      setStoppingRecording(true);
                      void stopRecording(jobId)
                        .catch((e: unknown) => {
                          setErrorText(String((e as Error)?.message ?? e));
                        })
                        .finally(() => setStoppingRecording(false));
                    }}
                    style={{
                      padding: "10px 16px",
                      borderRadius: 10,
                      background: c.primary,
                      color: c.primaryFg,
                      border: "none",
                      cursor: stoppingRecording ? "wait" : "pointer",
                      fontWeight: 600,
                    }}
                  >
                    {stoppingRecording ? "Finalizando…" : "Finalizar grabación"}
                  </button>
                </div>
              )}
          </div>
        )}

        {job && job.state === "running" && String(job.progress?.stage ?? "").includes("Ejecutando Puppeteer") && (
          <div
            style={{
              background: c.warnBg,
              border: `1px solid ${c.warnBorder}`,
              color: c.warnText,
              padding: 12,
              borderRadius: 10,
              marginBottom: 16,
              fontSize: 14,
            }}
          >
            Se está abriendo el <b>navegador de grabación</b>. En Windows intentamos pasarlo al primer plano; si sigues viendo
            solo ELIA, revisa la barra de tareas u otras ventanas de Chrome/Chromium.
          </div>
        )}

        {job?.error && (
          <div
            style={{
              background: c.errorBg,
              border: `1px solid ${c.errorBorder}`,
              padding: 12,
              borderRadius: 10,
              marginBottom: 16,
            }}
          >
            <b style={{ color: c.errorTitle }}>Job error</b>
            <div style={{ color: c.errorBody, marginTop: 6, whiteSpace: "pre-wrap" }}>
              {job.error.message}
              {job.error.details ? `\n${job.error.details}` : ""}
            </div>
          </div>
        )}

        {job?.state === "waiting_user" && activePrompt && (
          <div
            data-testid="elia-job-prompt"
            style={{
              background: c.surface,
              border: `1px solid ${c.border}`,
              borderRadius: 14,
              padding: 18,
              boxShadow: c.shadow,
            }}
          >
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
              <div style={{ fontSize: 13, color: c.muted }}>{formatPromptType(activePrompt.type)}</div>
              <div style={{ marginLeft: "auto", fontSize: 12, color: c.muted }}>job: {job.job_id.slice(0, 8)}...</div>
            </div>

            <h2 style={{ margin: "10px 0 6px", fontSize: 20, color: c.text }}>{activePrompt.title}</h2>
            {activePrompt.type !== "message_ack" && (
              <div style={{ color: c.text, marginBottom: 14 }}>{activePrompt.message}</div>
            )}

            {activePrompt.type === "pick_conversion_mode" && activePrompt.options && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {(activePrompt.options as { value: string; label: string }[]).map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={async () => {
                      if (!jobId) return;
                      await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: opt.value });
                    }}
                    style={{
                      padding: "12px 14px",
                      borderRadius: 10,
                      background: c.btnGhostBg,
                      color: c.text,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: "pointer",
                      textAlign: "left",
                    }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}

            {(activePrompt.type === "pick_project" || activePrompt.type === "pick_script") && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  {(activePrompt.options as { value: string; label: string }[]).map((opt) => (
                    <button
                      key={opt.value}
                      onClick={async () => {
                        if (!jobId) return;
                        await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: opt.value });
                      }}
                      style={{
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: `1px solid ${c.btnGhostBorder}`,
                        background: c.btnGhostBg,
                        color: c.text,
                        cursor: "pointer",
                      }}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
                {promptAllowsBack(activePrompt.payload) && (
                  <button
                    type="button"
                    onClick={async () => {
                      if (!jobId) return;
                      await sendPromptResponse({
                        jobId,
                        promptId: activePrompt.prompt_id,
                        answer: PROMPT_ANSWER_BACK,
                      });
                    }}
                    style={{
                      alignSelf: "flex-start",
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.btnGhostBg,
                      color: c.text,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: "pointer",
                    }}
                  >
                    Regresar
                  </button>
                )}
              </div>
            )}

            {activePrompt.type === "pick_scripts_multi" && activePrompt.actions && (
              <div>
                <div style={{ fontSize: 12, color: c.muted, marginBottom: 8 }}>
                  Marca al menos 2 grabaciones y pulsa Continuar.
                </div>
                <div style={{ border: `1px solid ${c.border}`, borderRadius: 12, padding: 12, maxHeight: 320, overflow: "auto" }}>
                  <ActionsCheckboxList
                    c={c}
                    actions={activePrompt.actions}
                    minSelected={2}
                    onSubmit={async (selectedLines) => {
                      if (!jobId) return;
                      await sendPromptResponse({
                        jobId,
                        promptId: activePrompt.prompt_id,
                        answer: selectedLines,
                      });
                    }}
                  />
                </div>
              </div>
            )}

            {activePrompt.type === "pick_actions" && activePrompt.actions && (
              <div>
                <div style={{ fontSize: 13, color: c.muted, marginBottom: 10 }}>
                  Marca las acciones a convertir
                </div>
                <div style={{ border: `1px solid ${c.border}`, borderRadius: 12, padding: 12, maxHeight: 320, overflow: "auto" }}>
                  <ActionsCheckboxList
                    c={c}
                    actions={activePrompt.actions}
                    onSubmit={async (selectedLines) => {
                      if (!jobId) return;
                      await sendPromptResponse({
                        jobId,
                        promptId: activePrompt.prompt_id,
                        answer: selectedLines,
                      });
                    }}
                  />
                </div>
              </div>
            )}

            {activePrompt.type === "yes_no" && (
              <div style={{ display: "flex", gap: 10 }}>
                <button
                  onClick={async () => {
                    if (!jobId) return;
                    await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: true });
                  }}
                  style={{
                    padding: "10px 14px",
                    borderRadius: 10,
                    background: c.primary,
                    color: c.primaryFg,
                    border: "none",
                    cursor: "pointer",
                  }}
                >
                  Sí
                </button>
                <button
                  onClick={async () => {
                    if (!jobId) return;
                    await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: false });
                  }}
                  style={{
                    padding: "10px 14px",
                    borderRadius: 10,
                    background: c.btnGhostBg,
                    color: c.text,
                    border: `1px solid ${c.btnGhostBorder}`,
                    cursor: "pointer",
                  }}
                >
                  No
                </button>
              </div>
            )}

            {activePrompt.type === "yes_no_cancel" && (
              <div style={{ display: "flex", gap: 10 }}>
                <button
                  onClick={async () => {
                    if (!jobId) return;
                    await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: true });
                  }}
                  style={{
                    padding: "10px 14px",
                    borderRadius: 10,
                    background: c.primary,
                    color: c.primaryFg,
                    border: "none",
                    cursor: "pointer",
                  }}
                >
                  Sí
                </button>
                <button
                  onClick={async () => {
                    if (!jobId) return;
                    await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: false });
                  }}
                  style={{
                    padding: "10px 14px",
                    borderRadius: 10,
                    background: c.btnGhostBg,
                    color: c.text,
                    border: `1px solid ${c.btnGhostBorder}`,
                    cursor: "pointer",
                  }}
                >
                  No
                </button>
                <button
                  onClick={async () => {
                    if (!jobId) return;
                    await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: null });
                  }}
                  style={{
                    padding: "10px 14px",
                    borderRadius: 10,
                    background: c.btnGhostBg,
                    color: c.muted,
                    border: `1px solid ${c.btnGhostBorder}`,
                    cursor: "pointer",
                  }}
                >
                  Cancelar
                </button>
              </div>
            )}

            {activePrompt.type === "bdd_preview" && (() => {
              const ap = activePrompt as Extract<ActivePrompt, { type: "bdd_preview" }>;
              if (!ap.payload) return null;
              return (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ fontSize: 13, color: c.muted }}>
                  Intento {ap.payload.attempt} de {ap.payload.max_attempts}.{" "}
                  {ap.payload.can_manual
                    ? "Puedes editar el escenario a mano o usar la versión heurística."
                    : "Revisa el texto; puedes aceptarlo o pedir otra versión con IA."}
                </div>
                {ap.payload.script_excerpt?.trim() ? (
                  <div>
                    <div style={{ fontSize: 12, color: c.muted, marginBottom: 6 }}>Extracto del script (referencia)</div>
                    <textarea
                      readOnly
                      value={ap.payload.script_excerpt}
                      style={{
                        width: "100%",
                        minHeight: 120,
                        padding: 10,
                        borderRadius: 10,
                        border: `1px solid ${c.border}`,
                        fontFamily: "ui-monospace, monospace",
                        fontSize: 12,
                        background: c.codeBg,
                        color: c.text,
                      }}
                    />
                  </div>
                ) : null}
                <div>
                  <div style={{ fontSize: 12, color: c.muted, marginBottom: 6 }}>Feature (.feature)</div>
                  <textarea
                    value={bddPreviewText}
                    onChange={(e) => setBddPreviewText(e.target.value)}
                    readOnly={!ap.payload.can_manual}
                    style={{
                      width: "100%",
                      minHeight: 220,
                      padding: 10,
                      borderRadius: 10,
                      border: `1px solid ${c.inputBorder}`,
                      fontFamily: "ui-monospace, monospace",
                      fontSize: 13,
                      background: ap.payload.can_manual ? c.inputBg : c.codeBg,
                      color: c.text,
                    }}
                  />
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                  <button
                    type="button"
                    onClick={async () => {
                      if (!jobId) return;
                      const orig = String(ap.payload?.feature_text ?? "");
                      const edited = bddPreviewText.trim() !== orig.trim();
                      await sendPromptResponse({
                        jobId,
                        promptId: ap.prompt_id,
                        answer: {
                          action: "accept",
                          feature_text: bddPreviewText,
                          edited,
                        },
                      });
                    }}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.primary,
                      color: c.primaryFg,
                      border: "none",
                      cursor: "pointer",
                    }}
                  >
                    {ap.payload.can_manual ? "Aceptar escenario" : "Aceptar"}
                  </button>
                  {!ap.payload.can_manual ? (
                    <button
                      type="button"
                      onClick={async () => {
                        if (!jobId) return;
                        await sendPromptResponse({
                          jobId,
                          promptId: ap.prompt_id,
                          answer: { action: "reject" },
                        });
                      }}
                      style={{
                        padding: "10px 14px",
                        borderRadius: 10,
                        background: c.btnGhostBg,
                        color: c.text,
                        border: `1px solid ${c.btnGhostBorder}`,
                        cursor: "pointer",
                      }}
                    >
                      Rechazar (regenerar)
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={async () => {
                        if (!jobId) return;
                        await sendPromptResponse({
                          jobId,
                          promptId: ap.prompt_id,
                          answer: { action: "use_heuristic" },
                        });
                      }}
                      style={{
                        padding: "10px 14px",
                        borderRadius: 10,
                        background: c.btnGhostBg,
                        color: c.text,
                        border: `1px solid ${c.btnGhostBorder}`,
                        cursor: "pointer",
                      }}
                    >
                      Usar generación heurística
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={async () => {
                      if (!jobId) return;
                      await sendPromptResponse({ jobId, promptId: ap.prompt_id, answer: null });
                    }}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.btnGhostBg,
                      color: c.muted,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: "pointer",
                    }}
                  >
                    Cancelar
                  </button>
                </div>
              </div>
              );
            })()}

            {activePrompt.type === "grouped_feature_review" && (() => {
              const ap = activePrompt as {
                prompt_id: string;
                payload?: {
                  feature_text?: string;
                  script_names?: string[];
                  background_count?: number;
                };
              };
              if (!ap.payload) return null;
              const names = ap.payload.script_names ?? [];
              const bg = ap.payload.background_count ?? 0;
              return (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div style={{ fontSize: 13, color: c.muted }}>
                    Grabaciones: {names.join(", ") || "—"}
                    {bg > 0 ? ` · Background: ${bg} paso(s)` : ""}
                  </div>
                  <textarea
                    value={bddPreviewText}
                    onChange={(e) => setBddPreviewText(e.target.value)}
                    style={{
                      width: "100%",
                      minHeight: 280,
                      padding: 10,
                      borderRadius: 10,
                      border: `1px solid ${c.inputBorder}`,
                      fontFamily: "ui-monospace, monospace",
                      fontSize: 13,
                      background: c.inputBg,
                      color: c.text,
                    }}
                  />
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                    <button
                      type="button"
                      onClick={async () => {
                        if (!jobId) return;
                        await sendPromptResponse({
                          jobId,
                          promptId: ap.prompt_id,
                          answer: { action: "accept", feature_text: bddPreviewText },
                        });
                      }}
                      style={{
                        padding: "10px 14px",
                        borderRadius: 10,
                        background: c.primary,
                        color: c.primaryFg,
                        border: "none",
                        cursor: "pointer",
                      }}
                    >
                      Aceptar y generar
                    </button>
                    <button
                      type="button"
                      onClick={async () => {
                        if (!jobId) return;
                        await sendPromptResponse({ jobId, promptId: ap.prompt_id, answer: null });
                      }}
                      style={{
                        padding: "10px 14px",
                        borderRadius: 10,
                        background: c.btnGhostBg,
                        color: c.muted,
                        border: `1px solid ${c.btnGhostBorder}`,
                        cursor: "pointer",
                      }}
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              );
            })()}

            {activePrompt.type === "message_ack" && (() => {
              const ap = activePrompt as Extract<ActivePrompt, { type: "message_ack" }>;
              const resultPayload = ap.payload ?? null;
              const hasFiles =
                Boolean(resultPayload?.generated_files?.length) ||
                Boolean(resultPayload?.output_dir || resultPayload?.project_dir);
              return (
              <div>
                {hasFiles ? (
                  <GeneratedFilesResultView
                    message={ap.message}
                    payload={resultPayload}
                    progress={job?.progress}
                    c={c}
                  />
                ) : (
                <div
                  style={{
                    background:
                      ap.severity === "error"
                        ? c.msgErrBg
                        : ap.severity === "warning"
                          ? c.msgWarnBg
                          : c.msgInfoBg,
                    border:
                      ap.severity === "error"
                        ? `1px solid ${c.msgErrBorder}`
                        : ap.severity === "warning"
                          ? `1px solid ${c.msgWarnBorder}`
                          : `1px solid ${c.msgInfoBorder}`,
                    color:
                      ap.severity === "error"
                        ? c.msgErrText
                        : ap.severity === "warning"
                          ? c.msgWarnText
                          : c.msgInfoText,
                    padding: 12,
                    borderRadius: 10,
                    marginBottom: 14,
                    whiteSpace: "pre-wrap",
                    fontSize: 14,
                    maxHeight: "min(50vh, 360px)",
                    overflow: "auto",
                  }}
                >
                  {ap.message}
                </div>
                )}
                <div
                  style={{
                    display: "flex",
                    gap: 10,
                    flexWrap: "wrap",
                    marginTop: 4,
                    position: "sticky",
                    bottom: 0,
                    background: c.stickyBarBg,
                    paddingTop: 8,
                  }}
                >
                  <button
                    type="button"
                    onClick={async () => {
                      if (!jobId) return;
                      await sendPromptResponse({ jobId, promptId: ap.prompt_id, answer: true });
                    }}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.primary,
                      color: c.primaryFg,
                      border: "none",
                      cursor: "pointer",
                    }}
                  >
                    Aceptar
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      if (!jobId) return;
                      await sendPromptResponse({ jobId, promptId: ap.prompt_id, answer: true });
                    }}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.btnGhostBg,
                      color: c.text,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: "pointer",
                    }}
                  >
                    Cerrar
                  </button>
                </div>
              </div>
              );
            })()}

            {activePrompt.type === "input_text" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <input
                  value={textValue}
                  onChange={(e) => setTextValue(e.target.value)}
                  placeholder={activePrompt.message}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: `1px solid ${c.inputBorder}`,
                    background: c.inputBg,
                    color: c.text,
                    outline: "none",
                    fontSize: 14,
                  }}
                />
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <button
                    onClick={async () => {
                      if (!jobId) return;
                      const value = textValue.trim();
                      await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: value });
                    }}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.primary,
                      color: c.primaryFg,
                      border: "none",
                      cursor: "pointer",
                    }}
                  >
                    Guardar
                  </button>
                  {promptAllowsBack(activePrompt.payload) && (
                    <button
                      type="button"
                      onClick={async () => {
                        if (!jobId) return;
                        await sendPromptResponse({
                          jobId,
                          promptId: activePrompt.prompt_id,
                          answer: PROMPT_ANSWER_BACK,
                        });
                      }}
                      style={{
                        padding: "10px 14px",
                        borderRadius: 10,
                        background: c.btnGhostBg,
                        color: c.text,
                        border: `1px solid ${c.btnGhostBorder}`,
                        cursor: "pointer",
                      }}
                    >
                      Regresar
                    </button>
                  )}
                  <button
                    onClick={async () => {
                      if (!jobId) return;
                      await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: null });
                    }}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: c.btnGhostBg,
                      color: c.muted,
                      border: `1px solid ${c.btnGhostBorder}`,
                      cursor: "pointer",
                    }}
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {!isHomeSurface && job?.state === "done" && (
          <div
            data-testid="elia-job-done"
            style={{
              background: c.successBg,
              border: `1px solid ${c.successBorder}`,
              padding: 16,
              borderRadius: 14,
            }}
          >
            <b style={{ color: c.successTitle }}>Conversión finalizada</b>
            <div style={{ marginTop: 10 }}>
              <GeneratedFilesResultView progress={job.progress} c={c} />
            </div>
            <div style={{ marginTop: 12, fontSize: 13, color: c.successHint }}>
              <b>Volver al inicio:</b> si abriste el flujo desde la pestaña de inicio, se cierra <b>esta</b> pestaña y se
              pone al frente la de inicio (no duplicas el inicio). Si abriste solo esta URL (p. ej. desde el escritorio),
              se abrirá otra vista de inicio en esta pestaña.
            </div>
            <div style={{ marginTop: 14, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
              <button
                type="button"
                title="Cierra esta pestaña de trabajo y enfoca la de inicio, si existe."
                onClick={() => {
                  if (!tryFocusOpenerAndCloseThisTab()) {
                    goHomeInThisTab();
                  }
                }}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: c.primary,
                  color: c.primaryFg,
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Volver al inicio
              </button>
            </div>
          </div>
        )}

        {!isHomeSurface && job?.state === "error" && (
          <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <button
              type="button"
              onClick={() => {
                if (!tryFocusOpenerAndCloseThisTab()) {
                  goHomeInThisTab();
                }
              }}
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                background: c.primary,
                color: c.primaryFg,
                border: "none",
                cursor: "pointer",
              }}
            >
              Volver al inicio
            </button>
          </div>
        )}

        {!isHomeSurface && job?.state === "cancelled" && (
          <div
            style={{
              background: c.neutralBg,
              border: `1px solid ${c.border}`,
              padding: 16,
              borderRadius: 14,
              marginTop: 8,
            }}
          >
            <b style={{ color: c.text }}>Operación cancelada</b>
            <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
              <button
                type="button"
                onClick={() => {
                  if (!tryFocusOpenerAndCloseThisTab()) {
                    goHomeInThisTab();
                  }
                }}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: c.primary,
                  color: c.primaryFg,
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Volver al inicio
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ActionsCheckboxList(props: {
  c: import("./eliaTheme").EliaPalette;
  actions: { type: string; description: string; original_line: string }[];
  minSelected?: number;
  onSubmit: (selectedLines: string[]) => void | Promise<void>;
}) {
  const { c } = props;
  const [selected, setSelected] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const next: Record<string, boolean> = {};
    for (const a of props.actions) next[a.original_line] = true;
    setSelected(next);
  }, [props.actions]);

  const selectedLines = useMemo(() => {
    return props.actions.filter((a) => selected[a.original_line]).map((a) => a.original_line);
  }, [props.actions, selected]);

  return (
    <div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {props.actions.map((a, idx) => (
          <label key={idx} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
            <input
              type="checkbox"
              checked={!!selected[a.original_line]}
              onChange={(e) => setSelected((prev) => ({ ...prev, [a.original_line]: e.target.checked }))}
              style={{ marginTop: 3 }}
            />
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: c.text }}>{a.type}</div>
              <div style={{ fontSize: 12, color: c.actionDesc }}>{a.description}</div>
            </div>
          </label>
        ))}
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 14, justifyContent: "flex-end" }}>
        <button
          onClick={() => setSelected((prev) => Object.fromEntries(Object.keys(prev).map((k) => [k, true])))}
          style={{
            padding: "8px 12px",
            borderRadius: 10,
            background: c.btnGhostBg,
            border: `1px solid ${c.btnGhostBorder}`,
            color: c.text,
            cursor: "pointer",
          }}
        >
          Incluir todas
        </button>
        <button
          onClick={() => setSelected((prev) => Object.fromEntries(Object.keys(prev).map((k) => [k, false])))}
          style={{
            padding: "8px 12px",
            borderRadius: 10,
            background: c.btnGhostBg,
            border: `1px solid ${c.btnGhostBorder}`,
            color: c.text,
            cursor: "pointer",
          }}
        >
          Excluir todas
        </button>
        <button
          disabled={props.minSelected != null && selectedLines.length < props.minSelected}
          onClick={async () => {
            await props.onSubmit(selectedLines);
          }}
          style={{
            padding: "8px 12px",
            borderRadius: 10,
            background: c.primary,
            color: c.primaryFg,
            border: "none",
            cursor:
              props.minSelected != null && selectedLines.length < props.minSelected
                ? "not-allowed"
                : "pointer",
            opacity: props.minSelected != null && selectedLines.length < props.minSelected ? 0.5 : 1,
          }}
        >
          Continuar
        </button>
      </div>
    </div>
  );
}
