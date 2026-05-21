import { execFileSync } from "child_process";
import path from "path";
import type { APIRequestContext } from "@playwright/test";

const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");
const E2E_ROOT = path.resolve(__dirname, "..");

export type LicenseStatus = {
  ok: boolean;
  can_run_jobs: boolean;
  machine_fingerprint: string;
  activated: boolean;
  reason: string;
};

function pythonExe(): string {
  return process.platform === "win32"
    ? path.join(REPO_ROOT, ".venv", "Scripts", "python.exe")
    : path.join(REPO_ROOT, ".venv", "bin", "python");
}

function e2eEnv(): NodeJS.ProcessEnv {
  const runtime = path.join(E2E_ROOT, ".runtime");
  return {
    ...process.env,
    LOCALAPPDATA: path.join(runtime, "LocalAppData"),
    TEMP: path.join(runtime, "Temp"),
    TMP: path.join(runtime, "Temp"),
    ELIA_USER_DATA: path.join(runtime, "UserData"),
    ELIA_SKIP_LICENSE: "",
  };
}

function scriptsDir(): string {
  return path.join(E2E_ROOT, "scripts");
}

export async function fetchLicenseStatus(request: APIRequestContext): Promise<LicenseStatus> {
  const res = await request.get("/api/license/status");
  if (!res.ok()) throw new Error(`license status ${res.status}`);
  return res.json();
}

export function generateActivationKey(fingerprint: string): string {
  return execFileSync(
    pythonExe(),
    [path.join(scriptsDir(), "e2e_generate_license.py"), fingerprint],
    { encoding: "utf-8", env: e2eEnv() },
  ).trim();
}

export function revokeLicenseE2E(): void {
  execFileSync(pythonExe(), [path.join(scriptsDir(), "e2e_revoke_license.py")], {
    env: e2eEnv(),
  });
}

export async function activateLicenseViaApi(
  request: APIRequestContext,
  key: string,
): Promise<void> {
  const res = await request.post("/api/license/activate", { data: { key } });
  if (!res.ok()) throw new Error(`activate failed: ${res.status()} ${await res.text()}`);
  const body = await res.json();
  if (!body.ok) throw new Error(`activate rejected: ${body.message ?? "unknown"}`);
}

export async function ensureLicensed(request: APIRequestContext): Promise<void> {
  const st = await fetchLicenseStatus(request);
  if (st.can_run_jobs) return;
  const key = generateActivationKey(st.machine_fingerprint);
  await activateLicenseViaApi(request, key);
}

export async function startDemoJob(request: APIRequestContext): Promise<string> {
  const res = await request.post("/api/jobs/convert", { data: { mode: "demo" } });
  if (!res.ok()) throw new Error(`demo job failed: ${res.status()} ${await res.text()}`);
  const body = await res.json();
  return body.job_id as string;
}

export async function answerDemoJobPrompt(
  request: APIRequestContext,
  jobId: string,
  answer = "Proyecto A",
): Promise<void> {
  for (let i = 0; i < 40; i++) {
    const res = await request.get(`/api/jobs/${jobId}`);
    const job = await res.json();
    if (job.state === "done") return;
    const prompt = job.active_prompt;
    if (prompt?.prompt_id) {
      await request.post(`/api/jobs/${jobId}/prompts/${prompt.prompt_id}/response`, {
        data: { answer },
      });
    }
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error(`demo job ${jobId} did not finish`);
}
