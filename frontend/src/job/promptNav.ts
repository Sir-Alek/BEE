import { cancelConvertJob, PROMPT_ANSWER_BACK, sendPromptResponse } from "../api";
import { ELIA_UI_BC } from "../app/constants";
import { inferBehaveProjectFromProgress, notifyHomeJobFinished, returnToHomeFromJobTab } from "../app/homeNavigation";

export { returnToHomeFromJobTab, notifyHomeJobFinished, inferBehaveProjectFromProgress };

export function broadcastJobFinished(jobId: string, extra?: { platform?: string; project?: string }) {
  notifyHomeJobFinished({ jobId, platform: extra?.platform, project: extra?.project });
}

export function broadcastJobTabClosed(jobId: string) {
  try {
    const bc = new BroadcastChannel(ELIA_UI_BC);
    bc.postMessage({ type: "elia_job_tab_closed", job_id: jobId });
    bc.close();
  } catch {
    // ignore
  }
}

/** Cancela el job en backend, avisa al inicio y cierra esta pestaña del flujo. */
export async function cancelJobFlow(jobId: string) {
  try {
    await cancelConvertJob(jobId);
  } catch {
    // ignore: la pestaña puede cerrarse igual
  }
  broadcastJobFinished(jobId);
  returnToHomeFromJobTab({ jobId });
}

export async function goBackPrompt(jobId: string, promptId: string) {
  await sendPromptResponse({ jobId, promptId, answer: PROMPT_ANSWER_BACK });
}
