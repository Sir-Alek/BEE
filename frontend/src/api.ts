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
    // ELIA
    | "elia_jira_smoke"
    | "elia_value_edge_smoke"
    | "elia_gherkin_batch";
  url?: string;
  use_ai?: boolean;
  elia_use_inline_connectors?: boolean;
  elia_jira?: EliaJiraCreds;
  elia_value_edge?: EliaValueEdgeCreds;
  // Mobile
  platform?: string;
  apk_path?: string;
  device_id?: string;
  // Legacy
  window_name?: string;
  exe_path?: string;
  // Doc-to-BDD
  doc_files?: string[];
  link_recording?: string;
  link_scenario?: string;
  link_scenario_by_doc?: Record<string, string>;
  link_recording_by_doc?: Record<string, string>;
}): Promise<{ job_id: string }> {
  const {
    mode, url, use_ai, elia_use_inline_connectors, elia_jira, elia_value_edge,
    platform, apk_path, device_id, window_name, exe_path,
    doc_files, link_recording, link_scenario, link_scenario_by_doc, link_recording_by_doc,
  } = params;
  const res = await fetch("/api/jobs/convert", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      mode,
      url,
      use_ai: use_ai ?? false,
      ...(elia_use_inline_connectors != null ? { elia_use_inline_connectors } : {}),
      ...(elia_jira != null ? { elia_jira } : {}),
      ...(elia_value_edge != null ? { elia_value_edge } : {}),
      ...(platform != null ? { platform } : {}),
      ...(apk_path != null ? { apk_path } : {}),
      ...(device_id != null ? { device_id } : {}),
      ...(window_name != null ? { window_name } : {}),
      ...(exe_path != null ? { exe_path } : {}),
      ...(doc_files != null ? { doc_files } : {}),
      ...(link_recording != null ? { link_recording } : {}),
      ...(link_scenario != null ? { link_scenario } : {}),
      ...(link_scenario_by_doc != null ? { link_scenario_by_doc } : {}),
      ...(link_recording_by_doc != null ? { link_recording_by_doc } : {}),
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to start job: ${res.status} ${text}`);
  }
  return res.json();
}

export async function getModulesStatus(): Promise<ModulesStatus> {
  const res = await fetch("/api/modules/status");
  if (!res.ok) throw new Error(`Failed to fetch modules: ${res.status}`);
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

export type LicenseStatusResponse = {
  ok: boolean;
  reason: string;
  demo_days_left: number | null;
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

