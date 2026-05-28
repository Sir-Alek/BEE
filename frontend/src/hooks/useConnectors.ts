import { useCallback, useEffect, useState } from "react";
import { getEliaConnectors, putEliaConnectors } from "../api";
import { ELIA_CONNECTORS_LS_KEY, newConnectorProfile, normalizeConnectorProfile } from "../connectorDefaults";
import type { EliaConnectorProfile } from "../types";

export type UseConnectorsOptions = {
  isHomeSurface: boolean;
};

export function useConnectors(options: UseConnectorsOptions) {
  const { isHomeSurface } = options;

  const [connectorProfiles, setConnectorProfiles] = useState<EliaConnectorProfile[]>([]);
  const [reqConnectorProfileId, setReqConnectorProfileId] = useState("");
  const [settingsProfileId, setSettingsProfileId] = useState("");
  const [settingsTestMsg, setSettingsTestMsg] = useState<string | null>(null);
  const [settingsSaveMsg, setSettingsSaveMsg] = useState<string | null>(null);

  const persistConnectorProfiles = useCallback(async (next: EliaConnectorProfile[]) => {
    const normalized = next.map((p) => normalizeConnectorProfile(p));
    const doc = { version: 2 as const, profiles: normalized };
    try {
      localStorage.setItem(ELIA_CONNECTORS_LS_KEY, JSON.stringify(doc));
    } catch {
      // ignore
    }
    try {
      await putEliaConnectors(doc);
    } catch {
      // guardar local aunque backend falle
    }
  }, []);

  useEffect(() => {
    if (!isHomeSurface) return;
    let alive = true;
    void (async () => {
      let localProfiles: EliaConnectorProfile[] = [];
      try {
        const raw = localStorage.getItem(ELIA_CONNECTORS_LS_KEY);
        if (raw) {
          const p = JSON.parse(raw) as { profiles?: EliaConnectorProfile[] };
          if (Array.isArray(p?.profiles)) localProfiles = p.profiles;
        }
      } catch {
        localProfiles = [];
      }
      try {
        const remote = await getEliaConnectors();
        if (!alive) return;
        const r = remote?.profiles ?? [];
        const use = (r.length ? r : localProfiles).map((p) => normalizeConnectorProfile(p));
        setConnectorProfiles(use);
        const firstId = use[0]?.id ?? "";
        setReqConnectorProfileId((prev) => (prev && use.some((x) => x.id === prev) ? prev : firstId));
        setSettingsProfileId((prev) => (prev && use.some((x) => x.id === prev) ? prev : firstId));
      } catch {
        if (!alive) return;
        setConnectorProfiles(localProfiles.map((p) => normalizeConnectorProfile(p)));
        const firstId = localProfiles[0]?.id ?? "";
        setReqConnectorProfileId((prev) =>
          prev && localProfiles.some((x) => x.id === prev) ? prev : firstId,
        );
        setSettingsProfileId((prev) =>
          prev && localProfiles.some((x) => x.id === prev) ? prev : firstId,
        );
      }
    })();
    return () => {
      alive = false;
    };
  }, [isHomeSurface]);

  const deleteConnectorProfile = useCallback(() => {
    const p = connectorProfiles.find((x) => x.id === settingsProfileId);
    if (!p) return;
    if (!window.confirm(`¿Eliminar el perfil «${p.name}»? Esta acción no se puede deshacer.`)) return;
    const next = connectorProfiles.filter((x) => x.id !== settingsProfileId);
    setConnectorProfiles(next);
    setSettingsProfileId(next[0]?.id ?? "");
    setSettingsTestMsg(null);
    setSettingsSaveMsg(null);
    void persistConnectorProfiles(next);
  }, [connectorProfiles, settingsProfileId, persistConnectorProfiles]);

  const duplicateConnectorProfile = useCallback(() => {
    const p = connectorProfiles.find((x) => x.id === settingsProfileId);
    if (!p) return;
    const np = newConnectorProfile(connectorProfiles.length + 1);
    const copy = normalizeConnectorProfile({
      ...np,
      name: `${p.name} (copia)`,
      jira: { ...p.jira },
      value_edge: { ...p.value_edge },
      git: { ...p.git },
      azure_devops: { ...p.azure_devops },
    });
    const next = [...connectorProfiles, copy];
    setConnectorProfiles(next);
    setSettingsProfileId(copy.id);
    setSettingsTestMsg(null);
    setSettingsSaveMsg(null);
  }, [connectorProfiles, settingsProfileId]);

  const syncSettingsProfileId = useCallback(() => {
    const fallback = reqConnectorProfileId || connectorProfiles[0]?.id || "";
    setSettingsProfileId((prev) =>
      prev && connectorProfiles.some((x) => x.id === prev) ? prev : fallback,
    );
  }, [connectorProfiles, reqConnectorProfileId]);

  return {
    connectorProfiles,
    setConnectorProfiles,
    reqConnectorProfileId,
    setReqConnectorProfileId,
    settingsProfileId,
    setSettingsProfileId,
    settingsTestMsg,
    setSettingsTestMsg,
    settingsSaveMsg,
    setSettingsSaveMsg,
    persistConnectorProfiles,
    duplicateConnectorProfile,
    deleteConnectorProfile,
    syncSettingsProfileId,
  };
}
