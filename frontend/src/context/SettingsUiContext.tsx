import React, { createContext, useContext } from "react";
import type {
  AiCapabilitiesResponse,
  AiMemoryStatusResponse,
  AppAboutResponse,
} from "../api";
import type { SettingsTabId } from "../app/settingsTabs";
import type { ModulesStatus } from "../types";

export type SettingsUiContextValue = {
  c: Record<string, string>;
  dark: boolean;
  toggleTheme: () => void;
  hudMode: boolean;
  setHudMode: (v: boolean) => void;
  visibleSettingsTabs: { id: SettingsTabId; label: string }[];
  settingsTab: SettingsTabId;
  setSettingsTab: (tab: SettingsTabId) => void;
  aiCaps: AiCapabilitiesResponse | null;
  aiPrefsSaving: boolean;
  setAiPrefsSaving: React.Dispatch<React.SetStateAction<boolean>>;
  setAiCaps: React.Dispatch<React.SetStateAction<AiCapabilitiesResponse | null>>;
  aiMemoryOpen: boolean;
  setAiMemoryOpen: React.Dispatch<React.SetStateAction<boolean>>;
  aiMemoryStatus: AiMemoryStatusResponse | null;
  aiMemoryTeamPassphrase: string;
  setAiMemoryTeamPassphrase: React.Dispatch<React.SetStateAction<string>>;
  aiMemoryImportMode: "merge" | "replace";
  setAiMemoryImportMode: React.Dispatch<React.SetStateAction<"merge" | "replace">>;
  aiMemoryImportFile: File | null;
  setAiMemoryImportFile: React.Dispatch<React.SetStateAction<File | null>>;
  aiMemoryBusy: boolean;
  setAiMemoryBusy: React.Dispatch<React.SetStateAction<boolean>>;
  aiMemoryMsg: string | null;
  setAiMemoryMsg: React.Dispatch<React.SetStateAction<string | null>>;
  refreshAiMemoryStatus: () => Promise<void>;
  setErrorText: React.Dispatch<React.SetStateAction<string | null>>;
  setModules: React.Dispatch<React.SetStateAction<ModulesStatus | null>>;
  aboutInfo: AppAboutResponse | null;
  aboutChangelogOpen: boolean;
  setAboutChangelogOpen: React.Dispatch<React.SetStateAction<boolean>>;
  reopenAiWizard: () => void;
};

const SettingsUiContext = createContext<SettingsUiContextValue | null>(null);

export function SettingsUiProvider(props: { value: SettingsUiContextValue; children: React.ReactNode }) {
  return <SettingsUiContext.Provider value={props.value}>{props.children}</SettingsUiContext.Provider>;
}

export function useSettingsUiContext(): SettingsUiContextValue {
  const ctx = useContext(SettingsUiContext);
  if (!ctx) throw new Error("useSettingsUiContext must be used within SettingsUiProvider");
  return ctx;
}
