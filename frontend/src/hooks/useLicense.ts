import { useCallback, useEffect, useState } from "react";
import { getLicenseStatus } from "../api";
import { licenseFromApi, type LicenseState } from "../app/licenseUtils";
import { SETTINGS_TABS_WITHOUT_LICENSE, type SettingsTabId } from "../app/settingsTabs";

export type UseLicenseOptions = {
  isHomeSurface: boolean;
  settingsOpen: boolean;
  settingsTab: SettingsTabId;
  setSettingsTab: (tab: SettingsTabId) => void;
};

export function useLicense(options: UseLicenseOptions) {
  const { isHomeSurface, settingsOpen, settingsTab, setSettingsTab } = options;

  const [license, setLicense] = useState<LicenseState | null>(null);
  const [activationKey, setActivationKey] = useState("");
  const [licenseActivateMsg, setLicenseActivateMsg] = useState<string | null>(null);
  const [fpCopyAck, setFpCopyAck] = useState(false);
  const [licenseFpVisible, setLicenseFpVisible] = useState(false);

  const canRunJobs = license?.can_run_jobs ?? false;

  const refreshLicense = useCallback(async () => {
    try {
      const l = await getLicenseStatus();
      setLicense(licenseFromApi(l));
    } catch {
      setLicense(null);
    }
  }, []);

  useEffect(() => {
    if (!isHomeSurface) return;
    void refreshLicense();
  }, [isHomeSurface, refreshLicense]);

  useEffect(() => {
    if (!settingsOpen || !isHomeSurface) return;
    void refreshLicense();
  }, [settingsOpen, isHomeSurface, refreshLicense]);

  useEffect(() => {
    if (!settingsOpen) {
      setLicenseFpVisible(false);
      setFpCopyAck(false);
    }
  }, [settingsOpen]);

  useEffect(() => {
    if (canRunJobs) return;
    if (!SETTINGS_TABS_WITHOUT_LICENSE.includes(settingsTab)) {
      setSettingsTab("license");
    }
  }, [canRunJobs, settingsTab, setSettingsTab]);

  return {
    license,
    setLicense,
    activationKey,
    setActivationKey,
    licenseActivateMsg,
    setLicenseActivateMsg,
    fpCopyAck,
    setFpCopyAck,
    licenseFpVisible,
    setLicenseFpVisible,
    canRunJobs,
    refreshLicense,
  };
}
