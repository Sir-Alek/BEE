import { useCallback, useEffect, useRef } from "react";

export type ApiSurfaceTab = "postman" | "load";

export type ApiSurfacePersistedFields = {
  url: string;
  preRequestScript: string;
  postRequestScript: string;
  apiTab: ApiSurfaceTab;
};

type PersistStore = {
  project: string;
  byProject: Record<string, ApiSurfacePersistedFields>;
};

const STORAGE_KEY = "elia.api.surface.v1";

const DEFAULT_FIELDS: ApiSurfacePersistedFields = {
  url: "{{base_url}}/recurso",
  preRequestScript: "",
  postRequestScript: "",
  apiTab: "postman",
};

function readStore(): PersistStore {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return { project: "DefaultApi", byProject: {} };
    const parsed = JSON.parse(raw) as Partial<PersistStore>;
    return {
      project: typeof parsed.project === "string" ? parsed.project : "DefaultApi",
      byProject: parsed.byProject && typeof parsed.byProject === "object" ? parsed.byProject : {},
    };
  } catch {
    return { project: "DefaultApi", byProject: {} };
  }
}

function writeStore(store: PersistStore) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  } catch {
    /* quota / private mode */
  }
}

export function loadApiSurfacePersist(project: string): ApiSurfacePersistedFields {
  const store = readStore();
  return { ...DEFAULT_FIELDS, ...(store.byProject[project] || {}) };
}

export function loadApiSurfacePersistProject(): string | null {
  const store = readStore();
  return store.project || null;
}

export function useApiSurfacePersist(
  project: string,
  fields: ApiSurfacePersistedFields,
  onRestore: (fields: ApiSurfacePersistedFields) => void,
) {
  const hydratedProject = useRef<string | null>(null);
  const skipNextSave = useRef(false);

  useEffect(() => {
    if (hydratedProject.current === project) return;
    hydratedProject.current = project;
    skipNextSave.current = true;
    onRestore(loadApiSurfacePersist(project));
  }, [project, onRestore]);

  const persist = useCallback(() => {
    const store = readStore();
    store.project = project;
    store.byProject[project] = { ...fields };
    writeStore(store);
  }, [project, fields]);

  useEffect(() => {
    if (skipNextSave.current) {
      skipNextSave.current = false;
      return;
    }
    persist();
  }, [persist]);
}
