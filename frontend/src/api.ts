import type {
  EliaConnectorsDocument,
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

export type AiCapabilitiesResponse = {
  preferences: { mode: AiMode; version: number };
  capability: {
    model_ok: boolean;
    llama_ok: boolean;
    runtime_ok: boolean;
    ram_ok: boolean;
    ram_total_gb: number | null;
    ram_available_gb: number | null;
    ram_min_total_gb: number;
    ram_min_free_gb: number;
    capable: boolean;
    reasons: string[];
    model: { path: string; exists: boolean; size_bytes: number; frozen: boolean };
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
  brand_line: string;
};

export async function getAiCapabilities(): Promise<AiCapabilitiesResponse> {
  const res = await fetch("/api/ai/capabilities");
  if (!res.ok) throw new Error(`Failed to fetch AI capabilities: ${res.status}`);
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
};

export async function getAppAbout(): Promise<AppAboutResponse> {
  const res = await fetch("/api/app/about");
  if (!res.ok) throw new Error(`Failed to fetch app about: ${res.status}`);
  return res.json();
}

export async function putAiPreferences(mode: AiMode): Promise<AiCapabilitiesResponse> {
  const res = await fetch("/api/ai/preferences", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
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
  encrypted: boolean;
  updated_at: number | null;
  export_format: string;
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
  kind: "jira" | "value_edge";
  jira: EliaJiraCreds;
  value_edge: EliaValueEdgeCreds;
}): Promise<{ ok: boolean; connection_ok?: boolean; source?: string }> {
  const res = await fetch("/api/elia/connectors/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof (data as any)?.detail === "string" ? (data as any).detail : JSON.stringify(data);
    throw new Error(`Prueba fallida (${res.status}): ${detail}`);
  }
  return data;
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

export async function getApiScenarios(project: string): Promise<{ scenarios: { id: string; name: string; path: string }[] }> {
  const res = await fetch(`/api/api/projects/${encodeURIComponent(project)}/scenarios`);
  if (!res.ok) throw new Error(`Failed to list scenarios: ${res.status}`);
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
): Promise<{ ok: boolean; scenario_ids: string[]; count: number }> {
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
}): Promise<{ ok: boolean; scenario_id: string }> {
  const res = await fetch("/api/api/scenarios", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to save scenario: ${res.status}`);
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
  project: string;
  kind?: string;
  feature_file?: string;
}): Promise<{ run_id: string }> {
  const res = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to start run: ${res.status}`);
  return res.json();
}

export async function getTestRun(runId: string): Promise<{
  run_id: string;
  state: string;
  return_code: number | null;
  lines: string[];
}> {
  const res = await fetch(`/api/runs/${encodeURIComponent(runId)}`);
  if (!res.ok) throw new Error(`Failed to get run: ${res.status}`);
  return res.json();
}

export async function runLoadTest(body: {
  project: string;
  users: number;
  spawn_rate: number;
  run_time: string;
  host?: string;
}): Promise<{ run_id: string; locustfile: string }> {
  const res = await fetch("/api/api/load-test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to start load test: ${res.status}`);
  return res.json();
}

