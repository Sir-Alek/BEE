import React, { createContext, useContext } from "react";
import type { EliaConnectorProfile } from "../types";

export type ConnectorContextValue = {
  connectorProfiles: EliaConnectorProfile[];
  setConnectorProfiles: React.Dispatch<React.SetStateAction<EliaConnectorProfile[]>>;
  reqConnectorProfileId: string;
  setReqConnectorProfileId: React.Dispatch<React.SetStateAction<string>>;
  settingsProfileId: string;
  setSettingsProfileId: React.Dispatch<React.SetStateAction<string>>;
  settingsTestMsg: string | null;
  setSettingsTestMsg: React.Dispatch<React.SetStateAction<string | null>>;
  settingsSaveMsg: string | null;
  setSettingsSaveMsg: React.Dispatch<React.SetStateAction<string | null>>;
  persistConnectorProfiles: (next: EliaConnectorProfile[]) => Promise<void>;
  duplicateConnectorProfile: () => void;
  deleteConnectorProfile: () => void;
};

const ConnectorContext = createContext<ConnectorContextValue | null>(null);

export function ConnectorProvider(props: { value: ConnectorContextValue; children: React.ReactNode }) {
  return <ConnectorContext.Provider value={props.value}>{props.children}</ConnectorContext.Provider>;
}

export function useConnectorContext(): ConnectorContextValue {
  const ctx = useContext(ConnectorContext);
  if (!ctx) throw new Error("useConnectorContext must be used within ConnectorProvider");
  return ctx;
}
