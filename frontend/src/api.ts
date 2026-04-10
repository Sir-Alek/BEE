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
  mode: "demo" | "puppeteer_to_behave" | "puppeteer_to_step_by_step" | "puppeteer_recorder";
  url?: string;
  use_ai?: boolean;
}): Promise<{ job_id: string }> {
  const { mode, url, use_ai } = params;
  const res = await fetch("/api/jobs/convert", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, url, use_ai: use_ai ?? false }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to start job: ${res.status} ${text}`);
  }
  return res.json();
}

export type AiStatusResponse = {
  llama_cli_configured?: boolean;
  llama_cli_path?: string | null;
  llama_cli_on_path?: boolean;
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

