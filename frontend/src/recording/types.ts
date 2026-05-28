import type { EliaConnectorProfile, LoadedDoc } from "../types";

export type RecordingPlatform = "web" | "mobile" | "legacy";

export type WebRecordingConfig = {
  platform: "web";
  url: string;
};

export type MobileRecordingConfig = {
  platform: "mobile";
  deviceId: string;
  deviceMode: "physical" | "emulator";
  appSource: "installed" | "apk";
  apkPath: string;
  appPackage: string;
  appActivity: string;
};

export type LegacyRecordingConfig = {
  platform: "legacy";
  windowName: string;
  exePath: string;
};

export type RecordingConfig = WebRecordingConfig | MobileRecordingConfig | LegacyRecordingConfig;

export type ConvertJobMode =
  | "puppeteer_recorder"
  | "puppeteer_to_behave"
  | "puppeteer_to_step_by_step"
  | "mobile_recorder"
  | "legacy_recorder"
  | "mobile_to_behave"
  | "legacy_to_behave"
  | "doc_to_bdd"
  | "elia_jira_smoke"
  | "elia_value_edge_smoke"
  | "elia_gherkin_batch";

export type RecordingValidationContext = {
  mode: ConvertJobMode;
  config: RecordingConfig;
  recorderPreflightOk: boolean | null;
  mobilePreflightOk: boolean | null;
  loadedDocsCount: number;
  connectorProfiles: EliaConnectorProfile[];
  reqConnectorProfileId: string;
};

export type RecordingValidationResult =
  | { ok: true }
  | { ok: false; message: string; mobileInline?: boolean };

export type DocToBddExtras = {
  loadedDocs: LoadedDoc[];
  linkMapping: Record<string, string>;
  recordingMapping: Record<string, string>;
  linkRecordings: boolean;
  autoLinkToScenario: boolean;
  autoLinkScenarioRef: string | null;
};
