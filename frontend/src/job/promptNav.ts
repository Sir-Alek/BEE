import { cancelConvertJob, PROMPT_ANSWER_BACK, sendPromptResponse } from "../api";
import { ELIA_UI_BC } from "../app/constants";
import { tryFocusOpenerAndCloseThisTab } from "../app/utils";

export function broadcastJobFinished(jobId: string) {
  try {
    const bc = new BroadcastChannel(ELIA_UI_BC);
    bc.postMessage({ type: "elia_job_finished", job_id: jobId });
    bc.close();
  } catch {
    // ignore
  }
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
  tryFocusOpenerAndCloseThisTab();
}

export async function goBackPrompt(jobId: string, promptId: string) {
  await sendPromptResponse({ jobId, promptId, answer: PROMPT_ANSWER_BACK });
}
