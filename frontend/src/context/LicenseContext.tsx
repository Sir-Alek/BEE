import React, { createContext, useContext } from "react";
import type { LicenseState } from "../app/licenseUtils";

export type LicenseContextValue = {
  license: LicenseState | null;
  licenseLoading: boolean;
  setLicense: React.Dispatch<React.SetStateAction<LicenseState | null>>;
  activationKey: string;
  setActivationKey: React.Dispatch<React.SetStateAction<string>>;
  licenseActivateMsg: string | null;
  setLicenseActivateMsg: React.Dispatch<React.SetStateAction<string | null>>;
  fpCopyAck: boolean;
  setFpCopyAck: React.Dispatch<React.SetStateAction<boolean>>;
  licenseFpVisible: boolean;
  setLicenseFpVisible: React.Dispatch<React.SetStateAction<boolean>>;
  canRunJobs: boolean;
  refreshLicense: () => Promise<void>;
};

const LicenseContext = createContext<LicenseContextValue | null>(null);

export function LicenseProvider(props: { value: LicenseContextValue; children: React.ReactNode }) {
  return <LicenseContext.Provider value={props.value}>{props.children}</LicenseContext.Provider>;
}

export function useLicenseContext(): LicenseContextValue {
  const ctx = useContext(LicenseContext);
  if (!ctx) throw new Error("useLicenseContext must be used within LicenseProvider");
  return ctx;
}
