import React, { createContext, useContext } from "react";
import type {
  MobileAppiumStatusResponse,
  MobileDeviceInfo,
  MobilePreflightResponse,
  RecorderPreflightResponse,
} from "../api";

export type RecordingContextValue = {
  platform: "web" | "mobile" | "legacy";
  setPlatform: (p: "web" | "mobile" | "legacy") => void;
  urlValue: string;
  setUrlValue: (v: string) => void;
  windowName: string;
  setWindowName: (v: string) => void;
  exePath: string;
  setExePath: (v: string) => void;
  recorderPreflight: RecorderPreflightResponse | null;
  recorderPreflightLoading: boolean;
  mobilePreflight: MobilePreflightResponse | null;
  mobilePreflightLoading: boolean;
  mobileEnvOpen: boolean;
  setMobileEnvOpen: (v: boolean) => void;
  appiumStatus: MobileAppiumStatusResponse | null;
  appiumStarting: boolean;
  handleStartAppium: () => void;
  refreshAppiumStatus: () => Promise<void>;
  refreshMobilePreflight: () => Promise<void>;
  deviceMode: "physical" | "emulator";
  setDeviceMode: (m: "physical" | "emulator") => void;
  deviceId: string;
  setDeviceId: (v: string) => void;
  mobileDevices: MobileDeviceInfo[];
  mobileDevicesLoading: boolean;
  mobileDevicesError: string | null;
  refreshMobileDevices: () => Promise<void>;
  mobileAvds: string[];
  mobileAvdsLoading: boolean;
  mobileAvdsError: string | null;
  selectedAvd: string;
  setSelectedAvd: (v: string) => void;
  refreshMobileAvds: () => Promise<void>;
  emulatorStarting: boolean;
  handleStartEmulator: () => void;
  emulatorMessage: string | null;
  mobileFieldError: string | null;
  setMobileFieldError: (v: string | null) => void;
  appPackage: string;
  setAppPackage: (v: string) => void;
  appActivity: string;
  setAppActivity: (v: string) => void;
  apkPath: string;
  setApkPath: (v: string) => void;
  detectingForegroundApp: boolean;
  detectForegroundApp: () => Promise<{ package: string; activity: string } | null>;
  captureApiTraffic: boolean;
  setCaptureApiTraffic: (v: boolean) => void;
};

const RecordingContext = createContext<RecordingContextValue | null>(null);

export function RecordingProvider(props: { value: RecordingContextValue; children: React.ReactNode }) {
  return <RecordingContext.Provider value={props.value}>{props.children}</RecordingContext.Provider>;
}

export function useRecordingContext(): RecordingContextValue {
  const ctx = useContext(RecordingContext);
  if (!ctx) throw new Error("useRecordingContext must be used within RecordingProvider");
  return ctx;
}
