import type {
  BddPublishTarget,
  EliaAzureDevOpsCreds,
  EliaConnectorsDocument,
  EliaGitCreds,
  EliaJiraCreds,
  EliaValueEdgeCreds,
  LoadedDoc,
  ModulesStatus,
  RecordingRef,
  ScenarioRef,
} from "./types";

export type { LoadedDoc, ModulesStatus, RecordingRef, ScenarioRef };

/** Respuesta especial para volver al paso anterior de un flujo de prompts. */
export const PROMPT_ANSWER_BACK = "__elia_back__";

export type JobStateResponse = {
  job_id: string;
  mode: string;
  state: string;
  progress: Record<string, any>;
  error: null | { message: string; details?: string };
  active_prompt: any;
  events_count: number;
};

export async function startConvertJob(params: {
  mode:
    | "demo"
    | "puppeteer_to_behave"
    | "puppeteer_to_step_by_step"
    | "puppeteer_recorder"
    | "mobile_recorder"
    | "legacy_recorder"
    | "mobile_to_behave"
    | "legacy_to_behave"
    | "doc_to_bdd"
    | "api_to_behave"
    | "api_run_behave"
    | "api_load_test"
    // ELIA
    | "elia_jira_smoke"
    | "elia_value_edge_smoke"
    | "elia_gherkin_batch";
  url?: string;
  /** Ignorado por el servidor; la política de IA se resuelve en backend (ai_preferences.json). */
  use_ai?: boolean;
  elia_use_inline_connectors?: boolean;
  elia_jira?: EliaJiraCreds;
  elia_value_edge?: EliaValueEdgeCreds;
  // Mobile
  platform?: string;
  apk_path?: string;
  device_id?: string;
  app_package?: string;
  app_activity?: string;
  // Legacy
  window_name?: string;
  exe_path?: string;
  // Doc-to-BDD
  doc_files?: string[];
  link_recording?: string;
  link_scenario?: string;
  link_scenario_by_doc?: Record<string, string>;
  link_recording_by_doc?: Record<string, string>;
  capture_api?: boolean;
  api_project?: string;
  api_traffic_path?: string;
  api_scenario_ids?: string[];
  api_feature_name?: string;
  load_test_users?: number;
  load_test_spawn_rate?: number;
  load_test_run_time?: string;
  load_test_host?: string;
}): Promise<{ job_id: string }> {
  const {
    mode, url, elia_use_inline_connectors, elia_jira, elia_value_edge,
    platform, apk_path, device_id, app_package, app_activity, window_name, exe_path,
    doc_files, link_recording, link_scenario, link_scenario_by_doc, link_recording_by_doc,
    capture_api, api_project, api_traffic_path, api_scenario_ids, api_feature_name,
    load_test_users, load_test_spawn_rate, load_test_run_time, load_test_host,
  } = params;
  const res = await fetch("/api/jobs/convert", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      mode,
      url,
      ...(elia_use_inline_connectors != null ? { elia_use_inline_connectors } : {}),
      ...(elia_jira != null ? { elia_jira } : {}),
      ...(elia_value_edge != null ? { elia_value_edge } : {}),
      ...(platform != null ? { platform } : {}),
      ...(apk_path != null ? { apk_path } : {}),
      ...(device_id != null ? { device_id } : {}),
      ...(app_package != null ? { app_package } : {}),
      ...(app_activity != null ? { app_activity } : {}),
      ...(window_name != null ? { window_name } : {}),
      ...(exe_path != null ? { exe_path } : {}),
      ...(doc_files != null ? { doc_files } : {}),
      ...(link_recording != null ? { link_recording } : {}),
      ...(link_scenario != null ? { link_scenario } : {}),
      ...(link_scenario_by_doc != null ? { link_scenario_by_doc } : {}),
      ...(link_recording_by_doc != null ? { link_recording_by_doc } : {}),
      ...(capture_api != null ? { capture_api } : {}),
      ...(api_project != null ? { api_project } : {}),
      ...(api_traffic_path != null ? { api_traffic_path } : {}),
      ...(api_scenario_ids != null ? { api_scenario_ids } : {}),
      ...(api_feature_name != null ? { api_feature_name } : {}),
      ...(load_test_users != null ? { load_test_users } : {}),
      ...(load_test_spawn_rate != null ? { load_test_spawn_rate } : {}),
      ...(load_test_run_time != null ? { load_test_run_time } : {}),
      ...(load_test_host != null ? { load_test_host } : {}),
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to start job: ${res.status} ${text}`);
  }
  return res.json();
}

export async function cancelConvertJob(jobId: string): Promise<void> {
  const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to cancel job: ${res.status} ${text}`);
  }
}

export async function getModulesStatus(): Promise<ModulesStatus> {
  const res = await fetch("/api/modules/status");
  if (!res.ok) throw new Error(`Failed to fetch modules: ${res.status}`);
  return res.json();
}

export type RecorderPreflightResponse = {
  ok: boolean;
  chrome_path: string | null;
  source: string | null;
  warnings: string[];
  errors: string[];
  chrome_required: boolean;
  chromium_fallback_enabled: boolean;
  platform: string;
};

export async function getRecorderPreflight(): Promise<RecorderPreflightResponse> {
  const res = await fetch("/api/recorder/preflight");
  if (!res.ok) throw new Error(`Failed to fetch recorder preflight: ${res.status}`);
  return res.json();
}

export type MobileDeviceInfo = {
  id: string;
  state: string;
  kind: "physical" | "emulator";
  model?: string | null;
  product?: string | null;
};

export type MobileDevicesResponse = {
  ok: boolean;
  devices: MobileDeviceInfo[];
  error?: string | null;
  android_only: boolean;
};

export type MobileAvdsResponse = {
  ok: boolean;
  avds: string[];
  error?: string | null;
  android_only: boolean;
};

export type MobilePreflightItem = {
  id: string;
  label: string;
  ok: boolean;
  message: string;
  hint?: string | null;
};

export type MobilePreflightResponse = {
  ok: boolean;
  platform: string;
  items: MobilePreflightItem[];
  warnings: string[];
  errors: string[];
  env: Record<string, string | null | undefined>;
  android_only: boolean;
};

export type MobileEmulatorStartResponse = {
  ok: boolean;
  message: string;
  device_id: string | null;
  reused?: boolean;
  hint?: string;
};

export type MobileForegroundAppResponse = {
  ok: boolean;
  package: string | null;
  activity: string | null;
  error?: string | null;
  source?: string | null;
  android_only: boolean;
};

export type MobileAppiumStatusResponse = {
  ok: boolean;
  running: boolean;
  installed: boolean;
  managed_by_elia: boolean;
  url: string;
  host: string;
  port: number;
  path?: string | null;
  source?: string | null;
  version?: string | null;
  android_only: boolean;
};

export async function getMobileDevices(): Promise<MobileDevicesResponse> {
  const res = await fetch("/api/mobile/devices");
  if (!res.ok) throw new Error(`Failed to fetch mobile devices: ${res.status}`);
  return res.json();
}

export async function getMobileAvds(): Promise<MobileAvdsResponse> {
  const res = await fetch("/api/mobile/avds");
  if (!res.ok) throw new Error(`Failed to fetch mobile AVDs: ${res.status}`);
  return res.json();
}

export async function getMobilePreflight(): Promise<MobilePreflightResponse> {
  const res = await fetch("/api/mobile/preflight");
  if (!res.ok) throw new Error(`Failed to fetch mobile preflight: ${res.status}`);
  return res.json();
}

export async function getMobileForegroundApp(deviceId: string): Promise<MobileForegroundAppResponse> {
  const res = await fetch(
    `/api/mobile/foreground-app?device_id=${encodeURIComponent(deviceId)}`,
  );
  if (!res.ok) throw new Error(`No se pudo detectar la app en primer plano: ${res.status}`);
  return res.json();
}

export async function getMobileAppiumStatus(): Promise<MobileAppiumStatusResponse> {
  const res = await fetch("/api/mobile/appium/status");
  if (!res.ok) throw new Error(`No se pudo consultar Appium: ${res.status}`);
  return res.json();
}

export async function startMobileAppium(timeoutSec = 60): Promise<{
  ok: boolean;
  running: boolean;
  message: string;
  url?: string;
  managed_by_elia?: boolean;
  hint?: string;
}> {
  const res = await fetch("/api/mobile/appium/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ timeout_sec: timeoutSec }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(typeof (data as any)?.detail === "string" ? (data as any).detail : "No se pudo iniciar Appium");
  }
  return data;
}

export async function stopMobileAppium(): Promise<{ ok: boolean; running: boolean; message: string }> {
  const res = await fetch("/api/mobile/appium/stop", { method: "POST" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error("No se pudo detener Appium");
  return data;
}

export async function startMobileEmulator(params: {
  avd: string;
  wait_boot?: boolean;
  timeout_sec?: number;
}): Promise<MobileEmulatorStartResponse> {
  const res = await fetch("/api/mobile/emulator/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof (data as any)?.detail === "string" ? (data as any).detail : JSON.stringify(data);
    throw new Error(`No se pudo iniciar el emulador: ${detail}`);
  }
  return data;
}

export async function stopMobileEmulator(deviceId?: string): Promise<{ ok: boolean; message: string }> {
  const res = await fetch("/api/mobile/emulator/stop", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(deviceId ? { device_id: deviceId } : {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(`No se pudo detener el emulador: ${res.status}`);
  }
  return data;
}

export type MobileAvdTemplate = {
  id: string;
  label: string;
  description: string;
  estimated_gb: string;
  avd_name: string;
};

export type MobileAvdWizardJobStatus = {
  active: boolean;
  phase: string;
  message: string;
  done: boolean;
  ok: boolean;
  error?: string | null;
  avd_name?: string | null;
  verified?: boolean;
};

export type MobileAvdWizardCapabilitiesResponse = {
  ok: boolean;
  orchestration_allowed: boolean;
  orchestration_tier: string;
  sdk_path?: string | null;
  sdk_ok?: boolean;
  cmdline_tools_ok: boolean;
  avd_count: number;
  avds: string[];
  avds_error?: string | null;
  has_online_emulator: boolean;
  studio_available: boolean;
  studio_path?: string | null;
  studio_configured_by?: string | null;
  studio_missing_sdk_ok?: boolean;
  suggested_sdk_path?: string | null;
  disk_free_gb?: number | null;
  disk_ok: boolean;
  templates: MobileAvdTemplate[];
  job: MobileAvdWizardJobStatus;
};

export async function getMobileAvdWizardCapabilities(): Promise<MobileAvdWizardCapabilitiesResponse> {
  const res = await fetch("/api/mobile/avd/wizard/capabilities");
  if (!res.ok) throw new Error(`No se pudo consultar el asistente AVD: ${res.status}`);
  return res.json();
}

export async function startMobileAvdWizard(templateId: string): Promise<{
  ok: boolean;
  started?: boolean;
  message?: string;
  status?: MobileAvdWizardJobStatus;
}> {
  const res = await fetch("/api/mobile/avd/wizard/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ template_id: templateId }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof (data as any)?.detail === "string" ? (data as any).detail : "No autorizado";
    throw new Error(detail);
  }
  return data;
}

export async function getMobileAvdWizardStatus(): Promise<{ ok: boolean; status: MobileAvdWizardJobStatus }> {
  const res = await fetch("/api/mobile/avd/wizard/status");
  if (!res.ok) throw new Error(`No se pudo consultar el estado AVD: ${res.status}`);
  return res.json();
}

export async function verifyMobileAvdInCatalog(avdName: string): Promise<{
  ok: boolean;
  avd_name?: string;
  avds?: string[];
  message?: string;
}> {
  const res = await fetch(
    `/api/mobile/avd/wizard/verify?avd_name=${encodeURIComponent(avdName)}`,
  );
  if (!res.ok) throw new Error("No se pudo verificar el catálogo AVD");
  return res.json();
}

export async function openMobileAndroidStudio(params?: {
  path?: string;
  save?: boolean;
}): Promise<{
  ok: boolean;
  message: string;
  hint?: string;
  path?: string;
  source?: string;
  searched_paths?: string[];
  sdk_ok?: boolean;
  settings_hint?: string;
}> {
  const res = await fetch("/api/mobile/avd/wizard/open-studio", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params ?? {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error("No se pudo abrir Android Studio");
  return data;
}

export type ToolPathEntryStatus = {
  label: string;
  kind: "file" | "dir";
  override?: string | null;
  detected?: string | null;
  detected_source?: string | null;
  effective?: string | null;
  effective_source?: string | null;
  ok: boolean;
  message: string;
};

export type ToolPathsStatusResponse = {
  ok: boolean;
  version: number;
  config_file: string;
  paths: Record<string, ToolPathEntryStatus>;
};

export async function getToolPathsStatus(): Promise<ToolPathsStatusResponse> {
  const res = await fetch("/api/settings/tool-paths");
  if (!res.ok) throw new Error(`No se pudo leer entorno local: ${res.status}`);
  return res.json();
}

export async function putToolPaths(paths: Record<string, string | null>): Promise<ToolPathsStatusResponse> {
  const res = await fetch("/api/settings/tool-paths", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paths }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof (data as any)?.detail === "string" ? (data as any).detail : "No se pudo guardar";
    throw new Error(detail);
  }
  return data;
}

export async function testToolPath(key: string, path?: string): Promise<{
  ok: boolean;
  key: string;
  path?: string;
  message: string;
}> {
  const res = await fetch("/api/settings/tool-paths/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, path }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error("No se pudo probar la ruta");
  return data;
}

export async function pickExecutable(title?: string): Promise<{
  ok: boolean;
  path?: string | null;
  message?: string;
}> {
  const res = await fetch("/api/system/pick-executable", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return res.json();
}

export type ToolPathsDiagnosticResponse = {
  ok: boolean;
  mobile: { ok: boolean; errors: string[]; warnings: string[]; items: unknown[] };
  chrome: { ok: boolean; path?: string | null; errors: string[] };
  tool_paths: ToolPathsStatusResponse;
};

export async function postToolPathsDiagnostic(): Promise<ToolPathsDiagnosticResponse> {
  const res = await fetch("/api/settings/tool-paths/diagnostic", { method: "POST" });
  if (!res.ok) throw new Error(`Diagnóstico falló: ${res.status}`);
  return res.json();
}

export async function pickDirectory(title?: string): Promise<{
  ok: boolean;
  path?: string | null;
  message?: string;
}> {
  const res = await fetch("/api/system/pick-directory", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return res.json();
}

export async function uploadDocs(files: File[]): Promise<{ ok: boolean; files: LoadedDoc[] }> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const res = await fetch("/api/req/upload-docs", { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function getScenarios(project?: string): Promise<{ scenarios: ScenarioRef[] }> {
  const url = project
    ? `/api/req/scenarios?project=${encodeURIComponent(project)}`
    : "/api/req/scenarios";
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch scenarios: ${res.status}`);
  return res.json();
}

export async function getRecordings(project?: string): Promise<{ recordings: RecordingRef[] }> {
  const url = project
    ? `/api/req/recordings?project=${encodeURIComponent(project)}`
    : "/api/req/recordings";
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch recordings: ${res.status}`);
  return res.json();
}

export type AiStatusResponse = {
  llama_cpp_python_available?: boolean;
  llama_cpp_python_version?: string | null;
  import_error?: string;
  model?: { path: string; exists: boolean; size_bytes: number; frozen: boolean };
  error?: string;
};

export async function getAiStatus(): Promise<AiStatusResponse> {
  const res = await fetch("/api/ai/status");
  if (!res.ok) {
    throw new Error(`Failed to fetch AI status: ${res.status}`);
  }
  return res.json();
}

export type AiMode = "auto" | "on" | "off";

export type AiPreferences = {
  mode: AiMode;
  version: number;
  memory_auto_learn?: boolean;
  memory_learn_after_retry?: boolean;
  gherkin_keywords_english?: boolean;
};

export type AiCapabilitiesResponse = {
  preferences: AiPreferences;
  capability: {
    model_ok: boolean;
    llama_ok: boolean;
    runtime_ok: boolean;
    ram_ok: boolean;
    ram_total_gb: number | null;
    ram_available_gb: number | null;
    ram_min_total_gb: number;
    ram_min_free_gb: number;
    profile?: string;
    runtime_profile?: string;
    capable: boolean;
    reasons: string[];
    model: {
      path: string;
      exists: boolean;
      size_bytes: number;
      frozen: boolean;
      profile?: string;
      models?: unknown[];
    };
  };
  resolution: {
    use_ai: boolean;
    mode: AiMode;
    capable: boolean;
    degraded: boolean;
    message: string;
    reasons: string[];
  };
  runtime: AiStatusResponse;
  setup?: AiSetupStatusResponse;
  brand_line: string;
};

export type AiSetupDownloadProfile = "auto" | "lite" | "standard";

export type AiSetupStatusResponse = {
  assigned_profile: string;
  models_root: string;
  lite_ready: boolean;
  standard_ready: boolean;
  lite_models: unknown[];
  standard_models: unknown[];
  download: AiDownloadStatusResponse;
  manifest_version: number;
  show_wizard?: boolean;
  wizard_completed?: boolean;
  profile_ready?: boolean;
  ram_total_gb?: number | null;
  ram_available_gb?: number | null;
  ram_min_free_gb?: number;
  ram_free_ok?: boolean;
  download_size_hint_gb?: number;
  wizard_state?: {
    completed?: boolean;
    completed_at?: string | null;
    version?: number;
  };
};

export type AiDownloadStatusResponse = {
  active: boolean;
  profile: string | null;
  current: string | null;
  completed: string[];
  errors: string[];
  done: boolean;
};

export async function getAiCapabilities(): Promise<AiCapabilitiesResponse> {
  const res = await fetch("/api/ai/capabilities");
  if (!res.ok) throw new Error(`Failed to fetch AI capabilities: ${res.status}`);
  return res.json();
}

export async function postAiSetupDownload(profile: "auto" | "lite" | "standard" = "auto"): Promise<{
  ok: boolean;
  started?: boolean;
  profile?: string;
  error?: string;
}> {
  const res = await fetch("/api/ai/setup/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile }),
  });
  if (!res.ok) throw new Error(`Failed to start model download: ${res.status}`);
  return res.json();
}

export async function getAiSetupDownloadStatus(): Promise<AiDownloadStatusResponse> {
  const res = await fetch("/api/ai/setup/download/status");
  if (!res.ok) throw new Error(`Failed to fetch download status: ${res.status}`);
  return res.json();
}

export async function postAiSetupVerify(profile: AiSetupDownloadProfile = "auto"): Promise<{
  profile: string;
  ok: boolean;
  models: unknown[];
}> {
  const res = await fetch("/api/ai/setup/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile }),
  });
  if (!res.ok) throw new Error(`Failed to verify models: ${res.status}`);
  return res.json();
}

export async function postAiSetupWizardComplete(): Promise<AiSetupStatusResponse> {
  const res = await fetch("/api/ai/setup/wizard/complete", { method: "POST" });
  if (!res.ok) throw new Error(`Failed to complete AI wizard: ${res.status}`);
  return res.json();
}

export type ChangelogEntry = {
  version: string;
  date: string | null;
  added: string[];
  fixed: string[];
  changed: string[];
};

export type AppAboutResponse = {
  app_name: string;
  version: string;
  version_display: string;
  developer: string;
  contact_email?: string | null;
  support_email?: string | null;
  tagline: string;
  license_text: string;
  changelog: ChangelogEntry[];
  beta_feedback_url?: string | null;
  local_logs_hint?: string | null;
  show_beta_disclaimer?: boolean;
};

export async function getAppAbout(): Promise<AppAboutResponse> {
  const res = await fetch("/api/app/about");
  if (!res.ok) throw new Error(`Failed to fetch app about: ${res.status}`);
  return res.json();
}

export async function putAiPreferences(
  patch: Partial<AiPreferences> & { mode?: AiMode },
): Promise<AiCapabilitiesResponse> {
  const res = await fetch("/api/ai/preferences", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to save AI preferences: ${res.status} ${text}`);
  }
  return res.json();
}

export type AiMemoryStatusResponse = {
  entries: number;
  max_entries: number;
  prompt_examples_limit: number;
  encrypted: boolean;
  updated_at: number | null;
  export_format: string;
};

export type AiMemoryEntryRow = {
  script_fp: string;
  ts: number;
  source: string;
  script_preview: string;
  feature_preview: string;
};

export type AiMemoryImportResponse = {
  ok: boolean;
  mode: string;
  added: number;
  updated: number;
  total: number;
};

export async function getAiMemoryStatus(): Promise<AiMemoryStatusResponse> {
  const res = await fetch("/api/ai/memory/status");
  if (!res.ok) throw new Error(`No se pudo leer el estado de memoria IA: ${res.status}`);
  return res.json();
}

export async function getAiMemoryEntries(): Promise<{ status: AiMemoryStatusResponse; entries: AiMemoryEntryRow[] }> {
  const res = await fetch("/api/ai/memory/entries");
  if (!res.ok) throw new Error(`No se pudo listar la memoria IA: ${res.status}`);
  return res.json();
}

export async function deleteAiMemoryEntry(scriptFp: string): Promise<{ ok: boolean; status: AiMemoryStatusResponse }> {
  const res = await fetch(`/api/ai/memory/entries/${encodeURIComponent(scriptFp)}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`No se pudo eliminar la entrada: ${res.status}`);
  return res.json();
}

export async function clearAiMemory(): Promise<{ ok: boolean; removed: number; status: AiMemoryStatusResponse }> {
  const res = await fetch("/api/ai/memory/clear", { method: "POST" });
  if (!res.ok) throw new Error(`No se pudo vaciar la memoria: ${res.status}`);
  return res.json();
}

export async function exportAiMemory(
  teamPassphrase: string,
): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch("/api/ai/memory/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ team_passphrase: teamPassphrase }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const detail = typeof (data as { detail?: string }).detail === "string" ? (data as { detail: string }).detail : "";
    throw new Error(detail || `No se pudo exportar la memoria: ${res.status}`);
  }
  const cd = res.headers.get("Content-Disposition") || "";
  const match = /filename="([^"]+)"/.exec(cd);
  const filename = match?.[1] || "elia_memory_team.enc";
  return { blob: await res.blob(), filename };
}

export async function importAiMemory(params: {
  teamPassphrase: string;
  mode: "merge" | "replace";
  file: File;
}): Promise<AiMemoryImportResponse> {
  const form = new FormData();
  form.append("team_passphrase", params.teamPassphrase);
  form.append("mode", params.mode);
  form.append("file", params.file);
  const res = await fetch("/api/ai/memory/import", { method: "POST", body: form });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof (data as { detail?: string }).detail === "string" ? (data as { detail: string }).detail : "";
    throw new Error(detail || `No se pudo importar la memoria: ${res.status}`);
  }
  return data as AiMemoryImportResponse;
}

export type LicenseStatusResponse = {
  ok: boolean;
  reason: string;
  activated: boolean;
  machine_fingerprint: string;
  message: string;
  can_run_jobs: boolean;
  expires_at?: number | null;
  duration_code?: string | null;
  tier?: string | null;
  tier_label?: string | null;
  is_beta?: boolean;
  upgrade_email?: string;
  features?: Record<string, boolean>;
};

export async function getLicenseStatus(): Promise<LicenseStatusResponse> {
  const res = await fetch("/api/license/status");
  if (!res.ok) {
    throw new Error(`Failed to fetch license: ${res.status}`);
  }
  return res.json();
}

export async function activateLicense(key: string): Promise<{ ok: boolean; message?: string }> {
  const res = await fetch("/api/license/activate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(`Failed to activate: ${res.status}`);
  }
  return data;
}

export async function getEliaConnectors(): Promise<EliaConnectorsDocument> {
  const res = await fetch("/api/elia/connectors");
  if (!res.ok) throw new Error(`Failed to fetch connectors: ${res.status}`);
  return res.json();
}

export async function putEliaConnectors(doc: EliaConnectorsDocument): Promise<{ ok: boolean }> {
  const res = await fetch("/api/elia/connectors", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(doc),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(`Failed to save connectors: ${res.status}`);
  }
  return data;
}

export async function testEliaConnector(params: {
  kind: "jira" | "value_edge" | "git" | "azure_devops" | "jira_xray";
  jira: EliaJiraCreds;
  value_edge: EliaValueEdgeCreds;
  git?: EliaGitCreds;
  azure_devops?: EliaAzureDevOpsCreds;
}): Promise<{ ok: boolean; connection_ok?: boolean; source?: string; message?: string }> {
  const res = await fetch("/api/elia/connectors/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      kind: params.kind,
      jira: params.jira,
      value_edge: params.value_edge,
      git: params.git ?? { provider: "github", repo_url: "", branch: "main", base_path: "features/", token: "" },
      azure_devops: params.azure_devops ?? {
        org: "",
        project: "",
        pat: "",
        default_work_item_id: "",
        target_field: "System.Description",
      },
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof (data as any)?.detail === "string" ? (data as any).detail : JSON.stringify(data);
    throw new Error(`Prueba fallida (${res.status}): ${detail}`);
  }
  return data;
}

export type BddPublishRequest = {
  target: BddPublishTarget;
  profile_id: string;
  gherkin_text: string;
  feature_name?: string;
  issue_key?: string;
  requirement_id?: string;
  work_item_id?: string;
  file_path?: string;
  branch?: string;
  commit_message?: string;
  output_dir?: string;
};

export async function publishBddFeature(body: BddPublishRequest): Promise<{
  ok: boolean;
  target: BddPublishTarget;
  message: string;
  external_id?: string;
  url?: string;
}> {
  const res = await fetch("/api/req/publish", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof (data as any)?.detail === "string" ? (data as any).detail : JSON.stringify(data);
    throw new Error(detail || `Publicación fallida (${res.status})`);
  }
  return data as {
    ok: boolean;
    target: BddPublishTarget;
    message: string;
    external_id?: string;
    url?: string;
  };
}

export async function testReqPublishTarget(params: {
  target: BddPublishTarget;
  profile_id: string;
}): Promise<{ ok: boolean; message: string }> {
  const res = await fetch("/api/req/publish/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof (data as any)?.detail === "string" ? (data as any).detail : JSON.stringify(data);
    throw new Error(detail || `Prueba fallida (${res.status})`);
  }
  return data as { ok: boolean; message: string };
}

export async function getJob(jobId: string): Promise<JobStateResponse> {
  const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch job: ${res.status}`);
  }
  return res.json();
}

export type JobEventRecord = {
  type: string;
  ts?: number;
  prompt_id?: string;
  prompt_type?: string;
  message?: string;
  payload?: Record<string, unknown>;
};

export async function getJobEvents(
  jobId: string,
  since = 0,
): Promise<{ job_id: string; events: JobEventRecord[]; next_index: number }> {
  const res = await fetch(
    `/api/jobs/${encodeURIComponent(jobId)}/events?since=${encodeURIComponent(String(since))}`,
  );
  if (!res.ok) {
    throw new Error(`Failed to fetch job events: ${res.status}`);
  }
  return res.json();
}

/** Descarga el reporte de error sanitizado (.txt) para un job en estado error. */
export async function downloadJobErrorReport(jobId: string): Promise<void> {
  const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/error-report`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `No se pudo descargar el reporte: ${res.status}`);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^";\n]+)"?/i.exec(disposition);
  const filename = match?.[1] ?? `elia_error_${jobId.slice(0, 8)}.txt`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function stopRecording(jobId: string): Promise<void> {
  const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/stop-recording`, {
    method: "POST",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`No se pudo finalizar la grabación: ${res.status} ${text}`);
  }
}

export async function sendPromptResponse(params: {
  jobId: string;
  promptId: string;
  answer: any;
}): Promise<void> {
  const res = await fetch(
    `/api/jobs/${encodeURIComponent(params.jobId)}/prompts/${encodeURIComponent(params.promptId)}/response`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer: params.answer }),
    },
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to send response: ${res.status} ${text}`);
  }
}

export async function getApiScriptsGuide(): Promise<{ title: string; content: string }> {
  const res = await fetch("/api/api/scripts-guide");
  if (!res.ok) throw new Error(`No se pudo cargar la guía de scripts: ${res.status}`);
  return res.json();
}

export async function getApiProjects(): Promise<{ projects: string[] }> {
  const res = await fetch("/api/api/projects");
  if (!res.ok) throw new Error(`Failed to list API projects: ${res.status}`);
  return res.json();
}

export async function createApiProject(name: string): Promise<{ ok: boolean; project: string }> {
  const res = await fetch(`/api/api/projects/${encodeURIComponent(name)}`, { method: "POST" });
  if (!res.ok) throw new Error(`Failed to create API project: ${res.status}`);
  return res.json();
}

export async function getApiScenarios(project: string): Promise<{
  scenarios: { id: string; name: string; path: string; collection_id: string; collection_name: string }[];
  collections: { id: string; name: string; scenario_count: number; source?: string }[];
}> {
  const res = await fetch(`/api/api/projects/${encodeURIComponent(project)}/scenarios`);
  if (!res.ok) throw new Error(`Failed to list scenarios: ${res.status}`);
  return res.json();
}

export async function deleteApiCollection(
  project: string,
  collectionId: string,
): Promise<{ ok: boolean; collection_id: string; deleted_scenarios: number }> {
  const res = await fetch(
    `/api/api/projects/${encodeURIComponent(project)}/collections/${encodeURIComponent(collectionId)}`,
    { method: "DELETE" },
  );
  if (!res.ok) throw new Error(`Failed to delete collection: ${res.status}`);
  return res.json();
}

export async function getApiTrafficCaptures(
  project: string,
): Promise<{ captures: { id: string; name: string; path: string }[] }> {
  const res = await fetch(`/api/api/projects/${encodeURIComponent(project)}/traffic-captures`);
  if (!res.ok) throw new Error(`Failed to list traffic captures: ${res.status}`);
  return res.json();
}

export async function importApiTrafficCapture(
  project: string,
  captureId: string,
): Promise<{ ok: boolean; scenario_ids: string[]; count: number; imported: number; skipped: number }> {
  const res = await fetch(`/api/api/projects/${encodeURIComponent(project)}/import-traffic`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ capture_id: captureId }),
  });
  if (!res.ok) throw new Error(`Failed to import traffic capture: ${res.status}`);
  return res.json();
}

export async function saveApiScenario(body: {
  project: string;
  scenario: Record<string, unknown>;
  scenario_id?: string;
  collection_id?: string;
}): Promise<{ ok: boolean; scenario_id: string }> {
  const res = await fetch("/api/api/scenarios", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to save scenario: ${res.status}`);
  return res.json();
}

export async function deleteApiScenario(
  project: string,
  scenarioId: string,
): Promise<{ ok: boolean; scenario_id: string }> {
  const res = await fetch(
    `/api/api/projects/${encodeURIComponent(project)}/scenarios/${encodeURIComponent(scenarioId)}`,
    { method: "DELETE" },
  );
  if (!res.ok) throw new Error(`Failed to delete scenario: ${res.status}`);
  return res.json();
}

export async function deleteApiScenarios(body: {
  project: string;
  scenario_ids: string[];
}): Promise<{ ok: boolean; deleted: number }> {
  const res = await fetch("/api/api/scenarios/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to delete scenarios: ${res.status}`);
  return res.json();
}

export async function getLoadTestProfiles(): Promise<{ profiles: { id: string; label: string }[] }> {
  const res = await fetch("/api/api/load-test/profiles");
  if (!res.ok) throw new Error(`Failed to list load profiles: ${res.status}`);
  return res.json();
}

export async function convertApiScenarios(body: {
  project: string;
  traffic_path?: string;
  scenario_ids?: string[];
  feature_name?: string;
}): Promise<{ ok: boolean; feature_file: string }> {
  const res = await fetch("/api/api/convert", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to convert API scenarios: ${res.status}`);
  return res.json();
}

export async function startTestRun(body: {
  platform?: string;
  project: string;
  kind?: string;
  feature_file?: string;
  generate_evidence?: boolean;
  headless?: boolean;
  locust_users?: number;
  locust_spawn_rate?: number;
  locust_run_time?: string;
  locust_host?: string;
}): Promise<{ run_id: string }> {
  const res = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      platform: body.platform ?? "api",
      project: body.project,
      kind: body.kind ?? "behave",
      feature_file: body.feature_file,
      generate_evidence: true,
      headless: body.headless ?? true,
      locust_users: body.locust_users,
      locust_spawn_rate: body.locust_spawn_rate,
      locust_run_time: body.locust_run_time,
      locust_host: body.locust_host,
    }),
  });
  if (!res.ok) throw new Error(`Failed to start run: ${res.status}`);
  return res.json();
}

export async function startUnifiedRun(body: {
  platform: string;
  project: string;
  kind: "behave" | "locust";
  feature_file?: string;
  generate_evidence?: boolean;
  headless?: boolean;
  locust_users?: number;
  locust_spawn_rate?: number;
  locust_run_time?: string;
  locust_host?: string;
}): Promise<{ run_id: string }> {
  return startTestRun(body);
}

export async function getPlatformProjects(platform: string): Promise<{ projects: string[] }> {
  const res = await fetch(`/api/projects/${encodeURIComponent(platform)}`);
  if (!res.ok) throw new Error(`Failed to list projects: ${res.status}`);
  return res.json();
}

export async function openEliaLogsFolder(): Promise<{ ok: boolean; path: string }> {
  const res = await fetch("/api/app/open-logs-folder", { method: "POST" });
  if (!res.ok) throw new Error(`Failed to open logs folder: ${res.status}`);
  return res.json();
}

export async function listProjectFiles(
  platform: string,
  project: string,
  advanced = false,
): Promise<{ files: { path: string; name: string; size: number }[] }> {
  const params = advanced ? "?advanced=true" : "";
  const res = await fetch(
    `/api/projects/${encodeURIComponent(platform)}/${encodeURIComponent(project)}/files${params}`,
  );
  if (res.status === 404) return { files: [] };
  if (!res.ok) throw new Error(`Failed to list files: ${res.status}`);
  return res.json();
}

export async function readProjectFile(
  platform: string,
  project: string,
  path: string,
): Promise<{ path: string; content: string }> {
  const res = await fetch(
    `/api/projects/${encodeURIComponent(platform)}/${encodeURIComponent(project)}/file?path=${encodeURIComponent(path)}`,
  );
  if (!res.ok) throw new Error(`Failed to read file: ${res.status}`);
  return res.json();
}

export async function writeProjectFile(
  platform: string,
  project: string,
  path: string,
  content: string,
): Promise<{ ok: boolean }> {
  const res = await fetch(
    `/api/projects/${encodeURIComponent(platform)}/${encodeURIComponent(project)}/file?path=${encodeURIComponent(path)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    },
  );
  if (!res.ok) throw new Error(`Failed to write file: ${res.status}`);
  return res.json();
}

export async function getTestRun(runId: string): Promise<{
  run_id: string;
  state: string;
  return_code: number | null;
  lines: string[];
  artifacts?: Array<{ kind: string; name: string; path: string; absolute_path?: string }>;
  platform?: string;
  project?: string;
  project_path?: string;
}> {
  const res = await fetch(`/api/runs/${encodeURIComponent(runId)}`);
  if (!res.ok) throw new Error(`Failed to get run: ${res.status}`);
  return res.json();
}

export function getProjectReportUrl(platform: string, project: string, filename: string): string {
  const params = new URLSearchParams({ name: filename });
  return `/api/projects/${encodeURIComponent(platform)}/${encodeURIComponent(project)}/reports/file?${params.toString()}`;
}

export function getProjectEvidenceUrl(platform: string, project: string, filename: string): string {
  const params = new URLSearchParams({ name: filename });
  return `/api/projects/${encodeURIComponent(platform)}/${encodeURIComponent(project)}/evidences/file?${params.toString()}`;
}

export async function openProjectFolder(
  platform: string,
  project: string,
  subpath = "outputs/pdfReports",
): Promise<{ ok: boolean; path: string }> {
  const res = await fetch(
    `/api/projects/${encodeURIComponent(platform)}/${encodeURIComponent(project)}/open-folder`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subpath }),
    },
  );
  if (!res.ok) throw new Error(`Failed to open folder: ${res.status}`);
  return res.json();
}

export async function listProjectReports(
  platform: string,
  project: string,
): Promise<{ reports: Array<{ name: string; path: string; absolute_path?: string }>; folder: string }> {
  const res = await fetch(
    `/api/projects/${encodeURIComponent(platform)}/${encodeURIComponent(project)}/reports`,
  );
  if (!res.ok) throw new Error(`Failed to list reports: ${res.status}`);
  return res.json();
}

export async function runLoadTest(body: {
  project: string;
  users: number;
  spawn_rate: number;
  run_time: string;
  host?: string;
  scenario_ids?: string[];
  scenario_weights?: Record<string, number>;
  collect_metrics?: boolean;
  flow_id?: string;
  run_setup_flow?: boolean;
  environment?: string;
  think_time?: Record<string, unknown>;
  stages?: Array<Record<string, unknown>>;
  processes?: number;
  sla?: Record<string, unknown>;
  mode?: string;
  master_host?: string;
  master_port?: number;
  expect_workers?: number;
  profile?: string;
  data_file?: string;
}): Promise<{
  run_id: string;
  locustfile: string;
  scenario_count?: number;
  flow?: boolean;
  flow_node_counts?: Record<string, number>;
  setup_sql?: boolean;
  profile?: string;
  run_time?: string;
  mode?: string;
  command?: string[];
}> {
  const res = await fetch("/api/api/load-test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to start load test: ${res.status}`);
  return res.json();
}

export async function runApiSuite(body: {
  project: string;
  environment?: string;
  scenario_ids?: string[];
  flow_id?: string;
  flow?: Record<string, unknown>;
  continue_on_failure?: boolean;
  data_file?: string;
}): Promise<{
  ok: boolean;
  passed_steps: number;
  failed_steps: number;
  iterations: number;
  runs: Array<{ ok: boolean; steps: Array<{ name: string; ok: boolean; type?: string; branch?: string }> }>;
}> {
  const res = await fetch("/api/api/run-suite", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to run API suite: ${res.status}`);
  return res.json();
}

export async function getApiDataFiles(project: string): Promise<{ files: { name: string; path: string }[] }> {
  const res = await fetch(`/api/api/projects/${encodeURIComponent(project)}/data-files`);
  if (!res.ok) throw new Error(`Failed to list data files: ${res.status}`);
  return res.json();
}

export async function saveApiDataFile(body: {
  project: string;
  filename: string;
  content: string;
}): Promise<{ ok: boolean; path: string }> {
  const res = await fetch("/api/api/data-files", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to save data file: ${res.status}`);
  return res.json();
}

export async function getLoadTestMetrics(runId: string): Promise<{
  run_id: string;
  state: string;
  metrics: {
    live: {
      total_requests: number;
      total_failures: number;
      error_rate_pct: number;
      current_rps: number;
      avg_ms: number;
      p50_ms: number;
      p95_ms: number;
      p99_ms: number;
    };
    csv: Record<string, unknown>;
  };
  sla?: {
    ok: boolean;
    checks: Array<{ metric: string; threshold: unknown; actual: number; passed: boolean }>;
  } | null;
}> {
  const res = await fetch(`/api/api/load-test/${encodeURIComponent(runId)}/metrics`);
  if (!res.ok) throw new Error(`Failed to get load metrics: ${res.status}`);
  return res.json();
}

export async function getApiProjectConfig(project: string): Promise<{
  default_environment: string;
  global_headers: Record<string, string>;
}> {
  const res = await fetch(`/api/api/projects/${encodeURIComponent(project)}/config`);
  if (!res.ok) throw new Error(`Failed to load API project config: ${res.status}`);
  return res.json();
}

export async function saveApiProjectConfig(
  project: string,
  body: { default_environment: string; global_headers: Record<string, string> },
): Promise<{ ok: boolean }> {
  const res = await fetch(`/api/api/projects/${encodeURIComponent(project)}/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to save API project config: ${res.status}`);
  return res.json();
}

export async function getApiEnvironments(project: string): Promise<{ environments: string[] }> {
  const res = await fetch(`/api/api/projects/${encodeURIComponent(project)}/environments`);
  if (!res.ok) throw new Error(`Failed to list environments: ${res.status}`);
  return res.json();
}

export async function getApiEnvironment(
  project: string,
  envName: string,
): Promise<{ name: string; variables: Record<string, string> }> {
  const res = await fetch(
    `/api/api/projects/${encodeURIComponent(project)}/environments/${encodeURIComponent(envName)}`,
  );
  if (!res.ok) throw new Error(`Failed to load environment: ${res.status}`);
  return res.json();
}

export async function saveApiEnvironment(
  project: string,
  envName: string,
  body: { name: string; variables: Record<string, string> },
): Promise<{ ok: boolean }> {
  const res = await fetch(
    `/api/api/projects/${encodeURIComponent(project)}/environments/${encodeURIComponent(envName)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  if (!res.ok) throw new Error(`Failed to save environment: ${res.status}`);
  return res.json();
}

export async function getApiScenarioDetail(
  project: string,
  scenarioId: string,
): Promise<{ scenario: Record<string, unknown> }> {
  const res = await fetch(
    `/api/api/projects/${encodeURIComponent(project)}/scenarios/${encodeURIComponent(scenarioId)}`,
  );
  if (!res.ok) throw new Error(`Failed to load scenario: ${res.status}`);
  return res.json();
}

export async function executeApiRequest(body: {
  project: string;
  environment?: string;
  request: Record<string, unknown>;
}): Promise<{
  ok: boolean;
  status_code: number;
  headers: Record<string, string>;
  body: string;
  elapsed_ms: number;
  assertions: Array<{ kind: string; passed: boolean; message: string }>;
  environment?: string;
  variables?: Record<string, string>;
  script_logs?: string[];
}> {
  const res = await fetch("/api/api/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to execute API request: ${res.status}`);
  }
  return res.json();
}

export async function importPostmanCollection(body: {
  project: string;
  collection: Record<string, unknown>;
}): Promise<{
  ok: boolean;
  count: number;
  scenario_ids: string[];
  collection_id?: string;
  collection_name?: string;
  variables_imported?: number;
}> {
  const res = await fetch("/api/api/import/postman", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to import collection: ${res.status}`);
  return res.json();
}

export async function importOpenApiSpec(body: {
  project: string;
  spec: Record<string, unknown>;
}): Promise<{
  ok: boolean;
  count: number;
  scenario_ids: string[];
  collection_id?: string;
  collection_name?: string;
}> {
  const res = await fetch("/api/api/import/openapi", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to import OpenAPI spec: ${res.status}`);
  return res.json();
}

export async function exportApiRequestEvidence(body: {
  project: string;
  environment?: string;
  request: Record<string, unknown>;
  result: Record<string, unknown>;
  format: "pdf" | "json";
}): Promise<{ ok: boolean; filename: string; path: string }> {
  const res = await fetch("/api/api/export/request-evidence", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to export request evidence: ${res.status}`);
  return res.json();
}

export async function exportApiLoadEvidence(body: {
  project: string;
  run_id: string;
  users?: number;
  run_time?: string;
  host?: string;
  scenario_count?: number;
  format?: "pdf" | "html" | "basic";
  enriched?: boolean;
}): Promise<{ ok: boolean; filename: string; path: string; format?: string }> {
  const res = await fetch("/api/api/export/load-evidence", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enriched: true, format: "pdf", ...body }),
  });
  if (!res.ok) throw new Error(`Failed to export load evidence: ${res.status}`);
  return res.json();
}

export async function exportApiSuiteEvidence(body: {
  project: string;
  environment?: string;
  suite: Record<string, unknown>;
  name?: string;
  format: "pdf" | "json";
}): Promise<{ ok: boolean; filename: string; path: string }> {
  const res = await fetch("/api/api/export/suite-evidence", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to export suite evidence: ${res.status}`);
  return res.json();
}

export type ApiDriverCapabilities = {
  sql: Record<string, boolean>;
  grpc: { available: boolean; missing: string[] };
  install_hint: string;
};

export async function getApiDriverCapabilities(): Promise<ApiDriverCapabilities> {
  const res = await fetch("/api/api/capabilities/drivers");
  if (!res.ok) throw new Error(`Failed to fetch driver capabilities: ${res.status}`);
  return res.json();
}

export async function listApiFlows(project: string): Promise<{ flows: { id: string; name: string; path: string }[] }> {
  const res = await fetch(`/api/api/projects/${encodeURIComponent(project)}/flows`);
  if (!res.ok) throw new Error(`Failed to list flows: ${res.status}`);
  return res.json();
}

export async function getApiFlow(
  project: string,
  flowId: string,
): Promise<{ flow: Record<string, unknown> }> {
  const res = await fetch(
    `/api/api/projects/${encodeURIComponent(project)}/flows/${encodeURIComponent(flowId)}`,
  );
  if (!res.ok) throw new Error(`Failed to load flow: ${res.status}`);
  return res.json();
}

export async function saveApiFlow(body: {
  project: string;
  flow: Record<string, unknown>;
  flow_id?: string;
}): Promise<{ ok: boolean; flow_id: string }> {
  const res = await fetch("/api/api/flows", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to save flow: ${res.status}`);
  return res.json();
}

export async function sqlPreflight(body: {
  project: string;
  environment?: string;
  sql: Record<string, unknown>;
}): Promise<{ ok: boolean; result: Record<string, unknown>; environment: string }> {
  const res = await fetch("/api/api/sql/preflight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed SQL preflight: ${res.status}`);
  return res.json();
}

export async function grpcPreflight(body: {
  project: string;
  environment?: string;
  grpc: Record<string, unknown>;
}): Promise<{ ok: boolean; result: Record<string, unknown>; environment: string }> {
  const res = await fetch("/api/api/grpc/preflight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed gRPC preflight: ${res.status}`);
  return res.json();
}

export async function getApiLoadHistory(
  project: string,
): Promise<{ runs: Array<Record<string, unknown>> }> {
  const res = await fetch(`/api/api/projects/${encodeURIComponent(project)}/load-history`);
  if (!res.ok) throw new Error(`Failed to list load history: ${res.status}`);
  return res.json();
}

export async function saveApiLoadSnapshot(body: {
  project: string;
  run_id: string;
  users?: number;
  run_time?: string;
  host?: string;
  scenario_count?: number;
  profile?: string;
  sla?: Record<string, unknown>;
}): Promise<{ ok: boolean; history_id: string }> {
  const res = await fetch("/api/api/load-history/snapshot", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to save load snapshot: ${res.status}`);
  return res.json();
}

export async function compareApiLoadRuns(body: {
  project: string;
  run_a: string;
  run_b: string;
}): Promise<{ run_a: Record<string, unknown>; run_b: Record<string, unknown>; delta: Record<string, { a: number; b: number; diff: number }> }> {
  const res = await fetch("/api/api/load-history/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to compare load runs: ${res.status}`);
  return res.json();
}

export async function syncApiEnvironmentFromWeb(
  project: string,
  envName: string,
): Promise<{ ok: boolean; base_url: string; origin: string }> {
  const res = await fetch(
    `/api/api/projects/${encodeURIComponent(project)}/environments/${encodeURIComponent(envName)}/sync-from-web`,
    { method: "POST" },
  );
  if (!res.ok) throw new Error(`Failed to sync environment from web: ${res.status}`);
  return res.json();
}

export async function getApiWebOrigin(project: string): Promise<{ origin: string | null; available: boolean }> {
  const res = await fetch(`/api/api/projects/${encodeURIComponent(project)}/web-origin`);
  if (!res.ok) throw new Error(`Failed to get web origin: ${res.status}`);
  return res.json();
}

export async function cloneApiScenario(
  project: string,
  scenarioId: string,
): Promise<{ ok: boolean; scenario_id: string }> {
  const res = await fetch(
    `/api/api/projects/${encodeURIComponent(project)}/scenarios/${encodeURIComponent(scenarioId)}/clone`,
    { method: "POST" },
  );
  if (!res.ok) throw new Error(`Failed to clone scenario: ${res.status}`);
  return res.json();
}

export async function getApiSuiteHistory(
  project: string,
): Promise<{ runs: Array<Record<string, unknown>> }> {
  const res = await fetch(`/api/api/projects/${encodeURIComponent(project)}/suite-history`);
  if (!res.ok) throw new Error(`Failed to list suite history: ${res.status}`);
  return res.json();
}

export async function getApiSuiteProgress(
  project: string,
): Promise<{ progress: Record<string, unknown> | null }> {
  const res = await fetch(`/api/api/projects/${encodeURIComponent(project)}/suite-progress`);
  if (!res.ok) throw new Error(`Failed to get suite progress: ${res.status}`);
  return res.json();
}

export async function loadPreflightApi(body: {
  mode?: string;
  master_host?: string;
  master_port?: number;
}): Promise<{ ok: boolean; checks: Array<{ id: string; ok: boolean; message: string }>; mode: string }> {
  const res = await fetch("/api/api/load-preflight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed load preflight: ${res.status}`);
  return res.json();
}

export async function exportLoadHistoryReport(body: {
  project: string;
  history_id: string;
  format?: "pdf" | "html";
}): Promise<{ ok: boolean; filename: string; path: string; format?: string }> {
  const res = await fetch("/api/api/load-history/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to export load history report: ${res.status}`);
  return res.json();
}

