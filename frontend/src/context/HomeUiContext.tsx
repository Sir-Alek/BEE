import React, { createContext, useContext } from "react";
import type { AiCapabilitiesResponse } from "../api";
import type { LicenseState } from "../app/licenseUtils";
import type { ConvertJobMode } from "../recording/types";
import type { LoadedDoc, ModulesStatus, RecordingRef, ScenarioRef } from "../types";

export type HomeUiContextValue = {
  c: Record<string, string>;
  dark: boolean;
  initialChecked: boolean;
  homeTab: "ui" | "req";
  setHomeTab: (tab: "ui" | "req") => void;
  homeHint: string | null;
  aiCaps: AiCapabilitiesResponse | null;
  license: LicenseState | null;
  setSettingsOpen: (open: boolean) => void;
  setSettingsTab: (tab: import("../app/settingsTabs").SettingsTabId) => void;
  setLicenseActivateMsg: (msg: string | null) => void;
  canRunJobs: boolean;
  modules: ModulesStatus | null;
  showLockModal: string | null;
  setShowLockModal: (v: string | null) => void;
  showHomeError: (msg: string, opts?: { mobileInline?: boolean }) => void;
  autoLinkToScenario: boolean;
  setAutoLinkToScenario: (v: boolean) => void;
  autoLinkScenarioRef: string;
  setAutoLinkScenarioRef: (v: string) => void;
  availableScenarios: ScenarioRef[];
  startJob: (mode: ConvertJobMode) => void;
  loadedDocs: LoadedDoc[];
  setLoadedDocs: React.Dispatch<React.SetStateAction<LoadedDoc[]>>;
  docDragOver: boolean;
  setDocDragOver: (v: boolean) => void;
  docUploadError: string | null;
  setDocUploadError: React.Dispatch<React.SetStateAction<string | null>>;
  linkRecordings: boolean;
  setLinkRecordings: (v: boolean) => void;
  linkMapping: Record<string, string>;
  setLinkMapping: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  recordingMapping: Record<string, string>;
  setRecordingMapping: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  availableRecordings: RecordingRef[];
  setAvailableScenarios: React.Dispatch<React.SetStateAction<ScenarioRef[]>>;
  setAvailableRecordings: React.Dispatch<React.SetStateAction<RecordingRef[]>>;
};

const HomeUiContext = createContext<HomeUiContextValue | null>(null);

export function HomeUiProvider(props: { value: HomeUiContextValue; children: React.ReactNode }) {
  return <HomeUiContext.Provider value={props.value}>{props.children}</HomeUiContext.Provider>;
}

export function useHomeUiContext(): HomeUiContextValue {
  const ctx = useContext(HomeUiContext);
  if (!ctx) throw new Error("useHomeUiContext must be used within HomeUiProvider");
  return ctx;
}
