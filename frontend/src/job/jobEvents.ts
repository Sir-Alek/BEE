export type JobEvent = {
  type: string;
  ts?: number;
  prompt_id?: string;
  prompt_type?: string;
  message?: string;
  payload?: Record<string, unknown>;
};

const EVENT_LABELS: Record<string, string> = {
  job_started: "Trabajo iniciado",
  job_done: "Trabajo completado",
  job_error: "Error en el trabajo",
  job_cancelled: "Trabajo cancelado",
  prompt_created: "Pregunta al usuario",
  prompt_answered: "Respuesta recibida",
  prompt_dismissed: "Pregunta descartada",
  ai_policy: "Política de IA",
  demo_choice: "Demo",
  legacy_recorder: "Grabación legacy finalizada",
  mobile_recorder: "Grabación móvil finalizada",
  exe_launch_started: "Lanzando ejecutable",
  exe_launch_failed: "No se pudo lanzar el ejecutable",
  window_search_started: "Buscando ventana",
  window_found: "Ventana encontrada",
  window_not_found: "Ventana no encontrada",
  hook_started: "Hook de captura iniciado",
  hook_failed: "Hook de captura no disponible",
  recording_started: "Grabación activa",
  event_captured: "Interacción capturada",
  screen_captured: "Pantalla capturada",
  video_started: "Video iniciado",
  video_failed: "Video no iniciado",
  device_check_ok: "Dispositivo verificado",
  device_check_failed: "Dispositivo no disponible",
  appium_check_ok: "Appium disponible",
  appium_check_failed: "Appium no disponible",
  appium_auto_started: "Appium iniciado por ELIA",
  foreground_app_detected: "App en primer plano detectada",
  session_started: "Sesión Appium iniciada",
  session_failed: "Sesión Appium fallida",
  app_left_foreground: "App salió de primer plano",
  recording_stopped: "Grabación detenida",
};

function formatEventDetail(event: JobEvent): string | null {
  const p = event.payload ?? {};
  if (event.type === "event_captured" && p.count != null) {
    return `${p.count} evento(s)`;
  }
  if (event.type === "screen_captured" && p.count != null) {
    return `${p.count} pantalla(s)`;
  }
  if (event.type === "window_found" && p.window_name) {
    return String(p.window_name);
  }
  if (event.type === "window_not_found" && p.window_name) {
    return String(p.window_name);
  }
  if (event.type === "foreground_app_detected" && p.package) {
    return String(p.package);
  }
  if (event.type === "session_failed" && p.error) {
    return String(p.error).slice(0, 120);
  }
  if (event.type === "job_error" && event.message) {
    return event.message;
  }
  if (event.type === "prompt_created" && event.prompt_type) {
    return event.prompt_type.replaceAll("_", " ");
  }
  return null;
}

export function describeJobEvent(event: JobEvent): { label: string; detail: string | null } {
  return {
    label: EVENT_LABELS[event.type] ?? event.type.replaceAll("_", " "),
    detail: formatEventDetail(event),
  };
}

export function isRecordingTimelineEvent(type: string): boolean {
  return [
    "exe_launch_started",
    "exe_launch_failed",
    "window_search_started",
    "window_found",
    "window_not_found",
    "hook_started",
    "hook_failed",
    "recording_started",
    "event_captured",
    "screen_captured",
    "video_started",
    "video_failed",
    "device_check_ok",
    "device_check_failed",
    "appium_check_ok",
    "appium_check_failed",
    "appium_auto_started",
    "foreground_app_detected",
    "session_started",
    "session_failed",
    "app_left_foreground",
    "recording_stopped",
  ].includes(type);
}
