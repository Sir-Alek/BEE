/** Utilidades compartidas: descarga y verificación de modelos IA. */
import {
  getAiCapabilities,
  getAiSetupDownloadStatus,
  postAiSetupDownload,
  postAiSetupVerify,
  type AiDownloadStatusResponse,
  type AiSetupDownloadProfile,
} from "../api";

export async function pollAiDownload(
  onProgress: (status: AiDownloadStatusResponse) => void,
  maxAttempts = 360,
  intervalMs = 2000,
): Promise<AiDownloadStatusResponse> {
  let last = await getAiSetupDownloadStatus();
  onProgress(last);
  for (let i = 0; i < maxAttempts; i++) {
    if (last.done || (!last.active && last.errors.length > 0)) break;
    await new Promise((r) => setTimeout(r, intervalMs));
    last = await getAiSetupDownloadStatus();
    onProgress(last);
    if (last.done) break;
  }
  return last;
}

export async function startProfileDownload(profile: AiSetupDownloadProfile = "auto") {
  return postAiSetupDownload(profile);
}

export async function verifyProfileInstall(profile: AiSetupDownloadProfile = "auto") {
  return postAiSetupVerify(profile);
}

export async function refreshAiCapabilitiesAfterSetup() {
  return getAiCapabilities();
}

export function downloadStatusMessage(st: AiDownloadStatusResponse): string {
  if (st.errors.length) return st.errors.join("; ");
  if (st.done && st.completed.length) return `Completado: ${st.completed.join(", ")}`;
  if (st.done) return "Descarga finalizada.";
  if (st.current) return `Descargando ${st.current}…`;
  if (st.active) return "Descarga en curso…";
  return "";
}
