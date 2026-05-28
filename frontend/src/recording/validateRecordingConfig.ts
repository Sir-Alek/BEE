import { emptyJiraCreds, emptyValueEdgeCreds } from "../connectorDefaults";
import { MANUAL_DEVICE_OPTION } from "../mobileEnvUi";
import type { EliaConnectorProfile } from "../types";
import type {
  ConvertJobMode,
  DocToBddExtras,
  RecordingConfig,
  RecordingValidationContext,
  RecordingValidationResult,
} from "./types";

const ELIA_PROFILE_MODES = new Set<ConvertJobMode>([
  "elia_jira_smoke",
  "elia_value_edge_smoke",
  "elia_gherkin_batch",
]);

export function validateRecordingStart(
  ctx: RecordingValidationContext,
): RecordingValidationResult {
  const { mode, config } = ctx;

  if (mode === "puppeteer_recorder") {
    if (config.platform !== "web") {
      return { ok: false, message: "Configuración web requerida para grabar en navegador." };
    }
    if (!config.url.trim()) {
      return { ok: false, message: "URL requerida para 'Grabar Interacciones'." };
    }
    if (ctx.recorderPreflightOk === false) {
      return {
        ok: false,
        message:
          "Google Chrome es obligatorio para grabar. Instálelo o defina ELIA_CHROME_PATH.",
      };
    }
  }

  if (mode === "mobile_recorder") {
    if (config.platform !== "mobile") {
      return { ok: false, message: "Configuración móvil requerida." };
    }
    const serial = config.deviceId.trim();
    if (!serial || serial === MANUAL_DEVICE_OPTION) {
      return {
        ok: false,
        message:
          config.deviceMode === "emulator"
            ? "Inicia un emulador o selecciona uno visible en adb devices."
            : "Conecta un dispositivo Android o selecciónalo en la lista adb.",
        mobileInline: true,
      };
    }
    if (mode === "mobile_recorder" && config.appSource === "apk" && !config.apkPath.trim()) {
      return {
        ok: false,
        message: "Indica la ruta del APK o cambia a «App instalada».",
        mobileInline: true,
      };
    }
    if (ctx.mobilePreflightOk === false) {
      return {
        ok: false,
        message:
          "Revisa el entorno móvil (adb, Appium, dispositivo) antes de grabar.",
        mobileInline: true,
      };
    }
  }

  if (mode === "legacy_recorder") {
    if (config.platform !== "legacy") {
      return { ok: false, message: "Configuración legacy requerida." };
    }
    if (!config.windowName.trim() && !config.exePath.trim()) {
      return {
        ok: false,
        message:
          "Introduce el nombre de ventana o la ruta del ejecutable para la grabación legacy.",
      };
    }
  }

  if (mode === "doc_to_bdd" && ctx.loadedDocsCount === 0) {
    return {
      ok: false,
      message: "Carga al menos un documento (.docx o .xlsx) antes de convertir.",
    };
  }

  const eliaNeedsProfile =
    mode === "elia_jira_smoke" ||
    mode === "elia_value_edge_smoke" ||
    mode === "elia_gherkin_batch";
  if (eliaNeedsProfile && ctx.connectorProfiles.length === 0) {
    return {
      ok: false,
      message: "Primero crea un perfil de conectores en Configuración (⚙).",
    };
  }
  if (
    (mode === "elia_jira_smoke" || mode === "elia_value_edge_smoke") &&
    !ctx.connectorProfiles.find((x) => x.id === ctx.reqConnectorProfileId)
  ) {
    return {
      ok: false,
      message: "Selecciona un perfil de conectores en la pestaña «Inteligencia de Requerimientos».",
    };
  }

  return { ok: true };
}

export function buildConvertJobBody(params: {
  mode: ConvertJobMode;
  config: RecordingConfig;
  urlValue: string;
  mobilePackageOverride?: { package: string; activity: string };
  docExtras?: DocToBddExtras;
  connectorProfile?: EliaConnectorProfile;
}): Parameters<typeof import("../api").startConvertJob>[0] {
  const { mode, config, urlValue, mobilePackageOverride, docExtras, connectorProfile } = params;

  const linkScenarioByDoc =
    mode === "doc_to_bdd" && docExtras
      ? Object.fromEntries(Object.entries(docExtras.linkMapping).filter(([, v]) => v))
      : undefined;

  let linkedScenario: string | undefined;
  if (mode === "doc_to_bdd" && docExtras) {
    linkedScenario = Object.values(linkScenarioByDoc ?? {})[0];
  } else if (
    docExtras &&
    (mode === "puppeteer_to_behave" ||
      mode === "mobile_to_behave" ||
      mode === "legacy_to_behave") &&
    docExtras.autoLinkToScenario &&
    docExtras.autoLinkScenarioRef
  ) {
    linkedScenario = docExtras.autoLinkScenarioRef;
  }

  const linkRecordingByDoc =
    mode === "doc_to_bdd" && docExtras?.linkRecordings
      ? Object.fromEntries(Object.entries(docExtras.recordingMapping).filter(([, v]) => v))
      : undefined;

  const pkgForJob =
    mobilePackageOverride?.package ??
    (config.platform === "mobile" ? config.appPackage : "");
  const actForJob =
    mobilePackageOverride?.activity ??
    (config.platform === "mobile" ? config.appActivity : "");

  return {
    mode,
    url: mode === "puppeteer_recorder" ? urlValue.trim() : undefined,
    ...(ELIA_PROFILE_MODES.has(mode)
      ? {
          elia_use_inline_connectors: true,
          elia_jira: connectorProfile?.jira ?? emptyJiraCreds(),
          elia_value_edge: connectorProfile?.value_edge ?? emptyValueEdgeCreds(),
        }
      : {}),
    ...(mode === "mobile_recorder" && config.platform === "mobile"
      ? {
          platform: "mobile",
          apk_path: config.appSource === "apk" ? config.apkPath.trim() : "",
          device_id: config.deviceId.trim(),
          app_package: config.appSource === "installed" ? pkgForJob.trim() : "",
          app_activity: config.appSource === "installed" ? actForJob.trim() : "",
        }
      : {}),
    ...(mode === "legacy_recorder" && config.platform === "legacy"
      ? {
          platform: "legacy",
          window_name: config.windowName.trim(),
          exe_path: config.exePath.trim(),
        }
      : {}),
    ...(mode === "doc_to_bdd" && docExtras
      ? {
          doc_files: docExtras.loadedDocs.map((d) => d.path),
          ...(linkScenarioByDoc && Object.keys(linkScenarioByDoc).length
            ? { link_scenario_by_doc: linkScenarioByDoc }
            : {}),
          ...(linkRecordingByDoc && Object.keys(linkRecordingByDoc).length
            ? { link_recording_by_doc: linkRecordingByDoc }
            : {}),
        }
      : {}),
    ...(linkedScenario != null ? { link_scenario: linkedScenario } : {}),
  };
}
