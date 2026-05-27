import type { APIRequestContext } from "@playwright/test";

type PromptShape = {
  prompt_id?: string;
  type?: string;
  title?: string;
};

function answerForPrompt(
  prompt: PromptShape,
  options: {
    projectName: string;
    fileName: string;
    recordVideo: boolean;
    captureApi: boolean;
    preferNewProject: boolean;
  },
): string | boolean | Record<string, boolean> | null {
  const title = prompt.title ?? "";
  const type = prompt.type ?? "";

  if (type === "input_text" && /Proyecto/i.test(title)) {
    return options.projectName;
  }
  if (type === "input_text" && /Archivo|grabaci/i.test(title)) {
    return options.fileName;
  }
  if (type === "yes_no" && /proyecto nuevo|selecci/i.test(title)) {
    return options.preferNewProject;
  }
  if (type === "pick_project") {
    return options.projectName;
  }
  if (type === "yes_no_cancel") {
    return true;
  }
  if (type === "recording_options") {
    return { video: options.recordVideo, capture_api: options.captureApi };
  }
  if (type === "yes_no") {
    return options.recordVideo;
  }
  return null;
}

/** Responde prompts de puppeteer_recorder según tipo (proyecto nuevo o existente). */
export async function answerPuppeteerRecorderPrompts(
  request: APIRequestContext,
  jobId: string,
  options?: {
    projectName?: string;
    fileName?: string;
    recordVideo?: boolean;
    captureApi?: boolean;
    preferNewProject?: boolean;
    timeoutMs?: number;
  },
): Promise<void> {
  const opts = {
    projectName: options?.projectName ?? "E2EProyecto",
    fileName: options?.fileName ?? "grabacion_e2e.js",
    recordVideo: options?.recordVideo ?? false,
    captureApi: options?.captureApi ?? false,
    preferNewProject: options?.preferNewProject ?? true,
    timeoutMs: options?.timeoutMs ?? 90_000,
  };

  const deadline = Date.now() + opts.timeoutMs;
  const answered = new Set<string>();

  while (Date.now() < deadline) {
    const res = await request.get(`/api/jobs/${jobId}`);
    const job = await res.json();
    if (job.state === "done") return;
    if (job.state === "error") {
      throw new Error(`job ${jobId} error: ${JSON.stringify(job.error)}`);
    }
    if (job.state === "cancelled") {
      throw new Error(`job ${jobId} was cancelled`);
    }

    const prompt = job.active_prompt as PromptShape | null | undefined;
    const pid = prompt?.prompt_id;
    if (pid && !answered.has(pid)) {
      const answer = answerForPrompt(prompt, opts);
      if (answer !== null) {
        await request.post(`/api/jobs/${jobId}/prompts/${pid}/response`, {
          data: { answer },
        });
        answered.add(pid);
      }
    }
    await new Promise((r) => setTimeout(r, 120));
  }

  const final = await request.get(`/api/jobs/${jobId}`);
  const job = await final.json();
  if (job.state !== "done") {
    throw new Error(`job ${jobId} did not finish: state=${job.state}`);
  }
}

export async function startPuppeteerRecorderJob(
  request: APIRequestContext,
  url: string,
): Promise<string> {
  const res = await request.post("/api/jobs/convert", {
    data: { mode: "puppeteer_recorder", url },
  });
  if (!res.ok()) throw new Error(`recorder job failed: ${res.status()} ${await res.text()}`);
  const body = await res.json();
  return body.job_id as string;
}
